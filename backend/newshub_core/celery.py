import os
from celery import Celery


# Django settings ko Celery ke liye default set karein
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newshub_core.settings')

app = Celery('newshub_core')

# Settings file mein 'CELERY_' se start hone wale variables ko load karein
app.config_from_object('django.conf:settings', namespace='CELERY')

# Django ke sabhi installed apps mein agar 'tasks.py' file hai, toh usko auto-discover karein
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

from celery.schedules import crontab

# Celery Beat Periodic Tasks Schedule
app.conf.beat_schedule = {
    'cleanup-unverified-users-daily': {
        'task': 'users.tasks.cleanup_unverified_users',
        'schedule': crontab(hour=0, minute=0), # Daily at midnight
    },
    'cleanup-old-contact-messages-weekly': {
        'task': 'core.tasks.cleanup_old_contact_messages',
        'schedule': crontab(day_of_week=0, hour=3, minute=0), # Weekly on Sunday at 3 AM
    },
}
