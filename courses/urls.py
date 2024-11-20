from django.urls import path
from . import views


urlpatterns = [
    path('', views.courses, name='courses'),
    path('search_course/', views.search_course, name='search_course'),
    path('enrollmment/<int:course_id>/', views.course_enrollment, name='course_enrollment'),
]