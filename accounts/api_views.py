"""
API mobile — Authentification (Phase 2).

JWT (simplejwt). Réutilise la logique de signup web : username auto, lien Thinkific,
email de bienvenue, notification admin, email marqué vérifié.
"""
import os

from django.contrib.auth import get_user_model
from django.db import IntegrityError

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken


class AuthThrottle(AnonRateThrottle):
    """Limite les tentatives sur login/register/google (par IP)."""
    scope = 'auth'

from drf_spectacular.utils import extend_schema

from .api_serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer, GoogleAuthSerializer,
    TokenResponseSerializer, RefreshRequestSerializer, ProfileUpdateSerializer,
)

User = get_user_model()


def _tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


def _auth_payload(user):
    return {**_tokens_for(user), 'user': UserSerializer(user).data}


def _post_signup(user, request):
    """Mêmes effets que le signup web (username, Thinkific, bienvenue, notif, email vérifié)."""
    from accounts.views import _assign_username
    from accounts.signals import _ensure_thinkific_linked, _send_welcome_email
    try:
        if not user.username:
            _assign_username(user)
        _ensure_thinkific_linked(user)
        _send_welcome_email(user, request)
        from allauth.account.models import EmailAddress
        EmailAddress.objects.update_or_create(
            user=user, email=user.email,
            defaults={'verified': True, 'primary': True},
        )
        from accounts.admin_notify import notify_admin_new_signup
        notify_admin_new_signup(user, method='API mobile')
    except Exception as e:
        print(f"[API register] post-signup pour {user.email}: {e}")


@extend_schema(
    summary="Inscription", request=RegisterSerializer, responses=TokenResponseSerializer,
    tags=['Auth'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def register(request):
    s = RegisterSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    try:
        user = User.objects.create_user(
            email=d['email'], password=d['password'],
            first_name=d['first_name'], last_name=d['last_name'],
            phone=d.get('phone', ''),
        )
    except IntegrityError:
        return Response({'detail': "Un compte existe déjà avec cet e-mail."},
                        status=status.HTTP_400_BAD_REQUEST)
    _post_signup(user, request)
    return Response(_auth_payload(user), status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Connexion (e-mail ou prénom)", request=LoginSerializer,
    responses=TokenResponseSerializer, tags=['Auth'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def login(request):
    s = LoginSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    ident = s.validated_data['login'].strip()
    password = s.validated_data['password']
    user = (User.objects.filter(email__iexact=ident).first()
            or User.objects.filter(username__iexact=ident).first())
    if not user or not user.check_password(password) or not user.is_active:
        return Response({'detail': "Identifiants invalides."}, status=status.HTTP_401_UNAUTHORIZED)
    return Response(_auth_payload(user))


@extend_schema(
    summary="Connexion Google (mobile)", request=GoogleAuthSerializer,
    responses=TokenResponseSerializer, tags=['Auth'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def google_auth(request):
    s = GoogleAuthSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    token = s.validated_data['id_token']

    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
    client_id = os.getenv('GOOGLE_CLIENT_ID', '')
    try:
        info = google_id_token.verify_oauth2_token(token, google_requests.Request(), client_id or None)
    except Exception as e:
        return Response({'detail': f"Token Google invalide : {e}"}, status=status.HTTP_401_UNAUTHORIZED)

    email = (info.get('email') or '').lower()
    if not email:
        return Response({'detail': "E-mail absent du token Google."}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(email__iexact=email).first()
    created = False
    if not user:
        user = User.objects.create_user(
            email=email, password=None,
            first_name=info.get('given_name', '') or '',
            last_name=info.get('family_name', '') or '',
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        _post_signup(user, request)
        created = True
    else:
        # S'assurer du lien Thinkific pour un compte existant
        from accounts.signals import _ensure_thinkific_linked
        _ensure_thinkific_linked(user)

    payload = _auth_payload(user)
    return Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@extend_schema(
    summary="Profil de l'utilisateur connecté (consulter / modifier)",
    request=ProfileUpdateSerializer, responses=UserSerializer, tags=['Auth'],
)
@api_view(['GET', 'PATCH', 'PUT'])
@permission_classes([IsAuthenticated])
def me(request):
    """GET → profil ; PATCH/PUT → met à jour prénom, nom, numéro de contact."""
    if request.method == 'GET':
        return Response(UserSerializer(request.user).data)

    partial = request.method == 'PATCH'
    s = ProfileUpdateSerializer(instance=request.user, data=request.data, partial=partial)
    s.is_valid(raise_exception=True)
    user = s.save()
    # Répercute prénom/nom sur Thinkific (best-effort).
    try:
        if user.thinkific_user_id and ('first_name' in s.validated_data or 'last_name' in s.validated_data):
            from accounts.views import thinkific
            thinkific.users.update_user(
                id=user.thinkific_user_id,
                values={'first_name': user.first_name, 'last_name': user.last_name},
            )
    except Exception as e:
        print(f"[API profil] Sync Thinkific échouée pour {user.email}: {e}")
    return Response(UserSerializer(user).data)


@extend_schema(
    summary="Déconnexion (blacklist du refresh token)",
    request=RefreshRequestSerializer, responses={205: None}, tags=['Auth'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    s = RefreshRequestSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    try:
        RefreshToken(s.validated_data['refresh']).blacklist()
    except Exception:
        return Response({'detail': "Token invalide ou déjà expiré."}, status=status.HTTP_400_BAD_REQUEST)
    return Response(status=status.HTTP_205_RESET_CONTENT)


@extend_schema(
    summary="Enregistrer un appareil (push notifications)",
    request=None, responses={200: None}, tags=['Auth'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_device(request):
    from .api_serializers import DeviceTokenSerializer
    from .models import DeviceToken
    s = DeviceTokenSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    _, created = DeviceToken.objects.update_or_create(
        user=request.user, token=s.validated_data['token'],
        defaults={'platform': s.validated_data.get('platform', '')},
    )
    # Push de bienvenue au tout premier appareil enregistré (timing correct : un device existe).
    if created and DeviceToken.objects.filter(user=request.user).count() == 1:
        try:
            from .push_service import send_push_to_user
            prenom = (request.user.first_name or '').strip()
            send_push_to_user(
                request.user,
                f"Bienvenue {prenom} 👋".strip(),
                "Votre compte KouLakay est prêt — découvrez les cours !",
                data={'type': 'welcome', 'route': 'courses', 'id': ''},
            )
        except Exception as e:
            print(f"[push] welcome échouée pour {request.user.email}: {e}")
    return Response({'registered': True})


@extend_schema(
    summary="Envoyer une push de test à soi-même",
    request=None, responses={200: None}, tags=['Auth'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_push(request):
    from .push_service import is_enabled, send_push_to_user
    if not is_enabled():
        return Response({'detail': "Push non configurées (FIREBASE_CREDENTIALS_JSON absent)."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    sent = send_push_to_user(
        request.user, "KouLakay", "Ceci est une notification de test ✅",
        data={'type': 'test', 'route': 'home', 'id': ''},
    )
    return Response({'sent': sent})
