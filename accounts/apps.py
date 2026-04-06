from django.apps import AppConfig


class AccountConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import accounts.signals  # noqa: F401
        from django.db.models.signals import post_migrate
        post_migrate.connect(_create_initial_superuser, sender=self)


def _create_initial_superuser(sender, **kwargs):
    """Crée le superuser initial après migrate si aucun n'existe (idempotent)."""
    from django.conf import settings
    from django.contrib.auth import get_user_model

    email    = getattr(settings, 'ADMIN_USER', '')
    password = getattr(settings, 'ADMIN_PASSWORD', '')

    if not email or not password:
        return

    User = get_user_model()
    try:
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(email=email, password=password)
            print(f"[init] Superuser créé : {email}")
    except Exception:
        pass  # Table pas encore créée (première migration) — ignoré silencieusement
