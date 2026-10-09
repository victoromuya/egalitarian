from django.db import migrations

GROUP_NAME = 'Content Managers'

# (app_label, model, actions) — authoring permission for courses/events/exams,
# change-only on payable records (the manual is_paid flip), view-only on exam
# submissions/certificates. No grading capability exists anywhere (see CLAUDE.md).
PERMS = [
    ('courses', 'course', ['add', 'change', 'view']),
    ('courses', 'enrollment', ['change', 'view']),
    ('events', 'event', ['add', 'change', 'view']),
    ('events', 'eventregistration', ['change', 'view']),
    ('exams', 'exam', ['add', 'change', 'view']),
    ('exams', 'question', ['add', 'change', 'delete', 'view']),
    ('exams', 'choice', ['add', 'change', 'delete', 'view']),
    ('exams', 'submission', ['view']),
    ('exams', 'certificate', ['view']),
    ('core', 'notification', ['view']),
]


def create_group(apps, schema_editor):
    # Ensure Permission rows exist even on a fresh DB where post_migrate
    # hasn't run yet for these apps.
    from django.contrib.auth.management import create_permissions
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    for app_label, model, actions in PERMS:
        for action in actions:
            perm = Permission.objects.get(
                content_type__app_label=app_label,
                codename=f'{action}_{model}',
            )
            group.permissions.add(perm)


def remove_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name=GROUP_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('courses', '0001_initial'),
        ('events', '0001_initial'),
        ('exams', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_group, remove_group),
    ]
