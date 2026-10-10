import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_registration_confirmation(registration):
    """Keep a saved registration even if email delivery is temporarily unavailable."""
    body = render_to_string('events/registration_confirmation_email.txt', {'registration': registration, 'event': registration.event})
    subject = f'Registration received: {registration.event.title}'.replace('\r', ' ').replace('\n', ' ')
    try:
        sent = send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [registration.email])
    except (SMTPException, OSError, ValueError):
        logger.exception('Event registration confirmation delivery failed for registration %s', registration.pk)
        return False
    if sent:
        registration.confirmation_email_sent_at = timezone.now()
        registration.save(update_fields=['confirmation_email_sent_at'])
    return bool(sent)
