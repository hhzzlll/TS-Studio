from rest_framework import serializers
from .models import TrainingModel

class TrainingModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingModel
        fields = '__all__'
