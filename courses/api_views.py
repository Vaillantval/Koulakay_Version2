"""
API mobile — Catalogue (Phase 1, lecture seule).

Réutilise les helpers métier de courses.views (prix, durée d'accès, contenu,
bundles, traductions) pour exposer le catalogue en JSON, sans dupliquer la logique.
Endpoints publics (AllowAny) : un visiteur non connecté peut parcourir le catalogue ;
le statut « enrolled » n'est renseigné que si la requête est authentifiée (JWT).
"""
from django.conf import settings
from django.utils import translation
from django.db.models import Count

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from pages.models import SiteConfig
from .models import (
    Enrollment, CourseCategory, CourseCategoryMembership,
    BundleCategoryMembership, CourseVisibility,
)
from .views import (
    thinkific,
    _format_access_duration,
    _price_in_currency,
    _build_currency_map,
    _fetch_course_content,
    _fetch_bundle_details,
    _fetch_bundle_courses,
    apply_course_translations,
    _sync_user_enrollments,
)
from .api_serializers import (
    EnrolledCourseSerializer, EnrollResultSerializer, SSOUrlSerializer,
)
from . import api_cache
import copy

_LANG_PARAM = OpenApiParameter(
    name='lang', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False,
    description="Langue du contenu (fr, en, es, ht). Défaut : fr.",
)


def _activate_lang(request):
    """Active la langue depuis ?lang= si fournie et valide."""
    lang = request.GET.get('lang')
    valid = {code for code, _ in getattr(settings, 'LANGUAGES', [])}
    if lang and lang in valid:
        translation.activate(lang)
    return lang


def _enrolled_ids(request):
    if request.user and request.user.is_authenticated:
        return set(Enrollment.objects.filter(user=request.user).values_list('course_id', flat=True))
    return set()


def _serialize_course(c, price_map, access_map, currency_map, site_currency,
                      enrolled_ids, popular_counts, categories_map):
    cid = c.get('id')
    raw_price = price_map.get(cid)
    price_str, disp_curr = _price_in_currency(raw_price, cid, currency_map, site_currency)
    return {
        'id': cid,
        'name': c.get('name'),
        'slug': c.get('slug') or '',
        'description': c.get('description', '') or '',
        'image_url': c.get('course_card_image_url') or c.get('banner_image_url') or '',
        'price': price_str,
        'currency': disp_curr,
        'is_free': raw_price is None or float(raw_price) == 0,
        'access_duration': access_map.get(cid),  # None = accès à vie
        'enrolled': cid in enrolled_ids,
        'enrollment_count': popular_counts.get(cid, 0),
        'categories': categories_map.get(cid, []),
    }


@extend_schema(
    summary="Liste des cours", operation_id="courses_list",
    description="Catalogue des cours visibles (prix, durée d'accès, catégories).",
    parameters=[_LANG_PARAM],
    responses=OpenApiTypes.OBJECT,
    tags=['Catalogue'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def course_list(request):
    _activate_lang(request)
    # deepcopy : apply_course_translations modifie les dicts → ne pas corrompre le cache
    items = copy.deepcopy(api_cache.courses_list())

    hidden = set(CourseVisibility.objects.filter(is_visible=False).values_list('course_id', flat=True))
    items = [c for c in items if c.get('id') not in hidden]

    products = api_cache.products_list()

    price_map = {p['productable_id']: p['price'] for p in products
                 if p.get('productable_id') and p.get('price') is not None}
    access_map = {p['productable_id']: _format_access_duration(p.get('days_until_expiry'))
                  for p in products if p.get('productable_id')}

    site_currency = SiteConfig.get().currency
    currency_map = _build_currency_map()
    enrolled = _enrolled_ids(request)
    popular = {row['course_id']: row['num'] for row in
               Enrollment.objects.values('course_id').annotate(num=Count('course_id'))}

    cat_map = {}
    for m in CourseCategoryMembership.objects.select_related('category').filter(category__is_active=True):
        cat_map.setdefault(m.course_id, []).append(m.category.slug)

    apply_course_translations(items)
    data = [_serialize_course(c, price_map, access_map, currency_map, site_currency,
                              enrolled, popular, cat_map) for c in items]
    return Response({'count': len(data), 'results': data})


@extend_schema(
    summary="Détail d'un cours", operation_id="courses_retrieve",
    description="Détails d'un cours + programme (chapitres et leçons) + instructeur.",
    parameters=[_LANG_PARAM],
    responses=OpenApiTypes.OBJECT,
    tags=['Catalogue'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def course_detail(request, course_id):
    _activate_lang(request)
    import requests as _requests
    try:
        course = copy.deepcopy(api_cache.retrieve_course(course_id))
    except _requests.exceptions.HTTPError as e:
        if getattr(e, 'response', None) is not None and e.response.status_code == 404:
            return Response({'detail': 'Cours introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        raise

    site_currency = SiteConfig.get().currency
    currency_map = _build_currency_map()
    price_str, disp_curr, access_duration = None, site_currency, None
    try:
        for p in api_cache.products_list():
            if p.get('productable_id') == course_id:
                if p.get('price') is not None:
                    price_str, disp_curr = _price_in_currency(p['price'], course_id, currency_map, site_currency)
                access_duration = _format_access_duration(p.get('days_until_expiry'))
                break
    except Exception:
        pass

    apply_course_translations(course)
    content = api_cache.course_content(course_id)

    instructor = None
    instructor_id = course.get('instructor_id')
    if instructor_id:
        try:
            ins = thinkific.instructors.retrieve_instructor(id=instructor_id)
            instructor = {'first_name': ins.get('first_name', ''), 'last_name': ins.get('last_name', ''),
                          'bio': ins.get('bio', '')}
        except Exception:
            instructor = None

    return Response({
        'id': course_id,
        'name': course.get('name'),
        'slug': course.get('slug') or '',
        'description': course.get('description', '') or '',
        'image_url': course.get('course_card_image_url') or course.get('banner_image_url') or '',
        'price': price_str,
        'currency': disp_curr,
        'is_free': price_str is None,
        'access_duration': access_duration,
        'enrolled': course_id in _enrolled_ids(request),
        'instructor': instructor,
        'chapters': content,
        'nb_chapters': len(content),
        'nb_lessons': sum(len(c.get('children', [])) for c in content),
    })


@extend_schema(
    summary="Programme d'un cours", operation_id="courses_content",
    description="Chapitres + leçons d'un cours (léger).",
    responses=OpenApiTypes.OBJECT,
    tags=['Catalogue'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def course_content(request, course_id):
    _activate_lang(request)
    content = api_cache.course_content(course_id)
    return Response({
        'chapters': content,
        'nb_chapters': len(content),
        'nb_lessons': sum(len(c.get('children', [])) for c in content),
    })


@extend_schema(
    summary="Liste des catégories", operation_id="categories_list",
    responses=OpenApiTypes.OBJECT,
    tags=['Catalogue'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def category_list(request):
    _activate_lang(request)
    cats = CourseCategory.objects.filter(is_active=True).order_by('order', 'name')
    data = [{
        'name': c.name,
        'slug': c.slug,
        'description': c.description or '',
        'icon': c.icon or '',
        'color': c.color or '',
        'image_url': c.image.url if c.image else '',
    } for c in cats]
    return Response({'count': len(data), 'results': data})


@extend_schema(
    summary="Liste des offres groupées (bundles)", operation_id="bundles_list",
    parameters=[_LANG_PARAM],
    responses=OpenApiTypes.OBJECT,
    tags=['Catalogue'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def bundle_list(request):
    _activate_lang(request)
    products = api_cache.products_list()
    hidden = set(CourseVisibility.objects.filter(is_visible=False).values_list('course_id', flat=True))
    currency_map = _build_currency_map()
    enrolled = _enrolled_ids(request)

    bcat_map = {}
    for m in BundleCategoryMembership.objects.select_related('category').filter(category__is_active=True):
        bcat_map.setdefault(m.bundle_id, []).append(m.category.slug)

    data = []
    for bp in [p for p in products if p.get('productable_type') == 'Bundle']:
        bid = bp.get('productable_id')
        if not bid or bid in hidden:
            continue
        try:
            info = _fetch_bundle_details(bid)
            courses = _fetch_bundle_courses(bid)
            raw_price = bp.get('price')
            course_ids = info.get('course_ids', [])
            price_str, disp_curr = _price_in_currency(raw_price, bid, currency_map, 'HTG')
            data.append({
                'id': bid,
                'name': info.get('name', f'Bundle #{bid}'),
                'image_url': info.get('bundle_card_image_url') or '',
                'slug': info.get('slug') or '',
                'price': price_str,
                'currency': disp_curr,
                'is_free': raw_price is None or float(raw_price) == 0,
                'access_duration': _format_access_duration(bp.get('days_until_expiry')),
                'course_ids': course_ids,
                'courses': courses,
                'all_enrolled': bool(course_ids) and all(c in enrolled for c in course_ids),
                'categories': bcat_map.get(bid, []),
            })
        except Exception as e:
            print(f"[api bundle] {bid}: {e}")
    return Response({'count': len(data), 'results': data})


# ══════════════════════════════════════════════════════════════════
#  Phase 3 — Inscriptions, Mon Apprentissage, accès SSO (WebView)
# ══════════════════════════════════════════════════════════════════

def _resolve_thinkific_user_id(user):
    """Retourne le thinkific_user_id du user (le retrouve par email si absent)."""
    if user.thinkific_user_id:
        return user.thinkific_user_id
    from accounts.views import get_thinkific_user_by_email
    tk = get_thinkific_user_by_email(user.email)
    if tk and tk.get('id'):
        user.thinkific_user_id = tk['id']
        user.save(update_fields=['thinkific_user_id'])
        return tk['id']
    return None


def _course_price_days(course_id):
    """(price float|0, days_until_expiry int|None, name) pour un cours."""
    price, days, name = 0.0, None, f'Cours #{course_id}'
    try:
        c = thinkific.courses.retrieve_course(id=course_id)
        name = c.get('name', name)
    except Exception:
        pass
    try:
        for p in thinkific.products.list(limit=100).get('items', []):
            if p.get('productable_id') == course_id:
                if p.get('price') is not None:
                    price = float(p['price'])
                days = p.get('days_until_expiry')
                break
    except Exception:
        pass
    return price, days, name


@extend_schema(
    summary="Mes cours (Mon Apprentissage)", operation_id="my_enrollments",
    description="Cours auxquels l'utilisateur connecté est inscrit (source : Thinkific, fallback DB).",
    parameters=[_LANG_PARAM], responses=EnrolledCourseSerializer(many=True), tags=['Apprentissage'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_enrollments(request):
    _activate_lang(request)
    user = request.user
    _sync_user_enrollments(user, request)

    # Maps (depuis le cache API)
    course_map = {c['id']: c for c in api_cache.courses_list() if c.get('id')}
    price_map, access_map, product_days = {}, {}, {}
    try:
        for p in api_cache.products_list():
            cid = p.get('productable_id')
            if not cid:
                continue
            if p.get('price') is not None:
                price_map[cid] = float(p['price'])
            days = p.get('days_until_expiry')
            if cid not in product_days or days is not None:
                product_days[cid] = int(days) if days else None
                access_map[cid] = _format_access_duration(days) if days else None
    except Exception:
        pass

    site_currency = SiteConfig.get().currency
    currency_map = _build_currency_map()
    results = []

    from datetime import datetime, timedelta
    def _pd(v):
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except Exception:
                return None
        return v

    tk_id = user.thinkific_user_id
    items = []
    if tk_id:
        try:
            items = thinkific.enrollments.list(user_id=tk_id, limit=100).get('items', [])
        except Exception as e:
            print(f"[api my_enrollments] {e}")

    if items:
        for it in items:
            info = it.get('course') or {}
            cid = it.get('course_id') or info.get('id')
            if not cid:
                continue
            full = course_map.get(cid, {})
            activated = _pd(it.get('activated_at'))
            expiry = _pd(it.get('expiry_date'))
            if expiry is None and product_days.get(cid) and activated:
                expiry = activated + timedelta(days=product_days[cid])
            lifetime = (product_days[cid] is None) if cid in product_days else (expiry is None)
            price_str, curr = _price_in_currency(price_map.get(cid), cid, currency_map, site_currency)
            results.append({
                'id': cid,
                'name': full.get('name') or info.get('name', f'Cours #{cid}'),
                'slug': full.get('slug') or info.get('slug', '') or '',
                'image_url': full.get('banner_image_url') or full.get('course_card_image_url') or '',
                'price': price_str, 'currency': curr,
                'activated_at': activated, 'expiry_date': expiry, 'lifetime': lifetime,
                'access_duration': access_map.get(cid),
                'percentage_completed': round(float(it.get('percentage_completed') or 0) * 100),
            })
    else:
        # Fallback DB locale
        for e in Enrollment.objects.filter(user=user).order_by('-activated_at'):
            full = course_map.get(e.course_id, {})
            price_str, curr = _price_in_currency(price_map.get(e.course_id), e.course_id, currency_map, site_currency)
            results.append({
                'id': e.course_id,
                'name': full.get('name', f'Cours #{e.course_id}'),
                'slug': full.get('slug', '') or '',
                'image_url': full.get('banner_image_url') or full.get('course_card_image_url') or '',
                'price': price_str, 'currency': curr,
                'activated_at': e.activated_at, 'expiry_date': e.expiry_date,
                'lifetime': product_days.get(e.course_id) is None,
                'access_duration': access_map.get(e.course_id),
                'percentage_completed': 0,
            })

    return Response({'count': len(results), 'results': results})


@extend_schema(
    summary="S'inscrire à un cours", operation_id="enroll_course",
    description="Inscription gratuite directe ; pour un cours payant, renvoie requires_payment.",
    request=None, responses=EnrollResultSerializer, tags=['Apprentissage'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enroll_course(request, course_id):
    user = request.user
    # 1) Déjà inscrit ? (check local, ne nécessite pas Thinkific)
    _sync_user_enrollments(user, request)
    if Enrollment.objects.filter(user=user, course_id=course_id).exists():
        return Response({'enrolled': True, 'already_enrolled': True, 'course_id': course_id})

    # 2) Profil Thinkific requis pour inscrire
    tk_id = _resolve_thinkific_user_id(user)
    if not tk_id:
        return Response({'detail': "Profil Thinkific introuvable."}, status=status.HTTP_400_BAD_REQUEST)

    price, days, name = _course_price_days(course_id)
    site_currency = SiteConfig.get().currency
    currency_map = _build_currency_map()

    if price and price > 0:
        price_str, curr = _price_in_currency(price, course_id, currency_map, site_currency)
        return Response({'requires_payment': True, 'course_id': course_id,
                         'price': price, 'currency': curr}, status=status.HTTP_200_OK)

    # Gratuit → inscription réelle
    from django.utils import timezone
    from datetime import timedelta
    activated = timezone.now()
    expiry = activated + timedelta(days=int(days)) if days else activated.replace(year=activated.year + 10)
    payload = {'course_id': course_id, 'user_id': tk_id, 'activated_at': activated.isoformat()}
    if days:
        payload['expiry_date'] = expiry.isoformat()
    try:
        thinkific.enrollments.create_enrollment(payload)
    except Exception as e:
        return Response({'detail': f"Échec de l'inscription Thinkific : {e}"},
                        status=status.HTTP_502_BAD_GATEWAY)
    Enrollment.objects.get_or_create(
        user=user, thinkific_user_id=tk_id, course_id=course_id,
        defaults={'activated_at': activated, 'expiry_date': expiry},
    )
    # Emails (non bloquant)
    try:
        from payment.email_service import send_enrollment_confirmation
        import uuid
        send_enrollment_confirmation(
            user=user, course_name=name,
            transaction_number=f"GRATUIT-{activated.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            amount=0, currency=site_currency, payment_method='Accès gratuit',
            activated_at=activated, expiry_date=expiry if days else None,
        )
    except Exception as e:
        print(f"[api enroll] email: {e}")
    try:
        from accounts.admin_notify import notify_admin_new_enrollment
        notify_admin_new_enrollment(user=user, course_name=name, is_free=True,
                                    payment_method='Accès gratuit (API)', activated_at=activated)
    except Exception as e:
        print(f"[api enroll] notif: {e}")
    try:
        from accounts.push_service import send_push_to_user
        send_push_to_user(user, "Inscription confirmée 🎓", f"Vous avez accès à « {name} ».",
                          data={'type': 'enrollment', 'route': 'course', 'id': str(course_id)})
    except Exception as e:
        print(f"[api enroll] push: {e}")

    return Response({'enrolled': True, 'course_id': course_id}, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Accès au cours (URL SSO pour WebView)", operation_id="course_access",
    description="Renvoie l'URL SSO Thinkific à ouvrir dans une WebView. Requiert d'être inscrit.",
    responses=SSOUrlSerializer, tags=['Apprentissage'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def course_access(request, course_id):
    user = request.user
    _sync_user_enrollments(user, request)
    if not Enrollment.objects.filter(user=user, course_id=course_id).exists():
        return Response({'detail': "Vous n'êtes pas inscrit à ce cours."},
                        status=status.HTTP_403_FORBIDDEN)
    slug = ''
    try:
        slug = (thinkific.courses.retrieve_course(id=course_id) or {}).get('slug', '') or ''
    except Exception:
        pass
    return_to = f"/courses/take/{slug}" if slug else '/enrollments'
    from accounts.views import build_thinkific_sso_url
    try:
        url, reason = build_thinkific_sso_url(user, return_to)
    except Exception as e:
        return Response({'detail': f"Erreur SSO : {e}"}, status=status.HTTP_502_BAD_GATEWAY)
    if reason == 'not_linked':
        return Response({'detail': "Compte non lié à Thinkific."}, status=status.HTTP_400_BAD_REQUEST)
    return Response({'sso_url': url})


@extend_schema(
    summary="S'inscrire à un bundle", operation_id="enroll_bundle",
    description="Bundle gratuit : inscrit tous les cours ; payant : renvoie requires_payment.",
    request=None, responses=EnrollResultSerializer, tags=['Apprentissage'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enroll_bundle(request, bundle_id):
    user = request.user
    tk_id = _resolve_thinkific_user_id(user)
    if not tk_id:
        return Response({'detail': "Profil Thinkific introuvable."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        products = thinkific.products.list(limit=100).get('items', [])
    except Exception:
        products = []
    bundle_product = next((p for p in products
                           if p.get('productable_id') == bundle_id and p.get('productable_type') == 'Bundle'), None)
    if not bundle_product:
        return Response({'detail': "Bundle introuvable."}, status=status.HTTP_404_NOT_FOUND)

    raw_price = bundle_product.get('price')
    info = _fetch_bundle_details(bundle_id)
    course_ids = info.get('course_ids', [])
    site_currency = SiteConfig.get().currency
    currency_map = _build_currency_map()

    if raw_price and float(raw_price) > 0:
        price_str, curr = _price_in_currency(raw_price, bundle_id, currency_map, 'HTG')
        return Response({'requires_payment': True, 'bundle_id': bundle_id,
                         'price': float(raw_price), 'currency': curr}, status=status.HTTP_200_OK)

    # Gratuit → inscrire chaque cours
    from django.utils import timezone
    activated = timezone.now()
    expiry = activated.replace(year=activated.year + 10)
    for cid in course_ids:
        try:
            thinkific.enrollments.create_enrollment(
                {'course_id': cid, 'user_id': tk_id, 'activated_at': activated.isoformat()})
            Enrollment.objects.get_or_create(
                user=user, thinkific_user_id=tk_id, course_id=cid,
                defaults={'activated_at': activated, 'expiry_date': expiry})
        except Exception as e:
            print(f"[api enroll_bundle] cours {cid}: {e}")
    try:
        from accounts.push_service import send_push_to_user
        send_push_to_user(user, "Inscription confirmée 🎓",
                          f"Vous avez accès à « {info.get('name', 'votre offre groupée')} ».",
                          data={'type': 'enrollment', 'route': 'bundle', 'id': str(bundle_id)})
    except Exception as e:
        print(f"[api enroll_bundle] push: {e}")
    return Response({'enrolled': True, 'bundle_id': bundle_id}, status=status.HTTP_201_CREATED)
