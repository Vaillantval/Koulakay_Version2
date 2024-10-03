from django.contrib import admin
import accounts.models as models




class UserAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'password',
        'last_login',
        'is_superuser',
        'username',
        'first_name',
        'last_name',
        'email',
        'is_staff',
        'is_active',
        'date_joined',
    )
    list_filter = (
        'last_login',
        'is_superuser',
        'is_staff',
        'is_active',
        'date_joined',
        'id',
        'password',
        'username',
        'first_name',
        'last_name',
        'email',
    )
    raw_id_fields = ('groups', 'user_permissions')


def _register(model, admin_class):
    admin.site.register(model, admin_class)


_register(models.User, UserAdmin)
