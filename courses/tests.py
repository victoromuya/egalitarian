from django.test import TestCase
from django.urls import reverse

from .models import Category, Course


class PortalTests(TestCase):
    def setUp(self):
        import tempfile
        from django.test import override_settings
        from django.contrib.auth.models import User
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import Enrollment, CourseMaterial, CourseCertificate
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        settings = override_settings(MEDIA_ROOT=self.media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.student = User.objects.create_user('portal-student', password='password')
        self.other = User.objects.create_user('portal-other', password='password')
        self.course = Course.objects.create(title='Portal Course', slug='portal-course', category=Category.objects.get_or_create(name='Programming')[0], price=50)
        self.enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        self.material = CourseMaterial.objects.create(course=self.course, title='Workbook', file=SimpleUploadedFile('workbook.pdf', b'workbook-content'))
        self.certificate = CourseCertificate.objects.create(enrollment=self.enrollment, file=SimpleUploadedFile('certificate.pdf', b'certificate-content'))

    def test_downloads_require_login_enrollment_and_certificate_ownership(self):
        urls = [reverse('material_download', args=[self.material.pk]), reverse('uploaded_certificate_download', args=[self.certificate.pk])]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.other)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 404)
        from .models import Enrollment
        Enrollment.objects.create(student=self.other, course=self.course)
        response = self.client.get(urls[0])
        self.assertEqual(b''.join(response.streaming_content), b'workbook-content')
        response.close()
        self.assertEqual(self.client.get(urls[1]).status_code, 404)
        self.client.force_login(self.student)
        response = self.client.get(urls[1])
        self.assertEqual(b''.join(response.streaming_content), b'certificate-content')
        self.assertIn('attachment', response['Content-Disposition'])
        response.close()

    def test_profile_shows_only_own_courses_and_downloads(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('profile'))
        self.assertContains(response, 'Workbook')
        self.assertContains(response, reverse('uploaded_certificate_download', args=[self.certificate.pk]))
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse('profile')), 'Workbook')

    def test_enrollment_is_authenticated_explicit_and_idempotent(self):
        from .models import Enrollment
        url = reverse('enroll', args=[self.course.slug])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertFalse(Enrollment.objects.filter(student=self.other).exists())
        for _ in range(2):
            self.assertRedirects(self.client.post(url), reverse('profile'))
        self.assertEqual(Enrollment.objects.filter(student=self.other, course=self.course).count(), 1)

    def test_content_managers_can_upload_and_students_cannot(self):
        from django.contrib.auth.models import Group
        self.other.is_staff = True
        self.other.save()
        self.other.groups.add(Group.objects.get(name='Content Managers'))
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('admin:courses_coursematerial_add')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:courses_coursecertificate_add')).status_code, 200)
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse('admin:courses_coursematerial_add')).status_code, 302)


    def test_admin_upload_assigns_certificate_to_selected_student_portal(self):
        from django.contrib.auth.models import Group, User
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import Enrollment, CourseCertificate
        manager = User.objects.create_user('certificate-manager', is_staff=True)
        manager.groups.add(Group.objects.get(name='Content Managers'))
        enrollment = Enrollment.objects.create(student=self.other, course=self.course)
        self.client.force_login(manager)
        response = self.client.post(reverse('admin:courses_coursecertificate_add'), {
            'enrollment': enrollment.pk,
            'file': SimpleUploadedFile('student-certificate.pdf', b'certificate-for-other-student'),
            '_save': 'Save',
        })
        self.assertEqual(response.status_code, 302)
        certificate = CourseCertificate.objects.get(enrollment=enrollment)
        url = reverse('uploaded_certificate_download', args=[certificate.pk])
        self.client.force_login(self.other)
        self.assertContains(self.client.get(reverse('profile')), url)
        response = self.client.get(url)
        self.assertEqual(b''.join(response.streaming_content), b'certificate-for-other-student')
        response.close()
        self.client.force_login(self.student)
        self.assertNotContains(self.client.get(reverse('profile')), url)
        self.assertEqual(self.client.get(url).status_code, 404)


class CategoryManagementTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Group, User
        self.manager = User.objects.create_user('category-manager', is_staff=True)
        self.manager.groups.add(Group.objects.get(name='Content Managers'))
        self.client.force_login(self.manager)

    def test_admin_creates_and_renames_category_on_both_pages(self):
        response = self.client.post(reverse('admin:courses_category_add'), {'name': 'Cybersecurity', 'display_order': 0, '_save': 'Save'})
        self.assertEqual(response.status_code, 302)
        category = Category.objects.get(name='Cybersecurity')
        course = Course.objects.create(title='Network Protection', slug='network-protection', category=category, price=0)
        for name in ('home', 'course_list'):
            self.assertContains(self.client.get(reverse(name)), 'Cybersecurity')
        response = self.client.post(reverse('admin:courses_category_change', args=[category.pk]), {'name': 'Security & Privacy', 'display_order': 0, '_save': 'Save'})
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('course_list'), {'category': 'Security & Privacy'})
        self.assertEqual([c.pk for c in response.context['courses']], [course.pk])
        self.assertContains(self.client.get(reverse('home')), 'data-course-filter="Security &amp; Privacy"')

    def test_homepage_limits_each_category_to_four_and_catalogue_keeps_all(self):
        category = Category.objects.create(name='New Learning Path', display_order=0)
        for i in range(5):
            Course.objects.create(title=f'New Course {i}', slug=f'new-course-{i}', category=category, price=0)
        response = self.client.get(reverse('home'))
        courses = [c for c in response.context['featured_courses'] if c.category_id == category.pk]
        self.assertEqual(len(courses), 4)
        initial = response.context['course_categories'][0]
        self.assertTrue(all(c.home_visible == (c.category.name == initial) for c in response.context['featured_courses']))
        self.assertNotContains(response, 'data-course-filter="All"')
        catalogue = self.client.get(reverse('course_list'), {'category': category.name})
        self.assertEqual(len(catalogue.context['courses']), 5)

    def test_categories_in_use_are_protected_and_reserved_name_is_rejected(self):
        from django.db.models.deletion import ProtectedError
        category = Category.objects.create(name='Protected Category')
        Course.objects.create(title='Protected Course', slug='protected-course', category=category, price=0)
        with self.assertRaises(ProtectedError):
            category.delete()
        response = self.client.post(reverse('admin:courses_category_add'), {'name': 'All', 'display_order': 0, '_save': 'Save'})
        self.assertContains(response, 'Enter a category name other than All.')


class CatalogueTests(TestCase):
    def setUp(self):
        Course.objects.all().delete()
        self.courses = []
        for title, slug, category, price in [
            ('Data Analysis', 'data-analysis', 'Programming', '49.00'),
            ('Web Applications', 'web-applications', 'Web Design', '75.00'),
            ('Blockchain Development', 'blockchain-development', 'Programming', '99.00'),
            ('Desktop Publishing', 'desktop-publishing', 'Business', '0.00'),
            ('Photography Basics', 'photography-basics', 'Photography', '25.00'),
        ]:
            self.courses.append(Course.objects.create(
                title=title, slug=slug, category=Category.objects.get_or_create(name=category)[0], price=price,
                description='A complete practical course description.',
                syllabus='First topic, Second topic', duration='4 weeks', level='Beginner',
            ))

    def test_all_courses_remain_visible_with_real_prices_and_detail_links(self):
        response = self.client.get(reverse('course_list'))
        self.assertEqual(len(response.context['courses']), 5)
        for course in self.courses:
            self.assertContains(response, reverse('course_detail', args=[course.slug]))
        self.assertContains(response, '$49.00')
        self.assertContains(response, 'Free')
        self.assertNotContains(response, 'class="popular-card" data-course-category="Data" hidden')

    def test_learning_paths_legacy_categories_and_empty_filters(self):
        for category, expected in [
            ('Web Design', ['Web Applications']),
            ('Business', ['Desktop Publishing']),
            ('Photography', ['Photography Basics']),
            ('Programming', ['Blockchain Development', 'Data Analysis']),
            ('Language', []), ('Unknown', []),
        ]:
            with self.subTest(category=category):
                response = self.client.get(reverse('course_list'), {'category': category})
                self.assertEqual([course.title for course in response.context['courses']], expected)
                if not expected:
                    self.assertContains(response, 'There are no courses in this category yet.')
