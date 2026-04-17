"""
ai_utils.py — Groq AI rewriting utility for automated news import.

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