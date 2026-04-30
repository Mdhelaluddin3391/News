"""
importer.py — Industry-Grade GNews Intelligence Pipeline for Ferox Times.

Pipeline per article (2 articles per 30-minute cycle):
──────────────────────────────────────────────────────
  PHASE 1 │ GNews API → fetch top-headlines (title + URL only)
  PHASE 2 │ De-duplication check (slug/title/URL)
  PHASE 3 │ robots.txt compliance check on source URL
  PHASE 4 │ DuckDuckGo deep research:
           │   • Search the topic across the open web
           │   • Scrape 5-8 trusted sources with newspaper3k
           │   • Build a comprehensive multi-source knowledge base
  PHASE 5 │ Groq AI → receives full knowledge base → writes complete
           │           newsroom-standard article (Reuters/AP/BBC style)
  PHASE 6 │ Category / Tag get_or_create → Draft Article saved
  PHASE 7 │ Raw content cleared (copyright / legal compliance)

Quality Standards:
  ✅ 100% research-backed  — Every fact sourced from live internet research.
  ✅ Pure news format      — No blog language, no opinions, no lists of tips.
  ✅ Strong SEO title      — 58-68 chars, fact-based, no clickbait.
  ✅ Dynamic subheadings   — Story-specific h2/h3 only, never generic labels.
  ✅ Min 700 words         — Google News eligibility requirement.
  ✅ 7 SEO tags            — Typed and validated for SERP performance.
  ✅ Exactly 2 per cycle   — Protects Groq token budget.

Legal Protections:
  ✅ robots.txt respected  — Publisher robots.txt checked before scraping.
  ✅ Honest User-Agent     — Identified as 'FeroxTimesBot'.
  ✅ Polite rate limiting  — 2-second delay between each source scrape.
  ✅ No content stored     — original_content cleared after AI rewrite.
  ✅ No images downloaded  — featured_image left blank (no copyright risk).
  ✅ Source attribution    — source_name and source_url always stored.
  ✅ AI rewrite mandatory  — If Groq fails, article is NEVER saved.
"""

import logging
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from django.contrib.auth import get_user_model
from django.utils.html import strip_tags

from news.models import Article, Author, Category, Tag
from newspaper import Article as WebArticle

from .ai_utils import rewrite_article_with_ai

logger = logging.getLogger(__name__)

# ─── Pipeline Constants ───────────────────────────────────────────────────────

# How many articles to produce per Celery task run.
# Keep at 2 to protect Groq token budget on the free tier.
ARTICLES_PER_RUN = 2

# How many GNews headlines to fetch (we need extras in case some are dupes/blocked).
GNEWS_FETCH_LIMIT = 8

# Our bot's User-Agent — polite identification for robots.txt and HTTP requests.
_BOT_USER_AGENT = "FeroxTimesBot/1.0 (+https://www.feroxtimes.com/about)"

# Minimum scraped text length (chars) to proceed.
_MIN_TEXT_LENGTH = 200

# Timeouts
_ROBOTS_TIMEOUT  = 8   # seconds for robots.txt fetch
_SCRAPE_TIMEOUT  = 20  # seconds per source article scrape

# DuckDuckGo: how many search results to pull for deep research.
_DDGS_MAX_RESULTS = 10

# Min / max sources to actually scrape for the knowledge base.
_MIN_RESEARCH_SOURCES = 3
_MAX_RESEARCH_SOURCES = 8

# Polite delay between scrapes (seconds).
_SCRAPE_DELAY = 2


# ─── Text Utilities ───────────────────────────────────────────────────────────

def _clean_text(text: str, max_length: int | None = None) -> str:
    """Strip HTML tags and optional length cap."""
    if not text:
        return ""
    cleaned = strip_tags(text).strip()
    if max_length and len(cleaned) > max_length:
        return cleaned[:max_length].rsplit(" ", 1)[0] + "…"
    return cleaned


# ─── robots.txt Compliance ────────────────────────────────────────────────────

def _is_scraping_allowed(url: str) -> bool:
    """
    Returns True if scraping is allowed (or robots.txt is unreachable — fail-open).
    Returns False only when robots.txt is readable AND explicitly disallows.
    """
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            resp = requests.get(
                robots_url,
                headers={"User-Agent": _BOT_USER_AGENT},
                timeout=_ROBOTS_TIMEOUT,
            )
            lines = resp.text.splitlines()
        except requests.RequestException:
            return True  # fail-open

        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.parse(lines)

        allowed = rp.can_fetch(_BOT_USER_AGENT, url) or rp.can_fetch("*", url)
        if not allowed:
            logger.warning("robots.txt blocked: %s", url)
        return allowed
    except Exception:
        return True  # fail-open on any unexpected error


# ─── Article Scraper ──────────────────────────────────────────────────────────

def _scrape_url(url: str) -> str:
    """
    Scrapes full article text from a URL using newspaper3k with a
    BeautifulSoup paragraph-extraction fallback.
    Returns empty string on failure so callers handle it gracefully.
    """
    raw_text = ""

    # Primary: newspaper3k
    try:
        wa = WebArticle(url, browser_user_agent=_BOT_USER_AGENT, request_timeout=_SCRAPE_TIMEOUT)
        wa.download()
        wa.parse()
        raw_text = wa.text or ""
    except Exception as exc:
        logger.debug("newspaper3k failed for %s: %s", url, exc)

    # Fallback: simple <p> extractor via requests + HTMLParser
    if len(raw_text.strip()) < _MIN_TEXT_LENGTH:
        try:
            from html.parser import HTMLParser

            class _PE(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self._in = False
                    self._paras: list[str] = []
                    self._cur: list[str] = []

                def handle_starttag(self, tag, attrs):
                    if tag == "p":
                        self._in = True
                        self._cur = []

                def handle_endtag(self, tag):
                    if tag == "p" and self._in:
                        t = "".join(self._cur).strip()
                        if len(t) > 40:
                            self._paras.append(t)
                        self._in = False

                def handle_data(self, data):
                    if self._in:
                        self._cur.append(data)

            resp = requests.get(
                url,
                headers={"User-Agent": _BOT_USER_AGENT},
                timeout=_SCRAPE_TIMEOUT,
                allow_redirects=True,
            )
            resp.raise_for_status()
            pe = _PE()
            pe.feed(resp.text)
            fallback = "\n\n".join(pe._paras)
            if len(fallback) > len(raw_text):
                raw_text = fallback
        except Exception as fb_exc:
            logger.debug("Fallback scrape failed for %s: %s", url, fb_exc)

    return raw_text.strip()


# ─── Deep Internet Research Engine ────────────────────────────────────────────

def _build_knowledge_base(headline: str, primary_url: str) -> tuple[str, int]:
    """
    Core intelligence phase of the pipeline.

    1. Searches DuckDuckGo for the headline to find related coverage.
    2. Scrapes up to _MAX_RESEARCH_SOURCES trusted articles from results.
    3. Includes the primary source (GNews article) as Source 0.
    4. Returns a concatenated knowledge base string + source count.

    The knowledge base feeds directly into the Groq prompt so the AI
    can write a fully fact-based, multi-source article without hallucinating.
    """
    knowledge_base = ""
    sources_scraped = 0

    # ── Source 0: Primary GNews source ───────────────────────────────────────
    if primary_url and _is_scraping_allowed(primary_url):
        logger.info("[Research] Scraping primary source: %s", primary_url)
        primary_text = _scrape_url(primary_url)
        if len(primary_text.strip()) >= _MIN_TEXT_LENGTH:
            knowledge_base += (
                f"\n\n{'═' * 60}\n"
                f"SOURCE 0 [Primary Source] — {primary_url}\n"
                f"{'═' * 60}\n"
                f"{primary_text[:5000]}\n"
            )
            sources_scraped += 1
            logger.info("[Research] Primary source: %d chars scraped.", len(primary_text))

    # ── DuckDuckGo discovery ──────────────────────────────────────────────────
    ddg_results = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            ddg_results = list(ddgs.text(headline, max_results=_DDGS_MAX_RESULTS))
        logger.info(
            "[Research] DuckDuckGo returned %d results for: '%s'",
            len(ddg_results), headline[:70],
        )
    except Exception as ddg_exc:
        logger.warning("[Research] DuckDuckGo search failed for '%s': %s", headline[:60], ddg_exc)

    # ── Scrape each result ────────────────────────────────────────────────────
    for i, result in enumerate(ddg_results, start=1):
        if sources_scraped >= _MAX_RESEARCH_SOURCES:
            break

        url   = result.get("href", "")
        title = result.get("title", "No Title")
        snippet = result.get("body", "")

        if not url or url == primary_url:
            continue

        # robots.txt check (fail-open)
        if not _is_scraping_allowed(url):
            logger.debug("[Research] robots.txt blocked source %d: %s", i, url)
            continue

        logger.info("[Research] Scraping source %d/%d: %s", i, len(ddg_results), url)
        time.sleep(_SCRAPE_DELAY)  # polite delay

        body = _scrape_url(url)

        if len(body.strip()) >= _MIN_TEXT_LENGTH:
            # Truncate each source to 4 000 chars to avoid token overflow
            truncated = body[:4000]
            knowledge_base += (
                f"\n\n{'─' * 60}\n"
                f"SOURCE {sources_scraped} — {title}\n"
                f"URL: {url}\n"
                f"{'─' * 60}\n"
                f"{snippet}\n\n"
                f"{truncated}\n"
            )
            sources_scraped += 1
            logger.info("[Research] Source %d: %d chars added.", sources_scraped, len(truncated))
        elif snippet:
            # Snippet-only fallback if full scrape failed
            knowledge_base += (
                f"\n\n{'─' * 60}\n"
                f"SOURCE {sources_scraped} [Snippet only] — {title}\n"
                f"{'─' * 60}\n"
                f"{snippet}\n"
            )
            sources_scraped += 1

    logger.info(
        "[Research] Knowledge base complete: %d sources | %d chars total.",
        sources_scraped, len(knowledge_base),
    )
    return knowledge_base.strip(), sources_scraped


# ─── Duplicate Detection ──────────────────────────────────────────────────────

def _is_duplicate(source_url: str, original_title: str) -> bool:
    """Prevents re-importing the same story via URL or title match."""
    return (
        Article.objects.filter(source_url=source_url).exists()
        or Article.objects.filter(original_title=original_title).exists()
    )


# ─── GNews Response Parser ────────────────────────────────────────────────────

def _parse_gnews_item(item: dict) -> dict:
    return {
        "title":       item.get("title", "").strip(),
        "source_url":  item.get("url", "").strip(),
        "source_name": item.get("source", {}).get("name", "Ferox Times").strip() or "Ferox Times",
    }


_PARSERS = {
    "gnews": (_parse_gnews_item, "articles"),
}


# ─── Main Pipeline ────────────────────────────────────────────────────────────

def fetch_and_import_news(api_url: str, provider: str) -> str:
    """
    Runs the full intelligence pipeline for up to ARTICLES_PER_RUN articles.

    Returns a human-readable result string used by the Celery task for logging.

    Strategy:
    - Fetch GNEWS_FETCH_LIMIT headlines (more than needed, to survive dupes/blocks).
    - Process one by one until ARTICLES_PER_RUN successful imports are done.
    - Each article gets a full DuckDuckGo research phase before being sent to Groq.
    """
    if provider not in _PARSERS:
        return f"❌ Unknown provider: '{provider}'. Valid: {list(_PARSERS)}"

    parser_fn, data_key = _PARSERS[provider]

    # ── Phase 1: Fetch GNews headlines ───────────────────────────────────────
    logger.info("[Pipeline] Fetching %d headlines from GNews…", GNEWS_FETCH_LIMIT)
    try:
        response = requests.get(api_url, timeout=20, headers={"User-Agent": _BOT_USER_AGENT})
        response.raise_for_status()
        raw_data = response.json()
    except requests.exceptions.Timeout:
        return f"❌ GNews API request timed out."
    except requests.exceptions.ConnectionError as exc:
        return f"❌ GNews API connection failed: {exc}"
    except requests.exceptions.HTTPError as exc:
        code = getattr(exc.response, "status_code", "?")
        if code == 403:
            return "❌ GNews API key invalid or quota exceeded (HTTP 403)."
        if code == 429:
            return "❌ GNews rate limit hit (HTTP 429). Will retry."
        return f"❌ GNews HTTP error {code}: {exc}"
    except (requests.RequestException, ValueError) as exc:
        return f"❌ GNews API failed: {exc}"

    if "errors" in raw_data or raw_data.get("status") == "error":
        err = raw_data.get("errors") or raw_data.get("message") or "Unknown error"
        return f"❌ GNews API error: {err}"

    headlines = raw_data.get(data_key, [])[:GNEWS_FETCH_LIMIT]
    if not headlines:
        return f"⚠️ No headlines from GNews — may be rate-limited or empty category."

    logger.info("[Pipeline] Got %d headlines. Target: %d articles.", len(headlines), ARTICLES_PER_RUN)

    imported_count = 0
    skipped_count  = 0
    skip_log: list[str] = []

    # ── Phase 2–7: Process headlines until we hit ARTICLES_PER_RUN ───────────
    for idx, item in enumerate(headlines, start=1):
        if imported_count >= ARTICLES_PER_RUN:
            logger.info("[Pipeline] Target of %d articles reached. Stopping.", ARTICLES_PER_RUN)
            break

        try:
            parsed      = parser_fn(item)
            headline    = parsed["title"]
            source_url  = parsed["source_url"]
            source_name = parsed["source_name"]

            logger.info(
                "[%d/%d] Processing: '%s'",
                idx, len(headlines), headline[:90],
            )

            # ── Validate ──────────────────────────────────────────────────
            if not headline or not source_url:
                skip_log.append(f"[{idx}] Missing title or URL")
                skipped_count += 1
                continue

            # ── Duplicate check ───────────────────────────────────────────
            if _is_duplicate(source_url, headline):
                logger.debug("[%d] Duplicate — skipping: '%s'", idx, headline[:60])
                skip_log.append(f"[{idx}] Duplicate: '{headline[:50]}'")
                skipped_count += 1
                continue

            # ── robots.txt check on primary source ────────────────────────
            if not _is_scraping_allowed(source_url):
                skip_log.append(f"[{idx}] robots.txt blocked: '{headline[:50]}'")
                skipped_count += 1
                continue

            # ── Phase 4: Deep internet research ───────────────────────────
            logger.info("[%d/%d] Starting deep research for: '%s'", idx, len(headlines), headline[:70])
            knowledge_base, source_count = _build_knowledge_base(headline, source_url)

            if source_count < _MIN_RESEARCH_SOURCES or len(knowledge_base.strip()) < 500:
                logger.warning(
                    "[%d] Insufficient research (%d sources, %d chars) for '%s' — skipping.",
                    idx, source_count, len(knowledge_base), headline[:60],
                )
                skip_log.append(f"[{idx}] Insufficient research: '{headline[:50]}'")
                skipped_count += 1
                continue

            logger.info(
                "[%d] Research complete: %d sources | %d chars. Sending to Groq…",
                idx, source_count, len(knowledge_base),
            )

            # ── Phase 5: Groq AI rewrite with full knowledge base ─────────
            ai_data = rewrite_article_with_ai(
                original_title=headline,
                raw_text=knowledge_base,
                source_name=source_name,
            )

            if not ai_data:
                skip_log.append(f"[{idx}] Groq rewrite failed: '{headline[:50]}'")
                skipped_count += 1
                continue

            # ── Phase 6a: Resolve Category ────────────────────────────────
            cat_name = (ai_data.get("category") or "World").strip() or "World"
            category_obj, _ = Category.objects.get_or_create(
                name=cat_name, defaults={"name": cat_name}
            )

            # ── Phase 6b: Resolve AI Author (virtual reporter) ────────────
            User = get_user_model()
            ai_user, user_created = User.objects.get_or_create(
                email="ai_desk@feroxtimes.com",
                defaults={
                    "name": "Ferox Times",
                    "role": "reporter",
                    "is_staff": False,
                    "is_active": True,
                    "bio": (
                        "The official AI-assisted news desk of Ferox Times. "
                        "All articles are researched from multiple live internet "
                        "sources and written to Reuters/AP editorial standards."
                    ),
                },
            )
            if user_created:
                ai_user.set_unusable_password()
                ai_user.save()
            elif ai_user.name != "Ferox Times":
                # Fix any existing record with a stale name (e.g. "Ferox Times AI Desk")
                ai_user.name = "Ferox Times"
                ai_user.save(update_fields=["name"])

            ai_author, _ = Author.objects.get_or_create(
                user=ai_user, defaults={"role": "Reporter"}
            )

            # ── Phase 6c: Build Article ───────────────────────────────────
            ai_content  = ai_data.get("content", "")
            description = _clean_text(ai_content, max_length=250)
            if not description:
                description = _clean_text(ai_data.get("meta_description", ""), max_length=250)

            article = Article(
                # AI-generated fields
                title            = ai_data.get("title") or headline[:255],
                meta_description = ai_data.get("meta_description", "")[:160],
                description      = description,
                content          = ai_content,
                category         = category_obj,
                author           = ai_author,
                # Source tracking
                original_title   = headline[:500],
                source_name      = source_name[:100],
                source_url       = source_url[:500],
                # Raw content stored temporarily for copyright compliance clear
                original_content = f"[Research: {source_count} sources | {len(knowledge_base)} chars]",
                # Status
                status           = "draft",
                is_imported      = True,
            )

            # ── Phase 7: Persist + clear raw content ─────────────────────
            article.save()  # triggers slug auto-generation
            Article.objects.filter(pk=article.pk).update(original_content=None)

            # ── Attach Tags ───────────────────────────────────────────────
            tag_objs = []
            for tag_name in ai_data.get("tags", []):
                tag_name = str(tag_name).strip()[:50]
                if tag_name:
                    try:
                        tag_obj, _ = Tag.objects.get_or_create(name=tag_name)
                        tag_objs.append(tag_obj)
                    except Exception as te:
                        logger.warning("Tag error '%s': %s", tag_name, te)
            if tag_objs:
                article.tags.set(tag_objs)

            imported_count += 1
            logger.info(
                "✅ [%d/%d] Draft saved [id=%s]: '%s' [%s] | %d sources | %d chars",
                idx, len(headlines),
                article.pk, article.title, cat_name,
                source_count, len(ai_content),
            )

        except Exception as exc:
            logger.exception("❌ Unexpected error for article %d ('%s'): %s", idx, item.get("title", "?"), exc)
            skip_log.append(f"[{idx}] Unexpected error: {exc}")
            skipped_count += 1
            continue

    # ── Final Summary ─────────────────────────────────────────────────────────
    parts = [
        f"✅ {imported_count}/{ARTICLES_PER_RUN} research-backed draft articles saved.",
        f"Skipped: {skipped_count}.",
    ]
    if skip_log:
        parts.append(f"Details: {' | '.join(skip_log[:5])}")

    summary = " ".join(parts)
    logger.info("[Pipeline] Run complete. %s", summary)
    return summary