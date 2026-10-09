from django.conf import settings
from django.db import models

from courses.models import Course


class Exam(models.Model):
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='exam')
    title = models.CharField(max_length=200)
    duration_minutes = models.PositiveIntegerField()
    passing_score = models.PositiveIntegerField(help_text='Percentage required to pass, e.g. 70')

    def __str__(self):
        return self.title


class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.text[:60]


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class Submission(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submissions',
    )
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='submissions')
    attempt_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    score = models.PositiveIntegerField(null=True, blank=True, help_text='Percentage score')
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.student} - {self.exam} (attempt {self.attempt_number})'

    @property
    def passed(self):
        return self.score is not None and self.score >= self.exam.passing_score


class Answer(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    selected_choice = models.ForeignKey(
        Choice, on_delete=models.SET_NULL, null=True, blank=True, related_name='answers',
    )
    is_flagged_by_student = models.BooleanField(default=False)

    class Meta:
        unique_together = ('submission', 'question')

    def __str__(self):
        return f'{self.submission} - {self.question}'

    @property
    def is_correct(self):
        return self.selected_choice is not None and self.selected_choice.is_correct


class Certificate(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name='certificate')
    pdf_file = models.FileField(upload_to='certificates/')
    issued_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Certificate - {self.submission}'
