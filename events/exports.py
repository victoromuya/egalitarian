import csv

from django.http import HttpResponse


def export_registrations(registrations, filename='event-registrations.csv'):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Cache-Control'] = 'no-store'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['Registration ID', 'Event', 'Full name', 'Email', 'Phone', 'Payment status', 'Registered at (UTC)', 'Confirmation email sent at (UTC)'])
    def safe(value):
        text = str(value)
        return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')) else text
    def timestamp(value):
        if not value:
            return ''
        from datetime import timezone as utc_timezone
        return value.astimezone(utc_timezone.utc).isoformat()
    for registration in registrations.select_related('event').order_by('event__title', 'registered_at').iterator():
        writer.writerow([
            registration.pk, safe(registration.event.title), safe(registration.full_name),
            safe(registration.email), safe(registration.phone),
            'Confirmed / paid' if registration.is_paid else 'Pending payment',
            timestamp(registration.registered_at), timestamp(registration.confirmation_email_sent_at),
        ])
    return response
