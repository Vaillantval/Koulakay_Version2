"""wificonnect URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from accounts.views import *
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings

from pages.views import redirect_to_default_language

admin.autodiscover()

from  django.contrib.sitemaps.views import sitemap

urlpatterns = [
    path("sitemap.xml", sitemap, name="sitemap-xml"),
    path("__reload__/", include("django_browser_reload.urls")),
]

urlpatterns += [
    path('', redirect_to_default_language),
]

urlpatterns += i18n_patterns(
    path('', include('pages.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('payment/', include('payment.urls')),
    path('courses/', include('courses.urls')),
)

# Servir les fichiers media
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# En développement, servir les fichiers statiques
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
