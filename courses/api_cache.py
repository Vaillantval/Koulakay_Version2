"""
Cache léger des appels Thinkific pour l'API mobile (Phase 5).

N'impacte QUE les vues API (pas le site web). Réduit drastiquement les appels
Thinkific répétés (le goulot identifié). LocMemCache par worker ; passer à Redis
en production pour un cache partagé entre workers.
"""
from django.core.cache import cache

from .views import thinkific, _fetch_course_content

# TTL (secondes)
TTL_LISTS = 300      # catalogue (cours/produits) : 5 min
TTL_CONTENT = 600    # programme d'un cours : 10 min
TTL_COURSE = 600     # détail d'un cours


def courses_list():
    key = 'api:tk:courses_list'
    data = cache.get(key)
    if data is None:
        try:
            data = thinkific.courses.list(limit=100).get('items', [])
        except Exception:
            data = []
        cache.set(key, data, TTL_LISTS)
    return data


def products_list():
    key = 'api:tk:products_list'
    data = cache.get(key)
    if data is None:
        try:
            data = thinkific.products.list(limit=100).get('items', [])
        except Exception:
            data = []
        cache.set(key, data, TTL_LISTS)
    return data


def course_content(course_id):
    key = f'api:tk:content:{course_id}'
    data = cache.get(key)
    if data is None:
        data = _fetch_course_content(course_id)
        cache.set(key, data, TTL_CONTENT)
    return data


def retrieve_course(course_id):
    """Détail brut d'un cours (peut lever HTTPError 404 — non caché dans ce cas)."""
    key = f'api:tk:course:{course_id}'
    data = cache.get(key)
    if data is None:
        data = thinkific.courses.retrieve_course(id=course_id)
        cache.set(key, data, TTL_COURSE)
    return data


def invalidate_all():
    """À appeler après une modif admin si besoin de rafraîchir immédiatement."""
    for k in ('api:tk:courses_list', 'api:tk:products_list'):
        cache.delete(k)
