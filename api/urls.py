from django.urls import path
from . import views

urlpatterns = [
    path('auth/login/', views.login, name='api_login'),
    path('auth/register/', views.register, name='api_register'),
    path('auth/password-reset/', views.password_reset, name='api_password_reset'),
    path('auth/firebase/', views.firebase_auth, name='api_firebase_auth'),
    path('me/', views.me, name='api_me'),
    path('courses/', views.courses_list, name='api_courses_list'),
    path('courses/<int:course_id>/', views.course_detail, name='api_course_detail'),
    path('courses/<int:course_id>/chapters/', views.course_chapters, name='api_course_chapters'),
    path('chapters/<int:chapter_id>/contents/', views.chapter_contents, name='api_chapter_contents'),
    path('enrollments/', views.enrollments_list, name='api_enrollments'),
]
