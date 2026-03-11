from django.shortcuts import render, redirect
from django.conf import settings
from django.db.models import Count
from .models import HeroSlide, SiteConfig


def home(request):
    hero_slides = list(HeroSlide.objects.filter(is_active=True).order_by("order"))

    # ── Stats (valeurs par défaut si la DB est vide ou API indisponible) ──
    stats = {
        'total_courses':      20,
        'total_users':       500,
        'local_enrollments': 136,
    }

    # ── Imports locaux pour éviter les imports circulaires ──
    from courses.models import Enrollment
    from courses.views import thinkific

    try:
        courses_response = thinkific.courses.list(limit=1)
        total = courses_response.get('meta', {}).get('pagination', {}).get('total_items', 0)
        if total:
            stats['total_courses'] = total
    except Exception:
        pass

    try:
        users_response = thinkific.users.list(limit=1)
        total = users_response.get('meta', {}).get('pagination', {}).get('total_items', 0)
        if total:
            stats['total_users'] = total
    except Exception:
        pass

    try:
        count = Enrollment.objects.count()
        if count:
            stats['local_enrollments'] = count
    except Exception:
        pass

    # ── Cours populaires ──
    popular_courses = []

    try:
        product_response = thinkific.products.list()
        product_items = product_response.get('items', [])
    except Exception:
        product_items = []

    try:
        top_qs = (
            Enrollment.objects
            .values('course_id')
            .annotate(num_enrollments=Count('course_id'))
            .order_by('-num_enrollments')[:6]
        )
        top_ids = [item['course_id'] for item in top_qs]

        if top_ids:
            # Cours classés par popularité
            for course_id in top_ids:
                try:
                    c = thinkific.courses.retrieve_course(id=course_id)
                    c['enrollment_count'] = next(
                        (x['num_enrollments'] for x in top_qs if x['course_id'] == course_id), 0
                    )
                    c['price'] = next(
                        (p['price'] for p in product_items
                         if p.get('productable_id') == course_id and p.get('price') is not None),
                        None
                    )
                    c['enroll'] = (
                        request.user.is_authenticated and
                        Enrollment.objects.filter(user=request.user, course_id=course_id).exists()
                    )
                    popular_courses.append(c)
                except Exception:
                    continue
        else:
            # Fallback : aucune inscription → 6 premiers cours Thinkific
            fallback = thinkific.courses.list(limit=6).get('items', [])
            for c in fallback:
                cid = c.get('id')
                c['enrollment_count'] = 0
                c['price'] = next(
                    (p['price'] for p in product_items
                     if p.get('productable_id') == cid and p.get('price') is not None),
                    None
                )
                c['enroll'] = (
                    request.user.is_authenticated and
                    Enrollment.objects.filter(user=request.user, course_id=cid).exists()
                )
                popular_courses.append(c)

    except Exception as e:
        print(f"[home] Erreur cours populaires: {e}")

    site_currency = SiteConfig.get().currency

    return render(request, 'pages/home.html', {
        'hero_slides':   hero_slides,
        'courses':       popular_courses,
        'stats':         stats,
        'site_currency': site_currency,
    })


def contact(request):
    return render(request, 'pages/contact.html')


def about(request):
    return render(request, 'pages/about.html')


def success_page(request):
    return render(request, 'pages/success.html')


def redirect_to_default_language(request):
    return redirect(f'/{settings.LANGUAGE_CODE}/')
