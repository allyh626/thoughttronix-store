from django.db import migrations, models
from django.db.models.functions import Lower


def blank_emails_to_null(apps, schema_editor):
    """Blank emails become NULL (so they can't collide under the unique
    rule), and the rest are lowercased to match what ``User.save`` stores."""
    User = apps.get_model("accounts", "User")
    User.objects.filter(email="").update(email=None)
    User.objects.exclude(email=None).update(email=Lower("email"))


def null_emails_to_blank(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(email=None).update(email="")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_address'),
    ]

    # Three steps: allow NULL, convert the blanks, and only then add the
    # unique rule — several existing blanks would otherwise break it.
    operations = [
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name='email address'),
        ),
        migrations.AddField(
            model_name='user',
            name='email_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(blank_emails_to_null, null_emails_to_blank),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True, verbose_name='email address'),
        ),
    ]
