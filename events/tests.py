import csv
import io
from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Event, EventRegistration


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EventRegistrationTests(TestCase):
    def setUp(self):
        Event.objects.all().delete()
        self.event = Event.objects.create(title='Practical Web Workshop', slug='web-workshop', event_type='Workshop', description='Build useful web apps.', date_display='October 30, 2026', time_display='10:00 AM WAT', location='Lagos', topics='Web, Python', price=0, capacity=2)
        self.details = {'full_name': 'Ada Example', 'email': 'ADA@example.com', 'phone': '+2348000000000'}

    def register(self, event=None, details=None):
        return self.client.post(reverse('event_register', args=[(event or self.event).slug]), details or self.details)

    def test_public_free_registration_saves_and_emails_event_details(self):
        response = self.register()
        self.assertRedirects(response, reverse('event_detail', args=[self.event.slug]))
        registration = self.event.registrations.get()
        self.assertEqual(registration.email, 'ada@example.com')
        self.assertTrue(registration.is_paid)
        self.assertIsNotNone(registration.confirmation_email_sent_at)
        self.assertEqual(mail.outbox[0].to, ['ada@example.com'])
        for detail in [self.event.title, self.event.date_display, self.event.time_display, self.event.location, 'Your registration is confirmed']:
            self.assertIn(detail, mail.outbox[0].body)

    def test_paid_registration_email_does_not_claim_payment_is_confirmed(self):
        paid = Event.objects.create(title='Paid Bootcamp', slug='paid-bootcamp', event_type='Bootcamp', description='Build apps.', date_display='November 1, 2026', time_display='9 AM WAT', location='Online', topics='Web', price=50, capacity=2)
        response = self.register(paid)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('https://wa.me/'))
        registration = paid.registrations.get()
        self.assertFalse(registration.is_paid)
        self.assertIn('awaiting payment confirmation', mail.outbox[0].body)
        self.assertIn('$50.00', mail.outbox[0].body)

    def test_invalid_details_never_register_or_send_email(self):
        response = self.register(details={'full_name': 'Ada', 'email': 'invalid', 'phone': ''})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please check your details')
        self.assertFalse(EventRegistration.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_duplicate_and_full_event_do_not_create_extra_registrations(self):
        self.register()
        self.register(details={**self.details, 'email': 'ada@EXAMPLE.COM'})
        self.assertEqual(self.event.registrations.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.register(details={**self.details, 'email': 'second@example.com'})
        self.register(details={**self.details, 'email': 'third@example.com'})
        self.assertEqual(self.event.registrations.count(), 2)
        self.assertEqual(len(mail.outbox), 2)

    def test_delivery_failure_preserves_registration_and_can_be_retried(self):
        from .emails import send_registration_confirmation
        with patch('events.emails.send_mail', side_effect=SMTPException('delivery unavailable')):
            with self.assertLogs('events.emails', level='ERROR'):
                response = self.register()
        self.assertEqual(response.status_code, 302)
        registration = self.event.registrations.get()
        self.assertIsNone(registration.confirmation_email_sent_at)
        self.assertTrue(send_registration_confirmation(registration))
        registration.refresh_from_db()
        self.assertIsNotNone(registration.confirmation_email_sent_at)

    def test_registration_requires_csrf(self):
        response = Client(enforce_csrf_checks=True).post(reverse('event_register', args=[self.event.slug]), self.details)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(EventRegistration.objects.exists())


class AttendeeExportTests(TestCase):
    def setUp(self):
        Event.objects.all().delete()
        self.event = Event.objects.create(title='Workshop', slug='workshop', event_type='Workshop', description='Learn.', date_display='October 30, 2026', time_display='10 AM WAT', location='Lagos', topics='Web', price=0, capacity=5)
        self.registration = EventRegistration.objects.create(event=self.event, full_name='=HYPERLINK("bad")', email='ada@example.com', phone='+2348000000000')
        other = Event.objects.create(title='Other event', slug='other-event', event_type='Seminar', description='Learn.', date_display='November 1', time_display='10 AM', location='Online', topics='Data', price=0, capacity=5)
        EventRegistration.objects.create(event=other, full_name='Other person', email='other@example.com', phone='123')
        self.url = reverse('admin:events_event_attendees', args=[self.event.pk])

    def test_admin_download_contains_only_selected_event_and_safe_csv_cells(self):
        admin = User.objects.create_superuser('admin', 'admin@example.com', 'Strong-Admin-42!')
        self.client.force_login(admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response['Content-Disposition'])
        rows = list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][1], 'Workshop')
        self.assertTrue(rows[1][2].startswith("'="))
        self.assertEqual(rows[1][3], 'ada@example.com')
        self.assertTrue(rows[1][4].startswith("'+"))

    def test_download_requires_staff_and_registration_permissions(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        staff = User.objects.create_user('limited', password='Strong-Staff-42!', is_staff=True)
        staff.user_permissions.add(Permission.objects.get(codename='view_event'))
        self.client.force_login(staff)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        staff.user_permissions.add(Permission.objects.get(codename='view_eventregistration'))
        self.assertEqual(self.client.get(self.url).status_code, 200)
