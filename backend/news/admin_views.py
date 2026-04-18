"""
admin_views.py — Custom Admin Views for Ferox Times.

Currently contains:
  - ai_writer_view: Admin AI Article Writer page.
    GET  → renders the AI writer form.
    POST → generates article via Groq AI + DuckDuckGo search → saves as Draft.
"""

import logging

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views import View

from .ai_utils import generate_article_from_prompt
from .models import Article, Author, Category, Tag

logger = logging.getLogger(__name__)

# ── Valid options (mirror ai_utils.py) ────────────────────────────────────────

VALID_CATEGORIES = [
    "Technology", "World", "Politics", "Sports",
    "Business", "Entertainment", "Science", "Health",
    "Environment", "Crime", "Education", "Economy",
]

VALID_TONES = [
    ("neutral",  "📰 Neutral / Standard News"),
    ("breaking", "🚨 Breaking News (Urgent)"),
    ("analysis", "🔍 In-Depth Analysis"),
    ("feature",  "📖 Feature / Human Interest"),
    ("opinion",  "✍️  Opinion / Editorial"),
]

VALID_LANGUAGES = [
    ("english", "🇬🇧 English"),
    ("urdu",    "🇵🇰 Urdu"),
    ("both",    "🌐 English + Urdu"),
]


# ── Helper: permission check ───────────────────────────────────────────────────

def _has_writer_permission(user) -> bool:
    """Only Admin, Editor, and Superuser can use the AI Article Writer."""
    return (
        user.is_superuser
        or getattr(user, "role", "") in ("admin", "editor")
    )


# ── Main View ──────────────────────────────────────────────────────────────────

@method_decorator(staff_member_required, name="dispatch")
class AIArticleWriterView(View):
    """
    GET  /admin/news/ai-writer/
         Renders the AI Article Writer form.

    POST /admin/news/ai-writer/
         1. Validates form inputs.
         2. Calls generate_article_from_prompt() → DuckDuckGo + Groq.
         3. Saves the result as a Draft Article.
         4. Redirects to the article's change page in Django admin.
    """

    template_name = "news/ai_writer.html"

    def _context(self, request, **extra):
        return {
            "title": "✍️ AI Article Writer",
            "categories": VALID_CATEGORIES,
            "tones": VALID_TONES,
            "languages": VALID_LANGUAGES,
            "has_permission": _has_writer_permission(request.user),
            **extra,
        }

    # ── GET ────────────────────────────────────────────────────────────────────

    def get(self, request):
        return render(request, self.template_name, self._context(request))

    # ── POST ───────────────────────────────────────────────────────────────────

    def post(self, request):
        # ── Permission guard ───────────────────────────────────────────────────
        if not _has_writer_permission(request.user):
            messages.error(
                request,
                "⛔ Permission denied. Only Admins and Editors can use the AI Article Writer.",
            )
            return render(request, self.template_name, self._context(request))

        # ── Read form fields ───────────────────────────────────────────────────
        description = request.POST.get("description", "").strip()
        category    = request.POST.get("category", "World").strip()
        tone        = request.POST.get("tone", "neutral").strip()
        language    = request.POST.get("language", "english").strip()
        status_flag = request.POST.get("save_status", "draft").strip()  # draft or published

        # ── Validate ───────────────────────────────────────────────────────────
        if len(description) < 15:
            messages.error(
                request,
                "❌ Please describe the article topic in at least 15 characters.",
            )
            return render(
                request,
                self.template_name,
                self._context(request, description=description, category=category,
                              tone=tone, language=language),
            )

        if category not in VALID_CATEGORIES:
            category = "World"

        if tone not in dict(VALID_TONES):
            tone = "neutral"

        if language not in dict(VALID_LANGUAGES):
            language = "english"

        # ── Generate Article ───────────────────────────────────────────────────
        logger.info(
            "[AI Writer View] Generating article | user=%s | topic='%s' | cat=%s | tone=%s | lang=%s",
            request.user.email, description[:60], category, tone, language,
        )

        messages.info(
            request,
            "⏳ AI is researching and writing your article… This may take 30–60 seconds. Please wait.",
        )

        try:
            ai_data = generate_article_from_prompt(
                description=description,
                category=category,
                tone=tone,
                language=language,
            )
        except Exception as exc:
            logger.exception("[AI Writer View] Unexpected error during generation: %s", exc)
            ai_data = None

        if not ai_data:
            messages.error(
                request,
                "❌ AI could not generate the article. Possible reasons: "
                "internet search failed, Groq API error, or prompt was too vague. "
                "Please try again with a more specific description.",
            )
            return render(
                request,
                self.template_name,
                self._context(request, description=description, category=category,
                              tone=tone, language=language),
            )

        # ── Resolve Category (get or create) ───────────────────────────────────
        category_obj, _ = Category.objects.get_or_create(
            name=category,
            defaults={"name": category},
        )

        # ── Resolve Author (logged-in admin's Author profile, or AI desk) ──────
        from django.contrib.auth import get_user_model
        User = get_user_model()

        if hasattr(request.user, "author_profile"):
            author_obj = request.user.author_profile
        else:
            # Fallback: use/create the AI desk author
            ai_user, created = User.objects.get_or_create(
                email="ai_desk@feroxtimes.com",
                defaults={
                    "name": "Ferox Times",
                    "role": "reporter",
                    "is_staff": False,
                    "is_active": True,
                },
            )
            if created:
                ai_user.set_unusable_password()
                ai_user.save()

            author_obj, _ = Author.objects.get_or_create(
                user=ai_user,
                defaults={"role": "Reporter"},
            )

        # ── Build & Save Article ───────────────────────────────────────────────
        ai_content  = ai_data.get("content", "")
        description_field = ai_data.get("meta_description", "")[:250] or description[:250]

        article = Article(
            title            = ai_data.get("title", description[:255]),
            meta_description = ai_data.get("meta_description", "")[:160],
            description      = description_field,
            content          = ai_content,
            category         = category_obj,
            author           = author_obj,
            source_name      = "AI Writer",
            is_imported      = False,   # This is NOT an auto-import; it's an intentional creation
            status           = "published" if status_flag == "published" else "draft",
        )

        try:
            article.save()  # triggers slug auto-generation in Article.save()
        except Exception as exc:
            logger.exception("[AI Writer View] DB save failed: %s", exc)
            messages.error(
                request,
                f"❌ Article was generated but could not be saved to database: {exc}",
            )
            return render(
                request,
                self.template_name,
                self._context(request, description=description, category=category,
                              tone=tone, language=language),
            )

        # ── Attach Tags ────────────────────────────────────────────────────────
        tag_objs = []
        for tag_name in ai_data.get("tags", []):
            tag_name = str(tag_name).strip()[:50]
            if tag_name:
                try:
                    tag_obj, _ = Tag.objects.get_or_create(name=tag_name)
                    tag_objs.append(tag_obj)
                except Exception as tag_exc:
                    logger.warning("[AI Writer View] Tag create error '%s': %s", tag_name, tag_exc)
        if tag_objs:
            article.tags.set(tag_objs)

        # ── Success ────────────────────────────────────────────────────────────
        sources = ai_data.get("research_sources_count", 0)
        status_label = "✅ Published" if article.status == "published" else "📝 Draft"

        logger.info(
            "[AI Writer View] ✅ Article saved [id=%s] '%s' | status=%s | sources=%d",
            article.pk, article.title, article.status, sources,
        )

        messages.success(
            request,
            f"🎉 Article generated successfully! "
            f"Researched {sources} internet source(s). "
            f"Saved as {status_label}. "
            f"Click the link below to review and edit.",
        )

        # Redirect to the article's change page in Django admin
        return redirect(f"/admin/news/article/{article.pk}/change/")
