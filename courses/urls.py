from django.urls import path
from . import views

urlpatterns = [
    path('', views.course_list, name='course_list'),
    # must precede the slug pattern so 'mine' isn't captured as a course slug
    path('mine/', views.my_courses, name='my_courses'),
    path('<slug:slug>/', views.course_detail, name='course_detail'),
    path('<slug:slug>/enroll/', views.enroll, name='enroll'),
]
