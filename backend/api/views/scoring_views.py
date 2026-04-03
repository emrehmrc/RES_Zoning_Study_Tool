import io

import numpy as np
import pandas as pd
from django.http import HttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from api.session_manager import SessionManager
from api.task_manager import create_task, get_task


class ImportScoringCSVView(APIView):
    def post(self, request):
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            return Response({'error': 'CSV file required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            content = csv_file.read().decode('utf-8')
            df = pd.read_csv(io.StringIO(content))
            if 'cell_id' not in df.columns:
                return Response({'error': "'cell_id' column not found."}, status=status.HTTP_400_BAD_REQUEST)

            SessionManager.save_dataframe(request.session_id, 'scoring_results', df)
            SessionManager.update_session(request.session_id, scoring_complete=True)

            return Response({
                'message': f'CSV loaded: {len(df):,} rows.',
                'total_rows': len(df),
                'columns': df.columns.tolist(),
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RunScoringView(APIView):
    """
    Applies level-based weighted scoring and hard exclusion constraints.
    Mirrors the logic from tab_level_scoring.py._run_calculation.
    """

    def post(self, request):
        session = SessionManager.get_session(request.session_id)
        if not session['scoring_complete']:
            return Response({'error': 'No analysis data available.'}, status=status.HTTP_400_BAD_REQUEST)

        df = SessionManager.load_dataframe(request.session_id, 'scoring_results')
        if df is None:
            return Response({'error': 'Analysis data not found on disk.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        scoring_config = request.data.get('scoring_config', {})
        constraint_config = request.data.get('constraint_config', {})

        try:
            results_df = df.copy()
            results_df = results_df.loc[:, ~results_df.columns.duplicated()]

            total_weighted_score = np.zeros(len(results_df))
            knockout_mask = np.zeros(len(results_df), dtype=bool)
            results_df['EXCLUSION_REASONS'] = ''

            # --- 1. Weighted Scoring ---
            for layer_name, cfg in scoring_config.items():
                if cfg['type'] == 'distance_coverage':
                    distance_col = cfg['distance_column']
                    coverage_col = cfg['coverage_column']
                    max_cov = cfg['max_coverage_threshold']
                    dist_levels = cfg.get('distance_levels') or cfg.get('levels', [])

                    def _dc_score(row, _d=distance_col, _c=coverage_col,
                                  _mc=max_cov, _levels=dist_levels):
                        cov = row.get(_c)
                        if pd.notna(cov) and cov > _mc:
                            return 0
                        dist_val = row.get(_d)
                        if pd.notna(dist_val):
                            for lv in _levels:
                                if lv['min'] <= dist_val <= lv['max']:
                                    return lv['score']
                        return 0

                    layer_scores = results_df.apply(_dc_score, axis=1)
                    results_df[f'{layer_name}_SCORE'] = layer_scores
                    total_weighted_score += layer_scores * cfg['weight']

                    layer_knockout = results_df[coverage_col].fillna(0) > max_cov
                    knockout_mask |= layer_knockout
                    results_df.loc[layer_knockout, 'EXCLUSION_REASONS'] += f'{layer_name} (cov>{max_cov}%) | '

                elif cfg['type'] == 'single_mode':
                    column = cfg['column']
                    levels = cfg['levels']

                    def _level_score(val, _levels=levels):
                        if pd.notna(val):
                            for lv in _levels:
                                if lv['min'] <= val <= lv['max']:
                                    return lv['score']
                        return 0

                    layer_scores = results_df[column].apply(_level_score)
                    results_df[f'{layer_name}_SCORE'] = layer_scores
                    total_weighted_score += layer_scores * cfg['weight']

                    layer_knockout = layer_scores == 0
                    knockout_mask |= layer_knockout
                    results_df.loc[layer_knockout, 'EXCLUSION_REASONS'] += f'{layer_name} (score=0) | '

            results_df['FINAL_GRID_SCORE'] = total_weighted_score
            results_df.loc[knockout_mask, 'FINAL_GRID_SCORE'] = 0

            # --- 2. Hard Exclusion Constraints ---
            exclusion_tracking = []
            for layer_name, cfg in constraint_config.items():
                column = cfg['column']
                threshold = cfg['threshold']
                exclusion_mask = results_df[column].fillna(0) > threshold
                excluded_count = int(exclusion_mask.sum())

                results_df.loc[exclusion_mask, 'FINAL_GRID_SCORE'] = 0
                results_df.loc[exclusion_mask, 'EXCLUSION_REASONS'] += f'{layer_name} | '

                exclusion_tracking.append({
                    'layer': layer_name,
                    'column': column,
                    'threshold': threshold,
                    'excluded_count': excluded_count,
                })

            SessionManager.save_dataframe(request.session_id, 'final_scored_results', results_df)

            total_cells = len(results_df)
            excluded_cells = int((results_df['FINAL_GRID_SCORE'] == 0).sum())
            avg_score = round(float(results_df['FINAL_GRID_SCORE'].mean()), 2)

            score_distribution = {
                'excellent': int((results_df['FINAL_GRID_SCORE'] >= 80).sum()),
                'good': int(((results_df['FINAL_GRID_SCORE'] >= 60) & (results_df['FINAL_GRID_SCORE'] < 80)).sum()),
                'fair': int(((results_df['FINAL_GRID_SCORE'] >= 40) & (results_df['FINAL_GRID_SCORE'] < 60)).sum()),
                'poor': int(((results_df['FINAL_GRID_SCORE'] >= 20) & (results_df['FINAL_GRID_SCORE'] < 40)).sum()),
                'very_poor': int(((results_df['FINAL_GRID_SCORE'] > 0) & (results_df['FINAL_GRID_SCORE'] < 20)).sum()),
                'excluded': excluded_cells,
            }

            preview_cols = ['cell_id', 'FINAL_GRID_SCORE']
            preview_cols += [c for c in results_df.columns if '_SCORE' in c and c != 'FINAL_GRID_SCORE']
            if 'EXCLUSION_REASONS' in results_df.columns:
                preview_cols.append('EXCLUSION_REASONS')
            seen = set()
            unique_cols = [x for x in preview_cols if x in results_df.columns and not (x in seen or seen.add(x))]

            return Response({
                'message': 'Scoring complete!',
                'total_cells': total_cells,
                'excluded_cells': excluded_cells,
                'avg_score': avg_score,
                'score_distribution': score_distribution,
                'exclusion_tracking': exclusion_tracking,
                'columns': results_df.columns.tolist(),
                'preview': results_df[unique_cols].head(50).to_dict(orient='records'),
            })

        except Exception as e:
            import traceback
            return Response(
                {'error': str(e), 'traceback': traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ScoringResultsView(APIView):
    def get(self, request):
        result = SessionManager.load_dataframe(request.session_id, 'final_scored_results')
        if result is None:
            return Response({'error': 'No scoring results.'}, status=status.HTTP_404_NOT_FOUND)

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


class ScoringDownloadView(APIView):
    def get(self, request):
        result = SessionManager.load_dataframe(request.session_id, 'final_scored_results')
        if result is None:
            return Response({'error': 'No results.'}, status=status.HTTP_404_NOT_FOUND)

        csv_data = result.to_csv(index=False, sep=';', decimal=',')
        response = HttpResponse(csv_data.encode('utf-8-sig'), content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="final_scored_analysis.csv"'
        return response


# ---- Async scoring ----

def _run_scoring_work(session_id, scoring_config, constraint_config, *, progress_callback):
    """Run level scoring in background thread."""
    progress_callback(5, 'Loading analysis data...')
    df = SessionManager.load_dataframe(session_id, 'scoring_results')
    results_df = df.copy()
    results_df = results_df.loc[:, ~results_df.columns.duplicated()]

    total_weighted_score = np.zeros(len(results_df))
    knockout_mask = np.zeros(len(results_df), dtype=bool)
    results_df['EXCLUSION_REASONS'] = ''

    total_items = len(scoring_config) + len(constraint_config)
    done = 0

    progress_callback(10, 'Applying weighted scoring...')
    for layer_name, cfg in scoring_config.items():
        done += 1
        pct = 10 + int(60 * done / max(total_items, 1))
        progress_callback(pct, f'Scoring layer: {layer_name}')

        if cfg['type'] == 'distance_coverage':
            distance_col = cfg['distance_column']
            coverage_col = cfg['coverage_column']
            max_cov = cfg['max_coverage_threshold']
            dist_levels = cfg.get('distance_levels') or cfg.get('levels', [])

            def _dc_score(row, _d=distance_col, _c=coverage_col,
                          _mc=max_cov, _levels=dist_levels):
                cov = row.get(_c)
                if pd.notna(cov) and cov > _mc:
                    return 0
                dist_val = row.get(_d)
                if pd.notna(dist_val):
                    for lv in _levels:
                        if lv['min'] <= dist_val <= lv['max']:
                            return lv['score']
                return 0

            layer_scores = results_df.apply(_dc_score, axis=1)
            results_df[f'{layer_name}_SCORE'] = layer_scores
            total_weighted_score += layer_scores * cfg['weight']

            layer_knockout = results_df[coverage_col].fillna(0) > max_cov
            knockout_mask |= layer_knockout
            results_df.loc[layer_knockout, 'EXCLUSION_REASONS'] += f'{layer_name} (cov>{max_cov}%) | '

        elif cfg['type'] == 'single_mode':
            column = cfg['column']
            levels = cfg['levels']

            def _level_score(val, _levels=levels):
                if pd.notna(val):
                    for lv in _levels:
                        if lv['min'] <= val <= lv['max']:
                            return lv['score']
                return 0

            layer_scores = results_df[column].apply(_level_score)
            results_df[f'{layer_name}_SCORE'] = layer_scores
            total_weighted_score += layer_scores * cfg['weight']

            layer_knockout = layer_scores == 0
            knockout_mask |= layer_knockout
            results_df.loc[layer_knockout, 'EXCLUSION_REASONS'] += f'{layer_name} (score=0) | '

    results_df['FINAL_GRID_SCORE'] = total_weighted_score
    results_df.loc[knockout_mask, 'FINAL_GRID_SCORE'] = 0

    progress_callback(75, 'Applying exclusion constraints...')
    exclusion_tracking = []
    for layer_name, cfg in constraint_config.items():
        done += 1
        pct = 75 + int(15 * (done - len(scoring_config)) / max(len(constraint_config), 1))
        progress_callback(pct, f'Exclusion: {layer_name}')

        column = cfg['column']
        threshold = cfg['threshold']
        exclusion_mask = results_df[column].fillna(0) > threshold
        excluded_count = int(exclusion_mask.sum())
        results_df.loc[exclusion_mask, 'FINAL_GRID_SCORE'] = 0
        results_df.loc[exclusion_mask, 'EXCLUSION_REASONS'] += f'{layer_name} | '
        exclusion_tracking.append({
            'layer': layer_name, 'column': column,
            'threshold': threshold, 'excluded_count': excluded_count,
        })

    progress_callback(92, 'Saving results...')
    SessionManager.save_dataframe(session_id, 'final_scored_results', results_df)

    total_cells = len(results_df)
    excluded_cells = int((results_df['FINAL_GRID_SCORE'] == 0).sum())
    avg_score = round(float(results_df['FINAL_GRID_SCORE'].mean()), 2)

    score_distribution = {
        'excellent': int((results_df['FINAL_GRID_SCORE'] >= 80).sum()),
        'good': int(((results_df['FINAL_GRID_SCORE'] >= 60) & (results_df['FINAL_GRID_SCORE'] < 80)).sum()),
        'fair': int(((results_df['FINAL_GRID_SCORE'] >= 40) & (results_df['FINAL_GRID_SCORE'] < 60)).sum()),
        'poor': int(((results_df['FINAL_GRID_SCORE'] >= 20) & (results_df['FINAL_GRID_SCORE'] < 40)).sum()),
        'very_poor': int(((results_df['FINAL_GRID_SCORE'] > 0) & (results_df['FINAL_GRID_SCORE'] < 20)).sum()),
        'excluded': excluded_cells,
    }

    preview_cols = ['cell_id', 'FINAL_GRID_SCORE']
    preview_cols += [c for c in results_df.columns if '_SCORE' in c and c != 'FINAL_GRID_SCORE']
    if 'EXCLUSION_REASONS' in results_df.columns:
        preview_cols.append('EXCLUSION_REASONS')
    seen = set()
    unique_cols = [x for x in preview_cols if x in results_df.columns and not (x in seen or seen.add(x))]

    return {
        'message': 'Scoring complete!',
        'total_cells': total_cells,
        'excluded_cells': excluded_cells,
        'avg_score': avg_score,
        'score_distribution': score_distribution,
        'exclusion_tracking': exclusion_tracking,
        'columns': results_df.columns.tolist(),
        'preview': results_df[unique_cols].head(50).to_dict(orient='records'),
    }


class RunScoringAsyncView(APIView):
    def post(self, request):
        session = SessionManager.get_session(request.session_id)
        if not session['scoring_complete']:
            return Response({'error': 'No analysis data available.'}, status=status.HTTP_400_BAD_REQUEST)

        df = SessionManager.load_dataframe(request.session_id, 'scoring_results')
        if df is None:
            return Response({'error': 'Analysis data not found on disk.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        scoring_config = request.data.get('scoring_config', {})
        constraint_config = request.data.get('constraint_config', {})

        task_id = create_task(
            _run_scoring_work,
            session_id=request.session_id,
            scoring_config=scoring_config,
            constraint_config=constraint_config,
        )
        return Response({'task_id': task_id, 'message': 'Scoring started.'})
