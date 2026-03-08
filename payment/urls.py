# payment/urls.py
from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    # Retour utilisateur après paiement plopplop (MonCash / NatCash / Kashpaw)
    path('retour/', views.payment_return, name='payment_return'),

    # Webhook de confirmation (ancien système — conservé)
    path('callback_url/', views.confirm, name='payment_callback'),

    # Endpoint de remboursement
    path('refund/<str:transaction_number>/', views.refund_transaction, name='refund_transaction'),
]
