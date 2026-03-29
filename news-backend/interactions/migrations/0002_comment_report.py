# Generated migration for comment reporting system

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('interactions', '0001_initial'),  # Adjust based on your last migration
    ]

    operations = [
        migrations.CreateModel(
            name='CommentReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reason', models.CharField(choices=[('spam', 'Spam'), ('offensive', 'Offensive Language'), ('inappropriate', 'Inappropriate Content'), ('harassment', 'Harassment'), ('false_info', 'False Information'), ('other', 'Other')], max_length=20)),
                ('description', models.TextField(blank=True, help_text='Additional details about the report', null=True)),
                ('is_reviewed', models.BooleanField(default=False, help_text='Admin review ho gaya ya nahi')),
                ('admin_action', models.CharField(choices=[('none', 'No Action'), ('hidden', 'Comment Hidden'), ('deleted', 'Comment Deleted'), ('warn_user', 'User Warned')], default='none', help_text='Admin ka action', max_length=20)),
                ('admin_notes', models.TextField(blank=True, help_text='Admin ke notes', null=True)),
                ('comment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='interactions.comment')),
                ('reported_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reported_comments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('comment', 'reported_by')},
            },
        ),
    ]
