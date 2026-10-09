from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
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

    if event.is_full:
        messages.error(request, 'Sorry, this event is at full capacity.')
        return redirect('event_detail', slug=event.slug)

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()

        registration = EventRegistration.objects.create(
            event=event, full_name=full_name, email=email, phone=phone,
        )

        if event.is_free:
            messages.success(request, f'You are registered for {event.title}.')
            return redirect('event_detail', slug=event.slug)

        whatsapp_message = quote(
            f'Hi, I would like to pay for the event "{event.title}" '
            f'(${event.price}). My name is {full_name}.'
        )
        whatsapp_url = f'https://wa.me/{settings.WHATSAPP_NUMBER}?text={whatsapp_message}'
        return redirect(whatsapp_url)

    return render(request, 'events/event_register.html', {'event': event})
