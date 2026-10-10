from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.http import FileResponse, Http404
from pathlib import Path

from .models import Category, Course, Enrollment, CourseMaterial, CourseCertificate


def course_list(request):
    category = request.GET.get('category', 'All') or 'All'
    categories = ['All'] + list(Category.objects.values_list('name', flat=True))
    all_courses = list(Course.objects.select_related('category'))
    for course in all_courses:
        course.home_group = course.category.name
    if category == 'All':
        courses = all_courses
    else:
        courses = [course for course in all_courses if course.category.name == category]
    return render(request, 'courses/course_list.html', {
        'courses': courses,
        'course_count': len(all_courses),
        'categories': categories,
        'active_category': category,
        'legacy_category': category if category not in categories else '',
        'build_whatsapp_url': f'https://wa.me/{settings.WHATSAPP_NUMBER}',
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
    enrollment = Enrollment.objects.filter(student=request.user, course=course).first()

    if request.method == 'POST':
        enrollment, _ = Enrollment.objects.get_or_create(student=request.user, course=course)
        messages.success(request, f'You are enrolled in {course.title}. Your materials are available in your profile.')
        return redirect('profile')

    return render(request, 'courses/enroll.html', {'course': course, 'enrollment': enrollment})


@login_required
def course_payment(request, slug):
    course = get_object_or_404(Course, slug=slug)
    get_object_or_404(Enrollment, student=request.user, course=course)
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

    return redirect('profile')


def _download(file):
    try:
        stream = file.open('rb')
    except (FileNotFoundError, ValueError):
        raise Http404('File is unavailable.')
    return FileResponse(stream, as_attachment=True, filename=Path(file.name).name)


@login_required
def material_download(request, pk):
    material = get_object_or_404(CourseMaterial, pk=pk, course__enrollments__student=request.user)
    return _download(material.file)


@login_required
def uploaded_certificate_download(request, pk):
    certificate = get_object_or_404(CourseCertificate, pk=pk, enrollment__student=request.user)
    return _download(certificate.file)
