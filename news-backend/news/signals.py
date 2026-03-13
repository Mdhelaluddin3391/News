import requests
import tweepy
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.conf import settings
from .models import Article, Category, Author
import json
from pywebpush import webpush, WebPushException
from interactions.models import PushSubscription
import threading
from django.core.mail import send_mail
from interactions.models import NewsletterSubscriber


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
    
    # 🔴 NAYA: 'not instance.push_sent' add kiya gaya hai 
    # Taaki check ho sake ki is article ka notification pehle toh nahi ja chuka
    if instance.status == 'published' and (instance.is_breaking or instance.is_featured) and not instance.push_sent:
        
        payload = {
            "title": "🚨 Breaking News" if instance.is_breaking else "⭐ Featured Article",
            "body": instance.title,
            "url": f"{settings.FRONTEND_URL}/article.html?id={instance.id}",
            "icon": instance.featured_image.url if instance.featured_image else f"{settings.FRONTEND_URL}/images/logo.png"
        }

        subscriptions = PushSubscription.objects.all()
        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {"p256dh": sub.p256dh, "auth": sub.auth}
                    },
                    data=json.dumps(payload),
                    vapid_private_key=settings.WEBPUSH_SETTINGS['VAPID_PRIVATE_KEY'],
                    vapid_claims={"sub": f"mailto:{settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']}"}
                )
            except WebPushException as ex:
                # Agar subscription invalid ho chuki hai (e.g., user ne permission hata di), toh DB se delete kar do
                if ex.response and ex.response.status_code in [404, 410]:
                    sub.delete()
            except Exception as e:
                # Any other general exceptions
                print(f"Push error for subscription {sub.id}: {e}")

        # 🔴 NAYA: Sabko notification bhejne ke baad database mein push_sent ko True kar dein.
        # Hum `.update()` use kar rahe hain taaki wapas save() trigger na ho aur infinite loop na bane.
        Article.objects.filter(pk=instance.pk).update(push_sent=True)
        print(f"✅ Push notifications sent successfully for article: {instance.title}")


@receiver(post_save, sender=Article)
def handle_social_media_autopost(sender, instance, created, **kwargs):
    # Check karein ki article published hai ya nahi
    if instance.status == 'published':
        article_url = f"{settings.FRONTEND_URL}/article.html?id={instance.id}"
        message = f"📰 Naya Article: {instance.title}\n\nPadhne ke liye yahan click karein: {article_url}"

        # 1. FACEBOOK AUTO POST
        if instance.post_to_facebook:
            print("🚀 Posting to Facebook...")
            # Yahan Facebook Graph API ka code aayega
            # requests.post(f"https://graph.facebook.com/PAGE_ID/feed?message={message}&access_token=YOUR_TOKEN")
            
            # Post hone ke baad checkbox wapas untick kar do taaki edit karne par dobara post na ho
            Article.objects.filter(pk=instance.pk).update(post_to_facebook=False)

        # 2. TWITTER AUTO POST
        if instance.post_to_twitter:
            print("🚀 Posting to Twitter...")
            # Yahan Twitter API v2 (Tweepy) ka code aayega
            
            # Untick checkbox
            Article.objects.filter(pk=instance.pk).update(post_to_twitter=False)

        # 3. TELEGRAM AUTO POST
        if instance.post_to_telegram:
            print("🚀 Posting to Telegram...")
            # Telegram bot API (Sabse aasan hoti hai)
            # BOT_TOKEN = 'your_bot_token'
            # CHANNEL_ID = '@your_channel_username'
            # requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHANNEL_ID}&text={message}")
            
            # Untick checkbox
            Article.objects.filter(pk=instance.pk).update(post_to_telegram=False)


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
    # Check karein: Status 'published' hona chahiye aur pehle email nahi gaya hona chahiye
    if instance.status == 'published' and not instance.newsletter_sent:
        
        # Sirf 'Active' subscribers ki email list nikalein
        subscribers = NewsletterSubscriber.objects.filter(is_active=True).values_list('email', flat=True)
        recipient_list = list(subscribers)
        
        if recipient_list:
            article_url = f"{settings.FRONTEND_URL}/article.html?id={instance.id}"
            subject = f"📰 Naya Article: {instance.title}"
            
            # Email ka body (Message)
            message = (
                f"Hello!\n\n"
                f"NewsHub par ek naya article publish hua hai:\n\n"
                f"📌 {instance.title}\n\n"
                f"Pura article padhne ke liye yahan click karein:\n"
                f"{article_url}\n\n"
            )


            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 0; }}
                    .container {{ max-width: 600px; margin: 30px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; }}
                    .header {{ background-color: #d32f2f; padding: 20px; text-align: center; color: white; }}
                    .content {{ padding: 30px; color: #334155; line-height: 1.6; font-size: 16px; }}
                    .article-title {{ font-size: 20px; color: #1a365d; margin-bottom: 10px; font-weight: bold; line-height: 1.4; }}
                    .btn {{ display: inline-block; background-color: #1a365d; color: #ffffff; text-decoration: none; padding: 12px 25px; border-radius: 5px; font-weight: bold; margin-top: 15px; }}
                    .footer {{ background-color: #f1f5f9; padding: 15px; text-align: center; color: #64748b; font-size: 12px; }}
                    .footer a {{ color: #d32f2f; text-decoration: none; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 style="margin:0; font-size: 22px;">🚨 Breaking News Alert</h1>
                    </div>
                    <div class="content">
                        <p>Hello Reader,</p>
                        <p>A new story has just been published on <strong>NewsHub</strong>!</p>
                        
                        <div style="background: #f8fafc; padding: 20px; border-left: 4px solid #d32f2f; margin: 25px 0;">
                            <div class="article-title">{instance.title}</div>
                            <a href="{article_url}" class="btn" style="color: #ffffff;">Read Full Article &rarr;</a>
                        </div>
                        
                        <p>Stay informed and keep reading!</p>
                    </div>
                    <div class="footer">
                        You are receiving this because you subscribed to NewsHub.<br><br>
                        <a href="{settings.FRONTEND_URL}/unsubscribe.html">Click here to Unsubscribe</a>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Threading ka use karke email bhejne ka process start karein
            email_thread = threading.Thread(
                target=send_bulk_emails_in_background, 
                args=(subject, message, recipient_list, html_content) # html_content yahan bheja gaya hai
            )
            email_thread.start()

        # Database mein update kar dein ki is article ka email ja chuka hai
        # .update() ka use isliye kiya hai taaki wapas save() call na ho aur infinite loop na bane
        Article.objects.filter(pk=instance.pk).update(newsletter_sent=True)


@receiver(post_save, sender=Article)
def handle_social_media_autopost(sender, instance, created, **kwargs):
    # Check karein ki article published hai ya nahi
    if instance.status == 'published':
        article_url = f"{settings.FRONTEND_URL}/article.html?id={instance.id}"
        short_desc = instance.description[:100] + "..." if instance.description else ""
        message = f"🚨 {instance.title}\n\n📝 {short_desc}\n\n🔗 Pura padhne ke liye click karein:\n{article_url}\n\n#NewsHub #DharmanagarLive #LatestNews"

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