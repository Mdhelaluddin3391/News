"""
debug_views.py — Sirf development/debugging ke liye.
Telegram bot connectivity test karta hai directly (Celery bypass).
URL: /admin/news/telegram-test/

⚠️ WARNING: Yeh view sirf staff members ke liye accessible hai.
"""
import logging
import os

import requests
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View

logger = logging.getLogger(__name__)


@method_decorator(staff_member_required, name="dispatch")
class TelegramTestView(View):
    """
    GET  /admin/news/telegram-test/
         Telegram bot token aur channel ID test karta hai.
         JSON response deta hai success ya error ke sath.

    POST /admin/news/telegram-test/?article_id=<id>
         Ek specific article ko directly Telegram par post karta hai
         (Celery bypass — synchronous).
    """

    def get(self, request):
        """Bot token aur channel validity check karo."""
        tg_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or os.getenv('TELEGRAM_BOT_TOKEN', '')
        tg_channel = getattr(settings, 'TELEGRAM_CHANNEL_ID', '') or os.getenv('TELEGRAM_CHANNEL_ID', '')

        result = {
            "token_set": bool(tg_token),
            "channel_set": bool(tg_channel),
            "token_preview": f"{tg_token[:10]}..." if tg_token else "NOT SET",
            "channel_id": tg_channel or "NOT SET",
        }

        if not tg_token or not tg_channel:
            result["status"] = "error"
            result["message"] = "TELEGRAM_BOT_TOKEN ya TELEGRAM_CHANNEL_ID missing hai!"
            return JsonResponse(result, status=400)

        # Bot info check
        try:
            info_resp = requests.get(
                f"https://api.telegram.org/bot{tg_token}/getMe",
                timeout=10,
            )
            info_data = info_resp.json()
            if info_data.get("ok"):
                bot_info = info_data.get("result", {})
                result["bot_username"] = f"@{bot_info.get('username', '?')}"
                result["bot_name"] = bot_info.get("first_name", "?")
                result["bot_valid"] = True
            else:
                result["bot_valid"] = False
                result["bot_error"] = info_data.get("description", "Unknown error")
        except Exception as e:
            result["bot_valid"] = False
            result["bot_error"] = str(e)

        # Test message bhejo
        try:
            test_resp = requests.post(
                f"https://api.telegram.org/bot{tg_token}/sendMessage",
                json={
                    "chat_id": tg_channel,
                    "text": "🔧 <b>Ferox Times — Telegram Test</b>\n\nYeh test message hai. Agar yeh dikh raha hai toh Telegram integration kaam kar rahi hai! ✅",
                    "parse_mode": "HTML",
                },
                timeout=15,
            )
            test_data = test_resp.json()
            if test_data.get("ok"):
                result["test_message_sent"] = True
                result["message_id"] = test_data.get("result", {}).get("message_id")
                result["status"] = "success"
                result["message"] = "✅ Test message successfully bhej diya gaya! Telegram channel check karein."
            else:
                result["test_message_sent"] = False
                result["telegram_error"] = test_data.get("description", "Unknown error")
                result["status"] = "error"
                result["message"] = f"❌ Telegram ne message reject kiya: {test_data.get('description')}"
        except Exception as e:
            result["test_message_sent"] = False
            result["status"] = "error"
            result["message"] = f"❌ Network error: {str(e)}"

        logger.info("[TelegramTest] Admin %s ne test kiya: %s", request.user.email, result.get("status"))
        return JsonResponse(result)

    def post(self, request):
        """Specific article ko directly Telegram par send karo (Celery bypass)."""
        from .models import Article

        article_id = request.GET.get("article_id") or request.POST.get("article_id")
        if not article_id:
            return JsonResponse({"status": "error", "message": "article_id parameter required"}, status=400)

        try:
            article = Article.objects.get(id=article_id, status="published")
        except Article.DoesNotExist:
            return JsonResponse({"status": "error", "message": f"Article {article_id} nahi mila ya published nahi hai"}, status=404)

        tg_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or os.getenv('TELEGRAM_BOT_TOKEN', '')
        tg_channel = getattr(settings, 'TELEGRAM_CHANNEL_ID', '') or os.getenv('TELEGRAM_CHANNEL_ID', '')

        if not tg_token or not tg_channel:
            return JsonResponse({"status": "error", "message": "TELEGRAM_BOT_TOKEN ya TELEGRAM_CHANNEL_ID missing!"}, status=400)

        article_url = f"{settings.FRONTEND_URL}/article/{article.slug}"
        short_desc = (article.description[:150].strip() + "...") if article.description else ""

        tg_message = (
            f"<b>{article.title}</b>\n\n"
            f"{short_desc}\n\n"
            f'<a href="{article_url}">\U0001f517 Puri Khabar Parhein</a>\n\n'
            "#FeroxTimes"
        )

        try:
            response = requests.post(
                f"https://api.telegram.org/bot{tg_token}/sendMessage",
                json={
                    "chat_id": tg_channel,
                    "text": tg_message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
                timeout=15,
            )
            data = response.json()
            if data.get("ok"):
                logger.info("[TelegramDebug] ✅ Article %s manually posted to Telegram by %s", article_id, request.user.email)
                return JsonResponse({
                    "status": "success",
                    "message": f"✅ Article '{article.title[:50]}' Telegram par post ho gaya!",
                    "message_id": data.get("result", {}).get("message_id"),
                })
            else:
                err = data.get("description", "Unknown error")
                logger.error("[TelegramDebug] ❌ Telegram rejected article %s: %s", article_id, err)
                return JsonResponse({"status": "error", "message": f"❌ Telegram error: {err}"}, status=400)
        except Exception as e:
            logger.exception("[TelegramDebug] Network error for article %s", article_id)
            return JsonResponse({"status": "error", "message": f"❌ Network error: {str(e)}"}, status=500)
