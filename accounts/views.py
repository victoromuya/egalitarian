from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django import forms
from django.utils.http import url_has_allowed_host_and_scheme


def _validated_email(value, user=None):
    email = forms.EmailField(max_length=254).clean(value.strip()).lower()
    existing = User.objects.filter(email__iexact=email)
    if user is not None:
        existing = existing.exclude(pk=user.pk)
    if existing.exists():
        raise ValidationError('An account with this email address already exists.')
    return email


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            next_url = request.POST.get('next', '')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)
            return redirect('dashboard')
        messages.error(request, 'Invalid email address or password.')

    return render(request, 'accounts/login.html', {'next_url': request.POST.get('next', request.GET.get('next', ''))})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'accounts/register.html')

        try:
            validate_password(password1)
        except ValidationError as e:
            for err in e.messages:
                messages.error(request, err)
            return render(request, 'accounts/register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'That username is already taken.')
            return render(request, 'accounts/register.html')

        try:
            email = _validated_email(email)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
            return render(request, 'accounts/register.html')

        try:
            user = User.objects.create_user(
                username=username, email=email, password=password1,
                first_name=first_name, last_name=last_name,
            )
        except IntegrityError:
            messages.error(request, 'Could not create account with those details.')
            return render(request, 'accounts/register.html')

        if phone:
            user.profile.phone = phone
            user.profile.save()

        login(request, user)
        return redirect('dashboard')

    return render(request, 'accounts/register.html')


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def profile(request):
    if request.method == 'POST':
        try:
            email = _validated_email(request.POST.get('email', ''), request.user)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
            return redirect('profile')
        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name = request.POST.get('last_name', '').strip()
        request.user.email = email
        try:
            request.user.save()
        except IntegrityError:
            messages.error(request, 'An account with this email address already exists.')
            return redirect('profile')
        messages.success(request, 'Profile updated.')
        return redirect('profile')

    from exams.models import Certificate
    enrollments = request.user.enrollments.select_related('course', 'uploaded_certificate').prefetch_related('course__materials')
    certificates = Certificate.objects.filter(submission__student=request.user).select_related('submission__exam__course').order_by('-issued_at')
    return render(request, 'accounts/profile.html', {'enrollments': enrollments, 'certificates': certificates})
