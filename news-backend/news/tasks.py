# news-backend/news/tasks.py
import json
from celery import shared_task
from django.conf import settings
from pywebpush import webpush, WebPushException
from interactions.models import PushSubscription
from .models import Article
import os
from io import BytesIO
from PIL import Image
from celery import shared_task
from django.core.files.base import ContentFile
from django.conf import settings
from .models import Article

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
    try:
        article = Article.objects.get(id=article_id)
        
        notif_title = f"🚨 Breaking: {article.title}" if article.is_breaking else f"📰 Naya Article: {article.title}"
        short_desc = article.description[:120] + "..." if article.description else "Read now..."

        payload = {
            "title": notif_title,
            "body": short_desc,
            "url": f"{settings.FRONTEND_URL}/article.html?id={article.id}",
            "icon": article.featured_image.url if article.featured_image else f"{settings.FRONTEND_URL}/images/logo.png"
        }

        subscriptions = PushSubscription.objects.all()
        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
                    data=json.dumps(payload),
                    vapid_private_key=settings.WEBPUSH_SETTINGS['VAPID_PRIVATE_KEY'],
                    vapid_claims={"sub": f"mailto:{settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']}"},
                    ttl=86400, headers={"urgency": "high"}
                )
            except WebPushException as ex:
                if ex.response and ex.response.status_code in [404, 410]:
                    sub.delete()

        # Update flag after sending
        Article.objects.filter(pk=article.id).update(push_sent=True)
    except Article.DoesNotExist:
        pass