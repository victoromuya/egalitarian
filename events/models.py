from django.conf import settings
from django.db import models


class Event(models.Model):
    TYPE_CHOICES = [
        ('Bootcamp', 'Bootcamp'),
        ('Seminar', 'Seminar'),
        ('Workshop', 'Workshop'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    event_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    description = models.TextField()
    date_display = models.CharField(max_length=100, help_text='e.g. "July 15-19, 2026"')
    time_display = models.CharField(max_length=100, help_text='e.g. "9:00 AM - 5:00 PM WAT"')
    location = models.CharField(max_length=255)
    topics = models.TextField(help_text='Comma-separated topics')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    capacity = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='events_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date_display']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self._state.adding:
            original = (
                type(self).objects.filter(pk=self.pk)
                .values('price', 'capacity').first()
            )
            if original is not None:
                if original['price'] != self.price:
                    raise ValueError('Event price is immutable after creation.')
                if original['capacity'] != self.capacity:
                    raise ValueError('Event capacity is immutable after creation.')
        super().save(*args, **kwargs)

    @property
    def is_free(self):
        return self.price == 0

    @property
    def type(self):
        """Template-facing alias for event_type (templates use event.type)."""
        return self.event_type

    @property
    def date(self):
        """Template-facing alias for date_display (templates use event.date)."""
        return self.date_display

    @property
    def time(self):
        """Template-facing alias for time_display (templates use event.time)."""
        return self.time_display

    @property
    def topics_items(self):
        return [item.strip() for item in self.topics.split(',') if item.strip()]

    @property
    def seats_left(self):
        return max(self.capacity - self.registrations.count(), 0)

    @property
    def is_full(self):
        return self.seats_left <= 0


class EventRegistration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    is_paid = models.BooleanField(default=False)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-registered_at']

    def __str__(self):
        return f'{self.full_name} -> {self.event}'

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.is_paid = self.event.is_free
        super().save(*args, **kwargs)
