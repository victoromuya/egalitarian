from django.core.validators import MinValueValidator
from django.contrib import admin

from .models import Course, Enrollment


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price', 'level', 'duration', 'created_by', 'created_at')
    list_filter = ('category', 'level')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        ('Course information', {'fields': ('title', 'slug', 'category', 'description')}),
        ('Learning details', {'fields': ('syllabus', 'duration', 'level'), 'description': 'Enter syllabus topics separated by commas. Duration and level appear on course cards.'}),
        ('Pricing', {'fields': ('price',), 'description': 'Enter the course fee in USD. Use 0 for a free course. Set the price when creating the course.'}),
        ('Publication details', {'fields': ('created_by', 'created_at')}),
    )
    view_on_site = True

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'price' in form.base_fields:
            form.base_fields['price'].min_value = 0
            form.base_fields['price'].validators.append(MinValueValidator(0))
            form.base_fields['price'].widget.attrs['min'] = '0'
        return form

    def get_readonly_fields(self, request, obj=None):
        # Price is immutable after creation (see CLAUDE.md) — enrollments
        # were created against it.
        if obj:
            return ('created_by', 'created_at', 'price')
        return ('created_by', 'created_at')

    def save_model(self, request, obj, form, change):
        if not change and obj.created_by is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'is_paid', 'enrolled_at')
    list_filter = ('is_paid', 'course')
    list_editable = ('is_paid',)
    search_fields = ('student__username', 'student__email', 'course__title')
    readonly_fields = ('student', 'course', 'enrolled_at')

    def has_add_permission(self, request):
        # Enrollments are created by students enrolling on the site;
        # admins only confirm payment.
        return False
