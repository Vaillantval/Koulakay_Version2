from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import User

# Importing django.forms under a special namespace because of my old mistake
from django import forms as d_forms
from allauth.account.forms import SignupForm

class CustomUserCreationForm(UserCreationForm):

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")


class CustomUserChangeForm(UserChangeForm):

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "thinkific_user_id")

class CustomSignupForm(SignupForm):
    first_name = d_forms.CharField(required=True)
    last_name = d_forms.CharField(required=True)

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.save(update_fields=['first_name', 'last_name'])
        return user
    
class UserUpdateForm(d_forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name','last_name']  # Ajoutez d'autres champs si nécessaire