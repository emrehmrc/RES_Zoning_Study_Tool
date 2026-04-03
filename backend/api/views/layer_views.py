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

class BrowseDirectoryView(APIView):
    """Return folders and .tif files under a given directory path."""

    ALLOWED_EXTENSIONS = {'.tif', '.tiff'}

    def get(self, request):
        path = request.query_params.get('path', '')

        # Default: show drive roots on Windows, or / on Linux
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

        parent = os.path.dirname(path)
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


# ---- Async analysis with progress ----

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

        task_id = create_task(
            _run_analysis_work,
            session_id=request.session_id,
            layer_configs=session['layer_configs'],
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
