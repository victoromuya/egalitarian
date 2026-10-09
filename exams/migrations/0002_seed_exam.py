from django.db import migrations

QUESTIONS = [
    {
        'text': 'Which Django component is responsible for mapping URLs to views?',
        'choices': [
            ('URLconf (urls.py)', True),
            ('settings.py', False),
            ('models.py', False),
            ('admin.py', False),
        ],
    },
    {
        'text': 'What does the Django ORM stand for?',
        'choices': [
            ('Object-Relational Mapper', True),
            ('Online Resource Manager', False),
            ('Output Rendering Module', False),
            ('Optimized Request Method', False),
        ],
    },
    {
        'text': 'Which template tag is used to extend a base template in Django?',
        'choices': [
            ('{% extends "base.html" %}', True),
            ('{% include "base.html" %}', False),
            ('{% inherit "base.html" %}', False),
            ('{% load "base.html" %}', False),
        ],
    },
]


def seed_exam(apps, schema_editor):
    Course = apps.get_model('courses', 'Course')
    Exam = apps.get_model('exams', 'Exam')
    Question = apps.get_model('exams', 'Question')
    Choice = apps.get_model('exams', 'Choice')

    try:
        course = Course.objects.get(slug='web-development-django')
    except Course.DoesNotExist:
        return

    exam, _ = Exam.objects.update_or_create(
        course=course,
        defaults={
            'title': 'Web Development with Django — Final Exam',
            'duration_minutes': 60,
            'passing_score': 70,
        },
    )
    exam.questions.all().delete()
    for order, q in enumerate(QUESTIONS):
        question = Question.objects.create(exam=exam, text=q['text'], order=order)
        for choice_text, is_correct in q['choices']:
            Choice.objects.create(question=question, text=choice_text, is_correct=is_correct)


def unseed_exam(apps, schema_editor):
    Course = apps.get_model('courses', 'Course')
    Exam = apps.get_model('exams', 'Exam')
    try:
        course = Course.objects.get(slug='web-development-django')
        Exam.objects.filter(course=course).delete()
    except Course.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0001_initial'),
        ('courses', '0002_seed_courses'),
    ]

    operations = [
        migrations.RunPython(seed_exam, unseed_exam),
    ]
