from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
import json

from .models import Transaction, Payment
from courses.models import Enrollment

User = get_user_model()


class TransactionModelTest(TestCase):
    """Tests pour le modèle Transaction"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_transaction_creation(self):
        """Test création d'une transaction"""
        transaction = Transaction.objects.create(
            user=self.user,
            price=Decimal('99.99'),
            currency=Transaction.Currencies.USD,
            status=Transaction.Status.PENDING,
            payment_method=Transaction.PaymentMethods.CREDIT_CARD,
            meta_data={
                "course": {
                    "course_id": 123,
                    "course_name": "Test Course"
                }
            }
        )
        
        self.assertIsNotNone(transaction.transaction_number)
        self.assertTrue(transaction.transaction_number.startswith('KOULKY'))
        self.assertEqual(len(transaction.transaction_number), 12)  # KOULKY + 6 digits
        self.assertTrue(transaction.is_pending)
        self.assertFalse(transaction.is_completed)
    
    def test_transaction_number_generator(self):
        """Test génération automatique du numéro de transaction"""
        t1 = Transaction.objects.create(
            user=self.user,
            price=Decimal('50.00'),
            currency=Transaction.Currencies.USD
        )
        
        t2 = Transaction.objects.create(
            user=self.user,
            price=Decimal('75.00'),
            currency=Transaction.Currencies.USD
        )
        
        self.assertNotEqual(t1.transaction_number, t2.transaction_number)
        
        # Extraire les numéros
        num1 = int(t1.transaction_number.replace('KOULKY', ''))
        num2 = int(t2.transaction_number.replace('KOULKY', ''))
        
        self.assertEqual(num2, num1 + 1)
    
    def test_transaction_properties(self):
        """Test des propriétés de Transaction"""
        transaction = Transaction.objects.create(
            user=self.user,
            price=Decimal('99.99'),
            currency=Transaction.Currencies.USD,
            status=Transaction.Status.COMPLETED,
            meta_data={
                "course": {
                    "course_id": 456,
                    "course_name": "Python Course"
                }
            }
        )
        
        self.assertTrue(transaction.is_completed)
        self.assertFalse(transaction.is_pending)
        self.assertTrue(transaction.is_refundable)
        self.assertEqual(transaction.course_name, "Python Course")
        self.assertEqual(transaction.course_id, 456)
    
    def test_transaction_str(self):
        """Test représentation string de Transaction"""
        transaction = Transaction.objects.create(
            user=self.user,
            price=Decimal('99.99'),
            currency=Transaction.Currencies.USD
        )
        
        str_repr = str(transaction)
        self.assertIn(transaction.transaction_number, str_repr)
        self.assertIn('99.99', str_repr)
        self.assertIn('USD', str_repr)


class PaymentConfirmViewTest(TestCase):
    """Tests pour la vue de confirmation de paiement"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.transaction = Transaction.objects.create(
            user=self.user,
            price=Decimal('99.99'),
            currency=Transaction.Currencies.USD,
            status=Transaction.Status.PENDING,
            payment_method=Transaction.PaymentMethods.CREDIT_CARD,
            meta_data={
                "course": {
                    "course_id": 123,
                    "course_name": "Test Course",
                    "product_id": 456
                },
                "user": {
                    "id": self.user.pk,
                    "email": self.user.email,
                    "thinkific_user_id": 789
                }
            }
        )
    
    def test_confirm_invalid_method(self):
        """Test méthode GET non autorisée"""
        response = self.client.get(reverse('payment:payment_callback'))
        self.assertEqual(response.status_code, 405)
    
    def test_confirm_invalid_json(self):
        """Test payload JSON invalide"""
        response = self.client.post(
            reverse('payment:payment_callback'),
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
    
    def test_confirm_missing_transaction_number(self):
        """Test sans numéro de transaction"""
        payload = {
            'status': 'success',
            'meta_data': {}
        }
        
        response = self.client.post(
            reverse('payment:payment_callback'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
    
    def test_confirm_transaction_not_found(self):
        """Test transaction inexistante"""
        payload = {
            'status': 'success',
            'meta_data': {
                'transaction_number': 'KOULKY999999'
            }
        }
        
        response = self.client.post(
            reverse('payment:payment_callback'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertFalse(data['success'])


class PaymentModelTest(TestCase):
    """Tests pour le modèle Payment"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.transaction = Transaction.objects.create(
            user=self.user,
            price=Decimal('99.99'),
            currency=Transaction.Currencies.USD,
            status=Transaction.Status.COMPLETED
        )
        
        self.enrollment = Enrollment.objects.create(
            user=self.user,
            thinkific_user_id=123,
            course_id=456
        )
    
    def test_payment_creation(self):
        """Test création d'un paiement"""
        payment = Payment.objects.create(
            user=self.user,
            enrollment=self.enrollment,
            transaction=self.transaction
        )
        
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.enrollment, self.enrollment)
        self.assertEqual(payment.transaction, self.transaction)
    
    def test_payment_str(self):
        """Test représentation string de Payment"""
        payment = Payment.objects.create(
            user=self.user,
            enrollment=self.enrollment,
            transaction=self.transaction
        )
        
        str_repr = str(payment)
        self.assertIn(self.transaction.transaction_number, str_repr)
        self.assertIn(self.user.email, str_repr)
    
    def test_payment_unique_transaction(self):
        """Test qu'une transaction ne peut être liée qu'à un seul paiement"""
        Payment.objects.create(
            user=self.user,
            enrollment=self.enrollment,
            transaction=self.transaction
        )
        
        # Créer un second enrollment
        enrollment2 = Enrollment.objects.create(
            user=self.user,
            thinkific_user_id=789,
            course_id=999
        )
        
        # Tenter de créer un second paiement avec la même transaction
        with self.assertRaises(Exception):
            Payment.objects.create(
                user=self.user,
                enrollment=enrollment2,
                transaction=self.transaction
            )


class TransactionStatusTest(TestCase):
    """Tests pour les changements de statut des transactions"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_status_transitions(self):
        """Test transitions de statut"""
        transaction = Transaction.objects.create(
            user=self.user,
            price=Decimal('99.99'),
            currency=Transaction.Currencies.USD,
            status=Transaction.Status.PENDING
        )
        
        # PENDING -> COMPLETED
        transaction.status = Transaction.Status.COMPLETED
        transaction.save()
        self.assertTrue(transaction.is_completed)
        self.assertTrue(transaction.is_refundable)
        
        # COMPLETED -> REFUNDED
        transaction.status = Transaction.Status.REFUNDED
        transaction.save()
        self.assertFalse(transaction.is_refundable)
    
    def test_failed_transaction(self):
        """Test transaction échouée"""
        transaction = Transaction.objects.create(
            user=self.user,
            price=Decimal('99.99'),
            currency=Transaction.Currencies.USD,
            status=Transaction.Status.FAILED
        )
        
        self.assertFalse(transaction.is_completed)
        self.assertFalse(transaction.is_pending)
        self.assertFalse(transaction.is_refundable)