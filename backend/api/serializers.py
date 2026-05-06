from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import TrainingModel

class TrainingModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingModel
        fields = '__all__'

class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_username(self, value):
        User = get_user_model()
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already exists')
        return value

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
