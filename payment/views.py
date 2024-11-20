from django.shortcuts import redirect
from django.http import HttpResponseNotFound 
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site

from courses.models import Enrollment
from .models import Transaction, Payment

from django.utils import timezone
from django.contrib.sites.shortcuts import get_current_site
from datetime import timedelta
from django.contrib.auth import get_user_model
from thinkific import Thinkific
thinkific = Thinkific(settings.THINKIFIC['AUTH_TOKEN'],settings.THINKIFIC['SITE_ID'])
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse


@csrf_exempt
def confirm(request):
    if request.method == 'POST':
        try:
            # Parse the incoming JSON payload
            payload = json.loads(request.body)
            transaction_number=payload.get('transaction_number')
            if transaction_number is not None:
                transaction = Transaction.objects.get(transaction_number=transaction_number)
                try:
                    transaction = Transaction.objects.get(transaction_number=transaction_number)
                    print(transaction)
                except:
                    return HttpResponseNotFound()

                try:

                    user     = get_user_model().objects.get(id=transaction.meta_data["user"]["id"])
                    course_id = transaction.meta_data['courses']["course_id"]
                    thinkific_user_id = transaction.meta_data['user']["thinkific_user_id"]
                    activated_at = timezone.now()
                    expiry_date = (timezone.now() + timedelta(days=30))

                    thinkific.enrollments.create_enrollment({
                    'user_id':thinkific_user_id,
                    'course_id':course_id,
                    'activated_at':activated_at.isoformat(),
                    'expiry_date':expiry_date.isoformat()
                    })
                
                    enrollment=Enrollment.objects.create(user=user, thinkific_user_id=thinkific_user_id,course_id=course_id,activated_at=activated_at,expiry_date=expiry_date)

                    Payment.objects.create(user=user,enrollment=enrollment,transaction=transaction)

                except get_user_model().DoesNotExist:
                    return HttpResponseNotFound()
                
                transaction.status = Transaction.Status.COMPLETE
                transaction.save()

                return redirect("courses")
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON payload'}, status=400)


    else:
        return HttpResponseNotFound()