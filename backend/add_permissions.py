import re

with open('/root/TS-Studio/backend/api/views.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Make sure IsAuthenticated is imported
if 'from rest_framework.permissions import IsAuthenticated' not in text:
    text = text.replace('from rest_framework.views import APIView', 'from rest_framework.views import APIView\nfrom rest_framework.permissions import IsAuthenticated\n')

classes_to_protect = [
    'FileUploadView', 'DatasetListView', 'DatasetColumnsView', 'DatasetInfoView',
    'DatasetDownloadView', 'StatisticalAnalysisView', 'ColumnAnalysisView',
    'TrainingView', 'ActiveTrainingView', 'CompletedModelsView', 'TrainingStatusView',
    'PredictView', 'PredictionResultView', 'TraditionalModelListView', 'TraditionalModelPredictView'
]

for cls in classes_to_protect:
    pattern = rf"(class {cls}\(APIView\):\n)"
    replacement = rf"\1    permission_classes = [IsAuthenticated]\n"
    if 'permission_classes = [IsAuthenticated]' not in re.search(rf"class {cls}\(APIView\):[\s\S]*?(?=class |\Z)", text).group():
        text = re.sub(pattern, replacement, text)

with open('/root/TS-Studio/backend/api/views.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
