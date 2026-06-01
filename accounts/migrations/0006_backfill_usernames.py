from django.db import migrations


def assign_usernames(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.filter(username__isnull=True):
        base = (user.first_name or 'user').lower().strip()
        username = base
        counter = 2
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1
        user.username = username
        user.save(update_fields=['username'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_add_username_field'),
    ]

    operations = [
        migrations.RunPython(assign_usernames, migrations.RunPython.noop),
    ]
