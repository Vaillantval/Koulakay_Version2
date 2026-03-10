from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import User

from import_export.admin import ImportExportModelAdmin

class CustomUserAdmin(ImportExportModelAdmin, UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    list_display = ("email", "first_name", "last_name", "thinkific_user_id", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active")
    fieldsets = (
        ("Identité", {"fields": ("first_name", "last_name", "email", "password")}),
        ("Thinkific", {"fields": ("thinkific_user_id",)}),
        ("Permissions", {"fields": ("is_staff", "is_active", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        ("Identité", {
            "classes": ("wide",),
            "fields": ("first_name", "last_name", "email", "password1", "password2"),
        }),
        ("Permissions", {
            "fields": ("is_staff", "is_active"),
        }),
    )
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)


admin.site.register(User, CustomUserAdmin)