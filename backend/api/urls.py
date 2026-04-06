from django.urls import path
from .views import (
    FileUploadView, TrainingView, ConfigView, TrainingStatusView, 
    PredictView, PredictionResultView, ActiveTrainingView, DatasetListView, 
    DatasetInfoView, CompletedModelsView, StatisticalAnalysisView, 
    ColumnAnalysisView, DatasetDownloadView, TraditionalModelListView, 
    TraditionalModelPredictView, DatasetColumnsView
)
from .extra_views import TrainingControlView

urlpatterns = [
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('datasets/', DatasetListView.as_view(), name='dataset-list'),
    path('datasets/<str:filename>/columns/', DatasetColumnsView.as_view(), name='dataset-columns'),
    path('datasets/info/', DatasetInfoView.as_view(), name='dataset-info'),
    path('datasets/analysis/', StatisticalAnalysisView.as_view(), name='dataset-analysis'),
    path('datasets/column-analysis/', ColumnAnalysisView.as_view(), name='column-analysis'),
    path('datasets/download/', DatasetDownloadView.as_view(), name='dataset-download'),
    path('models/completed/', CompletedModelsView.as_view(), name='completed-models'),
    path('config/', ConfigView.as_view(), name='config'),
    path('train/', TrainingView.as_view(), name='train'),
    path('train/active/', ActiveTrainingView.as_view(), name='train-active'),
    path('train/status/<int:pk>/', TrainingStatusView.as_view(), name='train-status'),
    path('train/control/<int:pk>/', TrainingControlView.as_view(), name='train-control'),
    path('predict/', PredictView.as_view(), name='predict'),
    path('result/<int:pk>/', PredictionResultView.as_view(), name='prediction-result'),
    # 传统模型相关
    path('traditional-models/', TraditionalModelListView.as_view(), name='traditional-models'),
    path('traditional-models/predict/', TraditionalModelPredictView.as_view(), name='traditional-predict'),
]
