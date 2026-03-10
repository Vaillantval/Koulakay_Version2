from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login
from django.contrib import messages
from django.conf import settings
from allauth.account.views import SignupView, LoginView
from thinkific import Thinkific
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils.translation import gettext_lazy as _
import requests

thinkific = Thinkific(settings.THINKIFIC['AUTH_TOKEN'], settings.THINKIFIC['SITE_ID'])


class ThinkificSignupView(SignupView):
    """Vue d'inscription qui crée l'utilisateur dans Thinkific"""
    
    def form_valid(self, form):
        # Récupérer les données du formulaire
        email = form.cleaned_data.get('email')
        first_name = form.cleaned_data.get('first_name')
        last_name = form.cleaned_data.get('last_name')
        password = form.cleaned_data.get('password1')
        
        try:
            # 1. Tenter de créer l'utilisateur dans Thinkific
            thinkific_user_data = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'password': password,
                'send_welcome_email': True
            }

            thinkific_user_id = None
            try:
                thinkific_user = thinkific.users.create_user(thinkific_user_data)
                thinkific_user_id = thinkific_user.get('id') if thinkific_user else None
            except requests.exceptions.HTTPError as e:
                # 422 = utilisateur déjà existant dans Thinkific → on récupère son ID
                if e.response is not None and e.response.status_code == 422:
                    existing = thinkific.users.list(email=email)
                    for u in existing.get('items', []):
                        if u.get('email', '').lower() == email.lower():
                            thinkific_user_id = u.get('id')
                            break
                else:
                    raise

            if not thinkific_user_id:
                messages.error(self.request, _("Erreur lors de la création du compte Thinkific."))
                return self.form_invalid(form)

            # 2. Créer l'utilisateur local Django
            response = super().form_valid(form)

            # 3. Stocker l'ID Thinkific dans le modèle User
            self.user.thinkific_user_id = thinkific_user_id
            self.user.save(update_fields=['thinkific_user_id'])

            messages.success(
                self.request,
                _("Votre compte a été créé avec succès ! Vous pouvez maintenant vous connecter.")
            )

            return response

        except requests.exceptions.HTTPError as e:
            error_msg = _("Erreur lors de la communication avec Thinkific")
            try:
                error_detail = e.response.json()
                if 'errors' in error_detail:
                    error_msg = f"{error_msg}: {error_detail['errors']}"
            except Exception:
                pass

            messages.error(self.request, error_msg)
            return self.form_invalid(form)
            
        except Exception as e:
            messages.error(
                self.request, 
                _("Une erreur inattendue s'est produite. Veuillez réessayer.")
            )
            print(f"Erreur signup Thinkific: {e}")
            return self.form_invalid(form)


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
def thinkific_sso(request):
    """
    Génère un SSO token Thinkific et redirige l'utilisateur directement
    sur la plateforme Thinkific sans qu'il ait à se reconnecter.

    Usage : /accounts/thinkific-sso/?return_to=/courses/mon-cours
    Si return_to est absent, redirige vers le dashboard Thinkific.
    """
    thinkific_user_id = request.user.thinkific_user_id

    if not thinkific_user_id:
        messages.error(request, _("Votre compte n'est pas lié à Thinkific."))
        return redirect('home')

    return_to = request.GET.get('return_to', '')
    site_id = settings.THINKIFIC['SITE_ID']

    try:
        api_url = f"https://api.thinkific.com/api/public/v1/users/{thinkific_user_id}/sso_token"
        headers = {
            "X-Auth-API-Key": settings.THINKIFIC['AUTH_TOKEN'],
            "X-Auth-Subdomain": site_id,
            "Content-Type": "application/json",
        }
        response = requests.post(api_url, headers=headers, json={})
        response.raise_for_status()

        token = response.json().get('token')
        if not token:
            raise ValueError("Token SSO absent de la réponse Thinkific")

        sso_url = f"https://{site_id}.thinkific.com/api/sso?token={token}"
        if return_to:
            sso_url += f"&return_to={return_to}"

        return redirect(sso_url)

    except Exception as e:
        print(f"Erreur SSO Thinkific: {e}")
        messages.error(request, _("Impossible d'accéder à Thinkific. Veuillez réessayer."))
        return redirect('home')