from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.conf import settings
from .models import Article, Category, Author
import json
from pywebpush import webpush, WebPushException

from interactions.models import PushSubscription

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