from django.db import models

from django.utils.translation import gettext_lazy as _

from accounts.models import User
from courses.models import Enrollment

def transaction_number_generator(sender, instance, **kwargs):

    if instance.transaction_number is None:

        def get_transaction_number(next_val):

            while len(str(next_val)) < 6:
                next_val = '0'+str(next_val)

            return 'KOULKY'+next_val

        last_transaction_number="KOULKY000000"

        last_transaction = Transaction.objects.filter(transaction_number__contains="KOULKY").last()

        if last_transaction:
            last_transaction_number=last_transaction.transaction_number

        next_val = int(last_transaction_number.replace('KOULKY',''))+1

        transaction_number = get_transaction_number(next_val)

        while Transaction.objects.filter(transaction_number=transaction_number):
            transaction_number = get_transaction_number(next_val+1)

        instance.transaction_number = transaction_number


class Transaction(models.Model):

    class Status(models.TextChoices):
        PENDING = 'PENDING', _("Pending")
        FAILED = 'FAILED', _("Failed")
        COMPLETE = 'COMPLETE', _("Complete")

    class Currencies(models.TextChoices):
        HTG = 'HTG', _("HTG")
        USD = 'USD', _("USD")
        EUR = 'EUR', _("EUR")
        GBP = 'GBP', _("GBP")

    transaction_number = models.CharField(_('transaction number'),help_text='Ex:MPT0001',max_length=255,default=None,unique=True)

    price = models.DecimalField(_('price'),help_text=_('Ex: 1000'),max_length=255,max_digits=11,decimal_places=2,blank=False,default=1000)
    currency = models.CharField(_('currency'),max_length=25,choices=Currencies.choices,default=Currencies.USD,blank=False)

    status = models.CharField(_('status'),max_length=25,choices=Status.choices,default=Status.PENDING,blank=False)

    meta_data = models.JSONField(_("Meta data"),null=True,blank=True)
    
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True) 

models.signals.pre_save.connect(transaction_number_generator, sender=Transaction)


class Payment(models.Model):
    user        = models.ForeignKey(User,on_delete=models.CASCADE,blank=False)
    enrollment    = models.ForeignKey(Enrollment,on_delete=models.CASCADE,blank=False)
    transaction    = models.ForeignKey(Transaction,on_delete=models.CASCADE,blank=False)

    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)
    