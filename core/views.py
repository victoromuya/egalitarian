from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.urls import reverse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from courses.models import Course
from events.models import Event
from .models import NewsletterSubscriber
from .homepage import COURSE_GROUPS, course_group


def home(request):
    all_courses = Course.objects.all()
    featured_courses = list(all_courses)
    visible_courses = 0
    for course in featured_courses:
        course.home_group = course_group(course)
        course.home_visible = course.home_group == COURSE_GROUPS[0] and visible_courses < 3
        if course.home_visible:
            visible_courses += 1
    upcoming_events = Event.objects.all()[:2]
    stats = {
        'countries': 150,
        'graduates': '28,000',
        'staff': 750,
        'courses': '1,200',
    }
    build_message = quote(
        "Hello Egalitarian Computers! I'd like to discuss a software project "
        "with your engineering team."
    )
    build_whatsapp_url = f'https://wa.me/{settings.WHATSAPP_NUMBER}?text={build_message}'
    return render(request, 'core/home.html', {
        'featured_courses': featured_courses,
        'course_count': len(featured_courses),
        'upcoming_events': upcoming_events,
        'stats': stats,
        'build_whatsapp_url': build_whatsapp_url,
        'course_categories': COURSE_GROUPS,
        'initial_group_empty': bool(featured_courses) and visible_courses == 0,
    })


@require_POST
def newsletter_subscribe(request):
    email = request.POST.get('email', '').strip().lower()
    try:
        validate_email(email)
        if len(email) > 254:
            raise ValidationError('Email is too long.')
    except ValidationError:
        message = 'Please enter a valid email address.'
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({'message': message}, status=400)
        messages.error(request, message)
        return redirect(reverse('home') + '#newsletter-title')
    NewsletterSubscriber.objects.get_or_create(email=email)
    message = 'Thanks! You’re on our list for course and event updates.'
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'message': message})
    messages.success(request, message)
    return redirect(reverse('home') + '#newsletter-title')


def about(request):
    team = [
        {'name': 'Michael Nnadi', 'role': 'Co-Founder & CEO', 'bio': 'A serial entrepreneur and investor leading Egalitarian Computers toward its mission of democratizing tech education across Africa and beyond.'},
        {'name': 'Edwin Osamezu', 'role': 'Co-Founder & Lead Instructor', 'bio': 'An experienced educator with decades of training and workshop facilitation, driving the curriculum and learner outcomes at Tech Egalitarian.'},
    ]
    return render(request, 'core/about.html', {
        'team': team,
        'build_whatsapp_url': f'https://wa.me/{settings.WHATSAPP_NUMBER}',
    })


def contact(request):
    import re
    from .forms import ContactForm

    form = ContactForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        message = (
            f"Hello Egalitarian Computers!\n\nSubject: {data['subject']}"
            f"\nName: {data['name']}\nEmail: {data['email']}"
            f"\nPhone: {data['phone'] or 'Not provided'}\n\n{data['message']}"
        )
        number = re.sub(r'[^0-9]', '', settings.WHATSAPP_NUMBER)
        return redirect(f'https://wa.me/{number}?text={quote(message)}')
    return render(request, 'core/contact.html', {
        'contact_form': form,
        'build_whatsapp_url': f'https://wa.me/{settings.WHATSAPP_NUMBER}',
    })


@login_required
def dashboard(request):
    enrollments = request.user.enrollments.select_related('course')
    notifications = request.user.notifications.all()[:5]
    return render(request, 'core/dashboard.html', {
        'enrollments': enrollments,
        'notifications': notifications,
    })


@login_required
def notifications(request):
    notifications = request.user.notifications.all()
    return render(request, 'core/notifications.html', {'notifications': notifications})


@login_required
@require_POST
def mark_all_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect('notifications')
