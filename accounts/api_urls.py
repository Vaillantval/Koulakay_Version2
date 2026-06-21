"""Routes API auth (Phase 2) — montées sous /api/v1/auth/ (hors i18n)."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import api_views

urlpatterns = [
    path('register/', api_views.register, name='api_register'),
    path('login/', api_views.login, name='api_login'),
    path('google/', api_views.google_auth, name='api_google'),
    path('refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    path('logout/', api_views.logout, name='api_logout'),
    path('me/', api_views.me, name='api_me'),
    path('devices/', api_views.register_device, name='api_register_device'),
    path('push/test/', api_views.test_push, name='api_test_push'),
]
