from django.db import models
from django.contrib.auth.models import AbstractUser

from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager

class User(AbstractUser):

    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    email = models.EmailField(_("email address"), unique=True)
    thinkific_user_id = models.IntegerField(null=True, blank=True, db_index=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return f'{self.email}'


class DeviceToken(models.Model):
    """Token d'un appareil mobile pour les notifications push (Phase 5 — fondation)."""
    class Platform(models.TextChoices):
        IOS = 'ios', 'iOS'
        ANDROID = 'android', 'Android'
        WEB = 'web', 'Web'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    token = models.CharField(max_length=255)
    platform = models.CharField(max_length=10, choices=Platform.choices, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'token')

    def __str__(self):
        return f'{self.user.email} · {self.platform or "?"}'