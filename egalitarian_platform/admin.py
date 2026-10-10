from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig
from django.urls import reverse


class EgalitarianAdminConfig(AdminConfig):
    default_site = 'egalitarian_platform.admin.EgalitarianAdminSite'


class EgalitarianAdminSite(AdminSite):
    site_header = 'Egalitarian Computers'
    site_title = 'Egalitarian Admin'
    index_title = 'Workspace overview'

    def each_context(self, request):
        context = super().each_context(request)
        context['workspace_navigation'] = self.get_app_list(request) if self.has_permission(request) else []
        return context

    def index(self, request, extra_context=None):
        from courses.models import Course, Enrollment, CourseMaterial, CourseCertificate
        from events.models import Event

        cards = []
        for model, label, caption in (
            (Course, 'Courses', 'Your learning catalogue'),
            (Enrollment, 'Registrations', 'Students enrolled in courses'),
            (CourseMaterial, 'Materials', 'Files available to learners'),
            (CourseCertificate, 'Certificates', 'Uploaded student certificates'),
        ):
            opts = model._meta
            if request.user.has_perm(f'{opts.app_label}.view_{opts.model_name}') or request.user.has_perm(f'{opts.app_label}.change_{opts.model_name}'):
                cards.append({'label': label, 'caption': caption, 'count': model.objects.count(), 'url': reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist')})
        actions = []
        for model, label, caption in (
            (Course, 'Create a course', 'Build your learning catalogue'),
            (CourseMaterial, 'Upload materials', 'Share resources with enrolled students'),
            (CourseCertificate, 'Upload a certificate', 'Deliver a certificate to a student'),
            (Event, 'Create an event', 'Plan a workshop or bootcamp'),
        ):
            opts = model._meta
            if request.user.has_perm(f'{opts.app_label}.add_{opts.model_name}'):
                actions.append({'label': label, 'caption': caption, 'url': reverse(f'admin:{opts.app_label}_{opts.model_name}_add')})
        context = {'overview_cards': cards, 'workspace_actions': actions}
        if request.user.has_perm('courses.view_enrollment') or request.user.has_perm('courses.change_enrollment'):
            context['pending_payments'] = Enrollment.objects.filter(is_paid=False).count()
            context['pending_payments_url'] = reverse('admin:courses_enrollment_changelist') + '?is_paid__exact=0'
        if 'pending_payments' in context:
            from datetime import timedelta
            from django.utils import timezone
            from django.db.models import Count
            from django.db.models.functions import TruncDate
            from zoneinfo import ZoneInfo
            total = Enrollment.objects.count()
            paid = Enrollment.objects.filter(is_paid=True).count()
            context['registration_summary'] = {'total': total, 'paid': paid, 'pending': total - paid, 'percentage': round(paid / total * 100) if total else 0}
            context['recent_enrollments'] = Enrollment.objects.select_related('student', 'course').order_by('-enrolled_at')[:5]
            local_zone = ZoneInfo('Africa/Lagos')
            today = timezone.localdate(timezone=local_zone)
            start = today - timedelta(days=6)
            daily = dict(Enrollment.objects.annotate(day=TruncDate('enrolled_at', tzinfo=local_zone)).filter(day__gte=start, day__lte=today).values('day').annotate(total=Count('id')).values_list('day', 'total'))
            values = [daily.get(start + timedelta(days=i), 0) for i in range(7)]
            maximum = max(max(values), 1)
            context['enrollment_chart'] = {'points': ' '.join(f'{40 + i * 80},{180 - value / maximum * 140:.1f}' for i, value in enumerate(values)), 'days': [{'label': (start + timedelta(days=i)).strftime('%a'), 'count': value, 'x': 40 + i * 80} for i, value in enumerate(values)], 'maximum': maximum, 'total': sum(values)}
        from exams.models import Submission
        if request.user.has_perm('exams.view_submission'):
            context['recent_results'] = Submission.objects.filter(status='submitted').select_related('student', 'exam')[:5]
        context.update(extra_context or {})
        return super().index(request, context)
