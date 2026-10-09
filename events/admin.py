from django.contrib import admin

from .models import Event, EventRegistration


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'date_display', 'price', 'capacity', 'seats_left', 'created_by')
    list_filter = ('event_type',)
    search_fields = ('title', 'description', 'location')
    prepopulated_fields = {'slug': ('title',)}

    def get_readonly_fields(self, request, obj=None):
        # Price and capacity are immutable after creation (see CLAUDE.md).
        if obj:
            return ('price', 'capacity')
        return ()

    def save_model(self, request, obj, form, change):
        if not change and obj.created_by is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'event', 'is_paid', 'registered_at')
    list_filter = ('is_paid', 'event')
    list_editable = ('is_paid',)
    search_fields = ('full_name', 'email', 'phone')
    readonly_fields = ('event', 'full_name', 'email', 'phone', 'registered_at')

    def has_add_permission(self, request):
        # Registrations come from the public event form; admins only
        # confirm payment (matched by name/email/phone from WhatsApp).
        return False
