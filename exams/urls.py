from django.urls import path
from . import views

urlpatterns = [
    path('<slug:slug>/take/', views.exam_take, name='exam_take'),
    path('<slug:slug>/submit/', views.submit_exam, name='submit_exam'),
    path('<slug:slug>/result/', views.exam_result, name='exam_result'),
    path('<slug:slug>/certificate/', views.certificate_download, name='certificate_download'),
]
