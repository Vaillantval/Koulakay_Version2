import logging
from django.db import migrations
from django.conf import settings
from django.contrib.auth.hashers import make_password
logger = logging.getLogger(__name__)

def generate_superuser(apps, schema_editor):
    # Utiliser le modèle HISTORIQUE (état à cette migration : pas de champ username,
    # ajouté plus tard en 0005). Évite l'échec sur une DB fraîche (tests, nouveaux envs).
    User = apps.get_model('accounts', 'User')

    email = settings.ADMIN_USER
    password = settings.ADMIN_PASSWORD

    if not User.objects.filter(email=email).exists():
        logger.info("Creating new superuser")
        User.objects.create(
            email=email,
            password=make_password(password),
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
    else:
        logger.info("Superuser already created!")


class Migration(migrations.Migration):
   dependencies = [("accounts", "0002_add_thinkific_user_id")]

   operations = [migrations.RunPython(generate_superuser)]