from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from interactions.models import Poll, PollOption

ACTIVE_POLL_CACHE_KEY = 'interactions:active-poll'


@receiver(post_save, sender=Poll)
@receiver(post_delete, sender=Poll)
@receiver(post_save, sender=PollOption)
@receiver(post_delete, sender=PollOption)
def invalidate_active_poll_cache(**_kwargs):
    cache.delete(ACTIVE_POLL_CACHE_KEY)
