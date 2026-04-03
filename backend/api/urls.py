from django.urls import path
from api.views.project_views import (
    SelectProjectView, ProjectStatusView, ResetProjectView, ProjectConfigView,
)
from api.views.grid_views import (
    CreateGridView, UploadGridView, GridDataView, GridDownloadView,
    CountryListView, EEZZoneListView, CountryBoundaryView,
    AlbaniaRegionsView, AlbaniaDistrictsView,
)
from api.views.layer_views import (
    LayerListView, AddLayerView, RemoveLayerView,
    RasterFilesView, UploadRasterFileView, RunAnalysisView, AnalysisResultsView, AnalysisDownloadView,
    BrowseDirectoryView, NativeFileDialogView, RunAnalysisAsyncView, TaskProgressView,
    GridInfoView, RasterPreviewView,
)
from api.views.scoring_views import (
    RunScoringView, ScoringResultsView, ScoringDownloadView, ImportScoringCSVView,
    RunScoringAsyncView,
)
from api.views.cluster_views import (
    RunClusterView, ClusterResultsView, ClusterDownloadView,
    UploadClusterCSVView, FinancialConstantsView, CPValuesView, ScoringRulesView,
    RunClusterAsyncView,
)

urlpatterns = [
    # Project management
    path('project/select/', SelectProjectView.as_view()),
    path('project/status/', ProjectStatusView.as_view()),
    path('project/reset/', ResetProjectView.as_view()),
    path('project/config/', ProjectConfigView.as_view()),

    # Grid
    path('grid/create/', CreateGridView.as_view()),
    path('grid/upload/', UploadGridView.as_view()),
    path('grid/data/', GridDataView.as_view()),
    path('grid/download/', GridDownloadView.as_view()),
    path('countries/', CountryListView.as_view()),
    path('eez-zones/', EEZZoneListView.as_view()),
    path('country-boundary/', CountryBoundaryView.as_view()),
    path('albania/regions/', AlbaniaRegionsView.as_view()),
    path('albania/districts/', AlbaniaDistrictsView.as_view()),

    # Layers & Analysis
    path('layers/', LayerListView.as_view()),
    path('layers/add/', AddLayerView.as_view()),
    path('layers/<int:index>/remove/', RemoveLayerView.as_view()),
    path('raster-files/', RasterFilesView.as_view()),
    path('raster-files/upload/', UploadRasterFileView.as_view()),
    path('analysis/run/', RunAnalysisView.as_view()),
    path('analysis/run-async/', RunAnalysisAsyncView.as_view()),
    path('analysis/results/', AnalysisResultsView.as_view()),
    path('analysis/download/', AnalysisDownloadView.as_view()),
    path('browse/', BrowseDirectoryView.as_view()),
    path('native-file-dialog/', NativeFileDialogView.as_view()),
    path('task/<str:task_id>/progress/', TaskProgressView.as_view()),
    path('grid-info/', GridInfoView.as_view()),
    path('raster-preview/', RasterPreviewView.as_view()),

    # Level Scoring
    path('scoring/run/', RunScoringView.as_view()),
    path('scoring/run-async/', RunScoringAsyncView.as_view()),
    path('scoring/results/', ScoringResultsView.as_view()),
    path('scoring/download/', ScoringDownloadView.as_view()),
    path('scoring/import-csv/', ImportScoringCSVView.as_view()),

    # Clustering
    path('cluster/run/', RunClusterView.as_view()),
    path('cluster/run-async/', RunClusterAsyncView.as_view()),
    path('cluster/results/', ClusterResultsView.as_view()),
    path('cluster/download/', ClusterDownloadView.as_view()),
    path('cluster/upload-csv/', UploadClusterCSVView.as_view()),

    # Reference data
    path('financial-constants/', FinancialConstantsView.as_view()),
    path('cp-values/', CPValuesView.as_view()),
    path('scoring-rules/', ScoringRulesView.as_view()),
]
