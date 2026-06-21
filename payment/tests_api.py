"""Tests API — Paiement (Phase 5) : validations & permissions."""
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from payment.models import Transaction
from payment.views import process_successful_payment

User = get_user_model()
DUMMY_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}


@override_settings(CACHES=DUMMY_CACHE)
class PaymentAPITests(TestCase):
    def setUp(self):
        self.c = APIClient()
        self.u = User.objects.create_user(email='pay@b.com', password='SuperPass123!', first_name='P')

    def test_init_requires_auth(self):
        r = self.c.post('/api/v1/payments/init/', {'course_id': 1, 'payment_method': 'moncash'}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_init_bad_method(self):
        self.c.force_authenticate(self.u)
        r = self.c.post('/api/v1/payments/init/', {'course_id': 1, 'payment_method': 'paypal'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_init_both_ids(self):
        self.c.force_authenticate(self.u)
        r = self.c.post('/api/v1/payments/init/', {'course_id': 1, 'bundle_id': 2, 'payment_method': 'moncash'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_init_no_id(self):
        self.c.force_authenticate(self.u)
        r = self.c.post('/api/v1/payments/init/', {'payment_method': 'moncash'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_status_owner_only(self):
        tx = Transaction.objects.create(
            user=self.u, price=Decimal('500'), currency='HTG',
            status=Transaction.Status.PENDING, payment_method='moncash',
            meta_data={'course': {'course_id': 111}, 'user': {'id': self.u.pk}})
        self.c.force_authenticate(self.u)
        r = self.c.get(f'/api/v1/payments/{tx.transaction_number}/status/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['status'], 'PENDING')
        self.assertEqual(r.data['course_id'], 111)

    def test_status_not_found(self):
        self.c.force_authenticate(self.u)
        r = self.c.get('/api/v1/payments/KL-NOPE/status/')
        self.assertEqual(r.status_code, 404)

    def test_status_other_user_404(self):
        other = User.objects.create_user(email='other@b.com', password='SuperPass123!', first_name='O')
        tx = Transaction.objects.create(
            user=other, price=Decimal('500'), currency='HTG',
            status=Transaction.Status.PENDING, payment_method='moncash',
            meta_data={'course': {'course_id': 111}, 'user': {'id': other.pk}})
        self.c.force_authenticate(self.u)
        r = self.c.get(f'/api/v1/payments/{tx.transaction_number}/status/')
        self.assertEqual(r.status_code, 404)  # n'appartient pas à self.u


@override_settings(CACHES=DUMMY_CACHE)
class PaymentIdempotencyTests(TestCase):
    """process_successful_payment doit être idempotent (anti double-e-mail)."""

    def setUp(self):
        self.u = User.objects.create_user(email='buyer@b.com', password='SuperPass123!', first_name='B')
        self.tx = Transaction.objects.create(
            user=self.u, price=Decimal('500'), currency='HTG',
            status=Transaction.Status.PENDING, payment_method='moncash',
            meta_data={'course': {'course_id': 111, 'course_name': 'Cours Test'},
                       'user': {'id': self.u.pk, 'thinkific_user_id': 999}})

    @patch('payment.views.create_thinkific_external_order', return_value=True)
    @patch('payment.views.thinkific')
    @patch('payment.views.send_enrollment_confirmation')
    def test_double_call_envoie_un_seul_email(self, m_email, m_tk, m_order):
        with patch('accounts.admin_notify.notify_admin_new_enrollment'), \
             patch('accounts.push_service.send_push_to_user'):
            r1 = process_successful_payment(self.tx, {})
            r2 = process_successful_payment(self.tx, {})  # 2e appel concurrent simulé

        self.assertTrue(r1['success'])
        self.assertTrue(r2['success'])
        self.assertTrue(r2.get('already_processed'))      # 2e appel : court-circuité
        self.assertEqual(r2.get('course_id'), 111)
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, Transaction.Status.COMPLETED)
        self.assertEqual(m_email.call_count, 1)           # ← un seul e-mail malgré 2 appels
