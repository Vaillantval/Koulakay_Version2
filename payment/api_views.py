"""
API mobile — Paiement (Phase 4).

Flux mobile :
  1. POST /payments/init/        → crée la Transaction + appelle PlopPlop → renvoie payment_url
  2. (app ouvre payment_url dans une WebView ; l'utilisateur paie)
  3. POST /payments/{ref}/verify/ → vérifie chez PlopPlop, active l'inscription (idempotent)
  4. GET  /payments/{ref}/status/ → état courant (pour polling)

Réutilise la même logique que le web : meta_data identique, PlopPlopService,
process_successful_payment (inscription Thinkific + emails + notif admin).
"""
from decimal import Decimal

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from pages.models import SiteConfig
from courses.models import Enrollment
from courses.views import thinkific, _fetch_bundle_details
from courses.api_views import _resolve_thinkific_user_id, _course_price_days

from .models import Transaction
from .plopplop_service import PlopPlopService
from .exchange_service import convert_to_htg
from .api_serializers import (
    PaymentInitSerializer, PaymentInitResponseSerializer, PaymentStatusSerializer,
)


def _product_id_for(productable_id):
    """Retourne l'id du produit Thinkific pour un course/bundle (pour le External Order)."""
    try:
        for p in thinkific.products.list(limit=100).get('items', []):
            if p.get('productable_id') == productable_id:
                return p.get('id')
    except Exception:
        pass
    return None


def _status_payload(tx):
    return {
        'transaction_number': tx.transaction_number,
        'status': tx.status,
        'paid': tx.status == Transaction.Status.COMPLETED,
        'course_id': (tx.meta_data.get('course') or {}).get('course_id'),
        'bundle_id': (tx.meta_data.get('bundle') or {}).get('bundle_id'),
        'provider_transaction_id': tx.provider_transaction_id,
    }


@extend_schema(
    summary="Initier un paiement (MonCash/NatCash)", operation_id="payment_init",
    request=PaymentInitSerializer, responses=PaymentInitResponseSerializer, tags=['Paiement'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payment_init(request):
    s = PaymentInitSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    method = d['payment_method']
    user = request.user

    tk_id = _resolve_thinkific_user_id(user)
    if not tk_id:
        return Response({'detail': "Profil Thinkific introuvable."}, status=status.HTTP_400_BAD_REQUEST)

    site_currency = SiteConfig.get().currency

    # ── Construire le contexte (cours ou bundle) ──
    if d.get('course_id'):
        course_id = d['course_id']
        if Enrollment.objects.filter(user=user, course_id=course_id).exists():
            return Response({'detail': "Vous êtes déjà inscrit à ce cours."},
                            status=status.HTTP_400_BAD_REQUEST)
        price, _days, name = _course_price_days(course_id)
        if not price or price <= 0:
            return Response({'detail': "Cours gratuit : utilisez l'inscription directe."},
                            status=status.HTTP_400_BAD_REQUEST)
        course_price = Decimal(str(price))
        meta = {
            "course": {"course_id": course_id, "course_name": name,
                       "product_id": _product_id_for(course_id)},
            "user": {"id": user.pk, "email": user.email, "thinkific_user_id": tk_id},
        }
    else:
        bundle_id = d['bundle_id']
        info = _fetch_bundle_details(bundle_id)
        course_ids = info.get('course_ids', [])
        # prix du bundle
        raw_price = None
        for p in thinkific.products.list(limit=100).get('items', []):
            if p.get('productable_id') == bundle_id and p.get('productable_type') == 'Bundle':
                raw_price = p.get('price'); break
        if not raw_price or float(raw_price) <= 0:
            return Response({'detail': "Bundle gratuit : utilisez l'inscription directe."},
                            status=status.HTTP_400_BAD_REQUEST)
        course_price = Decimal(str(raw_price))
        meta = {
            "bundle": {"bundle_id": bundle_id, "bundle_name": info.get('name', f'Bundle #{bundle_id}'),
                       "bundle_course_ids": course_ids, "product_id": _product_id_for(bundle_id)},
            "user": {"id": user.pk, "email": user.email, "thinkific_user_id": tk_id},
        }

    # ── Montant en HTG (PlopPlop) ──
    if site_currency == 'HTG':
        montant_htg = float(course_price)
    else:
        montant_htg = convert_to_htg(course_price, site_currency)
        if montant_htg is None:
            return Response({'detail': "Taux de change indisponible, réessayez."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

    tx = Transaction.objects.create(
        user=user, price=Decimal(str(montant_htg)),
        currency=Transaction.Currencies.HTG, status=Transaction.Status.PENDING,
        payment_method=method, meta_data=meta,
    )

    result = PlopPlopService().create_payment(
        refference_id=tx.transaction_number, montant=float(montant_htg), payment_method=method,
    )
    if not result.get('success'):
        tx.status = Transaction.Status.FAILED
        tx.save(update_fields=['status'])
        return Response({'detail': "Création du paiement échouée : " + result.get('error', '')},
                        status=status.HTTP_502_BAD_GATEWAY)

    tx.external_transaction_id = result.get('transaction_id')
    tx.save(update_fields=['external_transaction_id'])
    return Response({'transaction_number': tx.transaction_number,
                     'payment_url': result.get('url'), 'status': tx.status},
                    status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Vérifier un paiement et activer l'accès", operation_id="payment_verify",
    request=None, responses=PaymentStatusSerializer, tags=['Paiement'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payment_verify(request, transaction_number):
    try:
        tx = Transaction.objects.get(transaction_number=transaction_number, user=request.user)
    except Transaction.DoesNotExist:
        return Response({'detail': "Transaction introuvable."}, status=status.HTTP_404_NOT_FOUND)

    if tx.status == Transaction.Status.COMPLETED:
        return Response(_status_payload(tx))

    result = PlopPlopService().verify_payment(transaction_number)
    if not result.get('success'):
        return Response({'detail': "Vérification échouée : " + result.get('error', '')},
                        status=status.HTTP_502_BAD_GATEWAY)

    if result.get('paid'):
        id_tx = result.get('id_transaction')
        if id_tx and not tx.provider_transaction_id:
            tx.provider_transaction_id = str(id_tx)
            tx.save(update_fields=['provider_transaction_id'])
        from .views import process_successful_payment
        proc = process_successful_payment(tx, {})
        tx.refresh_from_db()
        if not proc.get('success'):
            return Response({**_status_payload(tx), 'detail': proc.get('error', 'Activation échouée')},
                            status=status.HTTP_502_BAD_GATEWAY)
        return Response(_status_payload(tx))

    # Pas encore payé / annulé
    return Response(_status_payload(tx))


@extend_schema(
    summary="État d'un paiement (polling)", operation_id="payment_status",
    responses=PaymentStatusSerializer, tags=['Paiement'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_status(request, transaction_number):
    try:
        tx = Transaction.objects.get(transaction_number=transaction_number, user=request.user)
    except Transaction.DoesNotExist:
        return Response({'detail': "Transaction introuvable."}, status=status.HTTP_404_NOT_FOUND)
    return Response(_status_payload(tx))
