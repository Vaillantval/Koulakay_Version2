from django.db import models
from django.contrib.auth import get_user_model
# Create your models here.


class Enrollment(models.Model):
    user_id = models.ForeignKey(get_user_model(),on_delete=models.CASCADE,blank=False)
    course_id = models.IntegerField('Course id',blank=False)
    activated_at = models.DateTimeField(('activated at'),blank=False)
    expiry_date = models.DateTimeField(('expiry date'), blank=False)
