# Generated migration for email verification fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),  # Adjust based on your last migration
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_email_verified',
            field=models.BooleanField(default=False, help_text='Is the email address verified?'),
        ),
        migrations.AddField(
            model_name='user',
            name='email_verification_token',
            field=models.CharField(blank=True, help_text='Unique token for email verification', max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='user',
            name='email_verification_token_created_at',
            field=models.DateTimeField(blank=True, help_text='When was the verification token created', null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='is_active',
            field=models.BooleanField(default=False, help_text='User is active only after email verification'),
        ),
    ]
