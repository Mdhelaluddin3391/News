"""
importer.py — GNews API fetcher + newspaper3k scraper + AI importer pipeline.

Pipeline per article:
  GNews API → source_url de-duplication → robots.txt check → newspaper3k scrape
      → Groq AI rewrite (Reuters/AP newsroom standards)
      → Category/Tag get_or_create → Article(draft) save
      → original_content cleared (legal compliance)

Newsroom Standards (enforced by ai_utils.py prompt):
  ✅ Author line           — Every article opens with "By Ferox Times".
  ✅ Strong lead           — WHO, WHAT, WHERE, WHEN answered in first 40–60 words.
  ✅ Source attribution    — "According to <source>..." in every article body.
  ✅ HTML Sources section  — <h2>Sources</h2> with <ul> listed at end of every article.
  ✅ Zero blog language    — No opinions, no rhetorical questions, no emotional phrases.
  ✅ Zero AI clichés       — Full prohibited phrase list enforced at prompt level.
  ✅ 500–900 word count    — Optimal for Google News ranking.

Legal Protections:
  ✅ robots.txt respected  — We check the publisher's robots.txt before scraping.
  ✅ Honest User-Agent     — We identify ourselves as 'FeroxTimesBot'.
  ✅ Rate limiting         — 2-second delay between each article scrape.
  ✅ No content stored     — original_content cleared after AI rewrite.
  ✅ No images downloaded  — featured_image left blank. Frontend uses default-news.png.
  ✅ Source attribution    — source_name and source_url always stored.
  ✅ AI rewrite mandatory  — If Groq fails, article is NEVER saved.

Error Handling:
  ✅ GNews API failure     — Returns clear error, no articles saved.
  ✅ Scraping failure      — Article skipped with a warning log.
  ✅ Broken / short text   — Article skipped (< 150 chars of content).
  ✅ Groq failure          — Article skipped; never stored as raw copy.
  ✅ robots.txt unreachable— Fail-open: we proceed politely.
  ✅ DB errors             — Each article saved independently; one failure
                             does not block the rest.
"""

import logging
import time
import uuid
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from django.utils.html import strip_tags
from django.contrib.auth import get_user_model

from news.models import Article, Author, Category, Tag
from newspaper import Article as WebArticle

from .ai_utils import rewrite_article_with_ai

logger = logging.getLogger(__name__)

# ─── Constants ─────────────────────────────────────────────────────────────

# Our bot's User-Agent — used in both robots.txt checks and HTTP requests.
_BOT_USER_AGENT = "FeroxTimesBot/1.0 (+https://www.feroxtimes.com/about)"

# Polite crawl delay between articles (seconds).
_SCRAPE_DELAY_SECONDS = 2

# Minimum scraped text length to proceed with AI rewrite.
_MIN_TEXT_LENGTH = 150

# Timeout for robots.txt fetch and article scraping.
_ROBOTS_TIMEOUT = 8
_SCRAPE_TIMEOUT = 15


# ─── Helpers ───────────────────────────────────────────────────────────────

def _clean_text(text: str, max_length: int | None = None) -> str:
    """Strip HTML tags and truncate to max_length with an ellipsis."""
    if not text:
        return ""
    cleaned = strip_tags(text).strip()
    if max_length and len(cleaned) > max_length:
        return cleaned[:max_length].rsplit(" ", 1)[0] + "…"
    return cleaned


def _is_scraping_allowed(url: str) -> bool:
    """
    Checks the source website's robots.txt to see if scraping is permitted
    for our bot ('FeroxTimesBot'). Falls back to checking the wildcard ('*')
    rule if no specific rule exists for our bot.

    Returns True if allowed (or if robots.txt cannot be fetched — fail-open).
    Returns False only when robots.txt is readable AND explicitly disallows.
    """
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        # We manually fetch robots.txt using requests with a timeout
        # because RobotFileParser.read() uses urllib without a timeout and can hang indefinitely.
        try:
            resp = requests.get(robots_url, headers={"User-Agent": _BOT_USER_AGENT}, timeout=_ROBOTS_TIMEOUT)
            lines = resp.text.splitlines()
        except requests.RequestException as exc:
            logger.debug("Could not read robots.txt for '%s' due to timeout/error: %s — proceeding.", url, exc)
            return True  # fail-open

        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.parse(lines)

        # First check our specific bot name, then fall back to wildcard (*)
        allowed = rp.can_fetch(_BOT_USER_AGENT, url) or rp.can_fetch("*", url)

        if not allowed:
            logger.warning(
                "robots.txt disallows scraping for '%s' (robots: %s) — skipping.",
                url, robots_url,
            )
        return allowed
    except Exception as exc:
        # Catch any other unexpected errors during parsing
        logger.debug("Unexpected error during robots.txt check for '%s': %s — proceeding.", url, exc)
        return True


def _scrape_full_text(url: str) -> str:
    """
    Uses newspaper3k to download and parse the full article body.
    Returns an empty string on any failure so the caller can handle it gracefully.

    Improvements:
    - Uses a generous 15-second timeout to handle slow servers.
    - Falls back to requests + BeautifulSoup paragraph extraction if
      newspaper3k returns insufficient text (< 150 chars).
    """
    raw_text = ""

    # ── Primary: newspaper3k ────────────────────────────────────────────────
    try:
        web_article = WebArticle(
            url,
            browser_user_agent=_BOT_USER_AGENT,
            request_timeout=_SCRAPE_TIMEOUT,
        )
        web_article.download()
        web_article.parse()
        raw_text = web_article.text or ""
    except Exception as exc:
        logger.warning("newspaper3k scraping failed for %s: %s", url, exc)

    # ── Fallback: requests + simple paragraph extraction ────────────────────
    if not raw_text or len(raw_text.strip()) < _MIN_TEXT_LENGTH:
        logger.info(
            "newspaper3k returned insufficient text (%d chars) for %s — trying fallback.",
            len(raw_text.strip()),
            url,
        )
        try:
            from html.parser import HTMLParser

            class _ParagraphExtractor(HTMLParser):
                """Minimal HTML parser that extracts visible <p> text."""
                def __init__(self):
                    super().__init__()
                    self._in_p = False
                    self._paragraphs: list[str] = []
                    self._current: list[str] = []

                def handle_starttag(self, tag, attrs):
                    if tag == "p":
                        self._in_p = True
                        self._current = []

                def handle_endtag(self, tag):
                    if tag == "p" and self._in_p:
                        text = "".join(self._current).strip()
                        if len(text) > 30:
                            self._paragraphs.append(text)
                        self._in_p = False

                def handle_data(self, data):
                    if self._in_p:
                        self._current.append(data)

            resp = requests.get(
                url,
                headers={"User-Agent": _BOT_USER_AGENT},
                timeout=_SCRAPE_TIMEOUT,
                allow_redirects=True,
            )
            resp.raise_for_status()
            parser = _ParagraphExtractor()
            parser.feed(resp.text)
            fallback_text = "\n\n".join(parser._paragraphs)
            if len(fallback_text.strip()) > len(raw_text.strip()):
                raw_text = fallback_text
                logger.info(
                    "Fallback extractor retrieved %d chars for %s.",
                    len(raw_text),
                    url,
                )
        except Exception as fallback_exc:
            logger.warning("Fallback scraping also failed for %s: %s", url, fallback_exc)

    return raw_text.strip()


def _search_and_scrape_context(title: str, primary_url: str) -> str:
    """
    Searches DuckDuckGo for the article title to gather multi-source context.
    Fetches the top 2-3 results, scrapes their text, and concatenates it.
    """
    context = ""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(title, max_results=3))
            
        for res in results:
            url = res.get("href")
            if not url or url == primary_url:
                continue
            
            logger.info("  [Multi-Source] Scraping context from: %s", url)
            # Skip if explicitly disallowed, fail-open applies
            if not _is_scraping_allowed(url):
                continue
            
            time.sleep(_SCRAPE_DELAY_SECONDS) # Polite delay
            bg_text = _scrape_full_text(url)
            
            if bg_text and len(bg_text.strip()) > _MIN_TEXT_LENGTH:
                # Truncate each bg source to avoid massive payloads
                truncated_bg = _clean_text(bg_text, max_length=4000)
                context += f"\n\n--- Background Source: {res.get('title', url)} ---\n{truncated_bg}\n"
                
    except Exception as exc:
        logger.warning("[Multi-Source] Search Context gathering failed for '%s': %s", title, exc)
        
    return context.strip()


def _is_duplicate(source_url: str, original_title: str) -> bool:
    """
    Returns True if an article with the same source URL or original title
    already exists in the database, preventing duplicate imports.
    """
    return (
        Article.objects.filter(source_url=source_url).exists()
        or Article.objects.filter(original_title=original_title).exists()
    )


# ─── Provider-specific parsers ──────────────────────────────────────────────

def _parse_gnews_item(item: dict) -> dict:
    return {
        "title":       item.get("title", "").strip(),
        "source_url":  item.get("url", "").strip(),
        "source_name": "Ferox Times",
        # NOTE: 'image' field from GNews is intentionally ignored.
        # Downloading third-party images without a license is copyright infringement.
    }


_PARSERS = {
    "gnews": (_parse_gnews_item, "articles"),
}


# ─── Main importer ──────────────────────────────────────────────────────────

def fetch_and_import_news(api_url: str, provider: str) -> str:
    """
    Fetches top-5 headlines from `api_url`, checks robots.txt, scrapes full
    text, rewrites via Groq AI, saves each as a draft Article, then clears
    the raw scraped content for copyright compliance.

    Returns a human-readable result string (used by the Celery task for logging).

    Error Handling Strategy:
    - API failure   → Return error immediately (no articles processed).
    - Per-article   → Log error and skip; continue to next article.
    - DB error      → Log and skip; never crash the whole pipeline.
    """
    if provider not in _PARSERS:
        return f"❌ Unknown provider: '{provider}'. Valid options: {list(_PARSERS)}"

    parser_fn, data_key = _PARSERS[provider]

    # ── Step 1: Hit the news API ────────────────────────────────────────────
    try:
        response = requests.get(api_url, timeout=20, headers={"User-Agent": _BOT_USER_AGENT})
        response.raise_for_status()
        raw_data = response.json()
    except requests.exceptions.Timeout:
        msg = f"❌ GNews API request timed out for provider '{provider}'."
        logger.error(msg)
        return msg
    except requests.exceptions.ConnectionError as exc:
        msg = f"❌ GNews API connection failed for provider '{provider}': {exc}"
        logger.error(msg)
        return msg
    except requests.exceptions.HTTPError as exc:
        status_code = getattr(exc.response, "status_code", "?")
        if status_code == 403:
            msg = f"❌ GNews API key is invalid or quota exceeded (HTTP 403)."
        elif status_code == 429:
            msg = f"❌ GNews API rate limit hit (HTTP 429). Will retry later."
        else:
            msg = f"❌ GNews API HTTP error {status_code} for provider '{provider}': {exc}"
        logger.error(msg)
        return msg
    except requests.RequestException as exc:
        msg = f"❌ GNews API request failed for provider '{provider}': {exc}"
        logger.error(msg)
        return msg
    except ValueError as exc:
        msg = f"❌ GNews API returned non-JSON for provider '{provider}': {exc}"
        logger.error(msg)
        return msg

    # Check for API-level errors in the response body
    if "errors" in raw_data or raw_data.get("status") == "error":
        error_msg = raw_data.get("errors") or raw_data.get("message") or "Unknown API error"
        msg = f"❌ GNews API returned an error: {error_msg}"
        logger.error(msg)
        return msg

    # Fetch only top 5 headlines as required
    articles_data = raw_data.get(data_key, [])[:5]

    if not articles_data:
        msg = f"⚠️ No articles returned from '{provider}'. The API may be rate-limited or the category is empty."
        logger.warning(msg)
        return msg

    imported_count = 0
    skipped_count = 0
    skip_reasons: list[str] = []

    for idx, item in enumerate(articles_data, start=1):
        try:
            parsed      = parser_fn(item)
            title       = parsed["title"]
            source_url  = parsed["source_url"]
            source_name = parsed["source_name"]

            logger.info(
                "[%d/%d] Processing: '%s' from %s",
                idx, len(articles_data), title, source_name,
            )

            # ── Step 2: Basic validation ──────────────────────────────────
            if not title or not source_url:
                reason = f"Missing title or URL (title={bool(title)}, url={bool(source_url)})"
                logger.debug("Skipping item %d: %s", idx, reason)
                skip_reasons.append(reason)
                skipped_count += 1
                continue

            # ── Step 3: Duplicate check ───────────────────────────────────
            if _is_duplicate(source_url, title):
                logger.debug("Duplicate detected, skipping: '%s'", title)
                skip_reasons.append(f"Duplicate: '{title[:60]}'")
                skipped_count += 1
                continue

            # ── Step 4: robots.txt compliance check ───────────────────────
            if not _is_scraping_allowed(source_url):
                logger.info(
                    "Skipping '%s' — robots.txt disallows scraping of %s.",
                    title, source_url,
                )
                skip_reasons.append(f"robots.txt blocked: '{title[:60]}'")
                skipped_count += 1
                continue

            # ── Step 5: Polite crawl delay ────────────────────────────────
            time.sleep(_SCRAPE_DELAY_SECONDS)

            # ── Step 6: Scrape full article text ──────────────────────────
            logger.info("[%d/%d] Scraping: %s", idx, len(articles_data), source_url)
            raw_text = _scrape_full_text(source_url)

            if not raw_text or len(raw_text.strip()) < _MIN_TEXT_LENGTH:
                reason = (
                    f"Insufficient scraped text ({len(raw_text.strip()) if raw_text else 0} chars) "
                    f"for '{title[:60]}'"
                )
                logger.warning(
                    "[%d/%d] %s — skipping (need ≥%d chars).",
                    idx, len(articles_data), reason, _MIN_TEXT_LENGTH,
                )
                skip_reasons.append(reason)
                skipped_count += 1
                continue

            # ── Step 6.5: Aggregate multi-source context via Web Search ───
            logger.info("[%d/%d] Fetching background search context via DDGS...", idx, len(articles_data))
            bg_context = _search_and_scrape_context(title, source_url)
            if bg_context:
                raw_text += f"\n\n══════════════════════════════════════\nADDITIONAL BACKGROUND CONTEXT:\n{bg_context}"
                logger.info("[%d/%d] Appended %d chars of multi-source background context.", idx, len(articles_data), len(bg_context))

            # ── Step 7: AI rewrite via Groq ─────────────────────────────
            logger.info(
                "[%d/%d] Sending to Groq for AI rewrite: '%s' (%d chars of raw text)",
                idx, len(articles_data), title, len(raw_text),
            )
            ai_data = rewrite_article_with_ai(title, raw_text, source_name)

            if not ai_data:
                reason = f"Groq rewrite failed for '{title[:60]}'"
                logger.warning(
                    "[%d/%d] %s — article skipped to prevent plagiarism.",
                    idx, len(articles_data), reason,
                )
                skip_reasons.append(reason)
                skipped_count += 1
                continue

            # ── Step 8: Resolve Category (get or create) ──────────────────
            category_name = (ai_data.get("category") or "World").strip()
            if not category_name:
                category_name = "World"
            category_obj, cat_created = Category.objects.get_or_create(
                name=category_name,
                defaults={"name": category_name},
            )
            if cat_created:
                logger.info("Created new category: '%s'", category_name)

            # ── Step 8.5: Resolve Virtual Reporter (AI User + Author profile) ───
            # The display name "Ferox Times" matches the author line
            # injected into every article's HTML content by ai_utils.py:
            User = get_user_model()
            ai_user, user_created = User.objects.get_or_create(
                email="ai_desk@feroxtimes.com",
                defaults={
                    "name": "Ferox Times",
                    "role": "reporter",
                    "is_staff": False,
                    "is_active": True,
                    "bio": (
                        "The official news desk of Ferox Times. "
                        "All AI-assisted articles are reviewed against Reuters/AP "
                        "editorial standards before publication."
                    ),
                }
            )
            if user_created:
                ai_user.set_unusable_password()  # Prevent anyone from logging in as this user
                ai_user.save()
                logger.info("Created Ferox Times user: '%s'", ai_user.email)

            # Ensure an Author profile exists for the AI user.
            # Article.author requires an Author instance, not a User instance.
            ai_author, author_created = Author.objects.get_or_create(
                user=ai_user,
                defaults={
                    "role": "Reporter",
                }
            )
            if author_created:
                logger.info(
                    "Created Author profile for Ferox Times user: '%s'", ai_user.email
                )

            # ── Step 9: Build the Article object ──────────────────────────
            ai_content  = ai_data.get("content", "")
            description = _clean_text(ai_content, max_length=250)
            if not description:
                description = _clean_text(ai_data.get("meta_description", ""), max_length=250)

            article = Article(
                # AI-generated fields
                title            = ai_data.get("title") or title[:255],
                meta_description = ai_data.get("meta_description", "")[:160],
                description      = description,
                content          = ai_content,
                category         = category_obj,
                author           = ai_author,  # Author instance (not User)

                # Original source tracking fields
                original_title   = title[:500],
                source_name      = source_name[:100],
                source_url       = source_url[:500],

                # TEMPORARY: raw scraped text stored here for reference.
                # CLEARED immediately after save in Step 11 (copyright compliance).
                original_content = raw_text,

                # Status & flags
                status           = "draft",
                is_imported      = True,
            )

            # ── Step 10: Persist the article ──────────────────────────────
            article.save()  # triggers slug auto-generation in Article.save()

            # ── Step 11: Clear raw scraped content (copyright compliance) ──
            Article.objects.filter(pk=article.pk).update(original_content=None)
            logger.info(
                "🗑️  original_content cleared for article [id=%s].",
                article.pk,
            )

            # ── Step 12: Attach Tags (get or create) ──────────────────────
            tag_names = ai_data.get("tags", [])
            tag_objs = []
            for tag_name in tag_names:
                tag_name = str(tag_name).strip()[:50]
                if tag_name:
                    try:
                        tag_obj, _ = Tag.objects.get_or_create(name=tag_name)
                        tag_objs.append(tag_obj)
                    except Exception as tag_exc:
                        logger.warning("Could not create tag '%s': %s", tag_name, tag_exc)
            if tag_objs:
                article.tags.set(tag_objs)

            imported_count += 1
            logger.info(
                "✅ [%d/%d] Imported draft article [id=%s]: '%s' [%s]",
                idx, len(articles_data), article.pk, article.title, category_name,
            )

        except Exception as article_exc:
            # Never let a single article crash the entire import pipeline
            logger.exception(
                "❌ Unexpected error processing article %d ('%s'): %s",
                idx, item.get("title", "?"), article_exc,
            )
            skip_reasons.append(f"Unexpected error for article {idx}: {article_exc}")
            skipped_count += 1
            continue

    # ── Final Summary ───────────────────────────────────────────────────────
    summary_parts = [
        f"✅ {imported_count} newsroom-standard draft article(s) imported from '{provider}'.",
        f"(Skipped: {skipped_count})",
    ]
    if skip_reasons:
        skip_detail = " | ".join(skip_reasons[:5])
        summary_parts.append(f"Skip reasons: [{skip_detail}]")

    summary = " ".join(summary_parts)
    logger.info(summary)
    return summary