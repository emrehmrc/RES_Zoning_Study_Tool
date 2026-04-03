from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.session_manager import SessionManager

from utils.config_solar import SolarConfig
from utils.config_onshore import OnShoreConfig
from utils.config_offshore import OffShoreConfig


def get_config_class(project_type):
    configs = {
        'Solar': SolarConfig,
        'OnShore': OnShoreConfig,
        'OffShore': OffShoreConfig,
    }
    return configs.get(project_type, SolarConfig)


def serialize_config(config_cls):
    """Serialize a config class to a JSON-friendly dict."""
    return {
        'project_type': config_cls.PROJECT_TYPE,
        'app_title': config_cls.APP_TITLE,
        'theme_color': config_cls.THEME_COLOR,
        'icon': config_cls.ICON,
        'layer_categories': config_cls.LAYER_CATEGORIES,
        'predefined_layer_modes': config_cls.PREDEFINED_LAYER_MODES,
        'all_layer_names': sorted(config_cls.ALL_LAYER_NAMES),
        'scoring_configs': config_cls.SCORING_CONFIGS,
        'cluster_scoring_rules': config_cls.CLUSTER_SCORING_RULES,
    }


class SelectProjectView(APIView):
    def post(self, request):
        project_type = request.data.get('project_type')
        if project_type not in ('Solar', 'OnShore', 'OffShore'):
            return Response(
                {'error': 'Invalid project type. Must be Solar, OnShore, or OffShore.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session_id = request.session_id
        SessionManager.reset_session(session_id)
        SessionManager.update_session(session_id, project_type=project_type)

        config_cls = get_config_class(project_type)
        return Response({
            'session_id': session_id,
            'project_type': project_type,
            'config': serialize_config(config_cls),
        })


class ProjectStatusView(APIView):
    def get(self, request):
        session = SessionManager.get_session(request.session_id)

        grid_count = 0
        if session['grid_created']:
            grid_df = SessionManager.load_dataframe(request.session_id, 'grid_df')
            if grid_df is not None:
                grid_count = len(grid_df)

        scoring_count = 0
        if session['scoring_complete']:
            results = SessionManager.load_dataframe(request.session_id, 'scoring_results')
            if results is not None:
                scoring_count = len(results)

        cluster_count = 0
        if SessionManager.has_dataframe(request.session_id, 'cluster_results'):
            cluster_df = SessionManager.load_dataframe(request.session_id, 'cluster_results')
            if cluster_df is not None:
                cluster_count = len(cluster_df)

        return Response({
            'project_type': session['project_type'],
            'grid_created': session['grid_created'],
            'grid_count': grid_count,
            'scoring_complete': session['scoring_complete'],
            'scoring_count': scoring_count,
            'layer_count': len(session['layer_configs']),
            'cluster_count': cluster_count,
            'has_final_scored': SessionManager.has_dataframe(request.session_id, 'final_scored_results'),
            'has_cluster_results': SessionManager.has_dataframe(request.session_id, 'cluster_results'),
        })


class ResetProjectView(APIView):
    def post(self, request):
        keep_project_type = request.data.get('keep_project_type', False)
        session = SessionManager.get_session(request.session_id)
        project_type = session['project_type'] if keep_project_type else None

        SessionManager.reset_session(request.session_id)
        if project_type:
            SessionManager.update_session(request.session_id, project_type=project_type)

        return Response({'message': 'Project reset successfully.'})


class ProjectConfigView(APIView):
    def get(self, request):
        session = SessionManager.get_session(request.session_id)
        project_type = session.get('project_type')
        if not project_type:
            return Response(
                {'error': 'No project selected.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        config_cls = get_config_class(project_type)
        return Response(serialize_config(config_cls))
