import logging

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger('newshub.tasks')


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={'max_retries': 5},
)
def send_async_email(self, subject, message, recipient_list, html_message=None):
    """
    Yeh Celery task Redis ki queue mein jayega aur background mein safely email bhejega.
    Sare emails BCC me jayenge taaki privacy bani rahe.
    NAYA UPDATE: Emails ko 50 ke batches me bheja jayega taaki SMTP limits (block) na ho.
    """
    batch_size = 50
    total_sent = 0

    try:
        # Recipient list ko chote batches (50-50) mein tod kar bhejein
        for i in range(0, len(recipient_list), batch_size):
            batch = recipient_list[i:i + batch_size]
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.DEFAULT_FROM_EMAIL],  # 'To' me apna hi email rakhein
                bcc=batch                          # 'BCC' me 50 users ka batch daalein
            )
            
            if html_message:
                email.attach_alternative(html_message, "text/html")
                
            email.send(fail_silently=False)
            total_sent += len(batch)

        logger.info("Email task delivered %s messages", total_sent)
        return f"Email sent successfully to {total_sent} recipients via BCC in batches."
    except Exception:
        logger.exception("Email task failed for %s recipients", len(recipient_list))
        raise

from datetime import timedelta
from django.utils import timezone
from .models import ContactMessage

@shared_task
def cleanup_old_contact_messages():
    """
    Background worker task to delete ContactMessages (including job applications)
    that have been resolved and are older than 60 days to prevent database bloat.
    """
    cutoff_time = timezone.now() - timedelta(days=60)
    
    old_resolved_messages = ContactMessage.objects.filter(
        is_resolved=True,
        created_at__lt=cutoff_time
    )
    
    count = old_resolved_messages.count()
    if count > 0:
        logger.info(f"Cleanup Task: Deleting {count} resolved contact messages older than 60 days.")
        old_resolved_messages.delete()
    else:
        logger.info("Cleanup Task: No stale contact messages found.")
        
    return f"Cleaned up {count} contact messages."
