from django.contrib import admin

from .models import Course, Enrollment


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price', 'level', 'created_by', 'created_at')
    list_filter = ('category',)
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}

    def get_readonly_fields(self, request, obj=None):
        # Price is immutable after creation (see CLAUDE.md) — enrollments
        # were created against it.
        if obj:
            return ('price',)
        return ()

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
