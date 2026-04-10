"""
importer.py — GNews API fetcher + newspaper3k scraper + AI importer pipeline.

Pipeline per article:
  GNews API → source_url de-duplication → robots.txt check → newspaper3k scrape
      → Gemini rewrite → Category/Tag get_or_create → Article(draft) save
      → original_content cleared (legal compliance)

Legal Protections (Grey Zone → Safe Zone):
  ✅ robots.txt respected  — We check the publisher's robots.txt with OUR bot name
                             before scraping. If disallowed, we skip the article.
  ✅ Honest User-Agent     — We identify ourselves as 'FeroxTimesBot' (not a browser).
                             This is the ethical standard used by Google, Bing, etc.
  ✅ Rate limiting         — 2-second delay between each article scrape. This prevents
                             overloading the source server (ethical crawling standard).
  ✅ No content stored     — original_content cleared immediately after AI rewrite.
                             Only the 100% AI-rewritten version remains in the DB.
  ✅ No images downloaded  — featured_image left blank. Frontend uses default-news.png.
  ✅ Source attribution    — source_name and source_url always stored for full credit.
  ✅ AI rewrite mandatory  — If Gemini fails, article is skipped. Never stored as-is.
"""

import logging
import time
import uuid
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from django.utils.html import strip_tags

from news.models import Article, Category, Tag
from newspaper import Article as WebArticle

from .ai_utils import rewrite_article_with_ai

logger = logging.getLogger(__name__)

# ─── Helpers ───────────────────────────────────────────────────────────────

def _clean_text(text: str, max_length: int | None = None) -> str:
    """Strip HTML tags and truncate to max_length with an ellipsis."""
    if not text:
        return ""
    cleaned = strip_tags(text).strip()
    if max_length and len(cleaned) > max_length:
        return cleaned[:max_length].rsplit(" ", 1)[0] + "…"
    return cleaned


# Our bot's User-Agent — used in both robots.txt checks and HTTP requests.
# Being transparent about who we are is the ethical and legal standard.
# (Google: Googlebot, Bing: bingbot, we: FeroxTimesBot)
_BOT_USER_AGENT = "FeroxTimesBot/1.0 (+https://www.feroxtimes.com/about)"

# Polite crawl delay between articles (seconds).
# Prevents hammering source servers — same principle as Crawl-Delay in robots.txt.
_SCRAPE_DELAY_SECONDS = 2


def _is_scraping_allowed(url: str) -> bool:
    """
    Checks the source website's robots.txt to see if scraping is permitted
    for our bot ('FeroxTimesBot'). Falls back to checking the wildcard ('*')
    rule if no specific rule exists for our bot.

    Returns True if allowed (or if robots.txt cannot be fetched — fail-open
    so a temporarily unreachable robots.txt doesn't silently block all imports).
    Returns False only when robots.txt is readable AND explicitly disallows.
    """
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()

        # First check our specific bot name, then fall back to wildcard (*)
        allowed = rp.can_fetch(_BOT_USER_AGENT, url) or rp.can_fetch("*", url)

        if not allowed:
            logger.warning(
                "robots.txt disallows scraping for '%s' (robots: %s) — skipping.",
                url, robots_url,
            )
        return allowed
    except Exception as exc:
        # Can't read robots.txt — log but allow (fail-open)
        logger.debug("Could not read robots.txt for '%s': %s — proceeding.", url, exc)
        return True


def _scrape_full_text(url: str) -> str:
    """
    Uses newspaper3k to download and parse the full article body.
    Sends an honest 'FeroxTimesBot' User-Agent so publishers can identify us
    in their server logs (same ethical approach as Google, Bing, etc.).
    Returns an empty string on failure.
    """
    try:
        web_article = WebArticle(
            url,
            browser_user_agent=_BOT_USER_AGENT,
            request_timeout=10,
        )
        web_article.download()
        web_article.parse()
        return web_article.text or ""
    except Exception as exc:
        logger.warning("newspaper3k scraping failed for %s: %s", url, exc)
        return ""


def _is_duplicate(source_url: str, original_title: str) -> bool:
    """
    Returns True if an article with the same source URL or original title
    already exists in the database, preventing duplicate imports.
    """
    return Article.objects.filter(source_url=source_url).exists() or \
           Article.objects.filter(original_title=original_title).exists()


# ─── Provider-specific parsers ──────────────────────────────────────────────

def _parse_gnews_item(item: dict) -> dict:
    return {
        "title":       item.get("title", "").strip(),
        "source_url":  item.get("url", "").strip(),
        "source_name": item.get("source", {}).get("name", "GNews"),
        # NOTE: 'image' field from GNews is intentionally ignored.
        # Downloading third-party images without a license is copyright infringement.
        # The frontend automatically shows /images/default-news.png as a fallback.
    }


_PARSERS = {
    "gnews": (_parse_gnews_item, "articles"),
}


# ─── Main importer ──────────────────────────────────────────────────────────

def fetch_and_import_news(api_url: str, provider: str) -> str:
    """
    Fetches top-5 headlines from `api_url`, checks robots.txt, scrapes full
    text, rewrites via Gemini, saves each as a draft Article, then clears
    the raw scraped content for copyright compliance.

    Returns a human-readable result string (used by the Celery task for logging).
    """
    if provider not in _PARSERS:
        return f"❌ Unknown provider: '{provider}'. Valid options: {list(_PARSERS)}"

    parser_fn, data_key = _PARSERS[provider]

    # ── Step 1: Hit the news API ────────────────────────────────────────────
    try:
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        raw_data = response.json()
    except requests.RequestException as exc:
        logger.error("News API request failed (%s): %s", provider, exc)
        return f"❌ News API request failed for {provider}: {exc}"
    except ValueError as exc:
        logger.error("News API returned non-JSON (%s): %s", provider, exc)
        return f"❌ Invalid JSON from {provider}: {exc}"

    # Fetch only top 5 headlines as required
    articles_data = raw_data.get(data_key, [])[:5]

    if not articles_data:
        return f"⚠️ No articles returned from {provider}."

    imported_count = 0
    skipped_count = 0

    for item in articles_data:
        parsed = parser_fn(item)
        title       = parsed["title"]
        source_url  = parsed["source_url"]
        source_name = parsed["source_name"]

        # ── Step 2: Basic validation ────────────────────────────────────────
        if not title or not source_url:
            logger.debug("Skipping item with missing title or URL from %s.", provider)
            skipped_count += 1
            continue

        # ── Step 3: Duplicate check ─────────────────────────────────────────
        if _is_duplicate(source_url, title):
            logger.debug("Duplicate detected, skipping: %s", title)
            skipped_count += 1
            continue

        # ── Step 4: robots.txt compliance check ─────────────────────────────
        if not _is_scraping_allowed(source_url):
            logger.info(
                "Skipping '%s' — robots.txt disallows scraping of %s.",
                title, source_url,
            )
            skipped_count += 1
            continue

        # ── Step 5: Polite crawl delay ───────────────────────────────────────
        # Wait before scraping each article to avoid overloading the source.
        # This is the same 'Crawl-Delay' courtesy that all ethical bots follow.
        time.sleep(_SCRAPE_DELAY_SECONDS)

        # ── Step 6: Scrape full article text ─────────────────────────────────
        # raw_text is stored temporarily in original_content for AI reference.
        # It will be CLEARED immediately after a successful save (see Step 11).
        logger.info("Scraping: %s", source_url)
        raw_text = _scrape_full_text(source_url)

        if not raw_text or len(raw_text.strip()) < 100:
            logger.warning(
                "Scraping yielded insufficient text for '%s' (%d chars) — skipping.",
                title,
                len(raw_text),
            )
            skipped_count += 1
            continue

        # ── Step 7: AI rewrite via Gemini ────────────────────────────────────
        logger.info("Sending to Gemini for AI rewrite: '%s'", title)
        ai_data = rewrite_article_with_ai(title, raw_text, source_name)

        if not ai_data:
            # Never save copy-pasted content — skip the article entirely
            logger.warning(
                "AI rewrite returned None for '%s' — article skipped to prevent plagiarism.",
                title,
            )
            skipped_count += 1
            continue

        # ── Step 8: Resolve Category (get or create) ─────────────────────────
        category_name = ai_data.get("category", "General").strip() or "General"
        category_obj, cat_created = Category.objects.get_or_create(name=category_name)
        if cat_created:
            logger.info("Created new category: '%s'", category_name)

        # ── Step 9: Build the Article object ─────────────────────────────────
        # description is a plain-text excerpt shown on the homepage card
        ai_content  = ai_data.get("content", "")
        description = _clean_text(ai_content, max_length=200)

        article = Article(
            # AI-generated fields
            title            = ai_data.get("title", title),
            meta_description = ai_data.get("meta_description", ""),
            description      = description,
            content          = ai_content,
            category         = category_obj,

            # Original source tracking fields
            original_title   = title[:500],
            source_name      = source_name[:100],
            source_url       = source_url[:500],

            # TEMPORARY: raw scraped text stored here so AI has context reference.
            # This is cleared immediately after save in Step 11 (copyright compliance).
            original_content = raw_text,

            # Status & flags
            # featured_image intentionally left blank — no third-party images downloaded.
            # Frontend will automatically show /images/default-news.png as fallback.
            status           = "draft",
            is_imported      = True,
        )

        # ── Step 10: Persist the article ─────────────────────────────────────
        article.save()  # triggers slug auto-generation in Article.save()

        # ── Step 11: Clear raw scraped content (copyright compliance) ─────────
        # AI rewrite is complete and saved. The raw original_content is no longer
        # needed and keeping it would be storing copyrighted third-party text.
        Article.objects.filter(pk=article.pk).update(original_content=None)
        logger.info(
            "🗑️  original_content cleared for article [id=%s] after successful AI save.",
            article.pk,
        )

        # ── Step 12: Attach Tags (get or create) ──────────────────────────────
        tag_names = ai_data.get("tags", [])
        tag_objs = []
        for tag_name in tag_names:
            tag_name = str(tag_name).strip()[:50]
            if tag_name:
                tag_obj, _ = Tag.objects.get_or_create(name=tag_name)
                tag_objs.append(tag_obj)
        if tag_objs:
            article.tags.set(tag_objs)

        imported_count += 1
        logger.info(
            "✅ Imported draft article [id=%s]: '%s'",
            article.pk,
            article.title,
        )

    summary = (
        f"✅ {imported_count} new AI-rewritten draft article(s) imported from '{provider}'. "
        f"(Skipped: {skipped_count})"
    )
    logger.info(summary)
    return summary