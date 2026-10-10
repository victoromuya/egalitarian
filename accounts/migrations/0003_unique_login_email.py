from django.db import migrations, models
from django.db.models.functions import Lower


def constraint():
    return models.UniqueConstraint(Lower('email'), condition=~models.Q(email=''), name='accounts_unique_login_email')


def add_unique_email(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    duplicates = User.objects.exclude(email='').annotate(normalized_email=Lower('email')).values('normalized_email').annotate(total=models.Count('id')).filter(total__gt=1)
    if duplicates.exists():
        raise RuntimeError('Duplicate email addresses exist. Assign a unique email to each account before applying this migration; no accounts have been modified.')
    schema_editor.add_constraint(User, constraint())


def remove_unique_email(apps, schema_editor):
    schema_editor.remove_constraint(apps.get_model('auth', 'User'), constraint())


class Migration(migrations.Migration):
    dependencies = [('accounts', '0002_alter_profile_id'), ('auth', '0012_alter_user_first_name_max_length')]
    operations = [migrations.RunPython(add_unique_email, remove_unique_email)]
