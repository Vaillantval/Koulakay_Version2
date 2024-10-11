from django.shortcuts import render, redirect
from thinkific import Thinkific
from django.conf import settings
thinkific = Thinkific(settings.THINKIFIC['AUTH_TOKEN'],"")
from .models import Enrollment
from accounts.models import User
from django.utils import timezone
from datetime import timedelta
# Create your views here.
def courses(request):
    # courses = thinkific.courses.list()
    return render(request,'pages/courses.html')

def course_enrollment(request,user_id,course_id):
    if request.method == 'POST':
        activated_at=timezone.now()
        expiry_date=(timezone.now() + timedelta(days=30)) 
        thinkific.enrollments.create_enrollment({
            'user_id':user_id,
            'course_id':course_id,
            'activated_at':activated_at,
            'expiry_date':expiry_date
        })
        Enrollment.objects.update_or_create(user_id=User.objects.get(pk=user_id),course_id=course_id,activated_at=activated_at,expiry_date=expiry_date)

    return redirect('courses')