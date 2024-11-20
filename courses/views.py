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
from payment.models import Transaction
from django.db.models import Q
from django.contrib.sites.shortcuts import get_current_site
import requests
from django.http import JsonResponse, HttpResponseRedirect

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

def generate_paylink(request, transaction:Transaction):
    domain = get_current_site(request).domain
    protocol = request.scheme
   
    amount = transaction.price
    return_url = protocol + "://"+ domain + "/payment/confirm/"
    auth_token = "970bce3247a398006c10152d6ffc51d55eb4be88"  # Replace with your token management logic

    meta_data=transaction.meta_data
    meta_data['transaction_number']=transaction.transaction_number
    # API request payload
    payload = {
        "amount": amount,
        "note": transaction.meta_data['course']['course_name'],
        "return_url": return_url,
        "meta_data": meta_data,
    }

    # API headers
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {auth_token}',
    }

    # API URL
    api_url = 'https://devfundme.com/api/pms/generate_paylink/'

    try:
        # Make the POST request to the external API
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an error for HTTP codes 4xx/5xx
       
        # Parse the response
        response_data = response.json()
        pay_url = response_data.get('pay_url')
        redirect_url = pay_url
       
        return redirect_url

    except requests.RequestException as e:
        # Handle errors gracefully
        return JsonResponse({'error': 'Failed to generate payment link', 'details': str(e)}, status=500)


@login_required
def course_enrollment(request,course_id):   
   
    if request.method == 'POST':
        thinkific_user_id=None
        user = thinkific.users.list()['items']
        course = thinkific.courses.retrieve_course(id=course_id)
        course_name = course['name']
        for u in user:
            if u['email'] == request.user.email:
                thinkific_user_id = u['id']

        transaction = Transaction.objects.create(price=1,currency=Transaction.Currencies.USD,status=Transaction.Status.PENDING,meta_data={"course":{"course_id":course_id,"course_name":course_name},"user":{"id":request.user.pk,"thinkific_user_id":thinkific_user_id,}})
        redirect_url=generate_paylink(request,transaction)
        return redirect(redirect_url)

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