from django.contrib import admin

from .models import Answer, Certificate, Choice, Exam, Question, Submission


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'duration_minutes', 'passing_score')
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'exam', 'order')
    list_filter = ('exam',)
    inlines = [ChoiceInline]


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    can_delete = False
    readonly_fields = ('question', 'selected_choice', 'is_flagged_by_student')


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    # Read-only: exams are fully auto-graded, no human review step.
    list_display = ('student', 'exam', 'attempt_number', 'status', 'score', 'submitted_at')
    list_filter = ('status', 'exam')
    search_fields = ('student__username', 'student__email')
    readonly_fields = ('student', 'exam', 'attempt_number', 'status', 'score', 'started_at', 'submitted_at')
    inlines = [AnswerInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('submission', 'pdf_file', 'issued_at')
    readonly_fields = ('submission', 'pdf_file', 'issued_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
