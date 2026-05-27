"""
Migration de données — Amorce les 4 slides hero par défaut.

• S'exécute UNE seule fois (Django ne re-joue pas les migrations déjà appliquées).
• Utilise filter().exists() pour être idempotente : si le slide existe déjà,
  il n'est pas recréé.
• Copie les images depuis config/static/images/ → media/hero_slides/
  en préfixant le nom avec « kl_default_ » pour les distinguer des uploads admin.
• Si une image source est absente (environnement sans fichiers statiques),
  le slide est quand même créé — il suffira d'uploader l'image via l'admin.
"""

import shutil
from pathlib import Path
from django.db import migrations


# ── Définition des 4 slides par défaut ─────────────────────────────────────
SLIDES = [
    {
        'order': 1,
        'image_src': 'course_2.jpg',
        'image_dst': 'kl_default_1.jpg',
        'title_fr': "L'éducation est l'arme la plus puissante",
        'subtitle_fr': "Chaque cours est un pas vers la version la plus accomplie de vous-même.",
        'cta_label_fr': "Explorer les cours",
        'cta_url': "/fr/courses/courses/",
    },
    {
        'order': 2,
        'image_src': 'slider_1.JPG',
        'image_dst': 'kl_default_2.jpg',
        'title_fr': "La connaissance d'aujourd'hui forge le leader de demain",
        'subtitle_fr': "Des formations conçues pour la jeunesse haïtienne ambitieuse.",
        'cta_label_fr': "Voir les formations",
        'cta_url': "/fr/courses/courses/",
    },
    {
        'order': 3,
        'image_src': 'slider_3.JPG',
        'image_dst': 'kl_default_3.jpg',
        'title_fr': "Chaque expert a commencé par une première leçon",
        'subtitle_fr': "Commencez votre parcours, peu importe votre niveau.",
        'cta_label_fr': "Commencer maintenant",
        'cta_url': "/fr/courses/courses/",
    },
    {
        'order': 4,
        'image_src': 'slider_background.jpg',
        'image_dst': 'kl_default_4.jpg',
        'title_fr': "Débloquez votre potentiel, construisez votre futur",
        'subtitle_fr': "L'investissement le plus rentable, c'est celui en vous-même.",
        'cta_label_fr': "Découvrir KouLakay",
        'cta_url': "/fr/courses/courses/",
    },
]


def seed_hero_slides(apps, schema_editor):
    """Crée les slides par défaut s'ils n'existent pas encore."""
    from django.conf import settings

    HeroSlide = apps.get_model('pages', 'HeroSlide')

    media_dir = Path(settings.MEDIA_ROOT) / 'hero_slides'
    media_dir.mkdir(parents=True, exist_ok=True)

    static_dir = Path(settings.BASE_DIR) / 'config' / 'static' / 'images'

    for slide in SLIDES:
        image_field = f"hero_slides/{slide['image_dst']}"

        # ── Ne pas recréer si ce slide existe déjà ──────────────────────────
        if HeroSlide.objects.filter(image=image_field).exists():
            continue

        # ── Copier l'image source → dossier media ───────────────────────────
        dst_path = media_dir / slide['image_dst']
        if not dst_path.exists():
            src_path = static_dir / slide['image_src']
            if src_path.exists():
                shutil.copy2(str(src_path), str(dst_path))

        # ── Créer le slide ───────────────────────────────────────────────────
        HeroSlide.objects.create(
            order=slide['order'],
            # Colonne de base (fallback modeltranslation)
            title=slide['title_fr'],
            subtitle=slide['subtitle_fr'],
            cta_label=slide['cta_label_fr'],
            # Colonnes traduites — on renseigne au moins le français
            title_fr=slide['title_fr'],
            subtitle_fr=slide['subtitle_fr'],
            cta_label_fr=slide['cta_label_fr'],
            cta_url=slide['cta_url'],
            image=image_field,
            is_active=True,
        )


def remove_default_slides(apps, schema_editor):
    """Rollback : supprime uniquement les slides par défaut (prefixe kl_default_)."""
    HeroSlide = apps.get_model('pages', 'HeroSlide')
    default_paths = [f"hero_slides/{s['image_dst']}" for s in SLIDES]
    HeroSlide.objects.filter(image__in=default_paths).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0005_add_logos_to_siteconfig'),
    ]

    operations = [
        migrations.RunPython(seed_hero_slides, remove_default_slides),
    ]
