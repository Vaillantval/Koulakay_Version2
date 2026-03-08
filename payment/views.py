from django.http import JsonResponse, HttpResponseNotAllowed
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import redirect, render
from datetime import timedelta
import hashlib
import hmac
import json
import requests

from courses.models import Enrollment
from .models import Transaction, Payment
from .plopplop_service import PlopPlopService
from .email_service import send_enrollment_confirmation
from thinkific import Thinkific

User = get_user_model()
thinkific = Thinkific(settings.THINKIFIC['AUTH_TOKEN'], settings.THINKIFIC['SITE_ID'])


def _verify_thinkific_hmac(request):
    """
    Valide la signature HMAC-SHA256 envoyée par Thinkific dans le header
    X-Thinkific-Hmac-SHA256.
    Retourne True si valide (ou si le header est absent = source non-Thinkific).
    Retourne False si le header est présent mais la signature ne correspond pas.
    """
    signature_header = request.headers.get('X-Thinkific-Hmac-SHA256')
    if not signature_header:
        # Pas un webhook Thinkific — on laisse passer (vérification PlopPlop suit)
        return True

    secret = settings.THINKIFIC.get('SECRET_KEY', '').encode('utf-8')
    expected = hmac.new(secret, request.body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@csrf_exempt
def confirm(request):
    """
    Webhook de confirmation de paiement (appelé par PlopPlop ou Thinkific).

    Sécurité :
    - Si la requête vient de Thinkific : signature HMAC-SHA256 vérifiée.
    - Dans tous les cas : le statut du paiement est RE-VÉRIFIÉ directement
      chez PlopPlop (on ne fait jamais confiance au payload seul).
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # 1. Valider la signature HMAC si c'est un webhook Thinkific
    if not _verify_thinkific_hmac(request):
        return JsonResponse({'success': False, 'error': 'Invalid HMAC signature'}, status=401)

    try:
        payload = json.loads(request.body)
        transaction_number = payload.get('meta_data', {}).get('transaction_number')
        external_transaction_id = payload.get('external_transaction_id')

        if not transaction_number:
            return JsonResponse({'success': False, 'error': 'Transaction number is required'}, status=400)

        try:
            transaction = Transaction.objects.get(transaction_number=transaction_number)
        except Transaction.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Transaction not found'}, status=404)

        if transaction.is_completed:
            return JsonResponse({'success': True, 'message': 'Transaction already completed'}, status=200)

        if external_transaction_id:
            transaction.external_transaction_id = external_transaction_id

        # 2. Re-vérifier le statut réel du paiement chez PlopPlop
        #    On n'utilise PAS le statut du payload — un attaquant peut le forger.
        plopplop = PlopPlopService()
        verification = plopplop.verify_payment(transaction_number)

        if not verification.get('success'):
            return JsonResponse({'success': False, 'error': 'Payment verification failed with provider'}, status=502)

        if verification.get('paid'):
            return process_successful_payment(transaction, payload)

        # Paiement non confirmé chez le fournisseur
        transaction.status = Transaction.Status.FAILED
        transaction.save()
        return JsonResponse({'success': False, 'error': 'Payment not confirmed by provider'}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON payload'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Internal server error: {str(e)}'}, status=500)


def process_successful_payment(transaction, payload):
    """
    Traite un paiement réussi:
    1. Crée l'External Order dans Thinkific
    2. Crée l'enrollment dans Thinkific
    3. Crée l'enrollment local
    4. Met à jour la transaction
    """
    try:
        # Récupérer les informations du payload
        meta_data = transaction.meta_data
        user_data = meta_data.get('user', {})
        course_data = meta_data.get('course', {})
        
        user_id = user_data.get('id')
        thinkific_user_id = user_data.get('thinkific_user_id')
        course_id = course_data.get('course_id')
        product_id = course_data.get('product_id')

        # Validation des données requises
        if not all([user_id, thinkific_user_id, course_id]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required data in transaction metadata'
            }, status=400)

        # Récupérer l'utilisateur
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'User not found'
            }, status=404)

        # 1. Créer l'External Order dans Thinkific
        external_order_created = create_thinkific_external_order(
            transaction, 
            thinkific_user_id, 
            product_id or course_id
        )
        
        if not external_order_created:
            transaction.status = Transaction.Status.FAILED
            transaction.save()
            return JsonResponse({
                'success': False,
                'error': 'Failed to create External Order in Thinkific'
            }, status=500)

        # 2. Créer l'enrollment dans Thinkific
        activated_at = timezone.now()
        expiry_date = activated_at + timedelta(days=365)  # 1 an d'accès
        
        enrollment_data = {
            'user_id': thinkific_user_id,
            'course_id': course_id,
            'activated_at': activated_at.isoformat(),
            'expiry_date': expiry_date.isoformat()
        }
        
        try:
            thinkific_enrollment = thinkific.enrollments.create_enrollment(enrollment_data)
        except Exception as e:
            transaction.status = Transaction.Status.FAILED
            transaction.save()
            return JsonResponse({
                'success': False,
                'error': f'Failed to create enrollment in Thinkific: {str(e)}'
            }, status=500)

        # 3. Créer l'enrollment local
        enrollment, created = Enrollment.objects.get_or_create(
            user=user,
            thinkific_user_id=thinkific_user_id,
            course_id=course_id,
            defaults={
                'activated_at': activated_at,
                'expiry_date': expiry_date
            }
        )

        # 4. Créer le Payment (lien entre user, enrollment et transaction)
        payment, _ = Payment.objects.get_or_create(
            user=user,
            enrollment=enrollment,
            transaction=transaction
        )

        # 5. Mettre à jour la transaction
        transaction.status = Transaction.Status.COMPLETED
        transaction.completed_at = timezone.now()
        transaction.save()

        # 6. Envoyer l'email de confirmation + reçu PDF
        try:
            send_enrollment_confirmation(
                user=user,
                course_name=course_data.get('name', f'Cours #{course_id}'),
                transaction_number=transaction.transaction_number,
                amount=transaction.price,
                currency=transaction.currency,
                payment_method=transaction.payment_method or 'mobile',
                activated_at=activated_at,
                expiry_date=expiry_date,
            )
        except Exception as email_err:
            # L'email ne doit jamais bloquer la confirmation du paiement
            print(f"[KouLakay] Avertissement email : {email_err}")

        return JsonResponse({
            'success': True,
            'message': 'Payment processed successfully',
            'data': {
                'transaction_number': transaction.transaction_number,
                'enrollment_id': enrollment.id,
                'course_id': course_id
            }
        }, status=200)

    except Exception as e:
        transaction.status = Transaction.Status.FAILED
        transaction.save()
        return JsonResponse({
            'success': False,
            'error': f'Error processing payment: {str(e)}'
        }, status=500)


def create_thinkific_external_order(transaction, thinkific_user_id, product_id):
    """
    Crée un External Order dans Thinkific via l'API
    Retourne True si succès, False sinon
    """
    try:
        api_url = "https://api.thinkific.com/api/public/v1/external_orders"
        headers = {
            "X-Auth-API-Key": settings.THINKIFIC['AUTH_TOKEN'],
            "X-Auth-Subdomain": settings.THINKIFIC['SITE_ID'],
            "Content-Type": "application/json"
        }
        
        # Construire le payload
        order_data = {
            "payment_provider": transaction.get_payment_method_display(),
            "user_id": thinkific_user_id,
            "product_id": product_id,
            "order_type": "one-time",
            "transaction": {
                "amount": int(float(transaction.price) * 100),  # Montant en cents
                "currency": transaction.currency,
                "reference": transaction.transaction_number,
                "action": "purchase"
            }
        }
        
        # Faire la requête
        response = requests.post(api_url, headers=headers, json=order_data)
        response.raise_for_status()
        
        # Récupérer l'ID de l'External Order
        response_data = response.json()
        external_order_id = response_data.get('id')
        
        if external_order_id:
            transaction.thinkific_external_order_id = external_order_id
            transaction.save()
            return True
        
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"Erreur création External Order Thinkific: {e}")
        return False
    except Exception as e:
        print(f"Erreur inattendue External Order: {e}")
        return False


@csrf_exempt
def refund_transaction(request, transaction_number):
    """
    Endpoint pour rembourser une transaction
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    try:
        # Récupérer la transaction
        try:
            transaction = Transaction.objects.get(transaction_number=transaction_number)
        except Transaction.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Transaction not found'
            }, status=404)

        # Vérifier si remboursable
        if not transaction.is_refundable:
            return JsonResponse({
                'success': False,
                'error': 'Transaction cannot be refunded'
            }, status=400)

        # Parser les données de remboursement
        payload = json.loads(request.body)
        refund_amount = payload.get('amount', float(transaction.price))
        refund_reason = payload.get('reason', 'Customer request')

        # Créer le remboursement dans Thinkific si External Order existe
        if transaction.thinkific_external_order_id:
            refund_created = create_thinkific_refund(
                transaction.thinkific_external_order_id,
                refund_amount,
                transaction.currency,
                transaction.transaction_number
            )
            
            if not refund_created:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to create refund in Thinkific'
                }, status=500)

        # Mettre à jour la transaction
        transaction.status = Transaction.Status.REFUNDED
        transaction.meta_data['refund'] = {
            'amount': refund_amount,
            'reason': refund_reason,
            'refunded_at': timezone.now().isoformat()
        }
        transaction.save()

        # Désactiver l'enrollment si nécessaire
        try:
            payment = Payment.objects.get(transaction=transaction)
            enrollment = payment.enrollment
            # Vous pouvez ici désactiver l'enrollment dans Thinkific
            # thinkific.enrollments.delete_enrollment(enrollment_id)
        except Payment.DoesNotExist:
            pass

        return JsonResponse({
            'success': True,
            'message': 'Transaction refunded successfully',
            'data': {
                'transaction_number': transaction.transaction_number,
                'refund_amount': refund_amount
            }
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON payload'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error processing refund: {str(e)}'
        }, status=500)


def create_thinkific_refund(external_order_id, amount, currency, reference):
    """
    Crée un remboursement dans Thinkific
    """
    try:
        api_url = f"https://api.thinkific.com/api/public/v1/external_orders/{external_order_id}/transactions/refund"
        headers = {
            "X-Auth-API-Key": settings.THINKIFIC['AUTH_TOKEN'],
            "X-Auth-Subdomain": settings.THINKIFIC['SITE_ID'],
            "Content-Type": "application/json"
        }
        
        refund_data = {
            "amount": int(float(amount) * 100),  # Montant en cents
            "currency": currency,
            "reference": f"REFUND-{reference}",
            "action": "refund"
        }
        
        response = requests.post(api_url, headers=headers, json=refund_data)
        response.raise_for_status()
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Erreur création remboursement Thinkific: {e}")
        return False
    except Exception as e:
        print(f"Erreur inattendue remboursement: {e}")
        return False





def payment_return(request):
    """
    Vue de retour après paiement plopplop.
    L'utilisateur est redirigé ici après avoir payé (ou annulé) sur plopplop.
    On vérifie le statut via /api/paiement-verify, puis on traite l'inscription.
    """
    # plopplop peut transmettre la référence en GET ou POST
    refference_id = request.GET.get('refference_id') or request.POST.get('refference_id')

    if not refference_id:
        messages.error(request, "Référence de paiement introuvable.")
        return redirect('courses')

    try:
        transaction = Transaction.objects.get(transaction_number=refference_id)
    except Transaction.DoesNotExist:
        messages.error(request, "Transaction introuvable.")
        return redirect('courses')

    # Si déjà traitée, ne pas re-traiter
    if transaction.is_completed:
        messages.info(request, "Ce paiement a déjà été traité.")
        course_id = transaction.course_id
        if course_id:
            return redirect('course_details', course_id=course_id)
        return redirect('courses')

    # Vérifier le statut sur plopplop
    plopplop = PlopPlopService()
    result = plopplop.verify_payment(refference_id)

    course_id = transaction.course_id

    if result.get('paid'):
        # Paiement confirmé → traiter l'inscription (ignore la JsonResponse)
        process_successful_payment(transaction, {})
        messages.success(request, "Paiement confirmé ! Votre accès au cours est activé. Un email de confirmation vous a été envoyé.")
        return redirect('success_page')
    elif not result.get('success'):
        messages.error(request, f"Erreur de vérification : {result.get('error', 'Inconnue')}")
        return redirect('course_details', course_id=course_id) if course_id else redirect('courses')
    else:
        # Paiement en cours ou annulé
        messages.warning(request, "Votre paiement n'a pas encore été confirmé. Veuillez réessayer dans quelques instants.")
        return redirect('course_details', course_id=course_id) if course_id else redirect('courses')
