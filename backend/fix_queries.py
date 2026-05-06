import re

with open('/root/TS-Studio/backend/api/views.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace TrainingModel.objects.get(pk=pk) with TrainingModel.objects.get(pk=pk, user=request.user)
# only inside view methods where 'request.user' is available.
# Find instances of job = TrainingModel.objects.get(pk=pk)
# Be careful of run_training_task which uses job_id = training_job_id and doesn't have request.user

text = text.replace('job = TrainingModel.objects.get(pk=pk)', 'job = TrainingModel.objects.get(pk=pk, user=request.user)')

# Check PredictionResultView logic
# Reconstruct setting string to find folder
# data_type = config.get('dataset_type', 'custom')
# It uses model_id as folder name which saves weights in checkpoints/. We don't have separate checkpoint folders per user...
# Since each model has a unique model_id (with dataset_name, seq_len, pred_len), if multiple users choose the same model config, they might conflict!
# However, for now, we just isolate the TrainingModel objects themselves.

with open('/root/TS-Studio/backend/api/views.py', 'w', encoding='utf-8') as f:
    f.write(text)
    
print("Updated queries.")
