from django.shortcuts import render, redirect
from django.conf import settings
from .models import HeroSlide


def home(request):
    hero_slides = list(HeroSlide.objects.filter(is_active=True).order_by("order"))
    return render(request, 'pages/home.html', {"hero_slides": hero_slides})


def contact(request):
    return render(request, 'pages/contact.html')


def about(request):
    return render(request, 'pages/about.html')


def success_page(request):
    return render(request, 'pages/success.html')


def redirect_to_default_language(request):
    return redirect(f'/{settings.LANGUAGE_CODE}/')
