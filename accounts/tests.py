from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AuthenticationPageTests(TestCase):
    def test_login_keeps_existing_authentication_and_failure_feedback(self):
        user = User.objects.create_user(username='ada', password='Strong-Learning-42!')
        failed = self.client.post(reverse('login'), {'username': 'ada', 'password': 'wrong'})
        self.assertEqual(failed.status_code, 200)
        self.assertContains(failed, 'Invalid username or password.')
        self.assertContains(failed, 'value="ada"')
        response = self.client.post(reverse('login'), {'username': 'ada', 'password': 'Strong-Learning-42!'})
        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_registration_errors_preserve_details_without_passwords(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'Ada', 'last_name': 'Example', 'username': 'ada',
            'email': 'ada@example.com', 'password1': 'Strong-Learning-42!', 'password2': 'different',
        })
        self.assertContains(response, 'Passwords do not match.')
        self.assertContains(response, 'value="Ada"')
        self.assertContains(response, 'value="ada@example.com"')
        self.assertNotContains(response, 'Strong-Learning-42!')
        self.assertFalse(User.objects.filter(username='ada').exists())

    def test_registration_still_creates_account_and_profile(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'Ada', 'last_name': 'Example', 'username': 'ada',
            'email': 'ada@example.com', 'phone': '+2348000000000',
            'password1': 'Strong-Learning-42!', 'password2': 'Strong-Learning-42!',
        })
        self.assertRedirects(response, reverse('dashboard'))
        user = User.objects.get(username='ada')
        self.assertEqual(user.first_name, 'Ada')
        self.assertEqual(user.profile.phone, '+2348000000000')
        self.assertTrue(user.check_password('Strong-Learning-42!'))


from django.test import override_settings


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='recovery', email='recovery@example.com', password='Original-Learning-42!')

    def request_link(self):
        import re
        from django.core import mail
        from urllib.parse import urlparse
        response = self.client.post(reverse('password_reset'), {'email': self.user.email})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        return urlparse(re.search(r'https?://[^\s]+', mail.outbox[0].body).group()).path

    def test_email_link_changes_password_and_cannot_be_reused(self):
        link = self.request_link()
        response = self.client.get(link)
        self.assertEqual(response.status_code, 302)
        confirm_url = response.url
        self.assertContains(self.client.get(confirm_url), 'Save new password')
        response = self.client.post(confirm_url, {'new_password1': 'Renewed-Learning-92!', 'new_password2': 'Renewed-Learning-92!'})
        self.assertRedirects(response, reverse('password_reset_complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Renewed-Learning-92!'))
        self.assertFalse(self.user.check_password('Original-Learning-42!'))
        self.assertContains(self.client.get(link, follow=True), 'This reset link is invalid')
        self.assertIsNone(self.client.session.get('_auth_user_id'))
        self.assertRedirects(self.client.post(reverse('login'), {'username': self.user.username, 'password': 'Renewed-Learning-92!'}), reverse('dashboard'))

    def test_unknown_email_does_not_reveal_account_existence(self):
        from django.core import mail
        response = self.client.post(reverse('password_reset'), {'email': 'unknown@example.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(self.client.get(reverse('password_reset_done')), 'If an active account uses that email')

    def test_mismatched_and_weak_passwords_are_rejected(self):
        confirm_url = self.client.get(self.request_link()).url
        for first, second in [('New-Learning-94!', 'Different-Learning-94!'), ('123', '123')]:
            response = self.client.post(confirm_url, {'new_password1': first, 'new_password2': second})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Original-Learning-42!'))

    def test_invalid_and_expired_links_offer_recovery(self):
        from datetime import datetime, timedelta
        from unittest.mock import patch
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        invalid = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': 'invalid'})
        self.assertContains(self.client.get(invalid), 'Request a new link')
        with patch.object(default_token_generator, '_now', return_value=datetime.now() - timedelta(hours=2)):
            token = default_token_generator.make_token(self.user)
        expired = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        self.assertContains(self.client.get(expired), 'This reset link is invalid')

    def test_csrf_is_required_and_invalid_email_is_not_sent(self):
        from django.core import mail
        from django.test import Client
        self.assertEqual(Client(enforce_csrf_checks=True).post(reverse('password_reset'), {'email': self.user.email}).status_code, 403)
        response = self.client.post(reverse('password_reset'), {'email': 'invalid'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(len(mail.outbox), 0)


    def test_ineligible_email_never_attempts_to_send_reset_mail(self):
        from unittest.mock import patch
        from django.contrib.auth.forms import PasswordResetForm
        for state in ['unknown', 'inactive', 'unusable_password']:
            with self.subTest(state=state):
                self.user.is_active = state != 'inactive'
                if state == 'unusable_password':
                    self.user.set_unusable_password()
                else:
                    self.user.set_password('Original-Learning-42!')
                self.user.save()
                email = 'not-registered@example.com' if state == 'unknown' else self.user.email
                with patch.object(PasswordResetForm, 'send_mail') as send_mail:
                    response = self.client.post(reverse('password_reset'), {'email': email})
                    self.assertRedirects(response, reverse('password_reset_done'))
                    send_mail.assert_not_called()

    def test_registered_email_matches_case_insensitively(self):
        from django.core import mail
        response = self.client.post(reverse('password_reset'), {'email': '  RECOVERY@EXAMPLE.COM  '})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
