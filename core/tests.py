from django.test import TestCase
from django.urls import reverse

from .models import NewsletterSubscriber
from courses.models import Category, Course


class HomepageTests(TestCase):
    def setUp(self):
        # The project's data migration pre-populates the course catalogue.
        Course.objects.all().delete()

    def test_homepage_renders_with_empty_catalogue(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'your chosen field.')
        self.assertContains(response, 'New courses are on the way')
        self.assertContains(response, 'id="newsletter-form"')

    def test_courses_keep_real_prices_and_detail_links(self):
        course = Course.objects.create(
            title='Learn Python', slug='learn-python', category=Category.objects.get_or_create(name='Programming')[0],
            description='Practical Python', syllabus='Functions, Lists',
            duration='4 weeks', level='Beginner', price='49.00',
        )
        response = self.client.get(reverse('home'))
        self.assertContains(response, reverse('course_detail', args=[course.slug]))
        self.assertContains(response, '$49.00')


class NewsletterTests(TestCase):
    def test_subscription_is_saved_and_case_insensitive_duplicates_are_ignored(self):
        for email in ['Student@Example.com', ' student@example.com ']:
            response = self.client.post(reverse('newsletter_subscribe'), {'email': email}, HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)
        self.assertEqual(NewsletterSubscriber.objects.count(), 1)
        self.assertEqual(NewsletterSubscriber.objects.get().email, 'student@example.com')

    def test_invalid_email_is_rejected(self):
        for email in ['', 'not-an-email', 'x' * 250 + '@example.com']:
            response = self.client.post(reverse('newsletter_subscribe'), {'email': email}, HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 400)
        self.assertFalse(NewsletterSubscriber.objects.exists())

    def test_get_cannot_create_subscription(self):
        self.assertEqual(self.client.get(reverse('newsletter_subscribe')).status_code, 405)

    def test_form_works_without_javascript(self):
        response = self.client.post(reverse('newsletter_subscribe'), {'email': 'reader@example.com'})
        self.assertRedirects(response, reverse('home') + '#newsletter-title')
        self.assertTrue(NewsletterSubscriber.objects.filter(email='reader@example.com').exists())

    def test_csrf_is_required(self):
        from django.test import Client
        response = Client(enforce_csrf_checks=True).post(reverse('newsletter_subscribe'), {'email': 'reader@example.com'})
        self.assertEqual(response.status_code, 403)


class WhatsAppContactTests(TestCase):
    def test_shared_contact_uses_configured_number_on_all_public_pages(self):
        from django.test import override_settings
        with override_settings(WHATSAPP_NUMBER='+234 812 441 1984'):
            for name in ['home', 'course_list', 'event_list', 'about', 'contact', 'login', 'register']:
                with self.subTest(page=name):
                    response = self.client.get(reverse(name))
                    self.assertContains(response, 'class="whatsapp-float"', count=1)
                    self.assertContains(response, 'https://wa.me/2348124411984?text=')


class ContactFormTests(TestCase):
    def test_valid_message_opens_whatsapp_with_configured_number(self):
        from django.test import override_settings
        from urllib.parse import parse_qs, urlparse
        with override_settings(WHATSAPP_NUMBER='+234 812 441 1984'):
            response = self.client.post(reverse('contact'), {
                'name': 'Ada Example', 'email': 'ada@example.com', 'phone': '+234 800 000 0000',
                'subject': 'Software project', 'message': 'I would like a web application.',
            })
        self.assertEqual(response.status_code, 302)
        url = urlparse(response.url)
        self.assertEqual(url.netloc, 'wa.me')
        self.assertEqual(url.path, '/2348124411984')
        message = parse_qs(url.query)['text'][0]
        self.assertIn('Ada Example', message)
        self.assertIn('ada@example.com', message)
        self.assertIn('I would like a web application.', message)

    def test_invalid_message_keeps_form_values_and_displays_errors(self):
        response = self.client.post(reverse('contact'), {
            'name': 'Ada Example', 'email': 'invalid', 'subject': 'Unknown', 'message': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please check the highlighted fields')
        self.assertContains(response, 'Ada Example')
        self.assertTrue(response.context['contact_form'].errors)

    def test_contact_post_requires_csrf(self):
        from django.test import Client
        response = Client(enforce_csrf_checks=True).post(reverse('contact'), {})
        self.assertEqual(response.status_code, 403)


class AdminCatalogueAuthoringTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.admin_user = User.objects.create_superuser('author', 'author@example.com', 'Author-Learning-42!')
        self.client.force_login(self.admin_user)
        self.course_data = {'title': 'New Data Course', 'slug': 'new-data-course', 'category': Category.objects.get_or_create(name='Programming')[0].pk, 'description': 'A practical data course.', 'syllabus': 'Analysis, Charts', 'duration': '6 weeks', 'level': 'Beginner', 'price': '75.00', '_save': 'Save'}
        self.course_data.update({'materials-TOTAL_FORMS': '0', 'materials-INITIAL_FORMS': '0', 'materials-MIN_NUM_FORMS': '0', 'materials-MAX_NUM_FORMS': '1000'})
        self.event_data = {'title': 'New Web Workshop', 'slug': 'new-web-workshop', 'event_type': 'Workshop', 'description': 'Learn web applications.', 'date_display': 'November 20, 2026', 'time_display': '10:00 AM WAT', 'location': 'Lagos', 'topics': 'HTML, CSS', 'price': '25.00', 'capacity': '20', '_save': 'Save'}

    def test_admin_creates_course_with_all_details_and_edits_description(self):
        response = self.client.post(reverse('admin:courses_course_add'), self.course_data)
        self.assertEqual(response.status_code, 302)
        course = Course.objects.get(slug='new-data-course')
        self.assertEqual(course.created_by, self.admin_user)
        self.assertEqual(str(course.price), '75.00')
        self.assertEqual(course.syllabus_items, ['Analysis', 'Charts'])
        self.assertContains(self.client.get(course.get_absolute_url()), 'A practical data course.')
        changed = dict(self.course_data, description='Updated course content.')
        response = self.client.post(reverse('admin:courses_course_change', args=[course.pk]), changed)
        self.assertEqual(response.status_code, 302)
        course.refresh_from_db()
        self.assertEqual(course.description, 'Updated course content.')
        self.assertEqual(str(course.price), '75.00')

    def test_admin_creates_event_with_schedule_fee_capacity_and_details(self):
        from events.models import Event
        response = self.client.post(reverse('admin:events_event_add'), self.event_data)
        self.assertEqual(response.status_code, 302)
        event = Event.objects.get(slug='new-web-workshop')
        self.assertEqual(event.created_by, self.admin_user)
        self.assertEqual(event.capacity, 20)
        self.assertEqual(str(event.price), '25.00')
        self.assertEqual(event.topics_items, ['HTML', 'CSS'])
        page = self.client.get(event.get_absolute_url())
        self.assertContains(page, '<li>HTML</li>')
        self.assertContains(page, '<li>CSS</li>')
        for text in ['Learn web applications.', 'November 20, 2026', '10:00 AM WAT', 'Lagos']:
            self.assertContains(page, text)

    def test_admin_price_updates_reach_public_pages_and_preserve_payment(self):
        from courses.models import Enrollment
        Course.objects.all().delete()
        self.client.post(reverse('admin:courses_course_add'), self.course_data)
        course = Course.objects.get(slug='new-data-course')
        enrollment = Enrollment.objects.create(student=self.admin_user, course=course)
        enrollment.is_paid = True
        enrollment.save()
        change_url = reverse('admin:courses_course_change', args=[course.pk])
        response = self.client.post(change_url, dict(self.course_data, price='123.45'))
        self.assertEqual(response.status_code, 302)
        course.refresh_from_db()
        self.assertEqual(str(course.price), '123.45')
        for url in [reverse('home'), reverse('course_list'), course.get_absolute_url(), reverse('enroll', args=[course.slug])]:
            self.assertContains(self.client.get(url), '$123.45')
        enrollment.refresh_from_db()
        self.assertTrue(enrollment.is_paid)
        response = self.client.post(change_url, dict(self.course_data, price='-1.00'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('price', response.context['adminform'].form.errors)
        course.refresh_from_db()
        self.assertEqual(str(course.price), '123.45')
        response = self.client.post(change_url, dict(self.course_data, price='0.00'))
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get(course.get_absolute_url()), 'Free')

    def test_admin_rejects_negative_price_and_zero_event_capacity(self):
        response = self.client.post(reverse('admin:courses_course_add'), dict(self.course_data, price='-1.00'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['adminform'].form.errors)
        self.assertFalse(Course.objects.filter(slug='new-data-course').exists())
        response = self.client.post(reverse('admin:events_event_add'), dict(self.event_data, capacity='0'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('capacity', response.context['adminform'].form.errors)

    def test_content_managers_can_author_but_regular_visitors_cannot(self):
        from django.contrib.auth.models import Group, User
        self.client.logout()
        self.assertEqual(self.client.get(reverse('admin:courses_course_add')).status_code, 302)
        staff = User.objects.create_user('editor', password='Editor-Learning-42!', is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse('admin:courses_course_add')).status_code, 403)
        staff.groups.add(Group.objects.get(name='Content Managers'))
        self.assertEqual(self.client.get(reverse('admin:courses_course_add')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:events_event_add')).status_code, 200)
