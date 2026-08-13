import io
import json
import threading
from functools import lru_cache

import fiona
import geopandas as gpd
import pandas as pd
from django.http import HttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from api.csv_utils import read_uploaded_csv
from api.session_manager import SessionManager
from config import Config
from engines.grid_engine import FastGridEngine

# ── Extra-country helpers ──────────────────────────────────────────────────────

# Files that are handled natively — never listed as "extra" countries
_NATIVE_FILES = {'NUTS_RG_01M_2021_4326.geojson', 'alb_admbnda_adm2_2019c.shp'}

def _extra_country_dir():
    return Config.BASE_DIR / "data" / "Country_Region_Data"

def _best_name_column(gdf):
    """Return the most suitable human-readable name column from a GeoDataFrame."""
    for col in ('ADMIN', 'NAME_EN', 'NAME', 'ADM0_EN', 'ADM0_NAME', 'COUNTRY',
                'name', 'NAME_LATN', 'NAME_0', 'SOVEREIGNT', 'name_en', 'Name'):
        if col in gdf.columns:
            return col
    for col in gdf.columns:
        if col != 'geometry' and gdf[col].dtype == object:
            return col
    return None

def _read_extra_file(path):
    """Read a shapefile/geojson tolerantly (recreate missing SHX if needed)."""
    with fiona.Env(SHAPE_RESTORE_SHX='YES'):
        try:
            return gpd.read_file(str(path), engine='fiona')
        except Exception:
            return gpd.read_file(str(path))

def _extra_country_names():
    """
    Return a dict {display_name: (path, row_filter_value, name_col)} for every
    feature found in Country_Region_Data that is not a native file.
    """
    d = _extra_country_dir()
    if not d.exists():
        return {}
    result = {}
    for ext in ('*.shp', '*.geojson'):
        for p in sorted(d.glob(ext)):
            if p.name in _NATIVE_FILES:
                continue
            try:
                gdf = _read_extra_file(p)
                name_col = _best_name_column(gdf)
                if name_col:
                    for val in gdf[name_col].dropna().unique():
                        result[str(val)] = (p, str(val), name_col)
                else:
                    # No name column — use the file stem as the country name
                    result[p.stem] = (p, None, None)
            except Exception:
                continue
    return result

def _load_extra_boundary(country_name):
    """
    Return a GeoDataFrame for *country_name* from the extra files, or None.
    The returned GDF is already in its native CRS (will be re-projected downstream).
    """
    names = _extra_country_names()
    if country_name not in names:
        return None
    path, filter_val, name_col = names[country_name]
    gdf = _read_extra_file(path)
    if name_col and filter_val is not None:
        sub = gdf[gdf[name_col] == filter_val]
        return sub if not sub.empty else gdf
    return gdf


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


@lru_cache(maxsize=1)
def _load_albania_adm_data():
    """Load and cache Albania administrative boundaries (ADM1 = Region, ADM2 = District)."""
    return gpd.read_file(str(Config.ALBANIA_ADM_PATH))


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
    try:
        _load_albania_adm_data()
    except Exception:
        pass

threading.Thread(target=_warmup_geo_cache, daemon=True).start()


class CountryListView(APIView):
    def get(self, request):
        try:
            nuts = _load_nuts_data()
            nuts_names = set(nuts['NAME_EN'].dropna().unique().tolist())
            extra_names = set(_extra_country_names().keys()) - nuts_names
            countries = sorted(nuts_names | extra_names)
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


class AlbaniaRegionsView(APIView):
    """Return sorted list of Albania ADM1 regions."""
    def get(self, request):
        try:
            gdf = _load_albania_adm_data()
            regions = sorted(gdf['ADM1_EN'].dropna().unique().tolist())
            return Response({'regions': regions})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AlbaniaDistrictsView(APIView):
    """Return sorted list of Albania ADM2 districts, optionally filtered by region."""
    def get(self, request):
        try:
            gdf = _load_albania_adm_data()
            region = request.query_params.get('region')
            if region:
                gdf = gdf[gdf['ADM1_EN'] == region]
            districts = sorted(gdf['ADM2_EN'].dropna().unique().tolist())
            return Response({'districts': districts})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CountryBoundaryView(APIView):
    """Return simplified GeoJSON boundary for a country, EEZ zone, or Albania region/district."""
    def get(self, request):
        country = request.query_params.get('country')
        zone = request.query_params.get('zone')
        adm1 = request.query_params.get('adm1')
        adm2 = request.query_params.get('adm2')
        try:
            if adm2:
                # Albania district boundary
                gdf = _load_albania_adm_data()
                gdf = gdf[gdf['ADM2_EN'] == adm2]
                if gdf.empty:
                    return Response({'error': f'District "{adm2}" not found.'}, status=status.HTTP_404_NOT_FOUND)
            elif adm1:
                # Albania region boundary (union of all districts in that region)
                gdf = _load_albania_adm_data()
                gdf = gdf[gdf['ADM1_EN'] == adm1]
                if gdf.empty:
                    return Response({'error': f'Region "{adm1}" not found.'}, status=status.HTTP_404_NOT_FOUND)
                # Dissolve into a single polygon
                gdf = gdf.dissolve().reset_index(drop=True)
            elif country:
                nuts = _load_nuts_data()
                gdf = nuts[nuts['NAME_EN'] == country]
                if gdf.empty:
                    # Fall back to extra-file countries (e.g. syr_admin0.shp)
                    gdf = _load_extra_boundary(country)
                    if gdf is None or gdf.empty:
                        return Response({'error': 'Country not found.'}, status=status.HTTP_404_NOT_FOUND)
            elif zone:
                eez = _load_eez_data()
                gdf = eez[eez['GEONAME'] == zone]
                if gdf.empty:
                    return Response({'error': 'EEZ zone not found.'}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({'error': 'Provide country, zone, adm1, or adm2.'}, status=status.HTTP_400_BAD_REQUEST)

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

                # Albania sub-national: check for adm2_district first, then adm1_region
                adm2_district = request.data.get('adm2_district')
                adm1_region = request.data.get('adm1_region')

                if adm2_district:
                    alb = _load_albania_adm_data()
                    boundary_gdf = alb[alb['ADM2_EN'] == adm2_district]
                    if boundary_gdf.empty:
                        return Response({'error': f'District "{adm2_district}" not found.'}, status=status.HTTP_404_NOT_FOUND)
                elif adm1_region:
                    alb = _load_albania_adm_data()
                    tmp = alb[alb['ADM1_EN'] == adm1_region]
                    if tmp.empty:
                        return Response({'error': f'Region "{adm1_region}" not found.'}, status=status.HTTP_404_NOT_FOUND)
                    boundary_gdf = tmp.dissolve().reset_index(drop=True)
                else:
                    nuts = _load_nuts_data()
                    boundary_gdf = nuts[nuts['NAME_EN'] == country_name]
                    if boundary_gdf.empty:
                        # Fall back to extra-file countries (e.g. syr_admin0.shp)
                        boundary_gdf = _load_extra_boundary(country_name)
                        if boundary_gdf is None or boundary_gdf.empty:
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

            # Compute true grid origin from actual cell data (min left / min bottom)
            grid_origin_x = float(grid_df['left'].min()) if 'left' in grid_df.columns else None
            grid_origin_y = float(grid_df['bottom'].min()) if 'bottom' in grid_df.columns else None

            session_update: dict = dict(
                grid_created=True,
                grid_size_x=grid_size_x,
                grid_size_y=grid_size_y,
            )
            if grid_origin_x is not None:
                session_update['grid_origin_x'] = grid_origin_x
                session_update['grid_origin_y'] = grid_origin_y
            SessionManager.update_session(request.session_id, **session_update)

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
            grid_df, delimiter = read_uploaded_csv(csv_file)

            required_cols = ['cell_id', 'wkt']
            missing = [c for c in required_cols if c not in grid_df.columns]
            if missing:
                return Response({'error': f'Missing columns: {missing}'}, status=status.HTTP_400_BAD_REQUEST)

            # Build boundary_gdf + grid dimensions from WKT cells
            import shapely
            from shapely.geometry import GeometryCollection

            grid_size_x = 0.0
            grid_size_y = 0.0
            batch_hulls = []
            first_geometry = None
            chunk_size = 10_000

            for start in range(0, len(grid_df), chunk_size):
                values = [
                    str(value).strip()
                    for value in grid_df['wkt'].iloc[start:start + chunk_size].dropna()
                    if str(value).strip()
                ]
                if not values:
                    continue

                try:
                    geometries = shapely.from_wkt(values)
                except shapely.errors.GEOSException as exc:
                    raise ValueError(
                        f'Invalid WKT geometry near CSV row {start + 2}: {exc}'
                    ) from exc

                if first_geometry is None:
                    first_geometry = geometries[0]
                batch_hulls.append(GeometryCollection(geometries.tolist()).convex_hull)

            if batch_hulls:
                # Convex hulls can be combined without the expensive union of every cell.
                boundary_geom = GeometryCollection(batch_hulls).convex_hull
                # WKT cells are in EPSG:3857 (grid engine output)
                boundary_gdf = gpd.GeoDataFrame(geometry=[boundary_geom], crs='EPSG:3857')
                SessionManager.save_dataframe(request.session_id, 'boundary_gdf', boundary_gdf)

                # Estimate grid cell dimensions from the first cell's bounding box
                first_bounds = first_geometry.bounds  # (minx, miny, maxx, maxy)
                grid_size_x = first_bounds[2] - first_bounds[0]
                grid_size_y = first_bounds[3] - first_bounds[1]

            # Compute true grid origin from actual cell data (min left / min bottom)
            grid_origin_x = float(grid_df['left'].min()) if 'left' in grid_df.columns else None
            grid_origin_y = float(grid_df['bottom'].min()) if 'bottom' in grid_df.columns else None

            SessionManager.save_dataframe(request.session_id, 'grid_df', grid_df)
            session_update: dict = dict(
                grid_created=True,
                grid_size_x=grid_size_x,
                grid_size_y=grid_size_y,
            )
            if grid_origin_x is not None:
                session_update['grid_origin_x'] = grid_origin_x
                session_update['grid_origin_y'] = grid_origin_y
            SessionManager.update_session(request.session_id, **session_update)

            return Response({
                'message': f'Grid loaded: {len(grid_df):,} cells',
                'total_cells': len(grid_df),
                'columns': grid_df.columns.tolist(),
                'preview': grid_df.head(50).to_dict(orient='records'),
                'delimiter': delimiter,
            })
        except (UnicodeError, pd.errors.ParserError, ValueError) as e:
            return Response({'error': f'Invalid CSV: {e}'}, status=status.HTTP_400_BAD_REQUEST)
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

        slice_df = grid_df.iloc[start:end].copy()
        # Replace NaN/Inf with None so JSON serialisation never breaks
        import numpy as np
        slice_df = slice_df.replace([np.inf, -np.inf], None)
        slice_df = slice_df.where(slice_df.notna(), None)

        return Response({
            'total': len(grid_df),
            'page': page,
            'page_size': page_size,
            'columns': grid_df.columns.tolist(),
            'data': slice_df.to_dict(orient='records'),
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
