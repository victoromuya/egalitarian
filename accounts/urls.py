from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.txt',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done'),
        extra_context={'reset_step': 'request'},
    ), name='password_reset'),
    path('password-reset/sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset.html', extra_context={'reset_step': 'sent'},
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset.html',
        success_url=reverse_lazy('password_reset_complete'),
        extra_context={'reset_step': 'confirm'},
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset.html', extra_context={'reset_step': 'complete'},
    ), name='password_reset_complete'),
]
