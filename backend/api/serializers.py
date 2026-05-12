from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import TrainingModel

class TrainingModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingModel
        fields = '__all__'

class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=True, allow_blank=False)

    def validate_password(self, value):
        if not any(c.isalpha() for c in value):
            raise serializers.ValidationError('密码必须包含至少一个字母')
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError('密码必须包含至少一个数字')
        return value
    def validate_username(self, value):
        User = get_user_model()
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already exists')
        return value

    def validate_email(self, value):
        User = get_user_model()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('邮箱已被使用')
        return value

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
