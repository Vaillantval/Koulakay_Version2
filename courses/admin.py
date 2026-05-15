from django.contrib import admin
import courses.models as models


class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'thinkific_user_id', 'course_id', 'activated_at', 'expiry_date')
    list_filter = ('user', 'activated_at', 'expiry_date', 'id', 'thinkific_user_id', 'course_id')


def _register(model, admin_class):
    admin.site.register(model, admin_class)


_register(models.Enrollment, EnrollmentAdmin)


@admin.register(models.CourseTranslation)
class CourseTranslationAdmin(admin.ModelAdmin):
    list_display = ('course_id', 'language', 'name')
    list_filter = ('language',)
    search_fields = ('course_id', 'name')
    ordering = ('course_id', 'language')


class CourseCategoryMembershipInline(admin.TabularInline):
    model = models.CourseCategoryMembership
    extra = 1
    fields = ('course_id', 'course_name_cache')


@admin.register(models.CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ('order', 'name', 'slug', 'icon', 'color', 'is_active', 'course_count')
    list_editable = ('order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CourseCategoryMembershipInline]

    def course_count(self, obj):
        return obj.memberships.count()
    course_count.short_description = 'Nb cours'
