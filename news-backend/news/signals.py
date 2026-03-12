from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.conf import settings
from .models import Article, Category, Author
import json
from pywebpush import webpush, WebPushException
import requests
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
    
    # Check if article is published AND is either breaking or featured
    if instance.status == 'published' and (instance.is_breaking or instance.is_featured):
        
        # Ye check karna zaroori hai taaki baar baar edit karne pe push na jaye.
        # Aap chahein toh ek naya field 'push_sent = models.BooleanField(default=False)' Article mein add karke handle kar sakte hain.
        
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


def send_bulk_emails_in_background(subject, message, recipient_list):
    """Ye function background mein chalega taaki website slow na ho"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
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
                f"Thank you for subscribing!\n"
                f"Unsubscribe karne ke liye visit karein: {settings.FRONTEND_URL}/unsubscribe.html"
            )
            
            # Threading ka use karke email bhejne ka process start karein
            email_thread = threading.Thread(
                target=send_bulk_emails_in_background, 
                args=(subject, message, recipient_list)
            )
            email_thread.start()

        # Database mein update kar dein ki is article ka email ja chuka hai
        # .update() ka use isliye kiya hai taaki wapas save() call na ho aur infinite loop na bane
        Article.objects.filter(pk=instance.pk).update(newsletter_sent=True)