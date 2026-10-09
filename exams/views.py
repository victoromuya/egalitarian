from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from core.models import Notification
from courses.models import Course, Enrollment

from .certificates import generate_certificate_pdf
from .models import Answer, Certificate, Choice, Exam, Submission

PAYMENT_REQUIRED_MESSAGE = 'You must be enrolled and have paid for this course before taking the exam.'


def _get_paid_enrollment_or_none(user, course):
    enrollment = Enrollment.objects.filter(student=user, course=course).first()
    return enrollment if enrollment and enrollment.is_paid else None


def _latest_submission(user, exam):
    return Submission.objects.filter(
        student=user, exam=exam, status='submitted',
    ).order_by('-submitted_at').first()


def _get_certificate_or_none(user, exam):
    # The certificate belongs to whichever attempt passed, which is not
    # necessarily the latest submission (e.g. a failed retake after a pass).
    return Certificate.objects.filter(
        submission__student=user, submission__exam=exam,
    ).order_by('-issued_at').first()


@login_required
def exam_take(request, slug):
    course = get_object_or_404(Course, slug=slug)
    exam = get_object_or_404(Exam, course=course)

    if _get_paid_enrollment_or_none(request.user, course) is None:
        messages.error(request, PAYMENT_REQUIRED_MESSAGE)
        return redirect('course_detail', slug=course.slug)

    return render(request, 'exams/exam_take.html', {'exam': exam, 'course_slug': slug})


@login_required
def submit_exam(request, slug):
    if request.method != 'POST':
        return redirect('exam_take', slug=slug)

    course = get_object_or_404(Course, slug=slug)
    exam = get_object_or_404(Exam, course=course)

    if _get_paid_enrollment_or_none(request.user, course) is None:
        messages.error(request, PAYMENT_REQUIRED_MESSAGE)
        return redirect('course_detail', slug=course.slug)

    previous_attempts = Submission.objects.filter(student=request.user, exam=exam).count()
    submission = Submission.objects.create(
        student=request.user, exam=exam, attempt_number=previous_attempts + 1,
    )

    questions = list(exam.questions.all())
    correct_count = 0
    for question in questions:
        selected_choice_id = request.POST.get(f'question_{question.id}')
        selected_choice = None
        if selected_choice_id:
            selected_choice = Choice.objects.filter(id=selected_choice_id, question=question).first()
        Answer.objects.create(
            submission=submission, question=question, selected_choice=selected_choice,
        )
        if selected_choice is not None and selected_choice.is_correct:
            correct_count += 1

    score = round((correct_count / len(questions)) * 100) if questions else 0

    submission.score = score
    submission.status = 'submitted'
    submission.submitted_at = timezone.now()
    submission.save()

    if submission.passed:
        generate_certificate_pdf(submission)
        message = f'Congratulations! You passed "{exam.title}" with a score of {score}%. Your certificate is ready.'
    else:
        message = f'You scored {score}% on "{exam.title}" - the passing score is {exam.passing_score}%. You can retake it.'
    Notification.objects.create(
        user=request.user, message=message, link=reverse('exam_result', args=[course.slug]),
    )

    return redirect('exam_result', slug=slug)


@login_required
def exam_result(request, slug):
    course = get_object_or_404(Course, slug=slug)
    exam = get_object_or_404(Exam, course=course)

    submission = _latest_submission(request.user, exam)
    if submission is None:
        messages.error(request, 'You have not taken this exam yet.')
        return redirect('exam_take', slug=slug)

    answers = list(submission.answers.select_related('selected_choice'))
    result = {
        'score': submission.score,
        'passing_score': exam.passing_score,
        'passed': submission.passed,
        'total_questions': len(answers),
        'correct': sum(1 for answer in answers if answer.is_correct),
        'exam': exam,
        'has_certificate': _get_certificate_or_none(request.user, exam) is not None,
    }
    return render(request, 'exams/exam_result.html', {'result': result, 'course_slug': slug})


@login_required
def certificate_download(request, slug):
    course = get_object_or_404(Course, slug=slug)
    exam = get_object_or_404(Exam, course=course)
    certificate = _get_certificate_or_none(request.user, exam)
    if certificate is None:
        raise Http404

    return FileResponse(
        certificate.pdf_file.open('rb'),
        as_attachment=True,
        filename=f'certificate-{course.slug}.pdf',
    )
