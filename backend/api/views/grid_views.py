import io
import json
import threading
from functools import lru_cache

import geopandas as gpd
import pandas as pd
from django.http import HttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from api.session_manager import SessionManager
from config import Config
from engines.grid_engine import FastGridEngine


@lru_cache(maxsize=1)
def _load_nuts_data():
    """Load and cache NUTS country boundaries."""
    gdf = gpd.read_file(str(Config.NUTS_PATH))
    countries_only = gdf[gdf['LEVL_CODE'] == 0].copy()

    nuts_mapping = {
        'AL': 'Albania', 'AT': 'Austria', 'BE': 'Belgium', 'BG': 'Bulgaria',
        'CH': 'Switzerland', 'CY': 'Cyprus', 'CZ': 'Czechia', 'DE': 'Germany',
        'DK': 'Denmark', 'EE': 'Estonia', 'EL': 'Greece', 'ES': 'Spain',
        'FI': 'Finland', 'FR': 'France', 'HR': 'Croatia', 'HU': 'Hungary',
        'IE': 'Ireland', 'IS': 'Iceland', 'IT': 'Italy', 'LI': 'Liechtenstein',
        'LT': 'Lithuania', 'LU': 'Luxembourg', 'LV': 'Latvia', 'ME': 'Montenegro',
        'MK': 'North Macedonia', 'MT': 'Malta', 'NL': 'Netherlands', 'NO': 'Norway',
        'PL': 'Poland', 'PT': 'Portugal', 'RO': 'Romania', 'RS': 'Serbia',
        'SE': 'Sweden', 'SI': 'Slovenia', 'SK': 'Slovakia', 'TR': 'Turkey',
        'UK': 'United Kingdom', 'XK': 'Kosovo',
    }

    if 'CNTR_CODE' in countries_only.columns:
        countries_only['NAME_EN'] = countries_only['CNTR_CODE'].map(nuts_mapping)
        countries_only['NAME_EN'] = countries_only['NAME_EN'].fillna(
            countries_only.get('NAME_LATN', countries_only.index.astype(str))
        )
    else:
        countries_only['NAME_EN'] = countries_only.get(
            'NAME_LATN', countries_only.index.astype(str)
        )
    return countries_only


@lru_cache(maxsize=1)
def _load_eez_data():
    """Load and cache EEZ zone boundaries."""
    return gpd.read_file(str(Config.EEZ_PATH))


# Warm up geo-data caches in a background thread so the first request is instant
def _warmup_geo_cache():
    try:
        _load_nuts_data()
    except Exception:
        pass
    try:
        _load_eez_data()
    except Exception:
        pass

threading.Thread(target=_warmup_geo_cache, daemon=True).start()


class CountryListView(APIView):
    def get(self, request):
        try:
            nuts = _load_nuts_data()
            countries = sorted(nuts['NAME_EN'].dropna().unique().tolist())
            return Response({'countries': countries})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EEZZoneListView(APIView):
    def get(self, request):
        try:
            eez = _load_eez_data()
            zones = sorted(eez['GEONAME'].dropna().unique().tolist())
            return Response({'zones': zones})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CountryBoundaryView(APIView):
    """Return simplified GeoJSON boundary for a country or EEZ zone."""
    def get(self, request):
        country = request.query_params.get('country')
        zone = request.query_params.get('zone')
        try:
            if country:
                nuts = _load_nuts_data()
                gdf = nuts[nuts['NAME_EN'] == country]
                if gdf.empty:
                    return Response({'error': 'Country not found.'}, status=status.HTTP_404_NOT_FOUND)
            elif zone:
                eez = _load_eez_data()
                gdf = eez[eez['GEONAME'] == zone]
                if gdf.empty:
                    return Response({'error': 'EEZ zone not found.'}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({'error': 'Provide country or zone.'}, status=status.HTTP_400_BAD_REQUEST)

            # Simplify geometry to reduce payload (tolerance in degrees ≈ ~500m)
            simplified = gdf.copy()
            simplified['geometry'] = simplified['geometry'].simplify(0.005, preserve_topology=True)
            geojson = json.loads(simplified.to_crs(epsg=4326).to_json())
            # Compute bounds [south, west, north, east]
            bounds = simplified.to_crs(epsg=4326).total_bounds  # [xmin, ymin, xmax, ymax]
            return Response({
                'geojson': geojson,
                'bounds': [[bounds[1], bounds[0]], [bounds[3], bounds[2]]],  # [[south,west],[north,east]]
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateGridView(APIView):
    def post(self, request):
        session = SessionManager.get_session(request.session_id)
        if not session['project_type']:
            return Response({'error': 'No project selected.'}, status=status.HTTP_400_BAD_REQUEST)

        boundary_method = request.data.get('boundary_method', 'country')
        grid_size_x = float(request.data.get('grid_size_x', Config.DEFAULT_GRID_SIZE_X))
        grid_size_y = float(request.data.get('grid_size_y', Config.DEFAULT_GRID_SIZE_Y))

        try:
            boundary_gdf = None

            if boundary_method == 'country':
                country_name = request.data.get('country_name')
                if not country_name:
                    return Response({'error': 'Country name is required.'}, status=status.HTTP_400_BAD_REQUEST)
                nuts = _load_nuts_data()
                boundary_gdf = nuts[nuts['NAME_EN'] == country_name]
                if boundary_gdf.empty:
                    return Response({'error': f'Country "{country_name}" not found.'}, status=status.HTTP_404_NOT_FOUND)

            elif boundary_method == 'eez':
                zone_name = request.data.get('zone_name')
                if not zone_name:
                    return Response({'error': 'EEZ zone name is required.'}, status=status.HTTP_400_BAD_REQUEST)
                eez = _load_eez_data()
                boundary_gdf = eez[eez['GEONAME'] == zone_name]
                if boundary_gdf.empty:
                    return Response({'error': f'EEZ zone "{zone_name}" not found.'}, status=status.HTTP_404_NOT_FOUND)

            elif boundary_method == 'file':
                boundary_file = request.FILES.get('boundary_file')
                if not boundary_file:
                    return Response({'error': 'Boundary file is required.'}, status=status.HTTP_400_BAD_REQUEST)
                content = boundary_file.read()
                boundary_gdf = gpd.read_file(io.BytesIO(content))

            else:
                return Response({'error': 'Invalid boundary_method.'}, status=status.HTTP_400_BAD_REQUEST)

            engine = FastGridEngine(boundary_gdf)
            grid_df = engine.create_rectangular_grid(dx=grid_size_x, dy=grid_size_y)

            SessionManager.save_dataframe(request.session_id, 'grid_df', grid_df)
            SessionManager.save_dataframe(request.session_id, 'boundary_gdf', gpd.GeoDataFrame(boundary_gdf))
            SessionManager.update_session(request.session_id, grid_created=True)

            preview = grid_df.head(50).to_dict(orient='records')

            return Response({
                'message': f'Grid created: {len(grid_df):,} cells',
                'total_cells': len(grid_df),
                'columns': grid_df.columns.tolist(),
                'preview': preview,
            })

        except Exception as e:
            import traceback
            return Response(
                {'error': str(e), 'traceback': traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UploadGridView(APIView):
    def post(self, request):
        csv_file = request.FILES.get('grid_file')
        if not csv_file:
            return Response({'error': 'CSV file is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            content = csv_file.read().decode('utf-8')
            grid_df = pd.read_csv(io.StringIO(content))

            required_cols = ['cell_id', 'wkt']
            missing = [c for c in required_cols if c not in grid_df.columns]
            if missing:
                return Response({'error': f'Missing columns: {missing}'}, status=status.HTTP_400_BAD_REQUEST)

            SessionManager.save_dataframe(request.session_id, 'grid_df', grid_df)
            SessionManager.update_session(request.session_id, grid_created=True)

            return Response({
                'message': f'Grid loaded: {len(grid_df):,} cells',
                'total_cells': len(grid_df),
                'columns': grid_df.columns.tolist(),
                'preview': grid_df.head(50).to_dict(orient='records'),
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GridDataView(APIView):
    def get(self, request):
        session = SessionManager.get_session(request.session_id)
        if not session['grid_created']:
            return Response({'error': 'No grid available.'}, status=status.HTTP_404_NOT_FOUND)

        grid_df = SessionManager.load_dataframe(request.session_id, 'grid_df')
        if grid_df is None:
            return Response({'error': 'Grid data not found.'}, status=status.HTTP_404_NOT_FOUND)

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 100))
        start = (page - 1) * page_size
        end = start + page_size

        return Response({
            'total': len(grid_df),
            'page': page,
            'page_size': page_size,
            'columns': grid_df.columns.tolist(),
            'data': grid_df.iloc[start:end].to_dict(orient='records'),
        })


class GridDownloadView(APIView):
    def get(self, request):
        grid_df = SessionManager.load_dataframe(request.session_id, 'grid_df')
        if grid_df is None:
            return Response({'error': 'No grid available.'}, status=status.HTTP_404_NOT_FOUND)

        csv_data = grid_df.to_csv(index=False)
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="grid.csv"'
        return response
