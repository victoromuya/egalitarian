from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from courses.models import Category, Course, Enrollment


class AdminWorkspaceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser('workspace-owner', 'owner@example.com', 'Learning-42!')
        self.manager = User.objects.create_user('workspace-manager', password='Learning-42!', is_staff=True)
        self.manager.groups.add(Group.objects.get(name='Content Managers'))

    def test_new_url_and_branded_login_old_url_is_removed(self):
        self.assertEqual(reverse('admin:index'), '/secret-admin-page/')
        self.assertEqual(self.client.get('/admin/').status_code, 404)
        self.assertRedirects(self.client.get('/secret-admin-page'), '/secret-admin-page/', status_code=301, fetch_redirect_response=False)
        response = self.client.get(reverse('admin:login'))
        self.assertContains(response, 'Your workspace awaits.')
        self.assertContains(response, '/static/images/logo.png')
        self.assertContains(response, 'css/admin-workspace.css')

    def test_dashboard_shows_live_counts_and_actions_for_manager(self):
        course = Course.objects.create(title='Admin Workspace Course', slug='admin-workspace-course', category=Category.objects.get_or_create(name='Programming')[0], price=50)
        Enrollment.objects.create(course=course, student=self.owner)
        self.client.force_login(self.manager)
        response = self.client.get(reverse('admin:index'))
        self.assertContains(response, 'Welcome back, workspace-manager.')
        self.assertContains(response, 'Upload materials')
        self.assertContains(response, 'Upload a certificate')
        self.assertContains(response, '1 pending payment')
        cards = {card['label']: card['count'] for card in response.context['overview_cards']}
        self.assertEqual(cards['Registrations'], 1)
        self.assertContains(response, reverse('admin:courses_coursematerial_add'))
        self.assertContains(response, 'aria-label="Admin navigation"')
        self.assertContains(response, 'Course Registrations')
        self.assertEqual(response.context['registration_summary']['pending'], 1)
        self.assertEqual(response.context['enrollment_chart']['total'], 1)
        self.assertEqual(len(response.context['enrollment_chart']['days']), 7)
        self.assertContains(response, 'workspace-owner')
        self.assertNotContains(response, 'href="/admin/')
        self.assertNotContains(response, 'action="/admin/')

    def test_staff_without_permissions_gets_no_metrics_or_shortcuts(self):
        staff = User.objects.create_user('limited-staff', is_staff=True)
        self.client.force_login(staff)
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.context['overview_cards'], [])
        self.assertEqual(response.context['workspace_actions'], [])
        self.assertNotContains(response, 'Review registrations')
        self.assertNotContains(response, 'Course Registrations')
        self.assertNotContains(response, 'Recent Registrations')

    def test_students_cannot_access_workspace(self):
        student = User.objects.create_user('workspace-student')
        self.client.force_login(student)
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/secret-admin-page/login/'))

    def test_admin_forms_lists_and_logout_use_new_url(self):
        self.client.force_login(self.owner)
        for name in ('admin:courses_course_changelist', 'admin:courses_course_add', 'admin:courses_coursematerial_add', 'admin:courses_coursecertificate_add', 'admin:password_change'):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'css/admin-workspace.css')
                self.assertContains(response, reverse('admin:logout'))
        app_response = self.client.get(reverse('admin:app_list', args=['courses']))
        self.assertContains(app_response, reverse('admin:courses_course_changelist'))
        self.assertNotContains(app_response, 'Admin Dashboard')
        self.client.post(reverse('admin:logout'))
        self.assertNotIn('_auth_user_id', self.client.session)
