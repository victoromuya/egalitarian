from django.core.validators import MinValueValidator
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html

from .exports import export_registrations
from .emails import send_registration_confirmation

from .models import Event, EventRegistration


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'date_display', 'price', 'capacity', 'seats_left', 'created_by', 'download_attendees')
    list_filter = ('event_type',)
    search_fields = ('title', 'description', 'location')
    prepopulated_fields = {'slug': ('title',)}
    actions = ['download_selected_attendees']
    fieldsets = (
        ('Event information', {'fields': ('title', 'slug', 'event_type', 'description')}),
        ('Schedule & location', {'fields': ('date_display', 'time_display', 'location'), 'description': 'Enter the event dates, time (including timezone), and physical venue or online location.'}),
        ('Topics', {'fields': ('topics',), 'description': 'Separate topics with commas. These appear in the event catalogue.'}),
        ('Pricing & registration', {'fields': ('price', 'capacity'), 'description': 'Enter the fee in USD (0 for free) and the maximum number of attendees. Set both when creating the event.'}),
        ('Publication details', {'fields': ('created_by', 'created_at')}),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field in ('price', 'capacity'):
            if field in form.base_fields:
                form.base_fields[field].min_value = 0 if field == 'price' else 1
                form.base_fields[field].validators.append(MinValueValidator(form.base_fields[field].min_value))
                form.base_fields[field].widget.attrs['min'] = str(form.base_fields[field].min_value)
        return form

    @admin.display(description='Attendees')
    def download_attendees(self, obj):
        return format_html('<a href="{}">Download CSV</a>', reverse('admin:events_event_attendees', args=[obj.pk]))

    def get_urls(self):
        return [path('<int:object_id>/attendees.csv', self.admin_site.admin_view(self.attendees_csv), name='events_event_attendees')] + super().get_urls()

    def check_registration_permission(self, request):
        if not (request.user.has_perm('events.view_eventregistration') or request.user.has_perm('events.change_eventregistration')):
            raise PermissionDenied

    def attendees_csv(self, request, object_id):
        event = get_object_or_404(Event, pk=object_id)
        if not self.has_view_permission(request, event):
            raise PermissionDenied
        self.check_registration_permission(request)
        return export_registrations(EventRegistration.objects.filter(event=event), f'{event.slug}-attendees.csv')

    @admin.action(description='Download attendees for selected events (CSV)', permissions=['view'])
    def download_selected_attendees(self, request, queryset):
        self.check_registration_permission(request)
        return export_registrations(EventRegistration.objects.filter(event__in=queryset))

    def get_readonly_fields(self, request, obj=None):
        # Price and capacity are immutable after creation (see CLAUDE.md).
        if obj:
            return ('created_by', 'created_at', 'price', 'capacity')
        return ('created_by', 'created_at')

    def save_model(self, request, obj, form, change):
        if not change and obj.created_by is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'event', 'is_paid', 'registered_at', 'confirmation_email_sent_at')
    list_filter = ('is_paid', 'event')
    list_editable = ('is_paid',)
    search_fields = ('full_name', 'email', 'phone')
    readonly_fields = ('event', 'full_name', 'email', 'phone', 'registered_at', 'confirmation_email_sent_at')

    actions = ['download_selected_registrations', 'retry_confirmation_emails']

    @admin.action(description='Download selected registrations (CSV)', permissions=['view'])
    def download_selected_registrations(self, request, queryset):
        return export_registrations(queryset)

    @admin.action(description='Retry unsent registration confirmation emails', permissions=['change'])
    def retry_confirmation_emails(self, request, queryset):
        sent = failed = 0
        for registration in queryset.filter(confirmation_email_sent_at__isnull=True).select_related('event'):
            if send_registration_confirmation(registration):
                sent += 1
            else:
                failed += 1
        self.message_user(request, f'{sent} confirmation emails sent; {failed} failed.', messages.WARNING if failed else messages.SUCCESS)

    def has_add_permission(self, request):
        # Registrations come from the public event form; admins only
        # confirm payment (matched by name/email/phone from WhatsApp).
        return False
