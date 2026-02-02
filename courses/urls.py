# courses/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('courses/', views.courses, name='courses'),
    path('course_details/<int:course_id>/', views.course_details, name="course_details"),
    
    # Nouvelles routes pour l'inscription avec paiement
    path('enrollment/<int:course_id>/', views.course_enrollment_step1, name='course_enrollment'),
    path('enrollment/payment/<str:payment_method>/', views.course_enrollment_payment, name='course_enrollment_payment'),
]