# news-backend/core/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_async_email(subject, message, recipient_list, html_message=None):
    """
    Yeh Celery task Redis ki queue mein jayega aur background mein safely email bhejega.
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
            html_message=html_message
        )
        return f"✅ Email sent successfully to {len(recipient_list)} recipients."
    except Exception as e:
        return f"❌ Email sending error: {str(e)}"