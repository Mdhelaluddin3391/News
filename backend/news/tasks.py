import json
import logging
import os
from io import BytesIO
import requests

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
    soft_time_limit=300,   # 5 min soft limit — raises SoftTimeLimitExceeded
    time_limit=360,        # 6 min hard kill
)
def auto_import_news_task(self):
    """
    Celery Beat task that runs every 30 minutes.
    Fetches top 5 trending headlines from GNews API, scrapes full text,
    rewrites via Gemini AI, and saves each as a draft Article.
    """
    gnews_key = os.getenv("GNEWS_API_KEY")

    if not gnews_key:
        msg = "❌ GNEWS_API_KEY is not set in the environment."
        logger.error(msg)
        return msg

    try:
        from .importer import fetch_and_import_news
    except ImportError as exc:
        msg = f"❌ Could not import fetch_and_import_news: {exc}"
        logger.exception(msg)
        return msg

    logger.info("[auto_import] Fetching GNews top-headlines (max=5)…")
    gnews_url = (
        f"https://gnews.io/api/v4/top-headlines"
        f"?category=general&lang=en&max=5&apikey={gnews_key}"
    )
    result = fetch_and_import_news(gnews_url, provider="gnews")
    logger.info("[auto_import] Result: %s", result)
    return result


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
