import re
from urllib.parse import quote

from django.conf import settings


def whatsapp_contact(request):
    number = re.sub(r'[^0-9]', '', settings.WHATSAPP_NUMBER)
    message = quote("Hello Egalitarian Computers! I'd like to learn more about your courses and services.")
    return {'whatsapp_contact_url': f'https://wa.me/{number}?text={message}'}


def course_categories(request):
    from courses.models import Category
    return {'footer_course_categories': Category.objects.all()[:4]}
