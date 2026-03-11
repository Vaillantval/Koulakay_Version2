"""
Service d'intégration Stripe — Payment Intents
"""
import stripe
from django.conf import settings


class StripeService:

    def __init__(self):
        stripe.api_key = settings.STRIPE['SECRET_KEY']

    def create_payment_intent(self, amount_usd, transaction_number, metadata=None):
        """
        Crée un PaymentIntent Stripe.

        Args:
            amount_usd (float): Montant en USD
            transaction_number (str): Référence interne (KOULKY000001)
            metadata (dict): Données supplémentaires à stocker sur le PaymentIntent

        Returns:
            dict: { 'success': bool, 'client_secret': str, 'payment_intent_id': str, 'error': str }
        """
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(round(amount_usd * 100)),  # en centimes
                currency='usd',
                metadata={
                    'transaction_number': transaction_number,
                    **(metadata or {}),
                },
                automatic_payment_methods={'enabled': True},
            )
            return {
                'success': True,
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
            }
        except stripe.error.StripeError as e:
            return {'success': False, 'error': getattr(e, 'user_message', str(e))}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def retrieve_payment_intent(self, payment_intent_id):
        """
        Récupère un PaymentIntent par son ID.

        Returns:
            dict: { 'success': bool, 'status': str, 'transaction_number': str }
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                'success': True,
                'status': intent.status,
                'transaction_number': intent.metadata.get('transaction_number'),
            }
        except stripe.error.StripeError as e:
            return {'success': False, 'error': getattr(e, 'user_message', str(e))}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def construct_webhook_event(self, payload, sig_header):
        """
        Valide la signature et construit un événement webhook Stripe.

        Returns:
            dict: { 'success': bool, 'event': Event, 'error': str }
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE['WEBHOOK_SECRET']
            )
            return {'success': True, 'event': event}
        except stripe.error.SignatureVerificationError:
            return {'success': False, 'error': 'Invalid signature'}
        except Exception as e:
            return {'success': False, 'error': str(e)}