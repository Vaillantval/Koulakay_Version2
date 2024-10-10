from django.shortcuts import render
from allauth.account.views import SignupView
from django.conf import settings
from thinkific import Thinkific
thinkific = Thinkific(settings.THINKIFIC['AUTH_TOKEN'],"")
class MySignupView(SignupView):

    def form_valid(self, form):
        response = super().form_valid(form)
       
        thinkific.users.create_user({
            'email':self.user.email,
            'first_name':self.user.first_name,
            'last_name':self.user.last_name,
            'full_name':f'{self.user.first_name} {self.user.last_name}',
            'password':self.user.password
        })

        return response