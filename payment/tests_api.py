"""Tests API — Paiement (Phase 5) : validations & permissions."""
from decimal import Decimal
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from payment.models import Transaction

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
