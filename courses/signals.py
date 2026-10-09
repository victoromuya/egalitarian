from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse

from core.models import Notification

from .models import Enrollment


@receiver(pre_save, sender=Enrollment)
def flag_payment_confirmation(sender, instance, **kwargs):
    # is_paid can be flipped from Django admin, so detect the transition
    # here rather than in a view.
    instance._payment_just_confirmed = False
    if instance.pk:
        old = Enrollment.objects.filter(pk=instance.pk).values_list('is_paid', flat=True).first()
        instance._payment_just_confirmed = old is False and instance.is_paid


@receiver(post_save, sender=Enrollment)
def notify_enrollment_events(sender, instance, created, **kwargs):
    course = instance.course
    link = reverse('course_detail', args=[course.slug])
    if created:
        if instance.is_paid:
            message = f'You are enrolled in "{course.title}". You have full access to the course.'
        else:
            message = (
                f'You are enrolled in "{course.title}". Complete payment via WhatsApp '
                f'to unlock the course content and exam.'
            )
        Notification.objects.create(user=instance.student, message=message, link=link)
    elif getattr(instance, '_payment_just_confirmed', False):
        Notification.objects.create(
            user=instance.student,
            message=f'Your payment for "{course.title}" has been confirmed. You now have full access.',
            link=link,
        )
