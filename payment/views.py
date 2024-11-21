from django.http import HttpResponseNotFound ,HttpResponseNotAllowed
from django.conf import settings
from courses.models import Enrollment
from .models import Transaction, Payment
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from thinkific import Thinkific
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse

thinkific = Thinkific(settings.THINKIFIC['AUTH_TOKEN'],settings.THINKIFIC['SITE_ID'])

@csrf_exempt
def confirm(request):
   
    if request.method == 'POST':

        try:
            # Parse the incoming JSON payload
            payload = json.loads(request.body)
            transaction_number=payload.get('paylink').get('meta_data').get('transaction_number')
            print(transaction_number)
            if transaction_number is not None:
                try:
                    transaction = Transaction.objects.get(transaction_number=transaction_number)
                except:
                    return JsonResponse({'success': False, 'error': 'Transaction not found'}, status=404)

                try:

                    user     = get_user_model().objects.get(id=transaction.meta_data.get("user").get("id"))
                    course_id = transaction.meta_data.get('course').get("course_id")
                    thinkific_user_id = transaction.meta_data.get('user').get("thinkific_user_id")
                    activated_at = timezone.now()
                    expiry_date = (timezone.now() + timedelta(days=30))
                   
                    if course_id is not None and thinkific_user_id is not None:
                        thinkific.enrollments.create_enrollment({
                        'user_id':thinkific_user_id,
                        'course_id':course_id,
                        'activated_at':activated_at.isoformat(),
                        'expiry_date':expiry_date.isoformat()
                        })
                    
                        enrollment,created=Enrollment.objects.update_or_create(user=user, thinkific_user_id=thinkific_user_id,course_id=course_id,activated_at=activated_at,expiry_date=expiry_date)

                        Payment.objects.create(user=user,enrollment=enrollment,transaction=transaction)

                        transaction.status = Transaction.Status.COMPLETE
                        transaction.save()

                except get_user_model().DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'NOt found user'}, status=400)
                
               

                return JsonResponse({'success': True, 'error': 'Transaction save successfully'}, status=200)
            
            else:
                return JsonResponse({'success': False, 'error': 'Transaction not found'}, status=404)
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON payload'}, status=400)


    else:
        return HttpResponseNotAllowed(['POST'])