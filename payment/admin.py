from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from .models import Transaction, Payment


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_number',
        'user_email_display',
        'course_name_display',
        'price_display',
        'payment_method',
        'status_badge',
        'created_at',
    )
    
    list_display_links = ('transaction_number',)
    
    list_filter = (
        'status',
        'payment_method',
        'currency',
        'created_at',
    )
    
    search_fields = (
        'transaction_number',
        'external_transaction_id',
        'user__email',
        'user__first_name',
        'user__last_name',
    )
    
    readonly_fields = (
        'transaction_number',
        'created_at',
        'updated_at',
        'completed_at',
        'thinkific_external_order_id',
    )
    
    fieldsets = (
        (_('Informations de base'), {
            'fields': (
                'transaction_number',
                'user',
                'status',
                'payment_method',
            )
        }),
        (_('Montant'), {
            'fields': (
                'price',
                'currency',
            )
        }),
        (_('Références externes'), {
            'fields': (
                'external_transaction_id',
                'thinkific_external_order_id',
            )
        }),
        (_('Métadonnées'), {
            'fields': ('meta_data',),
            'classes': ('collapse',)
        }),
        (_('Dates'), {
            'fields': (
                'created_at',
                'updated_at',
                'completed_at',
            )
        }),
    )
    
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    actions = ['mark_as_completed', 'mark_as_failed', 'export_transactions']
    
    def user_email_display(self, obj):
        """Affiche l'email de l'utilisateur"""
        if obj.user:
            return obj.user.email
        return obj.meta_data.get('user', {}).get('email', 'N/A')
    user_email_display.short_description = _('Email')
    
    def course_name_display(self, obj):
        """Affiche le nom du cours"""
        return obj.course_name
    course_name_display.short_description = _('Cours')
    
    def price_display(self, obj):
        """Affiche le prix formaté"""
        return f"{obj.price} {obj.currency}"
    price_display.short_description = _('Prix')
    
    def status_badge(self, obj):
        """Affiche le statut avec un badge coloré"""
        colors = {
            'PENDING': 'orange',
            'COMPLETED': 'green',
            'FAILED': 'red',
            'CANCELLED': 'gray',
            'REFUNDED': 'purple',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _('Statut')
    
    def mark_as_completed(self, request, queryset):
        """Action pour marquer comme complétée"""
        updated = queryset.update(status=Transaction.Status.COMPLETED)
        self.message_user(request, f'{updated} transaction(s) marquée(s) comme complétée(s).')
    mark_as_completed.short_description = _('Marquer comme complétée')
    
    def mark_as_failed(self, request, queryset):
        """Action pour marquer comme échouée"""
        updated = queryset.update(status=Transaction.Status.FAILED)
        self.message_user(request, f'{updated} transaction(s) marquée(s) comme échouée(s).')
    mark_as_failed.short_description = _('Marquer comme échouée')
    
    def export_transactions(self, request, queryset):
        """Exporter les transactions sélectionnées (à implémenter)"""
        # TODO: Implémenter l'export CSV/Excel
        self.message_user(request, 'Export non implémenté.')
    export_transactions.short_description = _('Exporter les transactions')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user_link',
        'transaction_link',
        'enrollment_link',
        'created_at',
    )
    
    list_filter = (
        'created_at',
    )
    
    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'transaction__transaction_number',
    )
    
    readonly_fields = (
        'created_at',
        'updated_at',
    )
    
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    def user_link(self, obj):
        """Lien vers l'utilisateur"""
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = _('Utilisateur')
    
    def transaction_link(self, obj):
        """Lien vers la transaction"""
        url = reverse('admin:payment_transaction_change', args=[obj.transaction.id])
        return format_html('<a href="{}">{}</a>', url, obj.transaction.transaction_number)
    transaction_link.short_description = _('Transaction')
    
    def enrollment_link(self, obj):
        """Lien vers l'inscription"""
        url = reverse('admin:courses_enrollment_change', args=[obj.enrollment.id])
        return format_html('<a href="{}">Enrollment #{}</a>', url, obj.enrollment.id)
    enrollment_link.short_description = _('Inscription')