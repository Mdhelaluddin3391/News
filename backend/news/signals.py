import logging

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from core.tasks import send_async_email
from interactions.models import NewsletterSubscriber
from news.models import Article, LiveUpdate
from news.tasks import (
    auto_post_article_task,
    process_article_image,
    send_push_notifications_task,
    auto_update_featured_task,
    auto_update_trending_task,
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Article)
def handle_article_publish(sender, instance, created, **kwargs):
    # ── Internal-only saves ko skip karo (e.g. post_to_telegram=False update after posting)
    # Ye prevent karta hai infinite loop aur unnecessary task queuing
    update_fields = kwargs.get('update_fields')
    internal_only_fields = {'post_to_facebook', 'post_to_twitter', 'post_to_telegram',
                            'push_sent', 'newsletter_sent', 'featured_image',
                            'is_featured', 'is_trending', 'views'}
    if update_fields and set(update_fields).issubset(internal_only_fields):
        return

    if instance.status == 'published' and not instance.push_sent:
        transaction.on_commit(lambda: send_push_notifications_task.delay(instance.id))

    if instance.status == 'published' and instance.is_breaking and not instance.newsletter_sent:
        subscribers = list(
            NewsletterSubscriber.objects.filter(is_active=True).values_list('email', flat=True)
        )
        if subscribers:
            article_url = f"{settings.FRONTEND_URL}/article/{instance.slug}"
            subject = f"🚨 BREAKING NEWS: {instance.title}"
            message = f"🚨 BREAKING NEWS\n\n{instance.title}\n\nRead now: {article_url}"
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
                        You received this because you are subscribed to Ferox Times Breaking Alerts.<br>
                        <a href="{settings.FRONTEND_URL}/unsubscribe" style="color: #d32f2f;">Unsubscribe</a>
                    </div>
                </div>
            </body>
            </html>
            """
            transaction.on_commit(lambda: send_async_email.delay(subject, message, subscribers, html_content))
            Article.objects.filter(pk=instance.pk).update(newsletter_sent=True)

    if instance.status == 'published' and any(
        [instance.post_to_facebook, instance.post_to_twitter, instance.post_to_telegram]
    ):
        article_id = instance.id
        logger.info(
            "[Signal] Social post queued for article %s | FB=%s TW=%s TG=%s",
            article_id, instance.post_to_facebook,
            instance.post_to_twitter, instance.post_to_telegram
        )
        transaction.on_commit(lambda: auto_post_article_task.delay(article_id))

    # ── Auto-update featured & trending instantly on publish ──────────────
    # Celery Beat wala 30-min/1-hour wait nahi karna padega.
    # Jaise hi article publish hoga, yeh tasks queue mein chali jayengi.
    if instance.status == 'published':
        transaction.on_commit(lambda: auto_update_featured_task.delay())
        transaction.on_commit(lambda: auto_update_trending_task.delay())

@receiver(post_save, sender=Article)
def trigger_image_processing(sender, instance, **_kwargs):
    if instance.featured_image and not instance.featured_image.name.lower().endswith('.webp'):
        transaction.on_commit(lambda: process_article_image.delay(instance.id))


@receiver(post_save, sender=LiveUpdate)
def broadcast_live_update(sender, instance, created, **_kwargs):
    if not created:
        return

    channel_layer = get_channel_layer()
    group_name = f'live_article_{instance.article.id}'
    update_data = {
        'id': instance.id,
        'title': instance.title,
        'content': instance.content,
        'timestamp': instance.timestamp.isoformat(),
    }
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'send_new_update',
            'update_data': update_data,
        },
    )
