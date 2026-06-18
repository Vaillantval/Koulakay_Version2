import requests as http_requests
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token

from .authentication import verify_firebase_token
from courses.models import Enrollment, CourseVisibility

User = get_user_model()

_thinkific = None


def _tk():
    global _thinkific
    if _thinkific is None:
        from courses.monkey_patch.patch_thinkific import ThinkificExtend
        _thinkific = ThinkificExtend(
            settings.THINKIFIC['AUTH_TOKEN'],
            settings.THINKIFIC['SITE_ID'],
        )
    return _thinkific


def _user_dict(user):
    role = 'Admin' if user.is_superuser else ('Enseignant' if user.is_staff else 'Etudiant')
    return {
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name or '',
        'last_name': user.last_name or '',
        'role': role,
    }


# ── Auth ──────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get('email', '').lower().strip()
    password = request.data.get('password', '')

    if not email or not password:
        return Response({'error': 'Email ak modpas obligatwa'}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=email, password=password)
    if user is None:
        return Response({'error': 'Email oswa modpas pa kòrèk'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_active:
        return Response({'error': 'Kont sa a dezaktive'}, status=status.HTTP_403_FORBIDDEN)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': _user_dict(user)})


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    email = request.data.get('email', '').lower().strip()
    password = request.data.get('password', '')
    first_name = request.data.get('first_name', '').strip()
    last_name = request.data.get('last_name', '').strip()

    if not email or not password:
        return Response({'error': 'Email ak modpas obligatwa'}, status=status.HTTP_400_BAD_REQUEST)

    if len(password) < 8:
        return Response({'error': 'Modpas a dwe gen omwen 8 karaktè'}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(email=email).exists():
        return Response({'error': 'Email sa a deja itilize'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )

    try:
        from allauth.account.models import EmailAddress
        EmailAddress.objects.create(user=user, email=email, primary=True, verified=True)
    except Exception:
        pass

    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': _user_dict(user)}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset(request):
    email = request.data.get('email', '').lower().strip()
    if not email:
        return Response({'error': 'Email obligatwa'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"https://koulakay.ht/fr/accounts/password/reset/key/{uid}-{token}/"
        send_mail(
            subject='Reinisyalize modpas KouLakay ou',
            message=(
                f'Bonjou {user.first_name or user.email},\n\n'
                f'Klike sou lyen sa a pou reinisyalize modpas ou:\n{reset_url}\n\n'
                'Si ou pa mande sa, inyore mesaj sa a.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except User.DoesNotExist:
        pass

    return Response({'message': 'Si email la egziste, yon mesaj ap voye.'})


@api_view(['POST'])
@permission_classes([AllowAny])
def firebase_auth(request):
    firebase_token = request.data.get('firebase_token', '').strip()
    if not firebase_token:
        return Response({'error': 'firebase_token obligatwa'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        claims = verify_firebase_token(firebase_token)
    except Exception as exc:
        return Response({'error': str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

    email = claims.get('email', '').lower()
    if not email:
        return Response({'error': 'Token pa gen email'}, status=status.HTTP_400_BAD_REQUEST)

    name = claims.get('name', '')
    parts = name.split(' ', 1) if name else ['', '']
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ''

    user, created = User.objects.get_or_create(
        email=email,
        defaults={'first_name': first_name, 'last_name': last_name},
    )
    if not created and (not user.first_name) and first_name:
        user.first_name = first_name
        user.last_name = last_name
        user.save(update_fields=['first_name', 'last_name'])

    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': _user_dict(user)})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me(request):
    if request.method == 'PATCH':
        u = request.user
        if 'first_name' in request.data:
            u.first_name = request.data['first_name'].strip()
        if 'last_name' in request.data:
            u.last_name = request.data['last_name'].strip()
        u.save(update_fields=['first_name', 'last_name'])

    u = request.user
    enrolled_ids = list(Enrollment.objects.filter(user=u).values_list('course_id', flat=True))
    data = _user_dict(u)
    data['enrolled_course_ids'] = enrolled_ids
    return Response(data)


# ── Courses ───────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def courses_list(request):
    try:
        all_items = []
        page = 1
        while True:
            resp = _tk().courses.list(limit=25, page=page)
            items = resp.get('items', [])
            all_items.extend(items)
            meta = resp.get('meta', {}).get('pagination', {})
            if page >= (meta.get('total_pages') or 1):
                break
            page += 1

        hidden_ids = set(
            CourseVisibility.objects.filter(is_visible=False).values_list('course_id', flat=True)
        )
        visible = [c for c in all_items if c.get('id') not in hidden_ids]
        return Response({'courses': visible, 'total': len(visible)})
    except Exception as exc:
        return Response({'error': str(exc), 'courses': []}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def course_detail(request, course_id):
    try:
        course = _tk().courses.retrieve_course(id=course_id)
        return Response(course)
    except Exception as exc:
        return Response({'error': str(exc)}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([AllowAny])
def course_chapters(request, course_id):
    try:
        resp = _tk().chapters.list(course_id=course_id)
        chapters = resp.get('items', [])
        return Response({'chapters': chapters})
    except Exception as exc:
        return Response({'error': str(exc), 'chapters': []}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def chapter_contents(request, chapter_id):
    try:
        headers = {
            'Authorization': f'Bearer {settings.THINKIFIC["AUTH_TOKEN"]}',
            'X-Auth-Subdomain': settings.THINKIFIC['SITE_ID'],
            'Content-Type': 'application/json',
        }
        resp = http_requests.get(
            'https://api.thinkific.com/api/public/v1/contents',
            params={'query[chapter_id]': chapter_id},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        contents = resp.json().get('items', [])
        return Response({'contents': contents})
    except Exception as exc:
        return Response({'error': str(exc), 'contents': []}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ── Enrollments ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def enrollments_list(request):
    from django.utils import timezone as dj_tz
    rows = Enrollment.objects.filter(user=request.user).values('course_id', 'activated_at', 'expiry_date')
    now = dj_tz.now()
    data = [
        {
            'course_id': r['course_id'],
            'activated_at': r['activated_at'].isoformat() if r['activated_at'] else None,
            'expiry_date': r['expiry_date'].isoformat() if r['expiry_date'] else None,
            'is_active': r['expiry_date'] > now if r['expiry_date'] else True,
        }
        for r in rows
    ]
    return Response({'enrollments': data})
