from django.test import TestCase
from django.urls import reverse

from .models import Course


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
                title=title, slug=slug, category=category, price=price,
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
            ('Data', ['Data Analysis']), ('Web', ['Web Applications']),
            ('Blockchain', ['Blockchain Development']),
            ('Desktop Publishing', ['Desktop Publishing']),
            ('Programming', ['Blockchain Development', 'Data Analysis']),
            ('Language', []), ('Unknown', []),
        ]:
            with self.subTest(category=category):
                response = self.client.get(reverse('course_list'), {'category': category})
                self.assertEqual([course.title for course in response.context['courses']], expected)
                if not expected:
                    self.assertContains(response, 'There are no courses in this category yet.')
