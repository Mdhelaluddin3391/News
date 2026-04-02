from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.cache_keys import (
    ACTIVE_ADS_CACHE_KEY,
    ACTIVE_JOBS_CACHE_KEY,
    ADVERTISE_PAGE_CACHE_KEY,
    SITE_SETTINGS_CACHE_KEY,
)
from core.models import Advertisement, AdvertiseOption, AdvertisePage, JobPosting, SiteSetting


def _delete_many(keys):
    cache.delete_many(keys)


@receiver(post_save, sender=Advertisement)
@receiver(post_delete, sender=Advertisement)
def invalidate_advertisement_cache(**_kwargs):
    _delete_many([
        ACTIVE_ADS_CACHE_KEY.format(device='desktop'),
        ACTIVE_ADS_CACHE_KEY.format(device='mobile'),
    ])


@receiver(post_save, sender=AdvertisePage)
@receiver(post_delete, sender=AdvertisePage)
@receiver(post_save, sender=AdvertiseOption)
@receiver(post_delete, sender=AdvertiseOption)
def invalidate_advertise_page_cache(**_kwargs):
    _delete_many([ADVERTISE_PAGE_CACHE_KEY])


@receiver(post_save, sender=SiteSetting)
@receiver(post_delete, sender=SiteSetting)
def invalidate_site_settings_cache(**_kwargs):
    _delete_many([SITE_SETTINGS_CACHE_KEY])


@receiver(post_save, sender=JobPosting)
@receiver(post_delete, sender=JobPosting)
def invalidate_job_cache(**_kwargs):
    _delete_many([ACTIVE_JOBS_CACHE_KEY])
