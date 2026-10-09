from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Course, Enrollment

CATEGORIES = ['All'] + [choice[0]
 for choice in Course.CATEGORY_CHOICES]


def course_list(request):
    category = request.GET.get('category', 'All')
    courses = Course.objects.all()
    if category and category != 'All':
        courses = courses.filter(category=category)
    return render(request, 'courses/course_list.html', {
        'courses': courses,
        'categories': CATEGORIES,
        'active_category': category,
    })


def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    return render(request, 'courses/course_detail.html', {'course': course})


@login_required
def my_courses(request):
    from exams.models import Certificate, Submission

    enrollments = request.user.enrollments.select_related('course')
    items = []
    for enrollment in enrollments:
        course = enrollment.course
        exam = getattr(course, 'exam', None)
        submission_count = 0
        certificate = None
        if exam and enrollment.is_paid:
            submission_count = Submission.objects.filter(
                student=request.user, exam=exam, status='submitted',
            ).count()
            certificate = Certificate.objects.filter(
                submission__student=request.user, submission__exam=exam,
            ).order_by('-issued_at').first()
        items.append({
            'enrollment': enrollment,
            'course': course,
            'exam': exam,
            'submission_count': submission_count,
            'certificate': certificate,
        })
    return render(request, 'courses/my_courses.html', {'items': items})


@login_required
def enroll(request, slug):
    course = get_object_or_404(Course, slug=slug)
    enrollment, _ = Enrollment.objects.get_or_create(student=request.user, course=course)

    if request.method == 'POST':
        if course.is_free:
            messages.success(request, f'You are enrolled in {course.title}.')
            return redirect('course_detail', slug=course.slug)

        whatsapp_message = quote(
            f'Hi, I would like to pay for the course "{course.title}" '
            f'(${course.price}). My username is {request.user.username}.'
        )
        whatsapp_url = f'https://wa.me/{settings.WHATSAPP_NUMBER}?text={whatsapp_message}'
        return redirect(whatsapp_url)

    return render(request, 'courses/enroll.html', {'course': course, 'enrollment': enrollment})
