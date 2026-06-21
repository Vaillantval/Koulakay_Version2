import re

from django.db import models
from django.utils.translation import gettext_lazy as _


class PageSlide(models.Model):
    """
    Slide photo-only pour les pages À propos et Contact.
    Pas de champ texte — uniquement une image qui défile.
    """
    PAGE_CHOICES = [
        ('about',   _('À propos')),
        ('contact', _('Contact')),
    ]
    page = models.CharField(
        _('Page'),
        max_length=20,
        choices=PAGE_CHOICES,
        db_index=True,
        help_text=_('Page sur laquelle ce slide apparaît.'),
    )
    image = models.ImageField(
        _('Image'),
        upload_to='page_slides/',
        help_text=_('Recommandé : 1920×800 px minimum'),
    )
    order = models.PositiveSmallIntegerField(_("Ordre d'affichage"), default=0)
    is_active = models.BooleanField(_('Actif'), default=True)

    class Meta:
        ordering = ['page', 'order']
        verbose_name = _('Slide de page')
        verbose_name_plural = _('Slides de pages')

    def __str__(self):
        return f"[{self.get_page_display()}] Slide {self.order}"


class HeroSlide(models.Model):
    """
    Slide du carousel hero sur la page d'accueil.
    Gérable depuis l'admin Django.
    """
    title = models.CharField(_("Titre"), max_length=120)
    subtitle = models.CharField(_("Sous-titre"), max_length=255, blank=True)
    image = models.ImageField(
        _("Image"),
        upload_to="hero_slides/",
        help_text=_("Recommandé : 1920×800 px minimum"),
    )
    cta_label = models.CharField(
        _("Texte du bouton CTA"),
        max_length=60,
        blank=True,
        default="Explorer les cours",
    )
    cta_url = models.CharField(
        _("URL du bouton CTA"),
        max_length=200,
        blank=True,
        default="/fr/courses/courses/",
    )
    order = models.PositiveSmallIntegerField(_("Ordre d'affichage"), default=0)
    is_active = models.BooleanField(_("Actif"), default=True)

    class Meta:
        verbose_name = _("Slide hero")
        verbose_name_plural = _("Slides hero")
        ordering = ["order"]

    def __str__(self):
        return f"[{self.order}] {self.title}"


class SiteConfig(models.Model):
    """
    Configuration globale du site — une seule instance (singleton).
    Modifiable depuis l'interface admin Django.
    """

    # ── Identité ──
    site_name = models.CharField(_("Nom du site"), max_length=100, default="KouLakay")
    tagline = models.CharField(_("Slogan"), max_length=255, blank=True,
                               default="Rendre l'éducation de qualité accessible à tous.")

    # ── Logos ──
    logo_principal = models.ImageField(
        _("Logo principal"),
        upload_to="logos/",
        blank=True,
        help_text=_("Logo KouLakay affiché dans le header et les pages de connexion. "
                    "Format PNG recommandé, fond transparent.")
    )
    logo_partenaire = models.ImageField(
        _("Logo partenaire"),
        upload_to="logos/",
        blank=True,
        help_text=_("Logo du partenaire (ex: Exam Haiti) affiché à côté du logo principal. "
                    "Format PNG ou JPEG, hauteur recommandée : 80px minimum.")
    )

    # ── Coordonnées ──
    address = models.CharField(_("Adresse"), max_length=255, blank=True,
                               default="Port-au-Prince, Haïti")
    phone_1 = models.CharField(_("Téléphone principal"), max_length=30, blank=True,
                               default="+509 3000 0000")
    phone_2 = models.CharField(_("Téléphone secondaire"), max_length=30, blank=True)
    email = models.EmailField(_("Email de contact"), blank=True,
                              default="info@koulakay.ht")
    email_support = models.EmailField(_("Email support"), blank=True)

    # ── Contact WhatsApp (bouton flottant) ──
    whatsapp_number = models.CharField(
        _("Numéro WhatsApp"), max_length=30, blank=True,
        help_text=_("Format international, ex : +509 3000 0000. Affiché en bouton flottant "
                    "sur tout le site. Laisser vide pour masquer le bouton."),
    )
    whatsapp_message = models.CharField(
        _("Message WhatsApp pré-rempli"), max_length=255, blank=True,
        default="Bonjour KouLakay, j'ai une question.",
        help_text=_("Texte inséré automatiquement dans la conversation quand on clique sur le bouton."),
    )

    # ── Vidéos démo paiement (MonCash / NatCash) ──
    payment_video_moncash_url = models.URLField(
        _("Vidéo MonCash — lien (recommandé)"), blank=True,
        help_text=_("Lien YouTube ou Vimeo (non-listé) montrant comment payer par MonCash. "
                    "Recommandé : contrairement à un fichier uploadé, le lien n'est jamais perdu."),
    )
    payment_video_moncash_file = models.FileField(
        _("Vidéo MonCash — fichier (option)"), upload_to="demo_videos/", blank=True,
        help_text=_("Alternative si vous n'avez pas de lien. ⚠️ Un fichier uploadé peut être perdu "
                    "lors d'une mise à jour du site — préférez le lien ci-dessus."),
    )
    payment_video_natcash_url = models.URLField(
        _("Vidéo NatCash — lien (recommandé)"), blank=True,
        help_text=_("Lien YouTube ou Vimeo (non-listé) montrant comment payer par NatCash."),
    )
    payment_video_natcash_file = models.FileField(
        _("Vidéo NatCash — fichier (option)"), upload_to="demo_videos/", blank=True,
        help_text=_("Alternative si vous n'avez pas de lien. ⚠️ Préférez le lien ci-dessus."),
    )

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

    # ── Devise ──
    CURRENCY_CHOICES = [
        ('USD', _('Dollar américain (USD)')),
        ('EUR', _('Euro (EUR)')),
        ('CAD', _('Dollar canadien (CAD)')),
        ('GBP', _('Livre sterling (GBP)')),
        ('HTG', _('Gourde haïtienne (HTG)')),
    ]
    currency = models.CharField(
        _("Devise d'affichage"),
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD',
        help_text=_("Devise utilisée pour afficher les prix sur toutes les pages (sauf la page de paiement qui affiche aussi l'équivalent HTG)."),
    )

    class Meta:
        verbose_name = _("Configuration du site")
        verbose_name_plural = _("Configuration du site")

    def __str__(self):
        return f"Configuration — {self.site_name}"

    # ── Helpers WhatsApp ──
    @property
    def whatsapp_link(self):
        """Lien wa.me prêt à l'emploi (numéro nettoyé + message pré-rempli)."""
        if not self.whatsapp_number:
            return ""
        digits = re.sub(r"\D", "", self.whatsapp_number)
        if not digits:
            return ""
        url = f"https://wa.me/{digits}"
        if self.whatsapp_message:
            from urllib.parse import quote
            url += f"?text={quote(self.whatsapp_message)}"
        return url

    # ── Helpers vidéos paiement ──
    @staticmethod
    def _resolve_video(url, file):
        """
        Transforme un lien/fichier vidéo en source affichable.
        Retourne un dict {'kind': 'youtube'|'vimeo'|'file'|'', 'src': str}.
        - YouTube/Vimeo → URL d'embed (iframe)
        - lien direct ou fichier uploadé → 'file' (balise <video>)
        """
        if url:
            u = url.strip()
            m = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/|v/))([\w-]{11})", u)
            if m:
                return {"kind": "youtube", "src": f"https://www.youtube.com/embed/{m.group(1)}"}
            m = re.search(r"vimeo\.com/(?:video/)?(\d+)", u)
            if m:
                return {"kind": "vimeo", "src": f"https://player.vimeo.com/video/{m.group(1)}"}
            return {"kind": "file", "src": u}
        if file:
            try:
                return {"kind": "file", "src": file.url}
            except Exception:
                return {"kind": "", "src": ""}
        return {"kind": "", "src": ""}

    @property
    def moncash_video(self):
        return self._resolve_video(self.payment_video_moncash_url, self.payment_video_moncash_file)

    @property
    def natcash_video(self):
        return self._resolve_video(self.payment_video_natcash_url, self.payment_video_natcash_file)

    @property
    def has_payment_videos(self):
        return bool(self.moncash_video["src"] or self.natcash_video["src"])

    def save(self, *args, **kwargs):
        """Garantit qu'il n'existe qu'une seule instance."""
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        """Retourne la config, la crée si elle n'existe pas."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
