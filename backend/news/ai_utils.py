"""
ai_utils.py — Google Gemini AI rewriting utility for automated news import.

Flow:
  raw_text (scraped by newspaper3k)
      ↓
  rewrite_article_with_ai()
      ↓ (Gemini 1.5 Flash, JSON mode)
  dict with keys: title, meta_description, content, category, tags
"""

import os
import json
import re
import logging

import google.generativeai as genai

logger = logging.getLogger(__name__)

# ─── Initialise Gemini once at module load ─────────────────────────────────
_GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if _GEMINI_KEY:
    genai.configure(api_key=_GEMINI_KEY)
else:
    logger.warning("GEMINI_API_KEY is not set — AI rewriting will be disabled.")


# ─── Prompt ────────────────────────────────────────────────────────────────
def _build_prompt(original_title: str, source_name: str) -> str:
    """
    Returns the system-level INSTRUCTION part of the prompt.

    Design decisions:
    • We use a single contents[] list (instruction + raw text) so that when
      response_mime_type='application/json' is set, Gemini treats the whole
      exchange as a JSON generation task.
    • We embed the JSON schema directly in the prompt so the model can never
      claim it doesn't know the expected structure.
    • Temperature 0.4 balances creativity with factual fidelity.
    """
    return f"""You are a Senior Journalistic Editor working for a professional news portal.
Your mission is to transform the provided raw scraped article into a completely original,
engaging, and SEO-optimised piece — while being 100% faithful to the facts in the source text.

── Context ──────────────────────────────────────────────────────────────────
Original Source  : {source_name}
Original Headline: {original_title}

── Rules ────────────────────────────────────────────────────────────────────
1. PLAGIARISM-FREE — Rewrite entirely in your own professional, neutral, journalistic voice.
   Do NOT copy sentences verbatim from the raw text.
2. NO HALLUCINATION — Do NOT introduce facts, quotes, statistics, or context that are
   not present in the raw article text below.
3. HTML CONTENT — Write the `content` field as clean, semantic HTML using only these tags:
   <p>, <h2>, <h3>, <ul>, <li>, <blockquote>, <strong>, <em>.
   • No <html>, <head>, <body>, <style>, or <script> tags.
   • No Markdown (no **, no ##, no ```).
   • Use <h2> for sub-headings and <p> for paragraphs.
   • Wrap notable quotes or pull-quotes in <blockquote>.
   Minimum 3 paragraphs.
4. SEO TITLE — Write a catchy `title` that is concise (40-70 characters), uses active
   voice, includes a primary keyword, and reads naturally.
5. META DESCRIPTION — Write a compelling `meta_description` (120-155 characters) that
   summarises the article and encourages clicks.
6. CATEGORY — Suggest exactly 1 broad `category` from this fixed list:
   Technology, World, Politics, Sports, Business, Entertainment, Science,
   Health, Environment, Crime, Education, Economy.
7. TAGS — Suggest between 3 and 5 specific, lowercase, hyphen-free `tags`
   (e.g. "Artificial Intelligence", "US Elections", "Indian Economy").

── Output Format ────────────────────────────────────────────────────────────
Respond ONLY with a single valid JSON object — no markdown fences, no explanation text.
The JSON MUST match this exact schema:

{{
  "title":            "<string: SEO headline, 40-70 chars>",
  "meta_description": "<string: SEO meta, 120-155 chars>",
  "content":          "<string: full HTML article body>",
  "category":         "<string: one of the 12 categories above>",
  "tags":             ["<string>", "<string>", "<string>"]
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


def _validate_ai_response(data: dict) -> bool:
    """
    Ensures the parsed dict has all required keys with non-empty values
    and that `tags` is a list with at least one entry.
    """
    if not isinstance(data, dict):
        return False
    if not _REQUIRED_KEYS.issubset(data.keys()):
        missing = _REQUIRED_KEYS - data.keys()
        logger.warning("AI response missing keys: %s", missing)
        return False
    if not data.get("title") or not data.get("content"):
        return False
    if not isinstance(data.get("tags"), list) or len(data["tags"]) == 0:
        logger.warning("AI response has invalid or empty tags list.")
        return False
    return True


# ─── Public API ────────────────────────────────────────────────────────────
def rewrite_article_with_ai(
    original_title: str,
    raw_text: str,
    source_name: str,
) -> dict | None:
    """
    Sends the raw scraped article text to Gemini 1.5 Flash and returns a dict
    containing the AI-rewritten article data.

    Parameters
    ----------
    original_title : str   — The headline fetched from the news API.
    raw_text       : str   — Full scraped body text from newspaper3k.
    source_name    : str   — Publisher name (e.g. "BBC News"), used in the prompt.

    Returns
    -------
    dict | None
        On success: {"title", "meta_description", "content", "category", "tags"}
        On any failure: None  (caller should skip the article gracefully)
    """
    if not _GEMINI_KEY:
        logger.error("Cannot call Gemini — GEMINI_API_KEY is not configured.")
        return None

    if not raw_text or len(raw_text.strip()) < 100:
        logger.warning(
            "Skipping AI rewrite for '%s' — scraped text too short (%d chars).",
            original_title,
            len(raw_text) if raw_text else 0,
        )
        return None

    # Truncate to avoid exceeding context window / cost limits
    # Gemini 1.5 Flash supports ~1M tokens, but 8000 chars is plenty for a news article
    truncated_text = raw_text[:8000]

    instruction = _build_prompt(original_title, source_name)
    user_content = f"Raw Article Text to Rewrite:\n\n{truncated_text}"

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            contents=[instruction, user_content],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.4,
                max_output_tokens=2048,
            ),
        )

        raw_response_text = response.text
        data = _extract_json(raw_response_text)

        if data is None:
            logger.error(
                "Could not extract JSON from Gemini response for '%s'. Raw: %s",
                original_title,
                raw_response_text[:500],
            )
            return None

        if not _validate_ai_response(data):
            logger.error(
                "Gemini response for '%s' failed validation. Data: %s",
                original_title,
                data,
            )
            return None

        # Enforce field length constraints to prevent DB errors
        data["title"] = data["title"][:250]
        data["meta_description"] = data["meta_description"][:160]
        data["category"] = data["category"][:100]
        data["tags"] = [str(t)[:50] for t in data["tags"][:5]]  # max 5 tags, 50 chars each

        logger.info(
            "✅ Gemini rewrite complete for '%s' → '%s' [%s]",
            original_title,
            data["title"],
            data["category"],
        )
        return data

    except Exception:
        logger.exception(
            "Gemini API call raised an exception for article '%s'.", original_title
        )
        return None