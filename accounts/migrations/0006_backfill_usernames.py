import unicodedata
from django.db import migrations, IntegrityError


def _normalize(first_name):
    name = (first_name or 'user').strip()
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    return name.lower() or 'user'


def assign_usernames(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.filter(username__isnull=True):
        base = _normalize(user.first_name)
        username, counter = base, 2
        while True:
            try:
                user.username = username
                user.save(update_fields=['username'])
                break
            except IntegrityError:
                username = f"{base}{counter}"
                counter += 1


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_add_username_field'),
    ]

    operations = [
        migrations.RunPython(assign_usernames, migrations.RunPython.noop),
    ]
