from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _

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
    phone = d_forms.CharField(
        required=True, max_length=30, label=_("Numéro de contact"),
        widget=d_forms.TextInput(attrs={'placeholder': _("Numéro de contact"),
                                        'autocomplete': 'tel', 'inputmode': 'tel'}),
    )

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.phone = self.cleaned_data.get('phone', '')
        user.save(update_fields=['first_name', 'last_name', 'phone'])
        return user


class UserUpdateForm(d_forms.ModelForm):
    """Édition du profil (page Mon Profil) — mêmes infos qu'à l'inscription."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone']
        labels = {
            'first_name': _("Prénom"),
            'last_name': _("Nom"),
            'phone': _("Numéro de contact"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.required = True