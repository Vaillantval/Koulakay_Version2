import logging
from django.db import migrations
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
logger = logging.getLogger(__name__)

def generate_superuser(apps, schema_editor):

    USERNAME = settings.ADMIN_USER
    PASSWORD = settings.ADMIN_PASSWORD

    user = get_user_model()
    
    if not user.objects.filter(email=USERNAME).exists():
        logger.info("Creating new superuser")
        admin = user.objects.create_superuser(
           email=USERNAME, password=PASSWORD, 
        )
        admin.save()
    else:
        logger.info("Superuser already created!")


class Migration(migrations.Migration):
   dependencies = [("accounts", "0001_initial")]

   operations = [migrations.RunPython(generate_superuser)]