ACTIVE_ADS_CACHE_KEY = 'core:active-ads:{device}'
ADVERTISE_PAGE_CACHE_KEY = 'core:advertise-page'
SITE_SETTINGS_CACHE_KEY = 'core:site-settings'
ACTIVE_JOBS_CACHE_KEY = 'core:active-jobs'


def active_ads_cache_key(is_mobile):
    return ACTIVE_ADS_CACHE_KEY.format(device='mobile' if is_mobile else 'desktop')
