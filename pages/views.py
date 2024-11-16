from django.shortcuts import render
from thinkific import Thinkific
from django.conf import settings
thinkific = Thinkific(settings.THINKIFIC['AUTH_TOKEN'],settings.THINKIFIC['SITE_ID'])
from django.core.paginator import Paginator

# Create your views here.
def home(request):
    courses = thinkific.courses.list()
    courses_items = courses['items']
    paginator = Paginator(courses_items, 5)  # Show 25 contacts per page.

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, 'pages/home.html', {'courses':page_obj})
    
def contact(request):
    return render(request,'pages/contact.html')
