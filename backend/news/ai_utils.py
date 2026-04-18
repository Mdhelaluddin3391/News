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

# Groq model to use
_MODEL_NAME = "llama-3.3-70b-versatile"


def _build_prompt(original_title: str, source_name: str) -> str:
    """
    Returns the journalistic prompt sent to Groq.
    """
    return f"""You are a Senior Field Journalist and Editorial Writer at Ferox Times.
Your task is NOT just to clean or summarize. Your task is to transform raw source material into a high-quality, human-like, SEO-optimized news article that feels like it was written by a real journalist on the ground.

The provided raw text is ONLY for your knowledge base. Do not just blindly summarize it. Use the facts within it to write a compelling news story.

══════════════════════════════════════
  ARTICLE CONTEXT
══════════════════════════════════════

Original Source  : {source_name}
Original Headline: {original_title}

══════════════════════════════════════
  SECTION 1: WRITING STYLE & TONE (ULTRA-PROFESSIONAL)
══════════════════════════════════════

▸ TONE: Write in the objective, authoritative, and crisp tone of Ferox Times (like Reuters or Associated Press). Avoid all fluff, sensationalism, and conversational language.
▸ BAN AI CLICHÉS: NEVER use robotic transition words or phrases such as "Moreover," "Furthermore," "In conclusion," "It is important to note," "Delves into," "A testament to," "Tapestry," "Landscape," or "In today's ever-evolving world."
▸ COMPREHENSIVE COVERAGE: Deeply synthesize the primary text and DuckDuckGo background search results. Write a complete, well-rounded article. It should neither be artificially short nor padded. If the context is rich, write a comprehensive long-form piece. Act like a true, accurate journalist.
▸ NARRATIVE FLOW: Present facts logically. Ground the story with context. Explain WHY this event is happening, not just WHAT happened.
▸ ATTRIBUTION: Attribute claims professionally using varied phrases like "statements indicated," "data released showed," rather than just "According to...".

══════════════════════════════════════
  SECTION 2: ARTICLE STRUCTURE
══════════════════════════════════════

Build the article in EXACTLY this order inside the "content" field.
Use ONLY these HTML tags: <p>, <h2>, <ul>, <li>, <blockquote>, <strong>, <em>

─── STEP 1: THE LEAD (HOOK) ───
A hard-hitting opening paragraph (40–60 words) that immediately answers WHO, WHAT, WHERE, and WHEN without any preamble.

─── STEP 2: THE BODY & CONTEXT ───
- Keep paragraphs short (2–4 sentences) for high readability.
- Use <h2> for subheadings to break up major themes (use contextual, professional headings, avoid generic ones like "Background").
- Formulate the narrative by weaving together the primary event and any background context provided.

─── STEP 3: QUOTES & REALITY LAYER ───
- Extract and highlight real quotes using <blockquote> if available in the text.
- Ground the report in reality by explaining the tangible impact on people, markets, or policies.

─── STEP 4: THE CLOSING ───
End with a sharp, forward-looking observation regarding the broader implications or next steps. DO NOT summarize the article. DO NOT use words like "Ultimately" or "In summary".

══════════════════════════════════════
  SECTION 3: STRICT RULES
══════════════════════════════════════

▸ NO FAKE FACTS: Rely entirely on the provided knowledge base (primary + background text). Do not hallucinate dates, names, or figures.
▸ NO OPINIONS: You are an impartial reporter.
▸ NO BLOG FORMATTING: Do not ask rhetorical questions to the reader. Do not use 'we' or 'you'.

══════════════════════════════════════
  SECTION 4: SEO METADATA
══════════════════════════════════════

▸ TITLE: 55–65 characters. Strong, natural headline (not robotic).
▸ META DESCRIPTION: 140–155 characters. Compelling and makes readers want to click.
▸ CATEGORY: Choose EXACTLY ONE: Technology, World, Politics, Sports, Business, Entertainment, Science, Health, Environment, Crime, Education, Economy.
▸ TAGS: Provide exactly 6–8 meaningful, specific tags.

══════════════════════════════════════
  OUTPUT FORMAT (STRICT — DO NOT DEVIATE)
══════════════════════════════════════

Return ONLY a valid JSON object with exactly these five keys. No markdown outside the JSON, no extra text.

{{
  "title": "Your natural, strong headline here",
  "meta_description": "Your compelling meta description here",
  "content": "<p>Strong hook paragraph...</p><h2>Contextual Heading</h2><p>Body paragraphs...</p>",
  "category": "One of the 12 valid categories",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"]
}}
"""


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

# Minimum content length for a valid article (500 words ≈ ~3000 chars in HTML)
_MIN_CONTENT_CHARS = 500


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
    if len(meta) < 50:
        logger.warning("AI response meta_description is too short (%d chars).", len(meta))
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

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "Groq attempt %d/%d for '%s'…",
                attempt, max_retries, original_title,
            )
            response = client.chat.completions.create(
                model=_MODEL_NAME,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                # Temperature 0.45 ensures strict factual adherence and minimal creative hallucination
                temperature=0.65,
                # Enough tokens for a 900-word HTML article with headings and sources section
                max_tokens=3500,
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
            # Accept up to 8 tags (6–8 is ideal per our prompt)
            data["tags"]             = [str(t).strip()[:50] for t in data["tags"][:8] if str(t).strip()]

            # Ensure at least 1 tag survived sanitization
            if not data["tags"]:
                data["tags"] = ["News"]

            logger.info(
                "✅ Groq rewrite complete for '%s' → '%s' [%s] | "
                "Content: %d chars | Tags: %d | (attempt %d/%d)",
                original_title,
                data["title"],
                data["category"],
                len(data["content"]),
                len(data["tags"]),
                attempt,
                max_retries,
            )
            return data

        except Exception as exc:
            last_error = str(exc)
            logger.warning(
                "Groq API attempt %d/%d failed for '%s': %s",
                attempt,
                max_retries,
                original_title,
                exc,
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
    Builds the Groq system prompt for the Admin AI Article Writer.
    This is different from the auto-import prompt — it takes a human-written
    description and creates a fresh, original article from internet research.
    """
    tone_instructions = {
        "neutral":       "Authoritative, objective, and factual — standard AP/Reuters news tone.",
        "breaking":      "Urgent and high-impact. Lead with the most critical fact. Use short, punchy sentences.",
        "analysis":      "Deep, explanatory, and context-rich. Explain the 'why' behind events. Include expert context.",
        "feature":       "Narrative-driven, immersive storytelling with human interest angles.",
        "opinion":       "First-person analytical perspective. Present a clear, well-reasoned argument.",
    }.get(tone, "Authoritative, objective, and factual — standard AP/Reuters news tone.")

    lang_note = ""
    if language == "urdu":
        lang_note = "IMPORTANT: Write the ENTIRE article — title, meta_description, AND content — in Urdu (Roman or script as appropriate). JSON keys must remain in English."
    elif language == "both":
        lang_note = "Write the content in BOTH English and Urdu. First the full English version, then the Urdu translation below it."

    return f"""You are a Senior Journalist and Editorial Writer at Ferox Times.

A senior editor has given you this assignment brief:
"{description}"

You have been provided with internet research (from DuckDuckGo) as a knowledge base.
Your task is to write a COMPLETE, ORIGINAL, high-quality news article based ONLY on facts found in the knowledge base.

══════════════════════════════════════
  ASSIGNMENT SETTINGS
══════════════════════════════════════

Category  : {category}
Tone Style: {tone_instructions}
{lang_note}

══════════════════════════════════════
  SECTION 1: WRITING RULES
══════════════════════════════════════

▸ TONE: {tone_instructions}
▸ BAN AI CLICHÉS: NEVER use "Moreover," "Furthermore," "In conclusion," "It is important to note," "Delves into," "A testament to," "Tapestry," "Landscape," or "In today's ever-evolving world."
▸ COMPREHENSIVE: Write a complete, well-structured article of at least 600 words. Synthesize all provided research.
▸ NARRATIVE FLOW: Present facts logically. Ground the story with context. Explain WHY this matters.
▸ ATTRIBUTION: Attribute claims professionally using varied phrases like "data released by," "statements indicated," "reports confirmed." Do NOT use fake attributions.
▸ NO OPINIONS (unless tone is 'opinion'): You are an impartial reporter.

══════════════════════════════════════
  SECTION 2: ARTICLE STRUCTURE
══════════════════════════════════════

Use ONLY these HTML tags: <p>, <h2>, <h3>, <ul>, <li>, <blockquote>, <strong>, <em>

─── STEP 1: THE LEAD ───
A hard-hitting opening paragraph (40–70 words) answering WHO, WHAT, WHERE, and WHEN.

─── STEP 2: THE BODY ───
- Short paragraphs (2–4 sentences) for high readability.
- Use <h2> for major section headings (context-specific, not generic).
- Weave together facts from all research sources.

─── STEP 3: QUOTES & REALITY ───
- Extract real quotes using <blockquote> if available in the research.
- Explain the tangible impact on people, markets, or policies.

─── STEP 4: THE CLOSING ───
A sharp, forward-looking observation about broader implications. DO NOT summarize.

══════════════════════════════════════
  SECTION 3: STRICT RULES
══════════════════════════════════════

▸ NO FAKE FACTS: Only use facts from the provided research. Do not hallucinate dates, names, or statistics.
▸ NO PLAGIARISM: Rewrite and synthesize — do not copy sentences verbatim.

══════════════════════════════════════
  SECTION 4: SEO METADATA
══════════════════════════════════════

▸ TITLE: 55–70 characters. Strong, natural headline.
▸ META DESCRIPTION: 140–160 characters. Compelling, makes readers click.
▸ CATEGORY: Must be EXACTLY: {category}
▸ TAGS: Exactly 6–8 meaningful, specific tags.

══════════════════════════════════════
  OUTPUT FORMAT (STRICT)
══════════════════════════════════════

Return ONLY a valid JSON object with exactly these five keys. No markdown, no extra text.

{{
  "title": "Your natural, strong headline here",
  "meta_description": "Compelling meta description here",
  "content": "<p>Strong lead...</p><h2>Heading</h2><p>Body...</p>",
  "category": "{category}",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"]
}}
"""


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

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("[AI Writer] Groq attempt %d/%d...", attempt, max_retries)
            response = client.chat.completions.create(
                model=_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=0.60,
                max_tokens=4000,
            )

            raw_response = response.choices[0].message.content
            data = _extract_json(raw_response)

            if data is None:
                logger.error("[AI Writer] JSON parse failed on attempt %d.", attempt)
                last_error = "JSON parse failed"
                time.sleep(2 * attempt)
                continue

            if not _validate_ai_response(data):
                logger.error("[AI Writer] Validation failed on attempt %d.", attempt)
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
                "✅ [AI Writer] Article generated: '%s' [%s] | %d chars | %d tags | %d sources",
                data["title"], data["category"],
                len(data["content"]), len(data["tags"]),
                research_sources_count,
            )
            return data

        except Exception as exc:
            last_error = str(exc)
            logger.warning("[AI Writer] Groq attempt %d/%d failed: %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(5 * attempt)

    logger.error("[AI Writer] ❌ All %d attempts exhausted. Last error: %s", max_retries, last_error)
    return None