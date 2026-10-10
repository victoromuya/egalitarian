from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.db import transaction, connection
from django.db.models import F
from .forms import EventRegistrationForm
from .emails import send_registration_confirmation
from django.shortcuts import get_object_or_404, redirect, render

from .models import Event, EventRegistration

TYPES = ['All'] + [choice[0] for choice in Event.TYPE_CHOICES]


def event_list(request):
    event_type = request.GET.get('type', 'All')
    events = Event.objects.all()
    if event_type and event_type != 'All':
        events = events.filter(event_type=event_type)
    return render(request, 'events/event_list.html', {
        'events': events,
        'types': TYPES,
        'active_type': event_type,
    })


def event_detail(request, slug):
    event = get_object_or_404(Event, slug=slug)
    return render(request, 'events/event_detail.html', {'event': event})


def event_register(request, slug):
    event = get_object_or_404(Event, slug=slug)
    form = EventRegistrationForm(request.POST if request.method == 'POST' else None)

    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            if connection.vendor == 'sqlite':
                # SQLite has no row locks: obtain its write lock before counting seats.
                Event.objects.filter(pk=event.pk).update(title=F('title'))
            event = Event.objects.select_for_update().get(pk=event.pk)
            if EventRegistration.objects.filter(event=event, email__iexact=form.cleaned_data['email']).exists():
                messages.info(request, 'A registration with this email already exists for this event. Contact us if you need help.')
                return redirect('event_detail', slug=event.slug)
            if event.is_full:
                messages.error(request, 'Sorry, this event is at full capacity.')
                return redirect('event_detail', slug=event.slug)
            registration = EventRegistration.objects.create(event=event, **form.cleaned_data)

        sent = send_registration_confirmation(registration)
        if sent:
            messages.success(request, 'Your registration is saved. A confirmation email has been sent to you.')
        else:
            messages.warning(request, 'Your registration is saved, but we could not send your confirmation email. Please contact us for assistance.')
        if event.is_free:
            return redirect('event_detail', slug=event.slug)
        whatsapp_message = quote(
            f'Hi, I would like to pay for the event "{event.title}" '
            f'(${event.price}). My name is {registration.full_name}. '
            f'My registration reference is {registration.pk}.'
        )
        return redirect(f'https://wa.me/{settings.WHATSAPP_NUMBER}?text={whatsapp_message}')

    if event.is_full:
        messages.error(request, 'Sorry, this event is at full capacity.')
        return redirect('event_detail', slug=event.slug)
    return render(request, 'events/event_register.html', {'event': event, 'form': form})
