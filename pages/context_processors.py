from .models import SiteConfig


def site_config(request):
    config = SiteConfig.get()
    return {
        "site_config": config,
        "site_currency": config.currency,
    }
