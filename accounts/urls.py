from django.urls import path, reverse, include
from .views import *

urlpatterns = [
    path('', include('allauth.urls')),
]
