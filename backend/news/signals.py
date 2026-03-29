import requests
import tweepy
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.conf import settings
from .models import Article, Category, Author
import json
from django.db import transaction
from pywebpush import webpush, WebPushException
from interactions.models import PushSubscription
import threading
from django.core.mail import send_mail
from interactions.models import NewsletterSubscriber
from core.tasks import send_async_email
from .tasks import process_article_image
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import LiveUpdate
from .tasks import send_push_notifications_task


# 1. Article Save (Create/Update) hone par
@receiver(post_save, sender=Article)
def clear_cache_on_article_save(sender, instance, **kwargs):
    print(f"Article '{instance.title}' saved. Clearing cache...")
    cache.clear()

# 2. Article Delete hone par
@receiver(post_delete, sender=Article)
def clear_cache_on_article_delete(sender, instance, **kwargs):
    print(f"Article '{instance.title}' deleted. Clearing cache...")
    cache.clear()

# 3. Category Save ya Delete hone par (Kyunki Categories bhi cache hoti hain)
@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
def clear_cache_on_category_change(sender, instance, **kwargs):
    print(f"Category '{instance.name}' updated. Clearing cache...")
    cache.clear()

# 4. Author Save ya Delete hone par
@receiver(post_save, sender=Author)
@receiver(post_delete, sender=Author)
def clear_cache_on_author_change(sender, instance, **kwargs):
    print("Author updated. Clearing cache...")
    cache.clear()


@receiver(post_save, sender=Article)
def handle_article_publish(sender, instance, created, **kwargs):
    cache.clear()
    
    if instance.status == 'published' and not instance.push_sent:
        # Pura lamba loop ab yahan nahi chalega!
        # Humne transaction.on_commit isliye use kiya taaki pehle article DB me
        # theek se save ho jaye, fir task chale.
        transaction.on_commit(lambda: send_push_notifications_task.delay(instance.id))

def send_bulk_emails_in_background(subject, message, recipient_list, html_message=None):
    """Ye function background mein chalega taaki website slow na ho"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
            html_message=html_message # <--- NAYA
        )
        print(f"✅ Automatically sent emails to {len(recipient_list)} subscribers!")
    except Exception as e:
        print(f"❌ Email sending error: {e}")


        
@receiver(post_save, sender=Article)
def auto_send_newsletter_on_publish(sender, instance, created, **kwargs):
    # SIRF tab email bhejenge jab article PUBLISHED ho, pehle na bheja gaya ho, aur BREAKING NEWS ho!
    if instance.status == 'published' and not instance.newsletter_sent and instance.is_breaking:
        
        # Sirf 'Active' subscribers ki email list nikalein
        subscribers = NewsletterSubscriber.objects.filter(is_active=True).values_list('email', flat=True)
        recipient_list = list(subscribers)
        
        if recipient_list:
            article_url = f"{settings.FRONTEND_URL}/article.html?id={instance.id}"
            subject = f"🚨 BREAKING NEWS: {instance.title}"
            
            # Email ka body (Message)
            message = f"🚨 BREAKING NEWS\n\n{instance.title}\n\nPadhne ke liye yahan click karein: {article_url}"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px; }}
                    .container {{ max-width: 600px; margin: auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; }}
                    .header {{ background-color: #d32f2f; padding: 20px; text-align: center; color: white; }}
                    .content {{ padding: 30px; color: #334155; line-height: 1.6; font-size: 16px; }}
                    .article-title {{ font-size: 22px; color: #1a365d; margin-bottom: 10px; font-weight: bold; line-height: 1.4; }}
                    .desc {{ color: #444; margin-bottom: 20px; }}
                    .btn {{ display: inline-block; background-color: #d32f2f; color: #ffffff; text-decoration: none; padding: 12px 25px; border-radius: 5px; font-weight: bold; }}
                    .footer {{ background-color: #f1f5f9; padding: 15px; text-align: center; color: #64748b; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 style="margin:0; font-size: 24px;">🚨 BREAKING NEWS ALERT</h1>
                    </div>
                    <div class="content">
                        <div class="article-title">{instance.title}</div>
                        <p class="desc">{instance.description[:150] if instance.description else ''}...</p>
                        <a href="{article_url}" class="btn" style="color: #ffffff;">Read Full Story</a>
                    </div>
                    <div class="footer">
                        You received this because you are subscribed to Forex Times Breaking Alerts.<br>
                        <a href="{settings.FRONTEND_URL}/unsubscribe.html" style="color: #d32f2f;">Unsubscribe</a>
                    </div>
                </div>
            </body>
            </html>
            """
            
            send_async_email.delay(subject, message, recipient_list, html_content)

        # Update database so we don't send it again
        Article.objects.filter(pk=instance.pk).update(newsletter_sent=True)


@receiver(post_save, sender=Article)
def handle_social_media_autopost(sender, instance, created, **kwargs):
    # Check karein ki article published hai ya nahi
    if instance.status == 'published':
        article_url = f"{settings.FRONTEND_URL}/article.html?id={instance.id}"
        short_desc = instance.description[:100] + "..." if instance.description else ""
        message = f"🚨 {instance.title}\n\n📝 {short_desc}\n\n🔗 Pura padhne ke liye click karein:\n{article_url}\n\n#ForexTimes #LatestNews"

        # 1. FACEBOOK AUTO POST
        if instance.post_to_facebook:
            print("🚀 Posting to Facebook...")
            try:
                fb_url = f"https://graph.facebook.com/v18.0/{settings.FACEBOOK_PAGE_ID}/feed"
                payload = {
                    "message": message,
                    "access_token": settings.FACEBOOK_ACCESS_TOKEN
                }
                # Agar image bhi bhejni hai (Optional, uske liye endpoint /photos hota hai)
                response = requests.post(fb_url, data=payload)
                if response.status_code == 200:
                    print("✅ Facebook par post successfully ho gaya!")
                else:
                    print(f"❌ Facebook post failed: {response.json()}")
            except Exception as e:
                print(f"❌ Facebook error: {e}")
            finally:
                Article.objects.filter(pk=instance.pk).update(post_to_facebook=False)

        # 2. TWITTER (X) AUTO POST
        if instance.post_to_twitter:
            print("🚀 Posting to Twitter...")
            try:
                client = tweepy.Client(
                    consumer_key=settings.TWITTER_API_KEY,
                    consumer_secret=settings.TWITTER_API_SECRET,
                    access_token=settings.TWITTER_ACCESS_TOKEN,
                    access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET
                )
                response = client.create_tweet(text=message)
                print(f"✅ Twitter par post successfully ho gaya! Tweet ID: {response.data['id']}")
            except Exception as e:
                print(f"❌ Twitter error: {e}")
            finally:
                Article.objects.filter(pk=instance.pk).update(post_to_twitter=False)

        # 3. TELEGRAM AUTO POST
        if instance.post_to_telegram:
            print("🚀 Posting to Telegram...")
            try:
                tg_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {
                    "chat_id": settings.TELEGRAM_CHANNEL_ID,
                    "text": message,
                    "parse_mode": "HTML" # Optional: Agar aap bold/italic formatting chahte hain
                }
                response = requests.post(tg_url, data=payload)
                if response.status_code == 200:
                    print("✅ Telegram par post successfully ho gaya!")
                else:
                    print(f"❌ Telegram post failed: {response.json()}")
            except Exception as e:
                print(f"❌ Telegram error: {e}")
            finally:
                Article.objects.filter(pk=instance.pk).update(post_to_telegram=False)

@receiver(post_save, sender=Article)
def trigger_image_processing(sender, instance, created, **kwargs):
    """
    Article save hone ke baad check karta hai ki kya image compress karni hai.
    Agar haan, toh background mein Celery task trigger karta hai.
    """
    if instance.featured_image and not instance.featured_image.name.lower().endswith('.webp'):
        # transaction.on_commit ensure karega ki task tabhi chale jab article DB me fully save ho chuka ho
        transaction.on_commit(lambda: process_article_image.delay(instance.id))


@receiver(post_save, sender=LiveUpdate)
def broadcast_live_update(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        group_name = f'live_article_{instance.article.id}'
        
        # Data jo frontend ko jayega
        update_data = {
            'id': instance.id,
            'title': instance.title,
            'content': instance.content,
            'timestamp': instance.timestamp.isoformat(),
        }

        # WebSocket group mein message push karein
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'send_new_update',
                'update_data': update_data
            }
        )