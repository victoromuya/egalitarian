from django.conf import settings
from django.db import models
import uuid
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db.models.functions import Lower


def portal_upload_path(instance, filename):
    from pathlib import Path
    return f'course_uploads/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name_plural = 'course categories'
        constraints = [models.UniqueConstraint(Lower('name'), name='courses_unique_category_name')]

    def clean(self):
        self.name = self.name.strip()
        if not self.name or self.name.lower() == 'all':
            raise ValidationError({'name': 'Enter a category name other than All.'})

    def __str__(self):
        return self.name


class Course(models.Model):

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='courses')
    description = models.TextField()
    syllabus = models.TextField(help_text='Comma-separated syllabus topics')
    duration = models.CharField(max_length=50)
    level = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='courses_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('course_detail', args=[self.slug])

    @property
    def is_free(self):
        return self.price == 0

    @property
    def syllabus_items(self):
        return [item.strip() for item in self.syllabus.split(',') if item.strip()]


class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments',
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    is_paid = models.BooleanField(default=False)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course')
        ordering = ['-enrolled_at']

    def __str__(self):
        return f'{self.student} -> {self.course}'

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.is_paid = self.course.is_free
        super().save(*args, **kwargs)


class CourseMaterial(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to=portal_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return f'{self.course}: {self.title}'


class CourseCertificate(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name='uploaded_certificate')
    file = models.FileField(upload_to=portal_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Certificate: {self.enrollment}'
