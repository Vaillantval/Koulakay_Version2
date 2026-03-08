from django.db import models
from django.utils.translation import gettext_lazy as _


class SiteConfig(models.Model):
    """
    Configuration globale du site — une seule instance (singleton).
    Modifiable depuis l'interface admin Django.
    """

    # ── Identité ──
    site_name = models.CharField(_("Nom du site"), max_length=100, default="KouLakay")
    tagline = models.CharField(_("Slogan"), max_length=255, blank=True,
                               default="Rendre l'éducation de qualité accessible à tous.")

    # ── Coordonnées ──
    address = models.CharField(_("Adresse"), max_length=255, blank=True,
                               default="Port-au-Prince, Haïti")
    phone_1 = models.CharField(_("Téléphone principal"), max_length=30, blank=True,
                               default="+509 3000 0000")
    phone_2 = models.CharField(_("Téléphone secondaire"), max_length=30, blank=True)
    email = models.EmailField(_("Email de contact"), blank=True,
                              default="info@koulakay.ht")
    email_support = models.EmailField(_("Email support"), blank=True)

    # ── Carte Google Maps ──
    map_embed_url = models.TextField(
        _("URL d'intégration Google Maps"),
        blank=True,
        help_text=_("Copiez l'URL src de l'iframe depuis Google Maps → Partager → Intégrer une carte")
    )

    # ── Réseaux sociaux ──
    facebook_url = models.URLField(_("Facebook"), blank=True)
    twitter_url = models.URLField(_("Twitter / X"), blank=True)
    instagram_url = models.URLField(_("Instagram"), blank=True)
    linkedin_url = models.URLField(_("LinkedIn"), blank=True)
    youtube_url = models.URLField(_("YouTube"), blank=True)

    # ── Footer ──
    footer_text = models.CharField(
        _("Texte pied de page"),
        max_length=255,
        blank=True,
        default="Conçu avec ❤️ pour Haïti"
    )

    class Meta:
        verbose_name = _("Configuration du site")
        verbose_name_plural = _("Configuration du site")

    def __str__(self):
        return f"Configuration — {self.site_name}"

    def save(self, *args, **kwargs):
        """Garantit qu'il n'existe qu'une seule instance."""
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        """Retourne la config, la crée si elle n'existe pas."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
