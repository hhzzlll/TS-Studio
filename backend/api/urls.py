from django.urls import path
from .views import FileUploadView, TrainingView, ConfigView, TrainingStatusView, PredictView, PredictionResultView, ActiveTrainingView, DatasetListView, DatasetInfoView, CompletedModelsView
from .extra_views import TrainingControlView

urlpatterns = [
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('datasets/', DatasetListView.as_view(), name='dataset-list'),
    path('datasets/info/', DatasetInfoView.as_view(), name='dataset-info'),
    path('models/completed/', CompletedModelsView.as_view(), name='completed-models'),
    path('config/', ConfigView.as_view(), name='config'),
    path('train/', TrainingView.as_view(), name='train'),
    path('train/active/', ActiveTrainingView.as_view(), name='train-active'),
    path('train/status/<int:pk>/', TrainingStatusView.as_view(), name='train-status'),
    path('train/control/<int:pk>/', TrainingControlView.as_view(), name='train-control'),
    path('predict/', PredictView.as_view(), name='predict'),
    path('result/<int:pk>/', PredictionResultView.as_view(), name='prediction-result'),
]
