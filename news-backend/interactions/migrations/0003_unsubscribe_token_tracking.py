# Generated migration for unsubscribe token tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0002_comment_report'),
    ]

    operations = [
        migrations.AddField(
            model_name='newslettersubscriber',
            name='unsubscribe_token',
            field=models.CharField(blank=True, help_text='Current unsubscribe token issued to user', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='newslettersubscriber',
            name='unsubscribe_token_used_at',
            field=models.DateTimeField(blank=True, help_text='When the unsubscribe token was used (one-time use)', null=True),
        ),
    ]
