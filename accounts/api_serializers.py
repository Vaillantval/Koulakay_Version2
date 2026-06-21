"""Serializers API — Auth (Phase 2)."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Représentation publique d'un utilisateur (réponses)."""
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'thinkific_user_id']
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet e-mail.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField(help_text="E-mail ou prénom (username)")
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True, help_text="Google ID token obtenu côté mobile")


class TokenResponseSerializer(serializers.Serializer):
    """Réponse d'auth : tokens JWT + utilisateur (documentation Swagger)."""
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class RefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class AccessResponseSerializer(serializers.Serializer):
    access = serializers.CharField()


class DeviceTokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(choices=['ios', 'android', 'web'], required=False, default='')
