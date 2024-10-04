from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import User

# Importing django.forms under a special namespace because of my old mistake
from django import forms as d_forms
from allauth.account.forms import SignupForm

class CustomUserCreationForm(UserCreationForm):

    class Meta:
        model = User
        fields = ("email",)


class CustomUserChangeForm(UserChangeForm):

    class Meta:
        model = User
        fields = ("email",)

class CustomSignupForm(SignupForm):
    first_name = d_forms.CharField(required=True)
    last_name = d_forms.CharField(required=True)
    
    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        return user
    
class UserUpdateForm(d_forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name','last_name']  # Ajoutez d'autres champs si nécessaire