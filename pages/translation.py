from modeltranslation.translator import TranslationOptions, register
from .models import HeroSlide, SiteConfig


@register(HeroSlide)
class HeroSlideTranslationOptions(TranslationOptions):
    fields = ('title', 'subtitle', 'cta_label')


@register(SiteConfig)
class SiteConfigTranslationOptions(TranslationOptions):
    fields = ('tagline', 'footer_text')
