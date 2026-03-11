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

    # Stripe Elements
    path('stripe/checkout/', views.stripe_checkout, name='stripe_checkout'),
    path('stripe/create-intent/', views.stripe_create_intent, name='stripe_create_intent'),
    path('stripe/success/', views.stripe_success, name='stripe_success'),
]
