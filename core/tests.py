from django.test import TestCase
from django.urls import reverse

from .models import NewsletterSubscriber
from courses.models import Course


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
            title='Learn Python', slug='learn-python', category='Programming',
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
