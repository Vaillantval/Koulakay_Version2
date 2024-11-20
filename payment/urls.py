from django.urls import path
from . import views

urlpatterns = [
    path('confirm/',views.confirm,name='payment_confirm'),
]