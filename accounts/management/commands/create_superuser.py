from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Crée le superuser initial si aucun superuser n'existe (idempotent)."

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        email    = settings.ADMIN_USER
        password = settings.ADMIN_PASSWORD

        if not email or not password:
            self.stdout.write(self.style.WARNING(
                "ADMIN_USER ou ADMIN_PASSWORD non définis — superuser ignoré."
            ))
            return

        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.SUCCESS(
                f"Superuser déjà existant — rien à faire."
            ))
            return

        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(
            f"Superuser créé : {email}"
        ))
