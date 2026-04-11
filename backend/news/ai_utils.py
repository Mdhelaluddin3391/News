"""
ai_utils.py — Groq AI rewriting utility for automated news import.

Flow:
  raw_text (scraped by newspaper3k)
      ↓
  rewrite_article_with_ai()
      ↓ (Groq LLM, JSON mode)
  dict with keys: title, meta_description, content, category, tags

Key Features:
  ✅ Strict neutrality / impartiality enforcement
  ✅ Professional journalistic SEO rewriting
  ✅ Robust fallback if Groq returns partial data
  ✅ Multi-strategy JSON extraction
  ✅ Field-level validation + length capping
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

# ─── Prompt ────────────────────────────────────────────────────────────────
def _build_prompt(original_title: str, source_name: str) -> str:
    """
    Returns the instruction prompt sent to Groq.

    Design decisions:
    • Strict IMPARTIALITY — even if the source article is heavily biased towards
      or against governments, political parties, corporations, or individuals,
      the AI must present BOTH sides and maintain journalistic neutrality.
      This is the same standard used by BBC, Reuters, AP.
    • Response must be a single valid JSON object only.
    • Temperature 0.35 keeps output factual and creative but grounded.
    """
    return f"""You are a Senior Journalistic Editor at a world-class, unbiased news portal.
Your mission is to transform the provided raw scraped article into a completely original,
professional, SEO-optimised, and STRICTLY IMPARTIAL piece.

── Context ──────────────────────────────────────────────────────────────────
Original Source  : {source_name}
Original Headline: {original_title}

── Rules ────────────────────────────────────────────────────────────────────
1. PLAGIARISM-FREE — Rewrite entirely in your own professional journalistic voice.
   Do NOT copy sentences verbatim from the raw text.

2. NO HALLUCINATION — Do NOT introduce any facts, quotes, statistics, or context
   that are NOT present in the raw article text below. Stay strictly faithful to
   the facts provided.

3. STRICT IMPARTIALITY (MOST IMPORTANT) ─────────────────────────────────────
   • You MUST write in a neutral, balanced, and non-partisan manner.
   • If the source article is biased FOR or AGAINST a government, political party,
     corporation, religion, nation, or individual — you MUST neutralise that bias.
   • Present ALL sides of the issue if multiple perspectives exist in the raw text.
   • NEVER editorialize or inject opinion. Attribute any claims to their sources.
   • Write like Reuters or BBC World — present facts, not judgements.
   • Even if a government, party, or person is praised in the source text, maintain
     journalistic distance. Report what happened, not what to think of it.
   • Use neutral language: prefer "officials say" over "officials admit/claim".

4. HTML CONTENT — Write the `content` field as clean, semantic HTML using only:
   <p>, <h2>, <h3>, <ul>, <li>, <blockquote>, <strong>, <em>.
   • No <html>, <head>, <body>, <style>, or <script> tags.
   • No Markdown (no **, no ##, no ```).
   • Use <h2> for sub-headings and <p> for paragraphs.
   • Wrap notable quotes or pull-quotes in <blockquote>.
   • Minimum 4 paragraphs. Each paragraph ≥ 40 words.
   • Structure: Lead/Hook → Background → Details → Impact/Context → Conclusion

5. SEO TITLE — Write a catchy `title` that:
   • Is concise (50-70 characters)
   • Uses active voice
   • Includes a primary keyword naturally
   • Does NOT use sensationalist or clickbait language

6. META DESCRIPTION — Write a compelling `meta_description` (130-155 characters)
   that summarises the article factually and encourages clicks without being
   misleading.

7. CATEGORY — Suggest exactly 1 broad `category` from this fixed list:
   Technology, World, Politics, Sports, Business, Entertainment, Science,
   Health, Environment, Crime, Education, Economy.

8. TAGS — Suggest 3-5 specific, relevant tags as a JSON array of strings.
   Examples: ["Artificial Intelligence", "US Elections", "Indian Economy"]

── Output Format ────────────────────────────────────────────────────────────
Respond ONLY with a single valid JSON object — no markdown fences, no preamble.
The JSON MUST match this exact schema:

{{
  "title":            "<string: SEO headline, 50-70 chars>",
  "meta_description": "<string: SEO meta, 130-155 chars>",
  "content":          "<string: full HTML article body, min 4 paragraphs>",
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
_VALID_CATEGORIES = {
    "Technology", "World", "Politics", "Sports", "Business",
    "Entertainment", "Science", "Health", "Environment",
    "Crime", "Education", "Economy",
}


def _validate_ai_response(data: dict) -> bool:
    """
    Ensures the parsed dict has all required keys with non-empty values,
    valid category, and tags as a non-empty list.
    """
    if not isinstance(data, dict):
        return False

    if not _REQUIRED_KEYS.issubset(data.keys()):
        missing = _REQUIRED_KEYS - data.keys()
        logger.warning("AI response missing keys: %s", missing)
        return False

    if not data.get("title") or len(str(data["title"]).strip()) < 10:
        logger.warning("AI response has missing or too-short title.")
        return False

    if not data.get("content") or len(str(data["content"]).strip()) < 200:
        logger.warning("AI response has missing or too-short content.")
        return False

    if not isinstance(data.get("tags"), list) or len(data["tags"]) == 0:
        logger.warning("AI response has invalid or empty tags list.")
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
    max_retries: int = 2,
) -> dict | None:
    """
    Sends the raw scraped article text to Groq and returns a dict
    containing the AI-rewritten, SEO-optimised, impartial article data.

    Parameters
    ----------
    original_title : str   — The headline fetched from the news API.
    raw_text       : str   — Full scraped body text from newspaper3k.
    source_name    : str   — Publisher name (e.g. "BBC News"), used in the prompt.
    max_retries    : int   — Number of times to retry on transient Groq errors.

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

    # Truncate to avoid exceeding context window
    truncated_text = raw_text[:10000]

    instruction = _build_prompt(original_title, source_name)
    user_content = f"Raw Article Text to Rewrite:\n\n{truncated_text}"

    last_error = None
    client = Groq(api_key=_GROQ_KEY)

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=_MODEL_NAME,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.35,
                max_tokens=3000,
            )

            raw_response_text = response.choices[0].message.content
            data = _extract_json(raw_response_text)

            if data is None:
                logger.error(
                    "Could not extract JSON from Groq response for '%s'. Raw: %s",
                    original_title,
                    raw_response_text[:500],
                )
                last_error = "JSON parse failed"
                time.sleep(2 * attempt)
                continue

            if not _validate_ai_response(data):
                logger.error(
                    "Groq response for '%s' failed validation. Data: %s",
                    original_title,
                    {k: str(v)[:100] for k, v in data.items()},
                )
                last_error = "Validation failed"
                time.sleep(2 * attempt)
                continue

            # ── Enforce field length constraints to prevent DB errors ──────
            data["title"]            = str(data["title"]).strip()[:250]
            data["meta_description"] = str(data["meta_description"]).strip()[:160]
            data["category"]         = str(data["category"]).strip()[:100]
            data["tags"]             = [str(t).strip()[:50] for t in data["tags"][:5] if str(t).strip()]

            # Ensure at least 1 tag survived sanitization
            if not data["tags"]:
                data["tags"] = ["News"]

            logger.info(
                "✅ Groq rewrite complete for '%s' → '%s' [%s] (attempt %d)",
                original_title,
                data["title"],
                data["category"],
                attempt,
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
                time.sleep(5 * attempt)

    logger.error(
        "❌ All %d Groq attempts failed for '%s'. Last error: %s",
        max_retries,
        original_title,
        last_error,
    )
    return None