# payment/urls.py
from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    # Callback de confirmation de paiement
    path('callback_url/', views.confirm, name='payment_callback'),
    
    # Endpoint de remboursement
    path('refund/<str:transaction_number>/', views.refund_transaction, name='refund_transaction'),
]