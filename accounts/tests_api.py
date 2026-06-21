"""Tests API — Auth (Phase 5). Externes (Thinkific/email) mockés ; cache dummy (anti-throttle)."""
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

DUMMY_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}


@override_settings(CACHES=DUMMY_CACHE)
class AuthAPITests(TestCase):
    def setUp(self):
        self.c = APIClient()

    @patch('accounts.signals._send_welcome_email')
    @patch('accounts.signals._ensure_thinkific_linked')
    def test_register_returns_tokens_and_user(self, m_link, m_mail):
        r = self.c.post('/api/v1/auth/register/', {
            'first_name': 'Api', 'last_name': 'Test',
            'email': 'a@b.com', 'password': 'SuperPass123!'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertIn('access', r.data)
        self.assertIn('refresh', r.data)
        self.assertEqual(r.data['user']['email'], 'a@b.com')
        self.assertTrue(r.data['user']['username'])  # username auto-généré

    @patch('accounts.signals._send_welcome_email')
    @patch('accounts.signals._ensure_thinkific_linked')
    def test_login_email_and_username(self, m_link, m_mail):
        self.c.post('/api/v1/auth/register/', {
            'first_name': 'Jean', 'last_name': 'X',
            'email': 'jean@b.com', 'password': 'SuperPass123!'}, format='json')
        # par email
        r = self.c.post('/api/v1/auth/login/', {'login': 'jean@b.com', 'password': 'SuperPass123!'}, format='json')
        self.assertEqual(r.status_code, 200)
        # par prénom (username)
        username = User.objects.get(email='jean@b.com').username
        r = self.c.post('/api/v1/auth/login/', {'login': username, 'password': 'SuperPass123!'}, format='json')
        self.assertEqual(r.status_code, 200)

    @patch('accounts.signals._send_welcome_email')
    @patch('accounts.signals._ensure_thinkific_linked')
    def test_me_and_refresh_and_logout(self, m_link, m_mail):
        reg = self.c.post('/api/v1/auth/register/', {
            'first_name': 'M', 'last_name': 'E', 'email': 'm@e.com', 'password': 'SuperPass123!'}, format='json')
        access, refresh = reg.data['access'], reg.data['refresh']
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + access)
        r = self.c.get('/api/v1/auth/me/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['email'], 'm@e.com')
        # refresh
        r = self.c.post('/api/v1/auth/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('access', r.data)
        new_refresh = r.data.get('refresh', refresh)
        # logout (blacklist)
        r = self.c.post('/api/v1/auth/logout/', {'refresh': new_refresh}, format='json')
        self.assertEqual(r.status_code, 205)
        # refresh après logout → rejeté
        r = self.c.post('/api/v1/auth/refresh/', {'refresh': new_refresh}, format='json')
        self.assertEqual(r.status_code, 401)

    @patch('accounts.signals._send_welcome_email')
    @patch('accounts.signals._ensure_thinkific_linked')
    def test_validation_errors(self, m_link, m_mail):
        self.c.post('/api/v1/auth/register/', {
            'first_name': 'D', 'last_name': 'U', 'email': 'dup@b.com', 'password': 'SuperPass123!'}, format='json')
        # email dupliqué
        r = self.c.post('/api/v1/auth/register/', {
            'first_name': 'D', 'last_name': 'U', 'email': 'dup@b.com', 'password': 'SuperPass123!'}, format='json')
        self.assertEqual(r.status_code, 400)
        # mot de passe trop court
        r = self.c.post('/api/v1/auth/register/', {
            'first_name': 'D', 'last_name': 'U', 'email': 'new@b.com', 'password': '123'}, format='json')
        self.assertEqual(r.status_code, 400)
        # mauvais identifiants
        r = self.c.post('/api/v1/auth/login/', {'login': 'dup@b.com', 'password': 'WRONG'}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_me_requires_auth(self):
        self.assertEqual(self.c.get('/api/v1/auth/me/').status_code, 401)

    @patch('accounts.signals._send_welcome_email')
    @patch('accounts.signals._ensure_thinkific_linked')
    def test_register_device(self, m_link, m_mail):
        reg = self.c.post('/api/v1/auth/register/', {
            'first_name': 'P', 'last_name': 'N', 'email': 'p@n.com', 'password': 'SuperPass123!'}, format='json')
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + reg.data['access'])
        r = self.c.post('/api/v1/auth/devices/', {'token': 'fcm-abc-123', 'platform': 'android'}, format='json')
        self.assertEqual(r.status_code, 200)
        from accounts.models import DeviceToken
        self.assertTrue(DeviceToken.objects.filter(token='fcm-abc-123', platform='android').exists())


@override_settings(CACHES=DUMMY_CACHE)
class PushServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='push@b.com', password='SuperPass123!', first_name='P')

    def test_no_op_when_firebase_not_configured(self):
        # FIREBASE_CREDENTIALS_JSON vide en test → send retourne 0, aucune erreur
        from accounts.push_service import send_push_to_user
        self.assertEqual(send_push_to_user(self.user, 't', 'b'), 0)

    def test_test_push_endpoint_503_when_unconfigured(self):
        c = APIClient()
        c.force_authenticate(self.user)
        r = c.post('/api/v1/auth/push/test/')
        self.assertEqual(r.status_code, 503)

    @patch('firebase_admin.messaging.send_each_for_multicast')
    @patch('accounts.push_service._get_app', return_value=object())
    def test_send_cleans_invalid_tokens(self, m_app, m_send):
        from accounts.models import DeviceToken
        DeviceToken.objects.create(user=self.user, token='good', platform='android')
        DeviceToken.objects.create(user=self.user, token='bad', platform='ios')

        class UnregisteredError(Exception):
            pass

        class _R:
            def __init__(self, success, exc=None):
                self.success = success
                self.exception = exc

        class _Resp:
            responses = [_R(True), _R(False, UnregisteredError('stale'))]

        m_send.return_value = _Resp()

        from accounts.push_service import send_push_to_user
        sent = send_push_to_user(self.user, 'Titre', 'Corps', data={'k': 1})
        self.assertEqual(sent, 1)
        # un token invalide purgé → il reste 1 token
        self.assertEqual(DeviceToken.objects.filter(user=self.user).count(), 1)

    @patch('accounts.push_service.send_push_to_user')
    def test_welcome_push_only_on_first_device(self, m_send):
        c = APIClient()
        c.force_authenticate(self.user)
        # 1er appareil → push de bienvenue
        c.post('/api/v1/auth/devices/', {'token': 'dev-1', 'platform': 'android'}, format='json')
        self.assertEqual(m_send.call_count, 1)
        self.assertEqual(m_send.call_args.kwargs['data']['type'], 'welcome')
        # 2e appareil → pas de nouvelle push de bienvenue
        c.post('/api/v1/auth/devices/', {'token': 'dev-2', 'platform': 'ios'}, format='json')
        self.assertEqual(m_send.call_count, 1)
