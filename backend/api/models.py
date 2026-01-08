from django.db import models

class TrainingModel(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default='pending') # pending, running, completed, failed
    config = models.JSONField(default=dict)
    metrics = models.JSONField(default=dict, null=True, blank=True)
    log = models.TextField(blank=True)
    checkpoint_path = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return f"{self.name} - {self.status}"
