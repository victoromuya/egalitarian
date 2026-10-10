import django.db.models.deletion
from django.db import migrations, models
from django.db.models.functions import Lower


def preserve_categories(apps, schema_editor):
    Category = apps.get_model('courses', 'Category')
    Course = apps.get_model('courses', 'Course')
    for name in Course.objects.values_list('category', flat=True).distinct():
        category, _ = Category.objects.get_or_create(name=name)
        Course.objects.filter(category=name).update(category_ref=category)


def restore_names(apps, schema_editor):
    Course = apps.get_model('courses', 'Course')
    for course in Course.objects.select_related('category_ref'):
        course.category = course.category_ref.name
        course.save(update_fields=['category'])


def grant_permissions(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')
    group, _ = Group.objects.get_or_create(name='Content Managers')
    content_type, _ = ContentType.objects.get_or_create(app_label='courses', model='category')
    for action in ('add', 'change', 'delete', 'view'):
        permission, _ = Permission.objects.get_or_create(content_type=content_type, codename=f'{action}_category', defaults={'name': f'Can {action} category'})
        group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [('courses', '0005_portal_permissions')]
    operations = [
        migrations.CreateModel(name='Category', fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('name', models.CharField(max_length=100, unique=True)), ('display_order', models.PositiveIntegerField(default=0))], options={'ordering': ['display_order', 'name'], 'verbose_name_plural': 'course categories', 'constraints': [models.UniqueConstraint(Lower('name'), name='courses_unique_category_name')]}),
        migrations.AddField(model_name='course', name='category_ref', field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='courses', to='courses.category')),
        migrations.RunPython(preserve_categories, restore_names),
        migrations.RemoveField(model_name='course', name='category'),
        migrations.RenameField(model_name='course', old_name='category_ref', new_name='category'),
        migrations.AlterField(model_name='course', name='category', field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='courses', to='courses.category')),
        migrations.RunPython(grant_permissions, migrations.RunPython.noop),
    ]
