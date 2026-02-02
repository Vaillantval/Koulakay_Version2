from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, authenticate
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
            # 1. Vérifier si l'utilisateur existe déjà dans Thinkific
            existing_users = thinkific.users.list()
            user_exists = any(u.get('email') == email for u in existing_users.get('items', []))
            
            if user_exists:
                messages.error(self.request, _("Un compte avec cet email existe déjà dans Thinkific."))
                return self.form_invalid(form)
            
            # 2. Créer l'utilisateur dans Thinkific
            thinkific_user_data = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'password': password,
                'send_welcome_email': True
            }
            
            thinkific_user = thinkific.users.create_user(thinkific_user_data)
            
            if not thinkific_user or not thinkific_user.get('id'):
                messages.error(self.request, _("Erreur lors de la création du compte Thinkific."))
                return self.form_invalid(form)
            
            # 3. Créer l'utilisateur local Django
            response = super().form_valid(form)
            
            # 4. Stocker l'ID Thinkific dans le profil utilisateur (optionnel)
            # Vous pouvez ajouter un champ thinkific_user_id dans votre modèle User
            # self.user.thinkific_user_id = thinkific_user.get('id')
            # self.user.save()
            
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
            except:
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
    """Vue de connexion qui vérifie les credentials dans Thinkific"""
    
    def form_valid(self, form):
        email = form.cleaned_data.get('login')
        password = form.cleaned_data.get('password')
        
        try:
            # 1. Vérifier les credentials dans Thinkific
            # Note: Thinkific n'a pas d'endpoint direct pour vérifier le password
            # On doit vérifier si l'utilisateur existe
            users_response = thinkific.users.list()
            thinkific_user = None
            
            for user in users_response.get('items', []):
                if user.get('email') == email:
                    thinkific_user = user
                    break
            
            if not thinkific_user:
                messages.error(self.request, _("Email ou mot de passe incorrect."))
                return self.form_invalid(form)
            
            # 2. Authentifier localement
            # Django va vérifier le password localement
            user = authenticate(
                self.request,
                username=email,  # Si vous utilisez email comme username
                password=password
            )
            
            if user is None:
                # Essayer de récupérer l'utilisateur local
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user = User.objects.get(email=email)
                    # Vérifier le password
                    if not user.check_password(password):
                        messages.error(self.request, _("Email ou mot de passe incorrect."))
                        return self.form_invalid(form)
                except User.DoesNotExist:
                    messages.error(self.request, _("Compte non trouvé localement. Veuillez vous inscrire."))
                    return self.form_invalid(form)
            
            # 3. Connecter l'utilisateur
            auth_login(self.request, user)
            
            messages.success(self.request, _("Connexion réussie !"))
            
            # 4. Redirection
            return redirect(self.get_success_url())
            
        except Exception as e:
            messages.error(
                self.request,
                _("Une erreur s'est produite lors de la connexion.")
            )
            print(f"Erreur login Thinkific: {e}")
            return self.form_invalid(form)
    
    def get_success_url(self):
        """Redirige vers la page d'origine ou home"""
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return '/'


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
            
            # Connecter automatiquement
            auth_login(request, user)
            
            messages.success(request, _("Compte créé avec succès !"))
            return redirect('home')
            
        except Exception as e:
            messages.error(request, _("Erreur lors de la création du compte."))
            print(f"Erreur: {e}")
            return render(request, 'account/signup_direct.html')


@login_required
def sync_thinkific_user(request):
    """Synchronise l'utilisateur local avec Thinkific"""
    try:
        # Récupérer l'utilisateur dans Thinkific
        users_response = thinkific.users.list()
        thinkific_user = None
        
        for user in users_response.get('items', []):
            if user.get('email') == request.user.email:
                thinkific_user = user
                break
        
        if thinkific_user:
            # Mettre à jour les informations locales si nécessaire
            request.user.first_name = thinkific_user.get('first_name', request.user.first_name)
            request.user.last_name = thinkific_user.get('last_name', request.user.last_name)
            request.user.save()
            
            messages.success(request, _("Profil synchronisé avec Thinkific."))
        else:
            messages.warning(request, _("Utilisateur non trouvé dans Thinkific."))
        
    except Exception as e:
        messages.error(request, _("Erreur lors de la synchronisation."))
        print(f"Erreur sync: {e}")
    
    return redirect('account_profile')