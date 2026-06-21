"""Serializers API — Catalogue & inscriptions (Phases 1/3)."""
from rest_framework import serializers


class EnrolledCourseSerializer(serializers.Serializer):
    """Un cours dans « Mon Apprentissage »."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField(allow_blank=True)
    image_url = serializers.CharField(allow_blank=True)
    price = serializers.CharField(allow_null=True)
    currency = serializers.CharField(allow_blank=True)
    activated_at = serializers.DateTimeField(allow_null=True)
    expiry_date = serializers.DateTimeField(allow_null=True)
    lifetime = serializers.BooleanField()
    access_duration = serializers.CharField(allow_null=True)
    percentage_completed = serializers.IntegerField()


class EnrollResultSerializer(serializers.Serializer):
    """Résultat d'une tentative d'inscription."""
    enrolled = serializers.BooleanField(required=False)
    already_enrolled = serializers.BooleanField(required=False)
    requires_payment = serializers.BooleanField(required=False)
    course_id = serializers.IntegerField(required=False)
    bundle_id = serializers.IntegerField(required=False)
    price = serializers.FloatField(required=False)
    currency = serializers.CharField(required=False)


class SSOUrlSerializer(serializers.Serializer):
    sso_url = serializers.CharField()
