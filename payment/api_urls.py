"""Routes API paiement (Phase 4) — montées sous /api/v1/payments/ (hors i18n)."""
from django.urls import path
from . import api_views

urlpatterns = [
    path('init/', api_views.payment_init, name='api_payment_init'),
    path('<str:transaction_number>/verify/', api_views.payment_verify, name='api_payment_verify'),
    path('<str:transaction_number>/status/', api_views.payment_status, name='api_payment_status'),
]
