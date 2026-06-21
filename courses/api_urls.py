"""Routes API catalogue + apprentissage — montées sous /api/v1/ (hors i18n)."""
from django.urls import path
from . import api_views

urlpatterns = [
    # Catalogue (Phase 1)
    path('courses/', api_views.course_list, name='api_course_list'),
    path('courses/<int:course_id>/', api_views.course_detail, name='api_course_detail'),
    path('courses/<int:course_id>/content/', api_views.course_content, name='api_course_content'),
    path('categories/', api_views.category_list, name='api_category_list'),
    path('bundles/', api_views.bundle_list, name='api_bundle_list'),

    # Apprentissage & inscriptions (Phase 3)
    path('my/enrollments/', api_views.my_enrollments, name='api_my_enrollments'),
    path('courses/<int:course_id>/enroll/', api_views.enroll_course, name='api_enroll_course'),
    path('courses/<int:course_id>/access/', api_views.course_access, name='api_course_access'),
    path('bundles/<int:bundle_id>/enroll/', api_views.enroll_bundle, name='api_enroll_bundle'),
]
