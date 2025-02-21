from django.shortcuts import render
from django.shortcuts import redirect

from thinkific import Thinkific
from django.conf import settings

thinkific = Thinkific(settings.THINKIFIC['AUTH_TOKEN'],settings.THINKIFIC['SITE_ID'])
from django.core.paginator import Paginator
from courses.models import Enrollment

# Create your views here.
def home(request):
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
    return render(request, 'pages/home.html', {'courses':page_obj})
    
def contact(request):
    return render(request,'pages/contact.html')

def about(request):
    return render(request,'pages/about.html')

def redirect_to_default_language(request):
    return redirect(f'/{settings.LANGUAGE_CODE}/')