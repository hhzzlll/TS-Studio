import os
import re

views_path = '/root/TS-Studio/backend/api/views.py'
with open(views_path, 'r', encoding='utf-8') as f:
    views_content = f.read()

# Add get_user_data_dir function
if 'def get_user_data_dir(user):' not in views_content:
    helper = """
def get_user_data_dir(user):
    if not user.is_authenticated:
        return os.path.join(settings.BASE_DIR, 'data')
    data_dir = os.path.join(settings.BASE_DIR, 'data', str(user.id))
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    return data_dir
"""
    views_content = views_content.replace('from rest_framework.views import APIView', 'from rest_framework.views import APIView\n' + helper)

# Replace all os.path.join(settings.BASE_DIR, 'data') with get_user_data_dir(request.user)
views_content = views_content.replace("os.path.join(settings.BASE_DIR, 'data')", "get_user_data_dir(request.user)")
views_content = views_content.replace("os.path.join(base_dir, 'data')", "get_user_data_dir(request.user)")

# Specifically fix FileUploadView if preview is requested... wait it uses data_dir
# Fix TrainingView to assign user
if 'job = TrainingModel.objects.create(' in views_content and 'user=request.user' not in views_content:
    views_content = views_content.replace(
        "job = TrainingModel.objects.create(\n            name",
        "job = TrainingModel.objects.create(\n            user=request.user if request.user.is_authenticated else None,\n            name"
    )

# Fix run_training_task root_path
if "args.root_path = './data/'" in views_content:
    views_content = views_content.replace(
        "args.root_path = './data/'",
        'args.root_path = f"./data/{job.user.id}/" if job.user else "./data/"'
    )

# Fix ActiveTrainingView, CompletedModelsView
views_content = views_content.replace(
"""        active_jobs = TrainingModel.objects.filter(
            status__in=['pending', 'running', 'paused']
        ).order_by('-created_at')""",
"""        active_jobs = TrainingModel.objects.filter(
            user=request.user if request.user.is_authenticated else None,
            status__in=['pending', 'running', 'paused']
        ).order_by('-created_at')"""
)

views_content = views_content.replace(
    "jobs = TrainingModel.objects.filter(status='completed').order_by('-created_at')",
    "jobs = TrainingModel.objects.filter(user=request.user if request.user.is_authenticated else None, status='completed').order_by('-created_at')"
)

# Traditional model Predict view root path
if "data_path = os.path.join(settings.BASE_DIR, 'data', filename)" in views_content:
    views_content = views_content.replace(
        "data_path = os.path.join(settings.BASE_DIR, 'data', filename)",
        "data_path = os.path.join(get_user_data_dir(request.user), filename)"
    )

with open(views_path, 'w', encoding='utf-8') as f:
    f.write(views_content)
    
print("views updated")
