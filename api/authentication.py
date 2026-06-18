import time
import requests
import jwt
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

GOOGLE_CERTS_URL = (
    'https://www.googleapis.com/robot/v1/metadata/x509/'
    'securetoken@system.gserviceaccount.com'
)

_certs_cache: dict = {}
_certs_expiry: float = 0.0


def _get_google_certs() -> dict:
    global _certs_cache, _certs_expiry
    now = time.time()
    if now < _certs_expiry and _certs_cache:
        return _certs_cache

    resp = requests.get(GOOGLE_CERTS_URL, timeout=10)
    resp.raise_for_status()

    max_age = 3600
    for part in resp.headers.get('Cache-Control', '').split(','):
        part = part.strip()
        if part.startswith('max-age='):
            try:
                max_age = int(part[8:])
            except ValueError:
                pass

    _certs_cache = resp.json()
    _certs_expiry = now + max_age
    return _certs_cache


def verify_firebase_token(id_token: str) -> dict:
    """
    Verifye yon Firebase ID token epi retounen claims yo.
    Leve AuthenticationFailed si token an pa valid.
    """
    project_id = getattr(settings, 'FIREBASE_PROJECT_ID', 'examhaiti')

    try:
        header = jwt.get_unverified_header(id_token)
    except jwt.exceptions.DecodeError as exc:
        raise AuthenticationFailed(f'Token header invalide: {exc}')

    kid = header.get('kid')
    if not kid:
        raise AuthenticationFailed('Token manke champ kid')

    try:
        certs = _get_google_certs()
    except Exception as exc:
        raise AuthenticationFailed(f'Enposib verifye sètifika Google: {exc}')

    if kid not in certs:
        raise AuthenticationFailed('kid pa jwenn nan sètifika Google yo')

    public_key_pem = certs[kid]

    try:
        payload = jwt.decode(
            id_token,
            public_key_pem,
            algorithms=['RS256'],
            audience=project_id,
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed('Token ekspire')
    except jwt.InvalidAudienceError:
        raise AuthenticationFailed('Token audience pa valid')
    except jwt.InvalidTokenError as exc:
        raise AuthenticationFailed(f'Token pa valid: {exc}')

    expected_issuer = f'https://securetoken.google.com/{project_id}'
    if payload.get('iss') != expected_issuer:
        raise AuthenticationFailed('Token issuer pa valid')

    return payload
