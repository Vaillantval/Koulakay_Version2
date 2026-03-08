from django.shortcuts import render, redirect
from django.conf import settings


def home(request):
    return render(request, 'pages/home.html')


def contact(request):
    return render(request, 'pages/contact.html')


def about(request):
    return render(request, 'pages/about.html')


def success_page(request):
    return render(request, 'pages/success.html')


def redirect_to_default_language(request):
    return redirect(f'/{settings.LANGUAGE_CODE}/')
