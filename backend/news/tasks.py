import json
import os
from io import BytesIO
from PIL import Image
import os
from .importer import fetch_and_import_news
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from pywebpush import webpush, WebPushException
from .importer import fetch_and_import_news
from interactions.models import PushSubscription
from .models import Article
from datetime import timedelta
from django.utils import timezone


@shared_task
def cleanup_expired_flags_task():
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

@shared_task
def process_article_image(article_id):
    """
    Yeh Celery task background mein run hoga. Article ki image ko 
    resize karke WebP format mein compress karega bina website ko slow kiye.
    """
    try:
        article = Article.objects.get(id=article_id)
        
        # Agar image nahi hai, ya pehle se WebP hai toh kuch mat karo
        if not article.featured_image or article.featured_image.name.lower().endswith('.webp'):
            return f"Skipped processing for Article {article_id}"

        # Image ko file system se open karein
        img = Image.open(article.featured_image.path)

        # PNG (RGBA) ko RGB mein convert karein taaki WebP support kare
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Resize karein (Max width 1200px)
        img.thumbnail((1200, 800), Image.Resampling.LANCZOS)

        # Memory buffer mein WebP format mein save karein
        output = BytesIO()
        img.save(output, format='WEBP', quality=80)
        output.seek(0)

        # Original file ka path note karein taaki baad mein delete kar sakein
        original_path = article.featured_image.path
        
        # Naya file name banayein (.webp extension ke sath)
        base_name = os.path.basename(article.featured_image.name)
        file_name = os.path.splitext(base_name)[0] + '.webp'

        # Nayi compressed file save karein (save=False taaki abhi database save na ho)
        article.featured_image.save(file_name, ContentFile(output.read()), save=False)
        
        # Sirf featured_image field update karein DB mein
        article.save(update_fields=['featured_image'])

        # Storage free karne ke liye puraani (badi) image ko delete kar dein
        if os.path.exists(original_path) and original_path != article.featured_image.path:
            os.remove(original_path)

        return f"✅ Image compressed to WebP for Article ID: {article_id}"

    except Article.DoesNotExist:
        return f"❌ Article {article_id} not found."
    except Exception as e:
        return f"❌ Image processing error for Article {article_id}: {str(e)}"
    

@shared_task
def send_push_notifications_task(article_id):
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
        icon_url = f"{base_url}/images/logo.png" # Default image
        
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
                    vapid_claims={"sub": f"mailto:{settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']}"},
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
        return f"❌ Push notification error: {str(e)}"
    



@shared_task
def auto_import_news_task():
    """
    Background Celery task jo har 30 minute mein chalega.
    Primary: GNews | Fallback: NewsData.io
    """
    gnews_key = os.getenv('GNEWS_API_KEY')
    newsdata_key = os.getenv('NEWSDATA_API_KEY')
    
    # Primary API (GNews)
    if gnews_key:
        print("Fetching from GNews...")
        url = f"https://gnews.io/api/v4/top-headlines?category=general&lang=en&apikey={gnews_key}"
        result = fetch_and_import_news(url, provider='gnews')
        
        # Agar success hua aur koi error nahi aayi, toh yahi ruk jao
        if "✅" in result:
            return result
        else:
            print("GNews failed or limit reached. Trying NewsData.io...")

    # Fallback API (NewsData.io)
    if newsdata_key:
        print("Fetching from NewsData.io...")
        url = f"https://newsdata.io/api/1/news?apikey={newsdata_key}&language=en&category=top"
        result = fetch_and_import_news(url, provider='newsdata')
        return result

    return "❌ No API keys found in .env file."
