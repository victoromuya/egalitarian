from django.conf import settings
from django.db import models


class Course(models.Model):
    CATEGORY_CHOICES = [
        ('Programming', 'Programming'),
        ('Web Design', 'Web Design'),
        ('Business', 'Business'),
        ('Language', 'Language'),
        ('Film & Video', 'Film & Video'),
        ('Photography', 'Photography'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField()
    syllabus = models.TextField(help_text='Comma-separated syllabus topics')
    duration = models.CharField(max_length=50)
    level = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='courses_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self._state.adding:
            original_price = (
                type(self).objects.filter(pk=self.pk)
                .values_list('price', flat=True).first()
            )
            if original_price is not None and original_price != self.price:
                raise ValueError('Course price is immutable after creation.')
        super().save(*args, **kwargs)

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
