"""Serializers API — Paiement (Phase 4)."""
from rest_framework import serializers

ALLOWED_METHODS = ['moncash', 'natcash', 'kashpaw']


class PaymentInitSerializer(serializers.Serializer):
    course_id = serializers.IntegerField(required=False)
    bundle_id = serializers.IntegerField(required=False)
    payment_method = serializers.ChoiceField(choices=ALLOWED_METHODS)

    def validate(self, attrs):
        if bool(attrs.get('course_id')) == bool(attrs.get('bundle_id')):
            raise serializers.ValidationError(
                "Fournir exactement un de 'course_id' ou 'bundle_id'."
            )
        return attrs


class PaymentInitResponseSerializer(serializers.Serializer):
    transaction_number = serializers.CharField()
    payment_url = serializers.CharField()
    status = serializers.CharField()


class PaymentStatusSerializer(serializers.Serializer):
    transaction_number = serializers.CharField()
    status = serializers.CharField()
    paid = serializers.BooleanField()
    course_id = serializers.IntegerField(allow_null=True)
    bundle_id = serializers.IntegerField(allow_null=True)
    provider_transaction_id = serializers.CharField(allow_null=True)
