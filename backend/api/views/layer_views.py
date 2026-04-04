import os

import geopandas as gpd
import numpy as np
import pandas as pd
from django.http import HttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from shapely import wkt

from api.session_manager import SessionManager
from api.task_manager import create_task, get_task
from engines.raster_scorer import UniversalRasterScorer
from config import Config


class LayerListView(APIView):
    def get(self, request):
        session = SessionManager.get_session(request.session_id)
        return Response({'layers': session['layer_configs']})


class AddLayerView(APIView):
    def post(self, request):
        session = SessionManager.get_session(request.session_id)

        layer_name = request.data.get('layer_name')
        raster_path = request.data.get('raster_path')
        analysis_modes = request.data.get('analysis_modes', ['distance'])
        target_value = int(request.data.get('target_value', 1))
        is_predefined = request.data.get('is_predefined', False)

        if not layer_name or not raster_path:
            return Response(
                {'error': 'layer_name and raster_path are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not os.path.isfile(raster_path):
            return Response(
                {'error': f'Raster file not found: {raster_path}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── File Size Validation: reject files larger than 10 GB ──
        _MAX_FILE_SIZE_BYTES = 10 * 1024 ** 3  # 10 GB
        _file_size = os.path.getsize(raster_path)
        if _file_size > _MAX_FILE_SIZE_BYTES:
            _size_gb = _file_size / (1024 ** 3)
            return Response(
                {'error': f'⚠️ File Size Error: This raster is {_size_gb:.2f} GB, '
                          f'which exceeds the maximum allowed size of 10 GB. '
                          f'Please crop or resample the raster to a smaller extent and try again.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── CRS Validation: only EPSG:3857 (Web Mercator) rasters accepted ──
        import rasterio as _rio
        try:
            with _rio.open(raster_path) as _src:
                _crs = _src.crs
                if _crs is None:
                    return Response(
                        {'error': '⚠️ CRS Error: This raster has no CRS metadata. '
                                  'Only EPSG:3857 (Web Mercator) rasters are supported. '
                                  'Please assign or reproject the CRS in QGIS and try again.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                _epsg = _crs.to_epsg()
                if _epsg != 3857:
                    return Response(
                        {'error': f'⚠️ CRS Error: Unsupported projection ({_crs}, EPSG:{_epsg}). '
                                  f'Only EPSG:3857 (Web Mercator) rasters are supported. '
                                  f'Please reproject your raster to EPSG:3857 in QGIS and try again.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except Exception as _e:
            if '⚠️ CRS Error' in str(_e):
                raise
            return Response(
                {'error': f'Could not read raster file: {_e}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_names = [c['prefix'] for c in session['layer_configs']]
        if layer_name in existing_names:
            return Response(
                {'error': f'Layer "{layer_name}" already exists.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        layer_config = {
            'path': raster_path,
            'prefix': layer_name,
            'analysis_modes': analysis_modes,
            'target_value': target_value,
            'config': {},
            'is_predefined': is_predefined,
        }

        configs = session['layer_configs']
        configs.append(layer_config)
        SessionManager.update_session(request.session_id, layer_configs=configs)

        return Response({'message': f'Layer "{layer_name}" added.', 'layers': configs})


class RemoveLayerView(APIView):
    def delete(self, request, index):
        session = SessionManager.get_session(request.session_id)
        configs = session['layer_configs']

        if index < 0 or index >= len(configs):
            return Response({'error': 'Invalid layer index.'}, status=status.HTTP_400_BAD_REQUEST)

        removed = configs.pop(index)
        SessionManager.update_session(request.session_id, layer_configs=configs)

        return Response({'message': f'Layer "{removed["prefix"]}" removed.', 'layers': configs})


class RasterFilesView(APIView):
    def get(self, request):
        directory = request.query_params.get('directory', str(Config.DATA_DIR))

        if not os.path.isdir(directory):
            return Response({'error': 'Invalid directory path.'}, status=status.HTTP_400_BAD_REQUEST)

        files = sorted(f for f in os.listdir(directory) if f.lower().endswith(('.tif', '.tiff')))
        return Response({'directory': directory, 'files': files})


class UploadRasterFileView(APIView):
    """Upload a .tif file; save it under DATA_DIR and return the saved path."""

    def post(self, request):
        f = request.FILES.get('raster_file')
        if not f:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)
        if not f.name.lower().endswith(('.tif', '.tiff')):
            return Response({'error': 'Only .tif / .tiff files are accepted.'}, status=status.HTTP_400_BAD_REQUEST)

        dest_dir = Config.DATA_DIR
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(str(dest_dir), f.name)

        # Stream write with larger buffer for large files
        with open(dest_path, 'wb') as out:
            for chunk in f.chunks(chunk_size=8 * 1024 * 1024):  # 8 MB chunks
                out.write(chunk)

        return Response({'path': dest_path, 'filename': f.name})


class RunAnalysisView(APIView):
    def post(self, request):
        session = SessionManager.get_session(request.session_id)

        if not session['grid_created']:
            return Response({'error': 'Grid not created yet.'}, status=status.HTTP_400_BAD_REQUEST)
        if not session['layer_configs']:
            return Response({'error': 'No layers configured.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            grid_df = SessionManager.load_dataframe(request.session_id, 'grid_df')
            if grid_df is None:
                return Response({'error': 'Grid data not found on disk.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            grid_df_copy = grid_df.copy()
            grid_df_copy['geometry'] = grid_df_copy['wkt'].apply(wkt.loads)
            grid_gdf = gpd.GeoDataFrame(grid_df_copy, geometry='geometry', crs='EPSG:3857')
            if 'cell_id' not in grid_gdf.columns:
                grid_gdf['cell_id'] = range(len(grid_gdf))

            scorer = UniversalRasterScorer()
            result = scorer.calculate_layers_adaptive(
                grid_gdf=grid_gdf,
                layer_configs=session['layer_configs'],
                chunk_size=Config.DEFAULT_CHUNK_SIZE,
                n_workers=Config.DEFAULT_N_WORKERS,
            )

            SessionManager.save_dataframe(request.session_id, 'scoring_results', result)
            SessionManager.update_session(request.session_id, scoring_complete=True)

            metadata_cols = ['cell_id', 'wkt']
            analysis_cols = [c for c in result.columns if c not in metadata_cols]
            stats = {}
            for col in analysis_cols:
                if result[col].dtype in ['float64', 'float32', 'int64', 'int32']:
                    stats[col] = {
                        'mean': round(float(result[col].mean()), 3),
                        'min': round(float(result[col].min()), 3),
                        'max': round(float(result[col].max()), 3),
                    }

            return Response({
                'message': f'Analysis complete: {len(result):,} cells processed.',
                'total_cells': len(result),
                'columns': result.columns.tolist(),
                'statistics': stats,
                'preview': result.head(50).to_dict(orient='records'),
            })

        except Exception as e:
            import traceback
            return Response(
                {'error': str(e), 'traceback': traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AnalysisResultsView(APIView):
    def get(self, request):
        session = SessionManager.get_session(request.session_id)
        if not session['scoring_complete']:
            return Response({'error': 'No analysis results available.'}, status=status.HTTP_404_NOT_FOUND)

        result = SessionManager.load_dataframe(request.session_id, 'scoring_results')
        if result is None:
            return Response({'error': 'Results not found on disk.'}, status=status.HTTP_404_NOT_FOUND)

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 100))
        start = (page - 1) * page_size

        return Response({
            'total': len(result),
            'page': page,
            'page_size': page_size,
            'columns': result.columns.tolist(),
            'data': result.iloc[start:start + page_size].to_dict(orient='records'),
        })


class AnalysisDownloadView(APIView):
    def get(self, request):
        result = SessionManager.load_dataframe(request.session_id, 'scoring_results')
        if result is None:
            return Response({'error': 'No results available.'}, status=status.HTTP_404_NOT_FOUND)

        csv_data = result.to_csv(index=False, sep=';', decimal=',')
        response = HttpResponse(csv_data.encode('utf-8-sig'), content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="raster_analysis_results.csv"'
        return response


# ---- File / Directory browser ----

import json as _json
from config import Config as _BrowseConfig

_BROWSER_PREFS_FILE = _BrowseConfig.BASE_DIR / 'config' / 'browser_prefs.json'

def _load_browser_prefs() -> dict:
    try:
        if _BROWSER_PREFS_FILE.exists():
            return _json.loads(_BROWSER_PREFS_FILE.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {}

def _save_browser_prefs(prefs: dict):
    try:
        _BROWSER_PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _BROWSER_PREFS_FILE.write_text(_json.dumps(prefs, indent=2), encoding='utf-8')
    except Exception:
        pass


class BrowseDefaultPathView(APIView):
    """Return the best default directory for the file browser."""

    def get(self, request):
        prefs = _load_browser_prefs()
        last = prefs.get('last_dir', '')

        # If saved path still exists, use it
        if last and os.path.isdir(last):
            return Response({'path': last})

        # Docker / Linux: start in /app/data if it exists
        if os.name != 'nt':
            data_dir = '/app/data'
            if os.path.isdir(data_dir):
                return Response({'path': data_dir})
            return Response({'path': '/'})

        # Windows: start at project data dir
        from config import Config
        data_dir = str(Config.DATA_DIR)
        if os.path.isdir(data_dir):
            return Response({'path': data_dir})
        return Response({'path': ''})


class BrowseSaveLastDirView(APIView):
    """Persist the last used directory."""

    def post(self, request):
        directory = request.data.get('directory', '')
        if directory and os.path.isdir(directory):
            prefs = _load_browser_prefs()
            prefs['last_dir'] = directory
            _save_browser_prefs(prefs)
        return Response({'ok': True})


class BrowseDirectoryView(APIView):
    """Return folders and .tif files under a given directory path."""

    ALLOWED_EXTENSIONS = {'.tif', '.tiff'}

    def get(self, request):
        path = request.query_params.get('path', '')

        # Default: show drive roots on Windows, or filesystem root on Linux/Docker
        if not path:
            if os.name == 'nt':
                import string
                drives = [
                    f'{d}:\\'
                    for d in string.ascii_uppercase
                    if os.path.exists(f'{d}:\\')
                ]
                return Response({'path': '', 'parent': '', 'folders': drives, 'files': []})
            else:
                path = '/'

        path = os.path.normpath(path)
        if not os.path.isdir(path):
            return Response({'error': 'Directory not found.'}, status=status.HTTP_400_BAD_REQUEST)

        # At filesystem root, parent stays empty so "Up" disables
        parent = '' if path == '/' else os.path.dirname(path)
        folders = []
        files = []

        try:
            for entry in sorted(os.scandir(path), key=lambda e: e.name.lower()):
                if entry.name.startswith('.'):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    folders.append(entry.name)
                elif entry.is_file():
                    ext = os.path.splitext(entry.name)[1].lower()
                    if ext in self.ALLOWED_EXTENSIONS:
                        files.append(entry.name)
        except PermissionError:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        return Response({
            'path': path,
            'parent': parent,
            'folders': folders,
            'files': files,
        })


class NativeFileDialogView(APIView):
    """Open the native OS file picker dialog and return the selected path.
    Only works in local desktop mode; returns 'not supported' in headless/server environments."""

    def get(self, request):
        import threading

        result = [None]

        def _open_dialog():
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                root.focus_force()
                file_path = filedialog.askopenfilename(
                    title="Select Raster File",
                    filetypes=[("GeoTIFF files", "*.tif *.tiff"), ("All files", "*.*")],
                )
                root.destroy()
                result[0] = file_path
            except Exception:
                result[0] = None

        t = threading.Thread(target=_open_dialog)
        t.start()
        t.join(timeout=30)

        path = result[0]
        if not path:
            return Response({'path': '', 'cancelled': True})

        return Response({'path': path, 'cancelled': False})

def _run_analysis_work(session_id, layer_configs, *, progress_callback):
    """Runs layer analysis using the original fast parallel method."""
    import geopandas as _gpd
    from shapely import wkt as _wkt
    from config import Config as _Cfg

    progress_callback(5, 'Loading grid data...')
    grid_df = SessionManager.load_dataframe(session_id, 'grid_df')
    grid_df['geometry'] = grid_df['wkt'].apply(_wkt.loads)
    grid_gdf = _gpd.GeoDataFrame(grid_df, geometry='geometry', crs='EPSG:3857')
    if 'cell_id' not in grid_gdf.columns:
        grid_gdf['cell_id'] = range(len(grid_gdf))

    n_layers = len(layer_configs)
    n_cells = len(grid_gdf)
    progress_callback(15, f'Running parallel analysis: {n_layers} layers, {n_cells:,} cells...')

    scorer = UniversalRasterScorer()
    result = scorer.calculate_layers_adaptive(
        grid_gdf=grid_gdf,
        layer_configs=layer_configs,
        chunk_size=_Cfg.DEFAULT_CHUNK_SIZE,
        n_workers=_Cfg.DEFAULT_N_WORKERS,
    )

    progress_callback(90, 'Saving results...')
    SessionManager.save_dataframe(session_id, 'scoring_results', result)
    SessionManager.update_session(session_id, scoring_complete=True)

    progress_callback(95, 'Computing statistics...')
    metadata_cols = ['cell_id', 'wkt']
    analysis_cols = [c for c in result.columns if c not in metadata_cols]
    stats = {}
    for col in analysis_cols:
        if result[col].dtype in ['float64', 'float32', 'int64', 'int32']:
            stats[col] = {
                'mean': round(float(result[col].mean()), 3),
                'min': round(float(result[col].min()), 3),
                'max': round(float(result[col].max()), 3),
            }

    return {
        'message': f'Analysis complete: {len(result):,} cells processed.',
        'total_cells': len(result),
        'columns': result.columns.tolist(),
        'statistics': _sanitize_value(stats),
        'preview': _sanitize_value(result.head(50).to_dict(orient='records')),
    }


def _sanitize_value(data):
    """Recursively replace NaN/Inf with None for JSON serialization."""
    if isinstance(data, dict):
        return {k: _sanitize_value(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_value(item) for item in data]
    if isinstance(data, float) and (np.isnan(data) or np.isinf(data)):
        return None
    return data


class RunAnalysisAsyncView(APIView):
    """Start analysis in background thread, return task_id."""

    def post(self, request):
        session = SessionManager.get_session(request.session_id)

        if not session['grid_created']:
            return Response({'error': 'Grid not created yet.'}, status=status.HTTP_400_BAD_REQUEST)
        if not session['layer_configs']:
            return Response({'error': 'No layers configured.'}, status=status.HTTP_400_BAD_REQUEST)

        grid_df = SessionManager.load_dataframe(request.session_id, 'grid_df')
        if grid_df is None:
            return Response({'error': 'Grid data not found.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        all_configs = session['layer_configs']
        selected_indices = request.data.get('selected_indices', None)
        if selected_indices is not None:
            # Filter to only the requested indices; ignore out-of-range values
            active_configs = [all_configs[i] for i in selected_indices if 0 <= i < len(all_configs)]
            if not active_configs:
                return Response({'error': 'No valid layers selected for analysis.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            active_configs = all_configs

        task_id = create_task(
            _run_analysis_work,
            session_id=request.session_id,
            layer_configs=active_configs,
        )
        return Response({'task_id': task_id, 'message': 'Analysis started.'})


class TaskProgressView(APIView):
    """Poll progress of a background task."""

    def get(self, request, task_id):
        task = get_task(task_id)
        if task is None:
            return Response({'error': 'Task not found.'}, status=status.HTTP_404_NOT_FOUND)

        resp = {
            'task_id': task_id,
            'status': task['status'],
            'progress': task['progress'],
            'message': task['message'],
            'steps': task['steps'][-5:],
        }
        if task['status'] == 'completed':
            resp['result'] = task['result']
        elif task['status'] == 'failed':
            resp['error'] = task['error']
            if task.get('traceback'):
                resp['traceback'] = task['traceback']
        return Response(resp)


# ---- Grid boundary info for Tab 2 map ----

class GridInfoView(APIView):
    """Return stored boundary GeoJSON + bounds + grid dimensions for map display."""

    def get(self, request):
        session = SessionManager.get_session(request.session_id)

        if not session.get('grid_created'):
            return Response({'error': 'Grid not created yet.'}, status=status.HTTP_404_NOT_FOUND)

        boundary_gdf = SessionManager.load_dataframe(request.session_id, 'boundary_gdf')
        if boundary_gdf is None:
            return Response({'error': 'Boundary data not found.'}, status=status.HTTP_404_NOT_FOUND)

        import json

        if not hasattr(boundary_gdf, 'geometry') or boundary_gdf.geometry is None:
            return Response({'error': 'Boundary has no geometry.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        boundary_4326 = boundary_gdf.to_crs('EPSG:4326')
        simplified = boundary_4326.simplify(0.005)
        boundary_4326 = boundary_4326.copy()
        boundary_4326['geometry'] = simplified

        geojson = json.loads(boundary_4326.to_json())
        bounds = boundary_4326.total_bounds  # (minx, miny, maxx, maxy)

        return Response({
            'geojson': geojson,
            'bounds': [[float(bounds[1]), float(bounds[0])], [float(bounds[3]), float(bounds[2])]],
            'grid_size_x': session.get('grid_size_x', 0),
            'grid_size_y': session.get('grid_size_y', 0),
            'grid_origin_x': session.get('grid_origin_x', None),
            'grid_origin_y': session.get('grid_origin_y', None),
        })


# ---- Raster preview for map overlay ----

def _build_colormap():
    """Create a 256-entry RGBA colormap: blue -> cyan -> green -> yellow -> red."""
    cmap = np.zeros((256, 4), dtype=np.uint8)
    for i in range(256):
        t = i / 255.0
        if t < 0.25:
            r, g, b = 0, int(t * 4 * 255), 255
        elif t < 0.5:
            r, g, b = 0, 255, int((1 - (t - 0.25) * 4) * 255)
        elif t < 0.75:
            r, g, b = int((t - 0.5) * 4 * 255), 255, 0
        else:
            r, g, b = 255, int((1 - (t - 0.75) * 4) * 255), 0
        cmap[i] = [r, g, b, 180]
    return cmap


_COLORMAP = _build_colormap()


class RasterPreviewView(APIView):
    """Return a base64-encoded PNG + geographic bounds for a raster file.

    Rasters are EPSG:3857. Bounds are converted to EPSG:4326 for Leaflet.
    """

    MAX_PREVIEW_DIM = 16000         # px – longest side of the output image

    def get(self, request):
        import base64
        import rasterio
        from rasterio.enums import Resampling
        from rasterio.io import MemoryFile
        from pyproj import Transformer

        raster_path = request.query_params.get('path', '')
        if not raster_path:
            return Response({'error': 'path parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        norm_path = os.path.normpath(raster_path)
        if not os.path.isfile(norm_path):
            return Response({'error': 'File not found.'}, status=status.HTTP_400_BAD_REQUEST)
        if not norm_path.lower().endswith(('.tif', '.tiff')):
            return Response({'error': 'Only .tif/.tiff files accepted.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with rasterio.open(norm_path) as src:
                nodata = src.nodata
                # Raster is EPSG:3857 (metres) — convert bounds to 4326 for Leaflet
                b = src.bounds  # (west_m, south_m, east_m, north_m)
                _t = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
                lon_w, lat_s = _t.transform(b.left, b.bottom)
                lon_e, lat_n = _t.transform(b.right, b.top)
                bounds_4326 = (lon_w, lat_s, lon_e, lat_n)

                h, w = src.height, src.width
                max_dim = self.MAX_PREVIEW_DIM
                if max(h, w) > max_dim:
                    ratio = max_dim / max(h, w)
                    out_h = max(1, int(h * ratio))
                    out_w = max(1, int(w * ratio))
                else:
                    out_h, out_w = h, w

                data = src.read(
                    1, out_shape=(out_h, out_w),
                    resampling=Resampling.nearest,
                ).astype(np.float32)

            # ── Colormapping ──
            if nodata is not None:
                mask = (data == nodata)
            else:
                mask = np.zeros(data.shape, bool)
            if np.issubdtype(data.dtype, np.floating):
                mask = mask | np.isnan(data)

            valid = data[~mask]
            if valid.size == 0:
                return Response({'error': 'Empty raster (all nodata).'}, status=status.HTTP_400_BAD_REQUEST)

            unique_vals = np.unique(valid)
            n_unique = len(unique_vals)

            if n_unique <= 2 and set(unique_vals).issubset({0, 1}):
                # ── Binary raster: 0 = black, 1 = white ──
                rgba = np.zeros((*data.shape, 4), dtype=np.uint8)
                rgba[data == 1] = [255, 255, 255, 200]
                rgba[data == 0] = [0, 0, 0, 200]
                rgba[mask] = [0, 0, 0, 0]

            elif n_unique <= 20:
                # ── Discrete raster: distinct color per unique value ──
                # Use a fixed seed derived from value count for reproducibility
                rng = np.random.RandomState(42)
                palette = np.zeros((n_unique, 4), dtype=np.uint8)
                for idx in range(n_unique):
                    palette[idx] = [rng.randint(40, 256), rng.randint(40, 256), rng.randint(40, 256), 200]
                # Build a lookup: value -> color
                val_to_idx = {v: i for i, v in enumerate(unique_vals)}
                rgba = np.zeros((*data.shape, 4), dtype=np.uint8)
                for val, idx in val_to_idx.items():
                    rgba[data == val] = palette[idx]
                rgba[mask] = [0, 0, 0, 0]

            else:
                # ── Continuous raster: gradient colormap ──
                vmin = float(np.nanpercentile(valid, 2))
                vmax = float(np.nanpercentile(valid, 98))

                if vmax - vmin < 1e-10:
                    indices = np.full(data.shape, 128, dtype=np.uint8)
                else:
                    normed = np.clip((data.astype(np.float64) - vmin) / (vmax - vmin), 0, 1)
                    indices = (normed * 255).astype(np.uint8)

                rgba = _COLORMAP[indices]
                rgba[mask] = [0, 0, 0, 0]

            vmin = float(valid.min())
            vmax = float(valid.max())
            rgba_bands = np.transpose(rgba, (2, 0, 1))  # (4, h, w)

            with MemoryFile() as memfile:
                with memfile.open(driver='PNG', dtype='uint8',
                                  width=out_w, height=out_h, count=4) as dst:
                    dst.write(rgba_bands)
                memfile.seek(0)
                png_bytes = memfile.read()

            b64 = base64.b64encode(png_bytes).decode('ascii')

            return Response({
                'bounds': [[bounds_4326[1], bounds_4326[0]],
                           [bounds_4326[3], bounds_4326[2]]],
                'image': f'data:image/png;base64,{b64}',
                'width': out_w,
                'height': out_h,
                'value_range': [vmin, vmax],
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
