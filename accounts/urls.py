# accounts/urls.py
from django.urls import path, include
from .views import ThinkificSignupView, ThinkificLoginView, sync_thinkific_user

urlpatterns = [
    # Vues personnalisées pour Thinkific
    path('signup/', ThinkificSignupView.as_view(), name='account_signup'),
    path('login/', ThinkificLoginView.as_view(), name='account_login'),
    path('sync-thinkific/', sync_thinkific_user, name='sync_thinkific'),
    
    # Routes allauth par défaut
    path('', include('allauth.urls')),
]