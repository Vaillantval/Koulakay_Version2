from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login
from django.contrib import messages
from django.conf import settings
from allauth.account.views import SignupView, LoginView
from courses.monkey_patch.patch_thinkific import ThinkificExtend as Thinkific
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils.translation import gettext_lazy as _
import requests

thinkific = Thinkific(settings.THINKIFIC['AUTH_TOKEN'], settings.THINKIFIC['SITE_ID'])


def _normalize_username_base(first_name: str) -> str:
    """
    Convertit un prénom en base de username ASCII minuscule.
    Élodie → elodie, François → francois, Jean-Pierre → jean-pierre
    """
    import unicodedata
    name = (first_name or 'user').strip()
    # Décompose les caractères accentués puis supprime les diacritiques
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    return name.lower() or 'user'


def _assign_username(user) -> None:
    """
    Assigne un username unique (prénom normalisé) directement sur le user.
    Utilise l'IntegrityError DB comme arbitre — robuste en environnement concurrent.
    """
    from django.db import IntegrityError
    base = _normalize_username_base(user.first_name)
    username, counter = base, 2
    while True:
        try:
            user.username = username
            user.save(update_fields=['username'])
            return
        except IntegrityError:
            username = f"{base}{counter}"
            counter += 1


class ThinkificSignupView(SignupView):
    """
    Vue d'inscription — crée le compte Django, le lie à Thinkific et connecte
    l'utilisateur immédiatement (ACCOUNT_EMAIL_VERIFICATION = "none").
    Le username est auto-généré depuis le prénom (sans le demander à l'user).
    """

    def form_valid(self, form):
        response = super().form_valid(form)  # crée le user Django + le connecte
        user = self.user
        try:
            if not user.username:
                _assign_username(user)
            from accounts.signals import _ensure_thinkific_linked, _send_welcome_email
            _ensure_thinkific_linked(user)
            _send_welcome_email(user, self.request)
            from accounts.admin_notify import notify_admin_new_signup
            notify_admin_new_signup(user, method='Email / mot de passe')
        except Exception as e:
            print(f"[Signup] Erreur post-inscription pour {user.email}: {e}")
        return response


class ThinkificLoginView(LoginView):
    """
    Vue de connexion — délègue entièrement à allauth.
    Allauth vérifie email + password localement via AUTHENTICATION_BACKENDS,
    gère la session et la redirection. Pas besoin de vérifier Thinkific ici :
    Thinkific ne peut pas valider un mot de passe via son API.
    """

    def get_success_url(self):
        # Allauth gère déjà le ?next= correctement (GET + POST hidden field)
        return super().get_success_url()


# Vue alternative pour inscription directe sans allauth
class DirectThinkificSignupView(View):
    """Vue d'inscription directe sans utiliser django-allauth"""
    
    def get(self, request):
        return render(request, 'account/signup_direct.html')
    
    def post(self, request):
        # Récupérer les données du formulaire
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password1')
        password_confirm = request.POST.get('password2')
        
        # Validation basique
        if not all([email, first_name, last_name, password, password_confirm]):
            messages.error(request, _("Tous les champs sont requis."))
            return render(request, 'account/signup_direct.html')
        
        if password != password_confirm:
            messages.error(request, _("Les mots de passe ne correspondent pas."))
            return render(request, 'account/signup_direct.html')
        
        try:
            # Créer l'utilisateur dans Thinkific
            thinkific_user_data = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'password': password,
                'send_welcome_email': True
            }
            
            thinkific_user = thinkific.users.create_user(thinkific_user_data)
            
            if not thinkific_user:
                messages.error(request, _("Erreur lors de la création du compte Thinkific."))
                return render(request, 'account/signup_direct.html')
            
            # Créer l'utilisateur local
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            user.thinkific_user_id = thinkific_user.get('id')
            user.save(update_fields=['thinkific_user_id'])

            # Connecter automatiquement
            auth_login(request, user)
            
            messages.success(request, _("Compte créé avec succès !"))
            return redirect('home')
            
        except Exception as e:
            messages.error(request, _("Erreur lors de la création du compte."))
            print(f"Erreur: {e}")
            return render(request, 'account/signup_direct.html')


def get_thinkific_user_by_email(email: str):
    """
    Cherche un utilisateur dans Thinkific par email.
    Retourne le dict utilisateur ou None.
    """
    try:
        result = thinkific.users.list(email=email)
        for u in result.get('items', []):
            if u.get('email', '').lower() == email.lower():
                return u
    except Exception as e:
        print(f"Erreur recherche Thinkific par email ({email}): {e}")
    return None


@login_required
def sync_thinkific_user(request):
    """Synchronise l'utilisateur local avec Thinkific"""
    try:
        thinkific_user = get_thinkific_user_by_email(request.user.email)

        if thinkific_user:
            update_fields = []
            if thinkific_user.get('first_name'):
                request.user.first_name = thinkific_user['first_name']
                update_fields.append('first_name')
            if thinkific_user.get('last_name'):
                request.user.last_name = thinkific_user['last_name']
                update_fields.append('last_name')
            if thinkific_user.get('id') and not request.user.thinkific_user_id:
                request.user.thinkific_user_id = thinkific_user['id']
                update_fields.append('thinkific_user_id')
            if update_fields:
                request.user.save(update_fields=update_fields)

            messages.success(request, _("Profil synchronisé avec Thinkific."))
        else:
            messages.warning(request, _("Utilisateur non trouvé dans Thinkific."))

    except Exception as e:
        messages.error(request, _("Erreur lors de la synchronisation."))
        print(f"Erreur sync: {e}")

    return redirect('account_profile')


@login_required
def profile(request):
    """Page « Mon Profil » — édition des infos d'inscription (prénom, nom, numéro)."""
    from .forms import UserUpdateForm
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            # Répercute prénom/nom sur Thinkific (best-effort, ne bloque pas).
            try:
                if user.thinkific_user_id:
                    thinkific.users.update_user(
                        id=user.thinkific_user_id,
                        values={'first_name': user.first_name, 'last_name': user.last_name},
                    )
            except Exception as e:
                print(f"[Profil] Sync Thinkific échouée pour {user.email}: {e}")
            messages.success(request, _("Profil mis à jour."))
            return redirect('account_profile')
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, 'account/profile.html', {'form': form})


def build_thinkific_sso_url(user, return_to='/enrollments'):
    """
    Construit l'URL SSO Thinkific (JWT signé) pour un utilisateur.
    Réutilisable par la vue web ET l'API mobile.

    Retourne (url, reason) :
      - (url, None)          → SSO OK
      - (fallback_url, 'no_sso_secret') → pas de secret SSO, URL sans SSO
      - (None, 'not_linked') → l'utilisateur n'est pas lié à Thinkific
    """
    import jwt as pyjwt
    import time
    from urllib.parse import quote

    site_id = settings.THINKIFIC['SITE_ID']
    sso_secret = settings.THINKIFIC.get('SSO_SECRET', '')
    fallback_url = f"https://{site_id}.thinkific.com{return_to}"

    if not user.thinkific_user_id:
        return None, 'not_linked'
    if not sso_secret:
        return fallback_url, 'no_sso_secret'

    now = int(time.time())
    payload = {
        'email': user.email,
        'first_name': user.first_name or '',
        'last_name': user.last_name or '',
        'iat': now,
        'exp': now + 300,  # 5 min — requis par certains validateurs JWT (Safari notamment)
    }
    token = pyjwt.encode(payload, sso_secret, algorithm='HS256')
    # Ne pas double-encoder return_to (urlencode casserait les / pour Thinkific).
    encoded_return_to = quote(return_to, safe='/-_.')
    url = (
        f"https://{site_id}.thinkific.com/api/sso/v2/sso/jwt"
        f"?jwt={quote(token, safe='')}&return_to={encoded_return_to}"
    )
    return url, None


@login_required
def thinkific_sso(request):
    """SSO JWT vers Thinkific — connecte l'utilisateur sans re-login (vue web)."""
    return_to = request.GET.get('return_to', '/enrollments')
    try:
        url, reason = build_thinkific_sso_url(request.user, return_to)
        if reason == 'not_linked':
            messages.error(request, _("Votre compte n'est pas lié à Thinkific."))
            return redirect('home')
        return redirect(url)
    except Exception as e:
        print(f"[SSO Thinkific] Erreur génération JWT user={request.user.email}: {e}")
        return redirect(f"https://{settings.THINKIFIC['SITE_ID']}.thinkific.com{return_to}")