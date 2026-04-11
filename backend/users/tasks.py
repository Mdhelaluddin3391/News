import logging
from datetime import timedelta
from django.utils import timezone
from celery import shared_task
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

@shared_task
def cleanup_unverified_users():
    """
    Background worker task to delete users who registered more than 24 hours ago
    but never verified their email. This prevents the database from filling up
    with inactive/fake accounts.
    """
    User = get_user_model()
    cutoff_time = timezone.now() - timedelta(hours=24)
    
    # Query for unverified users who joined before the cutoff time
    unverified_old_users = User.objects.filter(
        is_email_verified=False,
        created_at__lt=cutoff_time,
        is_superuser=False, # Safety measure
        is_staff=False,     # Safety measure
    )
    
    count = unverified_old_users.count()
    if count > 0:
        logger.info(f"Cleanup Task: Deleting {count} unverified users older than 24 hours.")
        unverified_old_users.delete()
    else:
        logger.info("Cleanup Task: No stale unverified users found.")
        
    return f"Cleaned up {count} unverified users."
