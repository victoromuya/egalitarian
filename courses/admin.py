from django.core.validators import MinValueValidator
from django.contrib import admin
from django import forms

from .models import Category, Course, Enrollment, CourseMaterial, CourseCertificate


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order')
    list_editable = ('display_order',)
    search_fields = ('name',)


class CourseMaterialInline(admin.TabularInline):
    model = CourseMaterial
    extra = 0


class CourseCertificateInline(admin.StackedInline):
    model = CourseCertificate
    extra = 1
    max_num = 1
    verbose_name = 'student certificate'
    verbose_name_plural = 'Certificate for this student and course'


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    inlines = [CourseMaterialInline]
    list_display = ('title', 'category', 'price', 'level', 'duration', 'created_by', 'created_at')
    list_filter = ('category', 'level')
    search_fields = ('title', 'description', 'category__name')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        ('Course information', {'fields': ('title', 'slug', 'category', 'description')}),
        ('Learning details', {'fields': ('syllabus', 'duration', 'level'), 'description': 'Enter syllabus topics separated by commas. Duration and level appear on course cards.'}),
        ('Pricing', {'fields': ('price',), 'description': 'Update the course fee in USD at any time. Use 0 for a free course. Changes appear on the website immediately and preserve existing payment confirmations.'}),
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
        return ('created_by', 'created_at')

    def save_model(self, request, obj, form, change):
        if not change and obj.created_by is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    inlines = [CourseCertificateInline]
    list_display = ('student', 'course', 'is_paid', 'enrolled_at')
    list_filter = ('is_paid', 'course')
    list_editable = ('is_paid',)
    search_fields = ('student__username', 'student__email', 'student__first_name', 'student__last_name', 'course__title')
    readonly_fields = ('student', 'course', 'enrolled_at')

    def has_add_permission(self, request):
        return False


@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'uploaded_at')
    list_filter = ('course',)
    search_fields = ('title', 'course__title')


class CourseCertificateForm(forms.ModelForm):
    class Meta:
        model = CourseCertificate
        fields = '__all__'
        labels = {'enrollment': 'Student and course', 'file': 'Certificate file'}
        help_texts = {
            'enrollment': 'Search by student name, username, email, or course. This certificate will appear only in the selected student’s portal for this course.',
            'file': 'Upload the certificate issued to this student. Save to make it available for download in their profile.',
        }


@admin.register(CourseCertificate)
class CourseCertificateAdmin(admin.ModelAdmin):
    form = CourseCertificateForm
    autocomplete_fields = ('enrollment',)
    list_display = ('student', 'course', 'uploaded_at')
    list_select_related = ('enrollment__student', 'enrollment__course')
    list_filter = ('enrollment__course',)
    search_fields = ('enrollment__student__username', 'enrollment__student__email', 'enrollment__student__first_name', 'enrollment__student__last_name', 'enrollment__course__title')
    readonly_fields = ('uploaded_at',)

    @admin.display(ordering='enrollment__student__username')
    def student(self, obj):
        user = obj.enrollment.student
        return f'{user.get_full_name() or user.username} ({user.username})'

    @admin.display(ordering='enrollment__course__title')
    def course(self, obj):
        return obj.enrollment.course
