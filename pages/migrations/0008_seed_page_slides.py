"""
Migration de données — Amorce les slides photo pour les pages À propos et Contact.

  À propos (2 slides)  : testimonials_user.jpg  ·  event_1.jpg
  Contact   (2 slides) : news_3.jpg             ·  event_2.jpg

Même logique que 0006_seed_default_hero_slides :
  • Idempotente : vérifie l'image path avant de créer.
  • Exécutée UNE SEULE FOIS par Railway au déploiement (via migrate --no-input).
  • Si l'image source est absente, le slide est quand même créé (image à uploader ensuite).
"""

import shutil
from pathlib import Path
from django.db import migrations


SLIDES = [
    # ── À propos ──────────────────────────────────────────────────────────
    {
        'page':      'about',
        'order':     1,
        'image_src': 'testimonials_user.jpg',
        'image_dst': 'kl_about_1.jpg',
    },
    {
        'page':      'about',
        'order':     2,
        'image_src': 'event_1.jpg',
        'image_dst': 'kl_about_2.jpg',
    },
    # ── Contact ───────────────────────────────────────────────────────────
    {
        'page':      'contact',
        'order':     1,
        'image_src': 'news_3.jpg',
        'image_dst': 'kl_contact_1.jpg',
    },
    {
        'page':      'contact',
        'order':     2,
        'image_src': 'event_2.jpg',
        'image_dst': 'kl_contact_2.jpg',
    },
]


def seed_page_slides(apps, schema_editor):
    from django.conf import settings

    PageSlide = apps.get_model('pages', 'PageSlide')

    media_dir  = Path(settings.MEDIA_ROOT) / 'page_slides'
    media_dir.mkdir(parents=True, exist_ok=True)

    static_dir = Path(settings.BASE_DIR) / 'config' / 'static' / 'images'

    for slide in SLIDES:
        image_field = f"page_slides/{slide['image_dst']}"

        # Idempotent — ne recrée pas si déjà en base
        if PageSlide.objects.filter(image=image_field).exists():
            continue

        # Copie de l'image static → media
        dst = media_dir / slide['image_dst']
        if not dst.exists():
            src = static_dir / slide['image_src']
            if src.exists():
                shutil.copy2(str(src), str(dst))

        PageSlide.objects.create(
            page=slide['page'],
            order=slide['order'],
            image=image_field,
            is_active=True,
        )


def remove_seeded_slides(apps, schema_editor):
    """Rollback : supprime uniquement les slides amorcés (préfixe kl_)."""
    PageSlide = apps.get_model('pages', 'PageSlide')
    seeded = [f"page_slides/{s['image_dst']}" for s in SLIDES]
    PageSlide.objects.filter(image__in=seeded).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0007_add_page_slide'),
    ]

    operations = [
        migrations.RunPython(seed_page_slides, remove_seeded_slides),
    ]
