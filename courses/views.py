from django.shortcuts import render
from thinkific import Thinkific
from django.conf import settings
thinkific = Thinkific(settings.THINKIFIC['AUTH_TOKEN'],"")

# Create your views here.
def courses(request):
    # courses = thinkific.courses.list()
    return render(request,'pages/courses.html')