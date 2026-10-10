from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.http import require_POST
from datetime import timedelta
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from core.models import Notification
from courses.models import Course, Enrollment

from .certificates import generate_certificate_pdf
from .models import Answer, Certificate, Exam, Submission

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


def _deadline(submission):
    return submission.started_at + timedelta(minutes=submission.exam.duration_minutes)


def _questions(exam):
    return list(exam.questions.prefetch_related('choices'))


def _ready(exam, questions):
    return bool(questions) and exam.duration_minutes > 0 and 0 <= exam.passing_score <= 100 and all(
        len(q.choices.all()) >= 2 and sum(c.is_correct for c in q.choices.all()) == 1 for q in questions
    )


def _save_answers(submission, questions, data):
    for question in questions:
        value = data.get(f'question_{question.pk}', '')
        choice = next((c for c in question.choices.all() if str(c.pk) == value), None)
        Answer.objects.update_or_create(submission=submission, question=question, defaults={'selected_choice': choice})


@login_required
def exam_take(request, slug):
    course = get_object_or_404(Course, slug=slug)
    exam = get_object_or_404(Exam, course=course)

    if _get_paid_enrollment_or_none(request.user, course) is None:
        messages.error(request, PAYMENT_REQUIRED_MESSAGE)
        return redirect('course_detail', slug=course.slug)

    questions = _questions(exam)
    context = {'exam': exam, 'course_slug': slug, 'questions': questions, 'exam_ready': _ready(exam, questions)}
    if context['exam_ready']:
        submission = Submission.objects.filter(student=request.user, exam=exam, status='in_progress').first()
        if submission is None:
            submission = Submission.objects.create(student=request.user, exam=exam, attempt_number=Submission.objects.filter(student=request.user, exam=exam).count() + 1)
        selected = dict(submission.answers.values_list('question_id', 'selected_choice_id'))
        for question in questions:
            question.selected_choice_id = selected.get(question.pk)
        context.update({'submission': submission, 'deadline_ms': int(_deadline(submission).timestamp() * 1000), 'server_now_ms': int(timezone.now().timestamp() * 1000)})
    return render(request, 'exams/exam_take.html', context)


@login_required
@require_POST
def save_exam_answers(request, slug):
    exam = get_object_or_404(Exam, course__slug=slug)
    if _get_paid_enrollment_or_none(request.user, exam.course) is None:
        return JsonResponse({'error': PAYMENT_REQUIRED_MESSAGE}, status=403)
    with transaction.atomic():
        submission = get_object_or_404(Submission.objects.select_for_update(), pk=request.POST.get('submission_id') if request.POST.get('submission_id', '').isdigit() else None, student=request.user, exam=exam)
        if submission.status != 'in_progress' or timezone.now() >= _deadline(submission):
            return JsonResponse({'error': 'This attempt has ended.'}, status=409)
        _save_answers(submission, _questions(exam), request.POST)
    return JsonResponse({'saved': True})


@login_required
@transaction.atomic
def submit_exam(request, slug):
    if request.method != 'POST':
        return redirect('exam_take', slug=slug)

    course = get_object_or_404(Course, slug=slug)
    exam = get_object_or_404(Exam, course=course)

    if _get_paid_enrollment_or_none(request.user, course) is None:
        messages.error(request, PAYMENT_REQUIRED_MESSAGE)
        return redirect('course_detail', slug=course.slug)

    submission = get_object_or_404(Submission.objects.select_for_update(), pk=request.POST.get('submission_id') if request.POST.get('submission_id', '').isdigit() else None, student=request.user, exam=exam)
    if submission.status == 'submitted':
        return redirect('exam_result', slug=slug)
    questions = _questions(exam)
    if not _ready(exam, questions):
        messages.error(request, 'This exam is not ready yet. Please contact the admin.')
        return redirect('profile')
    if timezone.now() < _deadline(submission):
        _save_answers(submission, questions, request.POST)
    correct_count = 0
    for question in questions:
        answer, _ = Answer.objects.get_or_create(submission=submission, question=question)
        if answer.selected_choice_id and answer.selected_choice.question_id == question.pk and answer.is_correct:
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

    try:
        stream = certificate.pdf_file.open('rb')
    except (FileNotFoundError, ValueError):
        raise Http404('Certificate file is unavailable.')
    return FileResponse(
        stream,
        as_attachment=True,
        filename=f'certificate-{course.slug}.pdf',
    )
