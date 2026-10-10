from django.db import migrations


def grant_permissions(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')
    group, _ = Group.objects.get_or_create(name='Content Managers')
    for model in ('coursematerial', 'coursecertificate'):
        content_type, _ = ContentType.objects.get_or_create(app_label='courses', model=model)
        for action in ('add', 'change', 'delete', 'view'):
            permission, _ = Permission.objects.get_or_create(
                content_type=content_type, codename=f'{action}_{model}',
                defaults={'name': f'Can {action} {model}'},
            )
            group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [('courses', '0004_coursecertificate_coursematerial'), ('core', '0002_content_managers_group')]
    operations = [migrations.RunPython(grant_permissions, migrations.RunPython.noop)]
