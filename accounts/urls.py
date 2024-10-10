from django.urls import path, reverse, include
from .views import *

urlpatterns = [
    path('signup/', MySignupView.as_view(), name='account_signup'),
    path('', include('allauth.urls')),
]
