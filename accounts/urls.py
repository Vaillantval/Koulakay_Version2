# accounts/urls.py
from django.urls import path, include
from .views import ThinkificSignupView, ThinkificLoginView, sync_thinkific_user, thinkific_sso, profile

urlpatterns = [
    # Vues personnalisées pour Thinkific
    path('signup/', ThinkificSignupView.as_view(), name='account_signup'),
    path('login/', ThinkificLoginView.as_view(), name='account_login'),
    path('sync-thinkific/', sync_thinkific_user, name='sync_thinkific'),
    # Mon profil — édition des infos d'inscription
    path('profile/', profile, name='account_profile'),
    # SSO : connexion automatique sur Thinkific depuis Django
    path('thinkific-sso/', thinkific_sso, name='thinkific_sso'),

    # Routes allauth par défaut
    path('', include('allauth.urls')),
]
