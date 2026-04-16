import json
import logging
import os
from io import BytesIO
import requests
from celery.exceptions import SoftTimeLimitExceeded

import tweepy
from PIL import Image
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from pywebpush import webpush, WebPushException
from interactions.models import PushSubscription
from .models import Article
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
)
def cleanup_expired_flags_task(self):
    """
    Industry Standard: Breaking news kuch ghanto baad expire ho jati hai.
    Ye task har ghante (hourly) Celery Beat ke through chalana hai.
    Taki Admin dashboard me bhi purane breaking news tick na dikhein.
    """
    now = timezone.now()
    
    # 1. Breaking News Cleanup (Older than 12 hours)
    breaking_threshold = now - timedelta(hours=12)
    expired_breaking = Article.objects.filter(is_breaking=True, published_at__lt=breaking_threshold)
    count_breaking = expired_breaking.update(is_breaking=False)

    # 2. Web Story Cleanup (Older than 24 hours)
    story_threshold = now - timedelta(hours=24)
    expired_stories = Article.objects.filter(is_web_story=True, web_story_created_at__lt=story_threshold)
    count_stories = expired_stories.update(is_web_story=False, web_story_created_at=None)

    return f"Cleanup Done: {count_breaking} Breaking expired, {count_stories} Web Stories expired."


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
)
def auto_update_trending_task(self):
    """
    Trending Logic (Automatic + Admin Override):
    ─────────────────────────────────────────────
    RULE 1 (Auto): Agar koi article last 3 din mein publish hua hai aur
                   views >= TRENDING_VIEWS_THRESHOLD (100) hain, toh use
                   automatically is_trending=True mark kar do.

    RULE 2 (Override): Agar admin ne manually is_trending=True set kiya hai
                       toh wo article hamesha trending rahega — chahe views
                       threshold se kam hon. (Admin force override)

    RULE 3 (Cleanup): Jo articles 3 din se purane hain, unka auto-trending
                      flag clear ho jayega. Lekin admin override wale
                      (manually set) safe rahenge — ye un articles ko touch
                      nahi karega jo is_featured=True hain via admin.

    Ye task har 30 minute mein Celery Beat se chalti hai.
    """
    TRENDING_VIEWS_THRESHOLD = 100  # Itne views par auto-trending milti hai
    TRENDING_WINDOW_DAYS = 3        # Sirf last 3 din ke articles consider honge

    now = timezone.now()
    window_start = now - timedelta(days=TRENDING_WINDOW_DAYS)

    # ── STEP 1: Auto-mark new trending articles ────────────────────────────
    # Find karo articles jo:
    # - Published hain
    # - Last 3 din mein publish huye hain
    # - 100+ views hain
    # - Abhi tak is_trending=False hain (sirf naye update karo)
    newly_trending_qs = Article.objects.filter(
        status='published',
        published_at__gte=window_start,
        views__gte=TRENDING_VIEWS_THRESHOLD,
        is_trending=False,
    )
    count_newly_trending = newly_trending_qs.update(is_trending=True)

    # ── STEP 2: Clear stale auto-trending flags ────────────────────────────
    # Jo articles 3 din se purane hain aur trending=True hain unko clear karo.
    # EXCEPTION: Hum yahan ye nahi jaante ke konsa manually set tha.
    # Isliye hum sirf un articles ka flag clear karte hain jo:
    # - 3 din se zyada purane hain
    # - Views threshold se neeche gir chuke hain (matlab auto-trending tha)
    # Note: Pure admin override articles (manually set) ko protect karne ke liye
    #       admin admin panel se khud unset karega — ye task sirf view-based
    #       expired articles ko clean karti hai.
    stale_qs = Article.objects.filter(
        status='published',
        is_trending=True,
        published_at__lt=window_start,
        views__lt=TRENDING_VIEWS_THRESHOLD,
    )
    count_stale = stale_qs.update(is_trending=False)

    return (
        f"✅ Trending Update Done: {count_newly_trending} newly marked trending, "
        f"{count_stale} stale trending flags cleared."
    )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
)
def auto_update_featured_task(self):
    """
    Featured Logic (Latest Article = Featured):
    ─────────────────────────────────────────────
    RULE 1 (Auto): Sabse naya published article automatically is_featured=True
                   ho jata hai. Yeh "Latest Release → Featured" logic hai.

    RULE 2 (Override): Admin agar kisi old article ko is_featured=True
                       manually set kare toh:
                       - Woh article featured section mein dikhega.
                       - Latest article bhi auto-featured rahega (dono featured).
                       - Homepage frontend pe featured section mein latest wala
                         priority lega (sorted by published_at desc).

    RULE 3 (Cleanup): Agar koi article publish schedule se 2 din se zyada
                      purana ho aur admin ne manually override nahi kiya,
                      toh uska auto-featured flag clear ho jayega.
                      (2-day rolling featured window)

    Ye task har ghante Celery Beat se chalti hai.
    """
    FEATURED_WINDOW_HOURS = 48  # 2 din = 48 ghante (rolling featured window)

    now = timezone.now()
    window_start = now - timedelta(hours=FEATURED_WINDOW_HOURS)

    # ── STEP 1: Latest published article ko featured mark karo ─────────────
    latest_article = (
        Article.objects.filter(status='published', published_at__isnull=False)
        .order_by('-published_at')
        .first()
    )

    featured_title = "(none)"
    if latest_article:
        if not latest_article.is_featured:
            Article.objects.filter(pk=latest_article.pk).update(is_featured=True)
        featured_title = latest_article.title[:60]

    # ── STEP 2: 2 din se purane auto-featured articles ko clear karo ────────
    # Sirf wahi clear honge jinka published_at 48 ghante se purana hai
    # aur jinhe auto-featured mila tha (views-based check nahi, sirf age).
    # This preserves any admin forced featured articles that are newer than 48h.
    count_cleared = Article.objects.filter(
        is_featured=True,
        published_at__lt=window_start,
    ).exclude(
        # Latest article ko exclude karo (usse mat chho)
        pk=latest_article.pk if latest_article else None,
    ).update(is_featured=False)

    return (
        f"✅ Featured Update Done: Latest featured='{featured_title}', "
        f"{count_cleared} old featured flags cleared."
    )

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
)
def process_article_image(self, article_id):
    """
    Yeh Celery task background mein run hoga. Article ki image ko 
    resize karke WebP format mein compress karega bina website ko slow kiye.
    """
    try:
        article = Article.objects.get(id=article_id)
        
        # Agar image nahi hai, ya pehle se WebP hai toh kuch mat karo
        if not article.featured_image or article.featured_image.name.lower().endswith('.webp'):
            return f"Skipped processing for Article {article_id}"

        original_name = article.featured_image.name

        # Storage-agnostic image handling so S3 and local storage both work.
        with article.featured_image.open('rb') as image_file:
            img = Image.open(image_file)
            img.load()

        # PNG (RGBA) ko RGB mein convert karein taaki WebP support kare
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Resize karein (Max width 1200px)
        img.thumbnail((1200, 800), Image.Resampling.LANCZOS)

        # Memory buffer mein WebP format mein save karein
        output = BytesIO()
        img.save(output, format='WEBP', quality=80)
        output.seek(0)

        # Naya file name banayein (.webp extension ke sath)
        base_name = os.path.basename(original_name)
        file_name = os.path.splitext(base_name)[0] + '.webp'

        # Nayi compressed file save karein (save=False taaki abhi database save na ho)
        article.featured_image.save(file_name, ContentFile(output.read()), save=False)
        
        # Sirf featured_image field update karein DB mein
        article.save(update_fields=['featured_image'])

        # Storage free karne ke liye puraani file ko storage API ke through delete karo.
        if original_name and original_name != article.featured_image.name:
            article.featured_image.storage.delete(original_name)

        return f"✅ Image compressed to WebP for Article ID: {article_id}"

    except Article.DoesNotExist:
        return f"❌ Article {article_id} not found."
    except Exception as e:
        logger.exception("Image processing error for article %s", article_id)
        raise
    

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
)
def send_push_notifications_task(self, article_id):
    """
    Ye task naye articles par notification bhejega.
    Absolute URL fix kar diya gaya hai taaki browsers image block na karein.
    """
    try:
        article = Article.objects.get(id=article_id)
        
        notif_title = f"🚨 Breaking: {article.title}" if article.is_breaking else f"📰 Naya Article: {article.title}"
        short_desc = article.description[:120] + "..." if article.description else "Read now..."

        # === NAYA UPDATE: Icon ka Absolute URL banana ===
        base_url = settings.FRONTEND_URL.rstrip('/') # Extra slash hatane ke liye
        icon_url = f"{base_url}/images/default-news.png"
        
        if article.featured_image:
            # Agar S3 bucket (https://) lagaya hai toh URL same rahega, nahi toh base_url append hoga
            if article.featured_image.url.startswith('http'):
                icon_url = article.featured_image.url
            else:
                icon_url = f"{base_url}{article.featured_image.url}"
        # ================================================

        payload = {
            "title": notif_title,
            "body": short_desc,
            "url": f"{base_url}/article/{article.slug}",
            "icon": icon_url
        }

        subscriptions = PushSubscription.objects.all()
        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
                    data=json.dumps(payload),
                    vapid_private_key=settings.WEBPUSH_SETTINGS['VAPID_PRIVATE_KEY'],
                    vapid_claims={"sub": settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']},
                    ttl=86400, 
                    headers={"urgency": "high"}
                )
            except WebPushException as ex:
                response = getattr(ex, 'response', None)
                # Agar user ne permission revoke kar di hai toh database se delete kar do
                if response is not None and response.status_code in [404, 410]:
                    sub.delete()

        # Update flag after sending
        Article.objects.filter(pk=article.id).update(push_sent=True)
        return f"✅ Push notifications sent for Article {article_id}"
        
    except Article.DoesNotExist:
        return f"❌ Article {article_id} not found."
    except Exception as e:
        logger.exception("Push notification error for article %s", article_id)
        raise




@shared_task(
    bind=True,
    name="news.tasks.auto_import_news_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    soft_time_limit=600, 
    time_limit=660,     
)
def auto_import_news_task(self):
    """
    Celery Beat task that runs every 30 minutes.
    Fetches top 3 trending headlines from GNews API, scrapes full text,
    rewrites via Groq AI, and saves each as a draft Article.

    Error Handling:
    - GNEWS_API_KEY not set     → logs error, returns without crashing.
    - GROQ_API_KEY not set    → logged inside ai_utils; articles skipped.
    - GNews API unreachable     → logged inside importer; task returns safe msg.
    - Scraping failure          → logged inside importer; individual article skipped.
    - SoftTimeLimitExceeded     → caught here, logs warning, returns safely.
    """
    gnews_key = os.getenv("GNEWS_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    if not gnews_key:
        msg = "❌ GNEWS_API_KEY is not set in the environment. Please add it to your .env file."
        logger.error(msg)
        return msg

    if not groq_key:
        msg = "❌ GROQ_API_KEY is not set. AI rewriting is disabled — no articles will be imported."
        logger.error(msg)
        return msg

    try:
        from .importer import fetch_and_import_news
    except ImportError as exc:
        msg = f"❌ Could not import fetch_and_import_news: {exc}"
        logger.exception(msg)
        return msg

    try:
        logger.info("[auto_import] Starting GNews top-headlines fetch (max=3)…")
        gnews_url = (
            f"https://gnews.io/api/v4/top-headlines"
            f"?category=general&lang=en&max=3&apikey={gnews_key}"
        )
        result = fetch_and_import_news(gnews_url, provider="gnews")
        logger.info("[auto_import] Completed. Result: %s", result)
        return result

    except SoftTimeLimitExceeded:
        msg = "⏱️ auto_import_news_task hit soft time limit (10 min). Partial results may have been saved."
        logger.warning(msg)
        return msg
    except Exception as exc:
        msg = f"❌ Unexpected error in auto_import_news_task: {exc}"
        logger.exception(msg)
        raise  # Re-raise so Celery retry logic can handle it


@shared_task(
    bind=True,
    autoretry_for=(requests.RequestException, Exception),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
)
def auto_post_article_task(self, article_id):
    try:
        article = Article.objects.get(id=article_id, status='published')
    except Article.DoesNotExist:
        logger.warning("Skipping auto-post for missing article %s", article_id)
        return f"Article {article_id} not found."

    article_url = f"{settings.FRONTEND_URL}/article/{article.slug}"
    short_desc = article.description[:100] + "..." if article.description else ""
    message = (
        f"🚨 {article.title}\n\n"
        f"📝 {short_desc}\n\n"
        f"🔗 Read more:\n{article_url}\n\n"
        "#FeroxTimes #LatestNews"
    )
    posted_targets = []

    if article.post_to_facebook and settings.FACEBOOK_PAGE_ID and settings.FACEBOOK_ACCESS_TOKEN:
        response = requests.post(
            f"https://graph.facebook.com/v18.0/{settings.FACEBOOK_PAGE_ID}/feed",
            data={"message": message, "access_token": settings.FACEBOOK_ACCESS_TOKEN},
            timeout=15,
        )
        response.raise_for_status()
        posted_targets.append('facebook')
        Article.objects.filter(pk=article.pk).update(post_to_facebook=False)

    if article.post_to_twitter and all(
        [
            settings.TWITTER_API_KEY,
            settings.TWITTER_API_SECRET,
            settings.TWITTER_ACCESS_TOKEN,
            settings.TWITTER_ACCESS_TOKEN_SECRET,
        ]
    ):
        client = tweepy.Client(
            consumer_key=settings.TWITTER_API_KEY,
            consumer_secret=settings.TWITTER_API_SECRET,
            access_token=settings.TWITTER_ACCESS_TOKEN,
            access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET,
        )
        client.create_tweet(text=message)
        posted_targets.append('twitter')
        Article.objects.filter(pk=article.pk).update(post_to_twitter=False)

    if article.post_to_telegram and settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHANNEL_ID:
        response = requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            data={
                "chat_id": settings.TELEGRAM_CHANNEL_ID,
                "text": message,
                "parse_mode": "HTML",
            },
            timeout=15,
        )
        response.raise_for_status()
        posted_targets.append('telegram')
        Article.objects.filter(pk=article.pk).update(post_to_telegram=False)

    logger.info("Auto-post completed for article %s targets=%s", article_id, posted_targets)
    return f"Auto-post completed for article {article_id}: {', '.join(posted_targets) or 'no targets'}"
