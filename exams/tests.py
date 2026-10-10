from datetime import timedelta
import tempfile

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from courses.models import Category, Course, Enrollment
from .models import Answer, Certificate, Choice, Exam, Question, Submission


class ExamFlowTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.student = User.objects.create_user('exam-student')
        self.other = User.objects.create_user('other-student')
        self.course = Course.objects.create(title='Exam Course', slug='exam-course', category=Category.objects.get_or_create(name='Programming')[0], price=0)
        self.enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        self.exam = Exam.objects.create(course=self.course, title='Course Assessment', duration_minutes=10, passing_score=70)
        self.questions = [Question.objects.create(exam=self.exam, text=f'Question {i}?', order=i) for i in range(2)]
        self.correct = [Choice.objects.create(question=q, text='Correct answer', is_correct=True) for q in self.questions]
        self.wrong = [Choice.objects.create(question=q, text='Incorrect answer') for q in self.questions]
        self.take_url = reverse('exam_take', args=[self.course.slug])
        self.submit_url = reverse('submit_exam', args=[self.course.slug])
        self.save_url = reverse('save_exam_answers', args=[self.course.slug])
        self.result_url = reverse('exam_result', args=[self.course.slug])
        self.client.force_login(self.student)

    def start(self):
        response = self.client.get(self.take_url)
        self.assertEqual(response.status_code, 200)
        return response.context['submission']

    def answers(self, submission):
        return {'submission_id': submission.pk, **{f'question_{q.pk}': choice.pk for q, choice in zip(self.questions, self.correct)}}

    def test_login_enrollment_and_payment_required_on_take_save_and_submit(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.take_url).status_code, 302)
        self.client.force_login(self.other)
        self.assertRedirects(self.client.get(self.take_url), reverse('course_detail', args=[self.course.slug]))
        self.enrollment.is_paid = False
        self.enrollment.save()
        self.client.force_login(self.student)
        self.assertEqual(self.client.post(self.save_url).status_code, 403)
        self.assertRedirects(self.client.post(self.submit_url), reverse('course_detail', args=[self.course.slug]))
        self.assertEqual(Submission.objects.count(), 0)

    def test_reload_preserves_attempt_deadline_and_saved_answers(self):
        submission = self.start()
        response = self.client.post(self.save_url, self.answers(submission))
        self.assertJSONEqual(response.content, {'saved': True})
        response = self.client.get(self.take_url)
        self.assertEqual(response.context['submission'].pk, submission.pk)
        self.assertEqual(Submission.objects.count(), 1)
        self.assertContains(response, 'checked')
        self.assertEqual(response.context['questions'][0].selected_choice_id, self.correct[0].pk)

    def test_successful_submit_grades_once_and_issues_downloadable_certificate(self):
        submission = self.start()
        data = self.answers(submission)
        self.assertRedirects(self.client.post(self.submit_url, data), self.result_url)
        submission.refresh_from_db()
        self.assertEqual(submission.score, 100)
        self.assertEqual(submission.status, 'submitted')
        self.assertEqual(Answer.objects.filter(submission=submission).count(), 2)
        self.assertEqual(Certificate.objects.count(), 1)
        self.assertRedirects(self.client.post(self.submit_url, data), self.result_url)
        self.assertEqual(Submission.objects.count(), 1)
        self.assertEqual(Certificate.objects.count(), 1)
        response = self.client.get(reverse('certificate_download', args=[self.course.slug]))
        self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF'))
        response.close()
        self.assertContains(self.client.get(reverse('profile')), 'Exam Certificates')

    def test_invalid_cross_question_and_unanswered_choices_score_zero(self):
        submission = self.start()
        self.client.post(self.submit_url, {'submission_id': submission.pk, f'question_{self.questions[0].pk}': self.correct[1].pk, f'question_{self.questions[1].pk}': 'invalid'})
        submission.refresh_from_db()
        self.assertEqual(submission.score, 0)
        self.assertEqual(Certificate.objects.count(), 0)
        self.assertContains(self.client.get(self.result_url), 'Retake Exam')

    def test_expired_attempt_grades_saved_answers_and_rejects_late_changes(self):
        submission = self.start()
        self.client.post(self.save_url, {'submission_id': submission.pk, f'question_{self.questions[0].pk}': self.correct[0].pk})
        Submission.objects.filter(pk=submission.pk).update(started_at=timezone.now() - timedelta(minutes=11))
        self.assertEqual(self.client.post(self.save_url, self.answers(submission)).status_code, 409)
        self.client.post(self.submit_url, self.answers(submission))
        submission.refresh_from_db()
        self.assertEqual(submission.score, 50)

    def test_attempt_ownership_and_csrf_are_enforced(self):
        submission = self.start()
        Enrollment.objects.create(student=self.other, course=self.course)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.submit_url, self.answers(submission)).status_code, 404)
        self.assertEqual(self.client.post(self.save_url, self.answers(submission)).status_code, 404)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        self.assertEqual(client.post(self.submit_url, self.answers(submission)).status_code, 403)
        self.assertEqual(client.post(self.save_url, self.answers(submission)).status_code, 403)

    def test_incomplete_exam_does_not_start_attempt(self):
        self.correct[0].delete()
        response = self.client.get(self.take_url)
        self.assertContains(response, 'This exam is being prepared')
        self.assertNotContains(response, 'id="exam-form"')
        self.assertEqual(Submission.objects.count(), 0)

    def test_failed_retake_keeps_previous_certificate_available(self):
        first = self.start()
        self.client.post(self.submit_url, self.answers(first))
        second = self.start()
        self.assertNotEqual(first.pk, second.pk)
        self.client.post(self.submit_url, {'submission_id': second.pk})
        response = self.client.get(self.result_url)
        self.assertFalse(response.context['result']['passed'])
        self.assertContains(response, 'Download Certificate PDF')

    def test_student_cannot_download_another_students_certificate(self):
        submission = self.start()
        self.client.post(self.submit_url, self.answers(submission))
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('certificate_download', args=[self.course.slug])).status_code, 404)
