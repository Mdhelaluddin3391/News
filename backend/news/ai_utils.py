"""
ai_utils.py — Groq AI rewriting utility for automated news import.
                Also powers the Admin AI Article Writer (generate_article_from_prompt).

Flow:
  raw_text (scraped by newspaper3k)
      ↓
  rewrite_article_with_ai()
      ↓ (Groq LLM, JSON mode)
  dict with keys: title, meta_description, content, category, tags

Key Features:
   Transforms raw data into high-quality, human-like journalism.
   Adapts length based on source material to produce a well-rounded article.
   Strong narrative flow with human context and significance.
   Strict adherence to factual accuracy (no fake facts).
"""

import os
import json
import re
import logging
import time

from groq import Groq

logger = logging.getLogger(__name__)

# ─── Initialise Groq once at module load ─────────────────────────────────
_GROQ_KEY = os.getenv("GROQ_API_KEY")
if not _GROQ_KEY:
    logger.warning("GROQ_API_KEY is not set — AI rewriting will be disabled.")

# Groq model strategy: Primary (high quality) → Fallback (high rate limit)
# llama-3.3-70b-versatile: 100k tokens/day free (better quality)
# llama-3.1-8b-instant:    500k tokens/day free (faster, great fallback)
_MODEL_PRIMARY  = "llama-3.3-70b-versatile"
_MODEL_FALLBACK = "llama-3.1-8b-instant"
_MODEL_NAME = _MODEL_PRIMARY  # Default (used in rewrite_article_with_ai)


def _build_prompt(original_title: str, source_name: str) -> str:
    """
    Returns the master journalistic prompt for the Auto-Import pipeline.
    Engineered to produce AP/Reuters-standard news articles.
    """
    return (
        "You are a veteran Senior Correspondent at Ferox Times, a global news publication.\n"
        "held to the same editorial standards as Reuters, AP, and the BBC.\n\n"
        f"SOURCE: {source_name}\n"
        f"HEADLINE: {original_title}\n\n"
        "You have been given raw source text and DuckDuckGo background research.\n"
        "Write a COMPLETE, ORIGINAL, PUBLICATION-READY news article.\n\n"
        "EDITORIAL RULES (non-negotiable):\n"
        "- Write in third person. Never use you/we/our.\n"
        "- Every sentence must carry new information. No padding.\n"
        "- Vary sentence length: short for impact, longer for causality.\n"
        "- First word of the article must be a proper noun or number, never A/The/In.\n"
        "- BANNED PHRASES: Moreover, Furthermore, Additionally, In conclusion, To summarize,\n"
        "  It is important to note, Needless to say, Delves into, A testament to,\n"
        "  Tapestry, Landscape, Ecosystem, Groundbreaking, Game-changing, Cutting-edge,\n"
        "  Robust, Shed light on, Pave the way, Paradigm shift, Holistic, Synergy,\n"
        "  In today's world, In the modern era, Ever-evolving, Unprecedented (unless citing the precedent).\n"
        "- ATTRIBUTION: Rotate phrases: officials said, data showed, the filing indicated,\n"
        "  statements confirmed, the announcement read, records showed, sources said.\n\n"
        "ARTICLE STRUCTURE (7 blocks, minimum 650 words of readable content):\n"
        "Use ONLY these HTML tags: <p> <h2> <h3> <ul> <li> <blockquote> <strong> <em>\n\n"
        "BLOCK 1 - THE LEAD (no heading): 45-65 words. WHO+WHAT+WHERE+WHEN+WHY NOW.\n"
        "  First word = proper noun or number. No dependent clauses before main clause.\n\n"
        "BLOCK 2 - NUT GRAF (no heading): 1-2 sentences. The so-what for an uninformed reader.\n\n"
        "BLOCK 3 - THE DEVELOPMENT (no heading): 3-4 paragraphs. Logical factual narrative.\n"
        "  Each paragraph = one complete idea. Use <strong> max once for the single most critical figure.\n\n"
        "BLOCK 4 - CONTEXT AND HISTORY (mandatory <h2>, specific heading): 2-3 paragraphs.\n"
        "  Place event in historical/legal/economic context. Heading must be story-specific.\n\n"
        "BLOCK 5 - HUMAN STAKES AND IMPACT (mandatory <h2>, specific heading): Who is affected and how?\n"
        "  Use concrete numbers. Real quotes in <blockquote> if available.\n\n"
        "BLOCK 6 - OFFICIAL RESPONSES (mandatory <h2>, specific heading): Key stakeholder positions.\n"
        "  Include at least one countervailing perspective if relevant.\n\n"
        "BLOCK 7 - ROAD AHEAD (mandatory <h2>, specific heading): 2 paragraphs.\n"
        "  Grounded in upcoming events, dates, hearings, or deadlines from the research.\n"
        "  Final sentence: one sharp factual observation about the broader implication.\n\n"
        "SEO METADATA:\n"
        "- TITLE: 58-68 characters. Specific: include a name, number, or place. No clickbait.\n"
        "  Good: Pakistan Raises Interest Rate to 22 Percent Amid IMF Pressure\n"
        "  Bad: Shocking Decision Rocks Pakistan Economy\n"
        "- META DESCRIPTION: 148-160 characters. Extends headline with second key fact. Active voice.\n"
        "- CATEGORY: Exactly one of: Technology, World, Politics, Sports, Business,\n"
        "  Entertainment, Science, Health, Environment, Crime, Education, Economy\n"
        "- TAGS: Exactly 7 tags, title-cased, max 4 words each.\n"
        "  2 broad topic tags, 2 named entity tags, 2 issue/event tags, 1 type tag.\n"
        "  Type tag must be one of: Breaking News, Analysis, Report, Feature, Investigation\n\n"
        "OUTPUT: Return ONLY a valid JSON object with exactly these five keys.\n"
        "No markdown fences. No preamble. No explanation. Pure JSON only.\n\n"
        "{{\n"
        '  \"title\": \"Specific fact-based headline 58-68 chars\",\n'
        '  \"meta_description\": \"Expanded detail, active voice, 148-160 chars.\",\n'
        '  \"content\": \"<p>Lead...</p><h2>Context Heading</h2><p>...</p>\",\n'
        '  \"category\": \"One valid category\",\n'
        '  \"tags\": [\"Broad Topic\", \"Named Entity\", \"Named Entity 2\", \"Issue\", \"Event\", \"Second Issue\", \"Report\"]\n'
        "}}"
    )



# ─── JSON extraction helper ────────────────────────────────────────────────
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_json(text: str) -> dict | None:
    """
    Tries multiple strategies to extract a valid JSON object from model output:
    1. Direct json.loads (model returned clean JSON).
    2. Strip a markdown ```json … ``` code fence.
    3. Find the first '{' … last '}' substring.
    Returns None if all strategies fail.
    """
    text = text.strip()

    # Strategy 1 — clean JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2 — markdown fence
    match = _JSON_BLOCK_RE.search(text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3 — substring between first { and last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


# ─── Validation helper ─────────────────────────────────────────────────────
_REQUIRED_KEYS = {"title", "meta_description", "content", "category", "tags"}
_VALID_CATEGORIES = {
    "Technology", "World", "Politics", "Sports", "Business",
    "Entertainment", "Science", "Health", "Environment",
    "Crime", "Education", "Economy",
}

# Minimum content length for a valid article (500 words ≈ ~1500 chars in HTML)
_MIN_CONTENT_CHARS = 1500


def _validate_ai_response(data: dict) -> bool:
    """
    Ensures the parsed dict has all required keys with non-empty values,
    valid category, and tags as a non-empty list.

    Also performs basic newsroom-standard checks:
    - Content length checks

    Raises a descriptive warning for each failure instead of a generic message.
    """
    if not isinstance(data, dict):
        logger.warning("AI response is not a dict — got: %s", type(data))
        return False

    if not _REQUIRED_KEYS.issubset(data.keys()):
        missing = _REQUIRED_KEYS - data.keys()
        logger.warning("AI response missing required keys: %s", missing)
        return False

    title = str(data.get("title", "")).strip()
    if len(title) < 10:
        logger.warning("AI response has missing or too-short title (got: '%s').", title)
        return False

    content = str(data.get("content", "")).strip()
    if len(content) < _MIN_CONTENT_CHARS:
        logger.warning(
            "AI response content is too short (%d chars, minimum %d). "
            "This usually means the AI did not fully follow the prompt.",
            len(content),
            _MIN_CONTENT_CHARS,
        )
        return False

    meta = str(data.get("meta_description", "")).strip()
    if len(meta) < 100:
        logger.warning("AI response meta_description is too short (%d chars, SEO needs >=100).", len(meta))
        return False

    if not isinstance(data.get("tags"), list) or len(data["tags"]) < 3:
        logger.warning(
            "AI response has invalid or insufficient tags list (got: %s).",
            data.get("tags"),
        )
        return False

    # Auto-correct invalid category to "World" instead of hard-failing
    if data.get("category") not in _VALID_CATEGORIES:
        logger.warning(
            "AI returned invalid category '%s' — defaulting to 'World'.",
            data.get("category"),
        )
        data["category"] = "World"

    return True


# ─── Public API ────────────────────────────────────────────────────────────
def rewrite_article_with_ai(
    original_title: str,
    raw_text: str,
    source_name: str,
    max_retries: int = 3,
) -> dict | None:
    """
    Sends the raw scraped article text to Groq and returns a dict
    containing the AI-rewritten, SEO-optimised, newsroom-standard article data.

    Uses a strict journalistic prompt engineered to:
    - Act as a copy-editor, extracting and cleaning text without expanding artificially.
    - Enforce strict Reuters/AP editorial standards (no blog/AI/emotional language, no fake attribution).
    - Produce a strong WHO/WHAT/WHERE/WHEN lead paragraph in 40–60 words.

    Parameters
    ----------
    original_title : str   — The headline fetched from the news API.
    raw_text       : str   — Full scraped body text from newspaper3k.
    source_name    : str   — Publisher name (e.g. "BBC News"), used in the prompt.
    max_retries    : int   — Number of times to retry on transient Groq errors (default: 3).

    Returns
    -------
    dict | None
        On success: {"title", "meta_description", "content", "category", "tags"}
        On any failure: None  (caller should skip the article gracefully)
    """
    if not _GROQ_KEY:
        logger.error("Cannot call Groq — GROQ_API_KEY is not configured.")
        return None

    if not raw_text or len(raw_text.strip()) < 100:
        logger.warning(
            "Skipping AI rewrite for '%s' — scraped text too short (%d chars).",
            original_title,
            len(raw_text) if raw_text else 0,
        )
        return None

    # Truncate to avoid exceeding context window (~12k chars is safe for llama-3.3-70b)
    truncated_text = raw_text[:12000]

    instruction = _build_prompt(original_title, source_name)
    user_content = (
        f"Raw Article Text to Transform:\n\n"
        f"---\n{truncated_text}\n---\n\n"
        f"REMINDER: Your output MUST:\n"
        f"1. Have a lead paragraph (40–60 words) answering WHO, WHAT, WHERE, WHEN\n"
        f"2. NARRATIVE FLOW: Write a compelling story with human context.\n"
        f"3. NO FAKE FACTS: Do not invent names, dates, or events. Stick to the source facts.\n"
        f"Return ONLY the JSON object — no preamble, no markdown, no explanation."
    )

    last_error = None
    client = Groq(api_key=_GROQ_KEY)

    # Model selection: try primary first, fallback on rate limit (429)
    models_to_try = [_MODEL_PRIMARY, _MODEL_FALLBACK]
    used_model = _MODEL_PRIMARY

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "Groq attempt %d/%d for '%s' [model=%s]…",
                attempt, max_retries, original_title, used_model,
            )
            response = client.chat.completions.create(
                model=used_model,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.40,
                max_tokens=4000,
            )

            raw_response_text = response.choices[0].message.content
            data = _extract_json(raw_response_text)

            if data is None:
                logger.error(
                    "Could not extract JSON from Groq response for '%s'. Raw (first 500 chars): %s",
                    original_title,
                    raw_response_text[:500],
                )
                last_error = "JSON parse failed"
                time.sleep(2 * attempt)
                continue

            if not _validate_ai_response(data):
                logger.error(
                    "Groq response for '%s' failed validation on attempt %d. "
                    "Content length: %d chars. Category: '%s'. Tags count: %d.",
                    original_title,
                    attempt,
                    len(str(data.get("content", ""))),
                    data.get("category"),
                    len(data.get("tags", [])) if isinstance(data.get("tags"), list) else 0,
                )
                last_error = "Validation failed"
                time.sleep(3 * attempt)
                continue

            # ── Enforce field length constraints to prevent DB errors ──────
            data["title"]            = str(data["title"]).strip()[:250]
            data["meta_description"] = str(data["meta_description"]).strip()[:160]
            data["category"]         = str(data["category"]).strip()[:100]
            data["tags"]             = [str(t).strip()[:50] for t in data["tags"][:8] if str(t).strip()]

            if not data["tags"]:
                data["tags"] = ["News"]

            logger.info(
                "✅ Groq rewrite complete for '%s' → '%s' [%s] | "
                "Content: %d chars | Tags: %d | model=%s | (attempt %d/%d)",
                original_title,
                data["title"],
                data["category"],
                len(data["content"]),
                len(data["tags"]),
                used_model,
                attempt,
                max_retries,
            )
            return data

        except Exception as exc:
            last_error = str(exc)
            error_str = str(exc)

            # ── Rate limit hit → switch to fallback model immediately ──────
            if "429" in error_str and used_model == _MODEL_PRIMARY:
                logger.warning(
                    "[AutoSwitch] Primary model '%s' rate-limited for '%s'. "
                    "Switching to fallback '%s'.",
                    _MODEL_PRIMARY, original_title, _MODEL_FALLBACK,
                )
                used_model = _MODEL_FALLBACK
                time.sleep(2)
                continue  # Retry immediately with fallback model

            logger.warning(
                "Groq API attempt %d/%d failed for '%s' [%s]: %s",
                attempt, max_retries, original_title, used_model, exc,
            )
            if attempt < max_retries:
                backoff = 5 * attempt
                logger.info("Retrying in %ds…", backoff)
                time.sleep(backoff)

    logger.error(
        "❌ All %d Groq attempts exhausted for '%s'. Last error: %s",
        max_retries,
        original_title,
        last_error,
    )
    return None


# ════════════════════════════════════════════════════════════════════════════
#  ADMIN AI ARTICLE WRITER  —  generate_article_from_prompt()
# ════════════════════════════════════════════════════════════════════════════

def _build_writer_prompt(
    description: str,
    category: str,
    tone: str,
    language: str,
) -> str:
    """
    Builds the ultra-professional Groq prompt for the Admin AI Article Writer.
    Takes an editor brief and returns a publication-ready news article.
    """
    tone_map = {
        "neutral":  "Standard news report: objective, factual, third-person. No emotion.",
        "breaking": "Breaking news urgent register: short sentences, present tense, critical fact FIRST.",
        "analysis": "In-depth analytical piece: explain causes and consequences. Use expert framing.",
        "feature":  "Long-form feature: narrative arc, vivid scenes grounded in facts.",
        "opinion":  "Signed editorial: evidence-backed argument. First-person allowed ONLY in this mode.",
    }
    tone_instruction = tone_map.get(tone, tone_map["neutral"])

    lang_block = ""
    if language == "urdu":
        lang_block = (
            "LANGUAGE: Write the ENTIRE article (title, meta_description, AND content) "
            "in Urdu script. JSON keys must remain in English. "
            "Apply the same journalistic standards in Urdu register."
        )
    elif language == "both":
        lang_block = (
            "LANGUAGE: Write the full article TWICE inside content. "
            "First: complete English version. Then <hr>. Then: complete Urdu translation. "
            "Title and meta_description in English only."
        )

    return (
        "You are a 20-year veteran Senior Correspondent and Deputy Editor at Ferox Times, "
        "held to Reuters, AP, BBC and Dawn editorial standards.\n\n"
        f"EDITOR BRIEF: {description}\n\n"
        "You have internet research as your knowledge base.\n"
        "Write a COMPLETE, PUBLICATION-READY article that passes any chief editor without revision.\n\n"
        f"CATEGORY: {category}\n"
        f"TONE: {tone_instruction}\n"
        f"{lang_block}\n\n"
        "THE IRON RULES:\n"
        "- Third person only (unless tone=opinion). Never you/we/our.\n"
        "- Every claim from the research only. Zero hallucination.\n"
        "- State facts. Do not tell reader how to feel.\n"
        "- Every paragraph must add new information or be deleted.\n"
        "- Vary sentence rhythm deliberately.\n"
        "- Numbers make news concrete. Use them: 47 percent not nearly half.\n"
        "- BANNED: Moreover, Furthermore, Additionally, In conclusion, To summarize,\n"
        "  It is important to note, Needless to say, Delves into, A testament to,\n"
        "  Tapestry, Landscape, Ecosystem, Groundbreaking, Game-changing, Cutting-edge,\n"
        "  Robust, Shed light on, Pave the way, Paradigm shift, Holistic, Synergy,\n"
        "  In today's fast-paced world, Ever-evolving, Unprecedented (cite the precedent if using).\n"
        "  Any rhetorical question to reader. Let us explore. As mentioned earlier.\n"
        "- ATTRIBUTION (rotate, never repeat same phrase twice): officials said, data showed,\n"
        "  the filing indicated, statements confirmed, records showed, sources said,\n"
        "  the announcement read, the decision document showed.\n\n"
        "ARTICLE STRUCTURE (7 blocks mandatory, minimum 700 words readable content):\n"
        "HTML tags ONLY: <p> <h2> <h3> <ul> <li> <blockquote> <strong> <em>\n\n"
        "BLOCK 1 - THE LEAD (no heading): 45-65 words. WHO+WHAT+WHERE+WHEN+WHY NOW.\n"
        "  First word must be a proper noun or number. No scene-setting preamble.\n\n"
        "BLOCK 2 - NUT GRAF (no heading): 1-2 sentences. Connects to bigger ongoing story/trend.\n\n"
        "BLOCK 3 - THE DEVELOPMENT (no heading): 3-4 paragraphs. Factual narrative in logical order.\n"
        "  Each paragraph = one complete idea. <strong> on single most critical figure (once only).\n\n"
        "BLOCK 4 - CONTEXT AND HISTORY (mandatory <h2>, story-specific heading NOT generic Background):\n"
        "  2-3 paragraphs. Historical, legal, or economic context. Reader unfamiliar with topic understands fully.\n\n"
        "BLOCK 5 - HUMAN STAKES AND IMPACT (mandatory <h2>, story-specific heading NOT generic Impact):\n"
        "  Who is directly affected and how? Concrete numbers, not vague descriptions.\n"
        "  Real quotes in <blockquote> if available. One <ul> list allowed for 4+ distinct consequences.\n\n"
        "BLOCK 6 - OFFICIAL RESPONSES AND EXPERT ANALYSIS (mandatory <h2>, story-specific heading):\n"
        "  Quote or paraphrase key stakeholders. Include countervailing perspective if relevant.\n\n"
        "BLOCK 7 - THE ROAD AHEAD (mandatory <h2>, story-specific heading NOT generic What Comes Next):\n"
        "  2 paragraphs. Verified upcoming events, dates, hearings, or deadlines from research.\n"
        "  Final sentence: sharp factual observation about broader implication. No moral judgement.\n\n"
        "SEO METADATA:\n"
        "- TITLE: 58-68 characters. Include primary keyword naturally. Specific: name, number, or place.\n"
        "  No sensationalism. No clickbait. No question format.\n"
        "  Good example: IMF Approves 3bn Pakistan Bailout, Demands Fuel Price Hike\n"
        "  Bad example: Shocking Move by IMF Rattles Pakistan Struggling Economy\n"
        "- META DESCRIPTION: 148-160 characters. Extends headline with second most important fact.\n"
        "  Active voice. Complete sentence. No trailing ellipsis.\n"
        f"- CATEGORY: Must be exactly: {category}\n"
        "- TAGS: Exactly 7 tags, title-cased, max 4 words each.\n"
        "  2 broad topic, 2 named entity, 2 issue/event, 1 type tag.\n"
        "  Type tag must be one of: Breaking News, Analysis, Report, Feature, Investigation\n\n"
        "OUTPUT: Return ONLY a valid JSON object with exactly these five keys.\n"
        "No markdown fences. No preamble. No explanation. Pure JSON only.\n\n"
        "{{\n"
        '  \"title\": \"Specific fact-based headline 58-68 chars\",\n'
        '  \"meta_description\": \"Second key fact, active voice, 148-160 chars\",\n'
        '  \"content\": \"<p>Lead...</p><p>Nut graf...</p><h2>Specific Context Heading</h2><p>...</p>\",\n'
        f'  \"category\": \"{category}\",\n'
        '  \"tags\": [\"Broad Topic\", \"Named Entity\", \"Named Entity 2\", \"Issue\", \"Event\", \"Second Issue\", \"Report\"]\n'
        "}}"
    )


def _search_web_for_topic(description: str, max_results: int = 5) -> str:
    """
    Searches DuckDuckGo for the given topic/description and scrapes the
    top results to build a rich research knowledge base for the AI.

    Returns a concatenated string of scraped text from multiple sources.
    """
    import time
    from duckduckgo_search import DDGS
    import requests

    _BOT_UA = "FeroxTimesBot/1.0 (+https://www.feroxtimes.com/about)"
    _SCRAPE_TIMEOUT = 15
    _MIN_TEXT = 150

    def _scrape_url(url: str) -> str:
        """Quick scraper for a single URL."""
        try:
            from newspaper import Article as WebArticle
            wa = WebArticle(url, browser_user_agent=_BOT_UA, request_timeout=_SCRAPE_TIMEOUT)
            wa.download()
            wa.parse()
            text = wa.text or ""
            if len(text.strip()) >= _MIN_TEXT:
                return text.strip()
        except Exception:
            pass

        # Fallback: simple requests + paragraph extraction
        try:
            from html.parser import HTMLParser

            class _PE(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self._in = False; self._paras = []; self._cur = []
                def handle_starttag(self, tag, attrs):
                    if tag == "p": self._in = True; self._cur = []
                def handle_endtag(self, tag):
                    if tag == "p" and self._in:
                        t = "".join(self._cur).strip()
                        if len(t) > 30: self._paras.append(t)
                        self._in = False
                def handle_data(self, data):
                    if self._in: self._cur.append(data)

            r = requests.get(url, headers={"User-Agent": _BOT_UA}, timeout=_SCRAPE_TIMEOUT, allow_redirects=True)
            r.raise_for_status()
            p = _PE(); p.feed(r.text)
            return "\n\n".join(p._paras)
        except Exception:
            return ""

    knowledge_base = ""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(description, max_results=max_results))

        logger.info("[AI Writer] DuckDuckGo returned %d results for: '%s'", len(results), description[:60])

        for i, res in enumerate(results, 1):
            url = res.get("href", "")
            title = res.get("title", "No Title")
            snippet = res.get("body", "")

            if not url:
                continue

            logger.info("[AI Writer] Scraping source %d/%d: %s", i, len(results), url)
            time.sleep(1)  # Polite delay
            body = _scrape_url(url)

            if body and len(body.strip()) > _MIN_TEXT:
                # Truncate each source to 3000 chars to avoid token overflow
                truncated = body[:3000]
                knowledge_base += f"\n\n--- Source {i}: {title} ({url}) ---\n{snippet}\n\n{truncated}\n"
            elif snippet:
                # Fallback: use DuckDuckGo snippet if scraping failed
                knowledge_base += f"\n\n--- Source {i} (snippet only): {title} ---\n{snippet}\n"

    except Exception as exc:
        logger.warning("[AI Writer] DuckDuckGo search failed for '%s': %s", description[:60], exc)

    return knowledge_base.strip()


def generate_article_from_prompt(
    description: str,
    category: str = "World",
    tone: str = "neutral",
    language: str = "english",
    max_retries: int = 3,
) -> dict | None:
    """
    Admin AI Article Writer — Core Engine.

    Takes a human-written description of what kind of article is needed,
    searches the internet for relevant information via DuckDuckGo, and
    generates a complete journalist-style article using Groq AI.

    Parameters
    ----------
    description : str  — What the article should be about (admin's brief).
    category    : str  — Target category (e.g., 'Technology', 'Sports').
    tone        : str  — Writing tone ('neutral', 'breaking', 'analysis', 'feature', 'opinion').
    language    : str  — Output language ('english', 'urdu', 'both').
    max_retries : int  — Number of Groq retry attempts.

    Returns
    -------
    dict | None
        On success: {"title", "meta_description", "content", "category", "tags", "research_sources_count"}
        On failure: None
    """
    if not _GROQ_KEY:
        logger.error("[AI Writer] Cannot generate — GROQ_API_KEY is not configured.")
        return None

    if not description or len(description.strip()) < 10:
        logger.warning("[AI Writer] Description too short — aborting.")
        return None

    # ── Step 1: Internet Research via DuckDuckGo ─────────────────────────────
    logger.info("[AI Writer] Starting internet research for: '%s'", description[:80])
    knowledge_base = _search_web_for_topic(description, max_results=5)

    if not knowledge_base or len(knowledge_base.strip()) < 200:
        logger.warning(
            "[AI Writer] Could not gather sufficient research for '%s'. "
            "Proceeding with description only.",
            description[:60],
        )
        knowledge_base = f"No web results found. Generate the best possible article based on your training knowledge about: {description}"

    research_sources_count = knowledge_base.count("--- Source")
    logger.info("[AI Writer] Research complete — %d sources gathered (%d chars).",
                research_sources_count, len(knowledge_base))

    # ── Step 2: Build Prompt & Call Groq ─────────────────────────────────────
    system_prompt = _build_writer_prompt(description, category, tone, language)
    user_content = (
        f"EDITOR'S BRIEF: {description}\n\n"
        f"══════════════════════════════════════\n"
        f"INTERNET RESEARCH KNOWLEDGE BASE:\n"
        f"(Use ONLY facts from below. Do not hallucinate.)\n"
        f"══════════════════════════════════════\n\n"
        f"{knowledge_base[:14000]}\n\n"
        f"══════════════════════════════════════\n"
        f"REMINDER: Return ONLY valid JSON. Lead paragraph must answer WHO, WHAT, WHERE, WHEN in 40–70 words."
    )

    client = Groq(api_key=_GROQ_KEY)
    last_error = None

    # Model selection: primary (better quality) → fallback (higher rate limit)
    used_model = _MODEL_PRIMARY

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("[AI Writer] Groq attempt %d/%d [model=%s]...", attempt, max_retries, used_model)
            response = client.chat.completions.create(
                model=used_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=0.42,
                max_tokens=4500,
            )

            raw_response = response.choices[0].message.content
            data = _extract_json(raw_response)

            if data is None:
                logger.error("[AI Writer] JSON parse failed on attempt %d.", attempt)
                last_error = "JSON parse failed"
                time.sleep(2 * attempt)
                continue

            if not _validate_ai_response(data):
                logger.error("[AI Writer] Validation failed on attempt %d [model=%s].", attempt, used_model)
                last_error = "Validation failed"
                time.sleep(3 * attempt)
                continue

            # ── Enforce field length constraints ──────────────────────────
            data["title"]            = str(data["title"]).strip()[:250]
            data["meta_description"] = str(data["meta_description"]).strip()[:160]
            data["category"]         = category  # Always use admin-selected category
            data["tags"]             = [str(t).strip()[:50] for t in data.get("tags", [])[:8] if str(t).strip()]
            if not data["tags"]:
                data["tags"] = ["News"]

            # Add metadata for caller
            data["research_sources_count"] = research_sources_count

            logger.info(
                "✅ [AI Writer] Article generated: '%s' [%s] | %d chars | %d tags | %d sources | model=%s",
                data["title"], data["category"],
                len(data["content"]), len(data["tags"]),
                research_sources_count, used_model,
            )
            return data

        except Exception as exc:
            last_error = str(exc)
            error_str = str(exc)

            # ── Rate limit (429) → auto-switch to fallback model ──────────
            if "429" in error_str and used_model == _MODEL_PRIMARY:
                logger.warning(
                    "[AI Writer] Primary model '%s' rate-limited. "
                    "Auto-switching to fallback '%s' (higher limit).",
                    _MODEL_PRIMARY, _MODEL_FALLBACK,
                )
                used_model = _MODEL_FALLBACK
                time.sleep(2)
                continue  # Immediate retry with fallback

            logger.warning("[AI Writer] Groq attempt %d/%d failed [%s]: %s",
                           attempt, max_retries, used_model, exc)
            if attempt < max_retries:
                time.sleep(5 * attempt)

    logger.error("[AI Writer] ❌ All %d attempts exhausted. Last error: %s", max_retries, last_error)
    return None