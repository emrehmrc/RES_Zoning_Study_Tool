import io
import json
import os

import numpy as np
import pandas as pd
from django.http import HttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from api.session_manager import SessionManager
from api.task_manager import create_task, get_task
from api.views.project_views import get_config_class
from engines.cluster_engine import ClusterEngine
from engines.cluster_scorer import ClusterScorer


def _sanitize_for_json(data):
    """Recursively replace NaN / Infinity with None so JSON serialization works."""
    if isinstance(data, dict):
        return {k: _sanitize_for_json(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_for_json(item) for item in data]
    if isinstance(data, float) and (np.isnan(data) or np.isinf(data)):
        return None
    return data


class UploadClusterCSVView(APIView):
    def post(self, request):
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            return Response({'error': 'CSV file required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            content = csv_file.read().decode('utf-8')
            df = pd.read_csv(io.StringIO(content))

            required = ['wkt', 'FINAL_GRID_SCORE']
            missing = [c for c in required if c not in df.columns]
            if missing:
                df = pd.read_csv(io.StringIO(content), sep=';', decimal=',')
                missing = [c for c in required if c not in df.columns]
                if missing:
                    return Response(
                        {'error': f'Missing required columns: {missing}'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            SessionManager.save_dataframe(request.session_id, 'cluster_input_csv', df)
            return Response({
                'message': f'CSV uploaded: {len(df)} rows.',
                'total_rows': len(df),
                'columns': df.columns.tolist(),
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RunClusterView(APIView):
    def post(self, request):
        session = SessionManager.get_session(request.session_id)
        project_type = session.get('project_type', 'Solar')

        nominal_capacity_mw = float(request.data.get('nominal_capacity_mw', 13.0))
        max_capacity_mw = float(request.data.get('max_capacity_mw', 250.0))
        adjust_for_coverage = request.data.get('adjust_for_coverage', True)
        scoring_rules = request.data.get('scoring_rules', [])
        financial_constants = request.data.get('financial_constants')
        cp_values = request.data.get('cp_values')
        source = request.data.get('source', 'step3')

        try:
            if source == 'step3':
                data_df = SessionManager.load_dataframe(request.session_id, 'final_scored_results')
                if data_df is None:
                    return Response(
                        {'error': 'No final scored results from Step 3.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            elif source == 'upload':
                data_df = SessionManager.load_dataframe(request.session_id, 'cluster_input_csv')
                if data_df is None:
                    return Response(
                        {'error': 'No uploaded CSV found. Upload first.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                return Response({'error': 'Invalid source.'}, status=status.HTTP_400_BAD_REQUEST)

            # Step A: Clustering
            cell_gdf = ClusterEngine.load_and_prepare_data(data_df)
            cell_gdf = ClusterEngine.calculate_cell_capacities(
                cell_gdf, nominal_capacity_mw, adjust_for_coverage,
            )
            cell_gdf, G, components = ClusterEngine.build_adjacency_components(cell_gdf)
            cell_gdf = ClusterEngine.enforce_capacity_limits(
                cell_gdf, G, components, max_capacity_mw,
            )
            cluster_gdf = ClusterEngine.dissolve_and_aggregate(cell_gdf)

            # Step B: Connection Scoring
            if scoring_rules:
                cluster_gdf = ClusterScorer.score_clusters(
                    cluster_gdf=cluster_gdf,
                    cell_gdf=cell_gdf,
                    scoring_rules=scoring_rules,
                    financial_constants=financial_constants,
                    cp_values=cp_values,
                    project_type=project_type,
                )

            SessionManager.save_dataframe(request.session_id, 'cluster_results', cluster_gdf)

            # Build summary
            summary = {'total_clusters': len(cluster_gdf)}

            cap_col = 'Installed_Capacity_MW' if 'Installed_Capacity_MW' in cluster_gdf.columns else 'Calculated_Capacity_MW'
            if cap_col in cluster_gdf.columns:
                summary['avg_capacity_mw'] = round(float(cluster_gdf[cap_col].mean()), 2)
                summary['total_capacity_mw'] = round(float(cluster_gdf[cap_col].sum()), 2)

            if 'Overall_Score' in cluster_gdf.columns:
                summary['avg_overall_score'] = round(float(cluster_gdf['Overall_Score'].mean()), 2)
            if 'LCOE($/MWh)' in cluster_gdf.columns:
                summary['avg_lcoe'] = round(float(cluster_gdf['LCOE($/MWh)'].mean()), 2)

            if 'Nearest_Connection_Type' in cluster_gdf.columns:
                conn = cluster_gdf['Nearest_Connection_Type'].value_counts().to_dict()
                summary['connection_types'] = {str(k): int(v) for k, v in conn.items() if k}
            if 'Nearest_Connection_kV' in cluster_gdf.columns:
                kv = cluster_gdf['Nearest_Connection_kV'].value_counts().to_dict()
                summary['kv_distribution'] = {str(k): int(v) for k, v in kv.items() if k > 0}

            exclude_cols = ['geometry', 'original_index']
            preview_cols = [c for c in cluster_gdf.columns if c not in exclude_cols]
            preview = cluster_gdf[preview_cols].head(30).to_dict(orient='records')

            return Response(_sanitize_for_json({
                'message': f'Clustering & scoring complete! {len(cluster_gdf)} clusters.',
                'summary': summary,
                'columns': preview_cols,
                'preview': preview,
            }))

        except Exception as e:
            import traceback
            return Response(
                {'error': str(e), 'traceback': traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ClusterResultsView(APIView):
    def get(self, request):
        result = SessionManager.load_dataframe(request.session_id, 'cluster_results')
        if result is None:
            return Response({'error': 'No cluster results.'}, status=status.HTTP_404_NOT_FOUND)

        cols = [c for c in result.columns if c != 'geometry']
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 100))
        start = (page - 1) * page_size

        data = result[cols].iloc[start:start + page_size].to_dict(orient='records')
        _sanitize_for_json(data)

        return Response({
            'total': len(result),
            'page': page,
            'page_size': page_size,
            'columns': cols,
            'data': data,
        })


class ClusterDownloadView(APIView):
    def get(self, request):
        result = SessionManager.load_dataframe(request.session_id, 'cluster_results')
        if result is None:
            return Response({'error': 'No results.'}, status=status.HTTP_404_NOT_FOUND)

        export_cols = [c for c in result.columns if c != 'geometry']
        csv_data = result[export_cols].to_csv(index=False, sep=';', decimal=',')
        response = HttpResponse(csv_data.encode('utf-8-sig'), content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="clustered_scored_results.csv"'
        return response


# ---------------------------------------------------------------------------
# Reference-data endpoints (financial constants, CP values, scoring rules)
# ---------------------------------------------------------------------------

_CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'config',
)


class FinancialConstantsView(APIView):
    def get(self, request):
        path = os.path.join(_CONFIG_DIR, 'financial_constants.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return Response(json.load(f))
        return Response({
            'pv_capex_per_mw': 500000,
            'wind_capex_per_mw': 1000000,
            'substation_pv_ratio': 0.08,
            'substation_wind_ratio': 0.06,
            'line_expropriation_ratio': 0.1,
            'land_cost_ratio': 0.1,
            'transport_network_base': 400000,
            'transport_network_per_mw': 500,
            'transmission': [],
        })

    def put(self, request):
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        path = os.path.join(_CONFIG_DIR, 'financial_constants.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(request.data, f, indent=4)
        return Response({'message': 'Financial constants saved.'})


class CPValuesView(APIView):
    def get(self, request):
        path = os.path.join(_CONFIG_DIR, 'cp_values.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return Response(json.load(f))
        return Response([{'Wind speed': 0, 'Cp': 0.0}])

    def put(self, request):
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        path = os.path.join(_CONFIG_DIR, 'cp_values.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(request.data, f, indent=4)
        return Response({'message': 'CP values saved.'})


class ScoringRulesView(APIView):
    def get(self, request):
        session = SessionManager.get_session(request.session_id)
        rules = session.get('scoring_rules')
        if rules:
            return Response(rules)
        project_type = session.get('project_type', 'Solar')
        config_cls = get_config_class(project_type)
        return Response(config_cls.CLUSTER_SCORING_RULES)

    def put(self, request):
        rules = request.data
        if not isinstance(rules, list):
            return Response(
                {'error': 'Expected a list of scoring rules.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        SessionManager.update_session(request.session_id, scoring_rules=rules)
        return Response({'message': 'Scoring rules updated.'})


# ---- Async cluster analysis ----

def _run_cluster_work(session_id, source, nominal_capacity_mw, max_capacity_mw,
                      adjust_for_coverage, scoring_rules, financial_constants,
                      cp_values, project_type, *, progress_callback):
    """Run cluster analysis + scoring in background thread."""
    progress_callback(5, 'Loading input data...')
    if source == 'step3':
        data_df = SessionManager.load_dataframe(session_id, 'final_scored_results')
        if data_df is None:
            raise ValueError('No final scored results from Step 3.')
    elif source == 'upload':
        data_df = SessionManager.load_dataframe(session_id, 'cluster_input_csv')
        if data_df is None:
            raise ValueError('No uploaded CSV found. Upload first.')
    else:
        raise ValueError('Invalid source.')

    progress_callback(10, 'Preparing grid geometry...')
    cell_gdf = ClusterEngine.load_and_prepare_data(data_df)

    progress_callback(20, 'Calculating cell capacities...')
    cell_gdf = ClusterEngine.calculate_cell_capacities(
        cell_gdf, nominal_capacity_mw, adjust_for_coverage,
    )

    progress_callback(35, 'Building adjacency graph...')
    cell_gdf, G, components = ClusterEngine.build_adjacency_components(cell_gdf)

    progress_callback(50, 'Enforcing capacity limits...')
    cell_gdf = ClusterEngine.enforce_capacity_limits(
        cell_gdf, G, components, max_capacity_mw,
    )

    progress_callback(60, 'Dissolving clusters...')
    cluster_gdf = ClusterEngine.dissolve_and_aggregate(cell_gdf)

    if scoring_rules:
        progress_callback(70, 'Scoring clusters...')
        cluster_gdf = ClusterScorer.score_clusters(
            cluster_gdf=cluster_gdf,
            cell_gdf=cell_gdf,
            scoring_rules=scoring_rules,
            financial_constants=financial_constants,
            cp_values=cp_values,
            project_type=project_type,
        )

    progress_callback(90, 'Saving results...')
    SessionManager.save_dataframe(session_id, 'cluster_results', cluster_gdf)

    # Build summary
    summary = {'total_clusters': len(cluster_gdf)}
    cap_col = 'Installed_Capacity_MW' if 'Installed_Capacity_MW' in cluster_gdf.columns else 'Calculated_Capacity_MW'
    if cap_col in cluster_gdf.columns:
        summary['avg_capacity_mw'] = round(float(cluster_gdf[cap_col].mean()), 2)
        summary['total_capacity_mw'] = round(float(cluster_gdf[cap_col].sum()), 2)
    if 'Overall_Score' in cluster_gdf.columns:
        summary['avg_overall_score'] = round(float(cluster_gdf['Overall_Score'].mean()), 2)
    if 'LCOE($/MWh)' in cluster_gdf.columns:
        summary['avg_lcoe'] = round(float(cluster_gdf['LCOE($/MWh)'].mean()), 2)
    if 'Nearest_Connection_Type' in cluster_gdf.columns:
        conn = cluster_gdf['Nearest_Connection_Type'].value_counts().to_dict()
        summary['connection_types'] = {str(k): int(v) for k, v in conn.items() if k}
    if 'Nearest_Connection_kV' in cluster_gdf.columns:
        kv = cluster_gdf['Nearest_Connection_kV'].value_counts().to_dict()
        summary['kv_distribution'] = {str(k): int(v) for k, v in kv.items() if k > 0}

    exclude_cols = ['geometry', 'original_index']
    preview_cols = [c for c in cluster_gdf.columns if c not in exclude_cols]
    preview = cluster_gdf[preview_cols].head(30).to_dict(orient='records')

    return _sanitize_for_json({
        'message': f'Clustering & scoring complete! {len(cluster_gdf)} clusters.',
        'summary': summary,
        'columns': preview_cols,
        'preview': preview,
    })


class RunClusterAsyncView(APIView):
    def post(self, request):
        session = SessionManager.get_session(request.session_id)
        project_type = session.get('project_type', 'Solar')

        task_id = create_task(
            _run_cluster_work,
            session_id=request.session_id,
            source=request.data.get('source', 'step3'),
            nominal_capacity_mw=float(request.data.get('nominal_capacity_mw', 13.0)),
            max_capacity_mw=float(request.data.get('max_capacity_mw', 250.0)),
            adjust_for_coverage=request.data.get('adjust_for_coverage', True),
            scoring_rules=request.data.get('scoring_rules', []),
            financial_constants=request.data.get('financial_constants'),
            cp_values=request.data.get('cp_values'),
            project_type=project_type,
        )
        return Response({'task_id': task_id, 'message': 'Cluster analysis started.'})
