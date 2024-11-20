from django.contrib import admin
from .models import Transaction


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id','transaction_number','price','currency','status')
    list_display_links = ('transaction_number',)
    list_filter = ('status',)
    search_fields = ('',)
    list_per_page = 25

admin.site.register(Transaction, TransactionAdmin)