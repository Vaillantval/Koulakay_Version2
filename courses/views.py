from django.shortcuts import render, redirect
from thinkific import Thinkific
from django.conf import settings
from .models import Enrollment
from accounts.models import User
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
thinkific = Thinkific(settings.THINKIFIC['AUTH_TOKEN'],settings.THINKIFIC['SITE_ID'])
from django.db.models import Q
# Create your views here.
def courses(request):
    courses = thinkific.courses.list()
    courses_items = courses['items']
    paginator = Paginator(courses_items, 5)  # Show 25 contacts per page.
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    if request.user.is_authenticated:
        for c in courses_items:
            e = Enrollment.objects.filter(user=request.user.pk,course_id=c['id'])
            if e :
                c['enroll']=True

    return render(request,'pages/courses.html',{'courses':page_obj})

@login_required
def course_enrollment(request,course_id):   
   
    if request.method == 'POST':
        activated_at=timezone.now()
        expiry_date=(timezone.now() + timedelta(days=30)) 
        user_id=0
        user = thinkific.users.list()['items']
        for u in user:
            if u['email'] == request.user.email:
                user_id = u['id']

        thinkific.enrollments.create_enrollment({
            'user_id':user_id,
            'course_id':course_id,
            'activated_at':activated_at.isoformat(),
            'expiry_date':expiry_date.isoformat()
        })
        
        Enrollment.objects.update_or_create(user=User.objects.get(pk=request.user.pk), thinkific_user_id=user_id,course_id=course_id,activated_at=activated_at,expiry_date=expiry_date)

    return redirect('courses')


def search_course(request):
    q = request.GET.get('q',None)
    courses = thinkific.courses.list()
    list_found =[]
    courses_items = courses['items']
    
    if q == None:
        return render(request,'pages/search_courses.html')
    
    for c in courses_items:

        if q in c['name']:
            q = c['name']
            list_found.append(c)

    return render(request,'pages/search_courses.html',{'courses':list_found,'q':q})