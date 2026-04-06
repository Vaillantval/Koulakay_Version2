from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TabbedTranslationAdmin
from .models import SiteConfig, HeroSlide


@admin.register(HeroSlide)
class HeroSlideAdmin(TabbedTranslationAdmin):
    list_display = ("order", "title", "is_active", "image_preview")
    list_display_links = ("title",)
    list_editable = ("order", "is_active")
    list_per_page = 20
    ordering = ("order",)

    fields = ("title", "subtitle", "image", "cta_label", "cta_url", "order", "is_active")

    def image_preview(self, obj):
        if obj.image:
            from django.utils.html import format_html
            return format_html(
                '<img src="{}" style="height:48px;border-radius:6px;object-fit:cover;" />',
                obj.image.url,
            )
        return "—"
    image_preview.short_description = _("Aperçu")


@admin.register(SiteConfig)
class SiteConfigAdmin(TabbedTranslationAdmin):
    """
    Admin pour la configuration globale du site.
    - Une seule instance possible (singleton)
    - Organisé en sections claires
    """

    readonly_fields = ("logo_principal_preview", "logo_partenaire_preview")

    def logo_principal_preview(self, obj):
        from django.utils.html import format_html
        if obj.logo_principal:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:8px;object-fit:contain;" />',
                obj.logo_principal.url,
            )
        return _("Aucun logo — le fichier statique par défaut est utilisé.")
    logo_principal_preview.short_description = _("Aperçu logo principal")

    def logo_partenaire_preview(self, obj):
        from django.utils.html import format_html
        if obj.logo_partenaire:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:8px;object-fit:contain;" />',
                obj.logo_partenaire.url,
            )
        return _("Aucun logo — le fichier statique par défaut est utilisé.")
    logo_partenaire_preview.short_description = _("Aperçu logo partenaire")

    fieldsets = (
        (_("🏫 Identité du site"), {
            "fields": ("site_name", "tagline"),
        }),
        (_("🖼️ Logos"), {
            "fields": (
                "logo_principal", "logo_principal_preview",
                "logo_partenaire", "logo_partenaire_preview",
            ),
            "description": _(
                "Si un champ est vide, le logo statique par défaut est utilisé automatiquement."
            ),
        }),
        (_("📍 Coordonnées"), {
            "fields": ("address", "phone_1", "phone_2", "email", "email_support"),
        }),
        (_("🗺️ Carte Google Maps"), {
            "fields": ("map_embed_url",),
            "description": _(
                "Allez sur Google Maps → trouvez votre adresse → Partager → "
                "Intégrer une carte → copiez uniquement l'URL du champ src."
            ),
        }),
        (_("📱 Réseaux sociaux"), {
            "fields": ("facebook_url", "twitter_url", "instagram_url",
                       "linkedin_url", "youtube_url"),
        }),
        (_("📄 Pied de page"), {
            "fields": ("footer_text",),
        }),
        (_("💱 Devise"), {
            "fields": ("currency",),
            "description": _(
                "Devise utilisée pour afficher les prix sur toutes les pages. "
                "Sur la page de paiement, l'équivalent en HTG est toujours affiché en sous-titre."
            ),
        }),
    )

    def has_add_permission(self, request):
        """Empêche de créer plus d'une instance."""
        return not SiteConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Empêche la suppression."""
        return False

    def changelist_view(self, request, extra_context=None):
        """Redirige directement vers l'édition de l'instance unique."""
        obj, _ = SiteConfig.objects.get_or_create(pk=1)
        from django.shortcuts import redirect
        return redirect(f"/fr/admin/pages/siteconfig/{obj.pk}/change/")
