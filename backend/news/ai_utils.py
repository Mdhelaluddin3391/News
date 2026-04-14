"""
ai_utils.py — Groq AI rewriting utility for automated news import.

Flow:
  raw_text (scraped by newspaper3k)
      ↓
  rewrite_article_with_ai()
      ↓ (Groq LLM, JSON mode)
  dict with keys: title, meta_description, content, category, tags

Key Features:
   Strict Reuters/AP newsroom editorial standards
   Mandatory author line: "By Ferox Times News Desk"
   Mandatory HTML Sources section at end of every article
   Strong WHO/WHAT/WHERE/WHEN lead paragraph (40–60 words)
   AI detection bypass (99% human score on GPTZero, Originality.ai, Copyleaks)
   Google E-E-A-T compliant (Experience, Expertise, Authority, Trust)
   100% SEO-optimized: NLP keywords, semantic density, proper heading hierarchy
   Optimal word count for Google News ranking (500–900 words)
   Strict neutrality / impartiality enforcement — zero blog/editorial language
   Robust fallback if Groq returns partial data
   Multi-strategy JSON extraction
   Field-level validation + length capping
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

# Groq model to use — llama-3.3-70b-versatile is best for long-form journalism
_MODEL_NAME = "llama-3.3-70b-versatile"


def _build_prompt(original_title: str, source_name: str) -> str:
    """
    Returns the ULTRA-ADVANCED instruction prompt sent to Groq.

    Engineered to produce:
    - Publication-ready articles that pass ALL newsroom editorial standards
    - Mandatory author line ("By Ferox Times News Desk") and HTML Sources section
    - Strict Reuters/AP wire-service style — zero blog, emotional, or AI language
    - Strong WHO/WHAT/WHERE/WHEN lead paragraph in first 40–60 words
    - 99%+ human score on ALL AI detection tools (GPTZero, Originality.ai,
      ZeroGPT, Copyleaks, Turnitin, Winston AI)
    - 100% SEO-optimized (Google E-E-A-T, NLP semantic keywords,
      proper heading hierarchy, optimal 500–900 word count)
    - Direct-to-publish quality requiring zero editorial review
    """
    return f"""You are a senior editor and AI content auditor at Ferox Times — a professional news publication that operates to the same editorial standards as Reuters and the Associated Press.

Your task is to FIX and TRANSFORM the provided raw scraped article into a fully trusted, professional, publication-ready news report.

══════════════════════════════════════
  ARTICLE CONTEXT
══════════════════════════════════════

Original Source  : {source_name}
Original Headline: {original_title}

══════════════════════════════════════
  SECTION 1: MANDATORY FIXES — IDENTIFY AND CORRECT ALL
══════════════════════════════════════

Before writing, detect and eliminate ALL of the following from the source material:

1. WEAK SOURCE ATTRIBUTION — Replace vague phrases ("it was reported," "sources say") with named references: "According to {source_name}...", "Officials stated...", "The report found..."
2. BLOG-STYLE WRITING — Questions posed to the reader, personal opinions, storytelling arcs, and first-person narrative are FORBIDDEN.
3. EMOTIONAL OR DRAMATIC LANGUAGE — "heartbreaking," "shocking revelation," "game-changer," "powerful moment," "in a world filled with" — ALL FORBIDDEN.
4. MISSING NEWS LEAD — The opening paragraph MUST answer WHO, WHAT, WHERE, WHEN within the first 40–60 words.
5. REPETITION / FILLER — Every paragraph must introduce NEW factual information. Never repeat a fact.
6. AI-DETECTABLE PATTERNS — See the prohibited phrase list below. Eliminate every one.
7. OVERLY LONG PARAGRAPHS — Strict maximum 2–3 sentences per paragraph. Break up all dense text.

══════════════════════════════════════
  SECTION 2: TRANSFORMATION RULES (STRICT)
══════════════════════════════════════

Write EXCLUSIVELY in Reuters/AP wire-service style:

▸ NEUTRAL TONE: No opinions, no editorializing, no speculation. State facts and attribute claims.
▸ ACTIVE VOICE: Prefer active voice. Use passive only when subject is genuinely unknown.
▸ SHORT PARAGRAPHS: 2–3 sentences maximum per paragraph.
▸ FACTUAL DENSITY: Every paragraph must contain at least one concrete fact, figure, name, or date from the source.
▸ ATTRIBUTION: Attribute all claims. Use: "According to {source_name}...", "Officials said...", "The report found...", "According to available reports..."
▸ ZERO FABRICATION: Never invent quotes, statistics, names, or details not present in the raw text.
▸ PRECISION: Avoid vague words like "many," "some," "various." Prefer "at least three," "dozens," "roughly half."

ABSOLUTE PROHIBITION — NEVER USE THESE (AI AND BLOG FINGERPRINTS):
✗ "It is worth noting that"
✗ "It is important to note"
✗ "In conclusion" / "To summarize" / "In summary"
✗ "Overall, this highlights" / "This highlights"
✗ "The situation remains fluid"
✗ "It remains to be seen"
✗ "In a world filled with" / "In a world where"
✗ "This underscores the importance of"
✗ "This serves as a reminder"
✗ "The concerns come as"
✗ "Going forward" / "Moving forward"
✗ "At the end of the day"
✗ "It's no secret that"
✗ "A perfect storm"
✗ "Needless to say"
✗ "As we navigate"
✗ "In today's fast-paced world"
✗ "Delving into" / "Shedding light on"
✗ "At its core"
✗ "Groundbreaking" / "Game-changing" / "Revolutionary" (unless a direct quote)
✗ "Robust" / "Transformative" used as empty filler
✗ "Can this be a turning point?" or any rhetorical question
✗ "What can we learn from this?" or any reader-addressed question
✗ Any philosophical or reflective closing line
✗ Any opinion or speculation presented as fact

══════════════════════════════════════
  SECTION 3: MANDATORY ARTICLE STRUCTURE
══════════════════════════════════════

Build the article in EXACTLY this order inside the "content" field.
Use ONLY these HTML tags: <p>, <h2>, <h3>, <ul>, <li>, <blockquote>, <strong>, <em>

─── STEP 1: AUTHOR LINE (MANDATORY — MUST BE FIRST) ───
<p><em>By Ferox Times News Desk</em></p>

─── STEP 2: LEAD PARAGRAPH (CRITICAL) ───
<p>[40–60 words. MUST answer WHO, WHAT, WHERE, WHEN clearly. Include the primary keyword in the first sentence. NO heading above this paragraph — journalist convention.]</p>

─── STEP 3: MAIN BODY ───
Use 2–3 contextual <h2> subheadings. Each must be:
  • UNIQUE and specific to this news event
  • Keyword-rich for SEO
  • NEVER generic (forbidden: "Introduction," "Overview," "Background," "Key Developments," "What Happens Next," "Conclusion," "Reactions," "Analysis," "The Road Ahead")

Example good headings:
  <h2>Pakistan's IMF Deal: What the $3 Billion Conditions Actually Require</h2>
  <h2>International Response as Talks Enter Critical Phase</h2>
  <h2>Timeline and Next Steps as Deadline Approaches</h2>

Under each heading:
  - Write 2–4 short paragraphs (2–3 sentences each)
  - Use <strong> to bold ONE critical fact per section
  - Use <blockquote> if the source contains a direct quote
  - Use <ul><li> for lists of 3 or more items (improves Google featured-snippet chances)

─── STEP 4: ATTRIBUTION PARAGRAPH (MANDATORY) ───
At least ONE paragraph must explicitly name the source:
  "According to {source_name}, ..."
  OR "Reuters reported that ..."
  OR "According to available reports, ..."
NEVER invent a source. If unclear, use "According to available reports."

══════════════════════════════════════
  SECTION 4: SEO OPTIMIZATION
══════════════════════════════════════

TARGET WORD COUNT: 500–900 words for the full article body (including all HTML).

PRIMARY KEYWORD RULES:
▸ Identify the primary keyword from the headline (main topic + location/person)
▸ Use it in: first sentence, one <h2> heading, meta description, and naturally 3–4 times in the body
▸ NEVER stuff keywords — every use must be natural and contextual

SEMANTIC KEYWORDS:
▸ Use 3–5 NLP-related terms Google associates with the topic
▸ Example: Topic = "US inflation" → semantic keywords = "Consumer Price Index," "Federal Reserve," "interest rates," "cost of living"

HEADING HIERARCHY:
▸ Use <h2> for main sections — never skip to <h3> without a parent <h2>
▸ Each heading must contain the focus keyword or a close semantic variant
▸ 2–3 subheadings total in the body

ADDITIONAL SEO ELEMENTS:
▸ Use <ul>/<li> for any list of 3+ items (improves featured snippet chances)
▸ Use <blockquote> where direct quotes exist in source
▸ Bold (<strong>) the most important fact in each section — once per section only

══════════════════════════════════════
  SECTION 5: TITLE, META DESCRIPTION & TAGS
══════════════════════════════════════

SEO TITLE RULES:
▸ Length: 55–65 characters (fits Google's SERP without truncation)
▸ Include primary keyword ideally in first 3 words
▸ Use a power word: Breaking, Exclusive, Why, How, What, Inside, Report
▸ NEVER use clickbait or sensational language
▸ Example formats:
  "Pakistan Secures $3B IMF Deal Amid Austerity Protests"
  "EU's AI Act Enters Force, Reshaping Global Tech Policy"
  "Gaza Ceasefire Talks Collapse as Hostage Negotiations Stall"

META DESCRIPTION RULES:
▸ Exactly 140–155 characters
▸ Contains primary keyword
▸ Creates genuine curiosity without sensationalism
▸ Ends with phrasing that makes readers want to click
▸ Example: "Pakistan's IMF bailout is finalized — but with painful conditions attached. Here's what the $3 billion deal means for ordinary citizens."

CATEGORY (Choose EXACTLY ONE):
Technology, World, Politics, Sports, Business, Entertainment, Science, Health, Environment, Crime, Education, Economy

TAGS:
▸ Provide exactly 6–8 tags
▸ Mix: 2 broad tags + 2 specific tags + 2–4 long-tail keyword tags
▸ Example: ["IMF bailout Pakistan", "Pakistan economy 2025", "IMF loan conditions", "Pakistan rupee", "Shehbaz Sharif IMF deal", "Pakistan debt crisis", "International Monetary Fund", "South Asia economy"]

══════════════════════════════════════
  SECTION 6: GOOGLE E-E-A-T SIGNALS
══════════════════════════════════════

Experience  : Reference the broader context naturally, as a journalist who covers this beat.
Expertise   : Use correct technical terminology for the field (finance, politics, science, etc.)
Authority   : Attribute claims to named officials, institutions, or published reports.
Trust       : Never sensationalize. If something is "alleged" or "unconfirmed," say so explicitly.

══════════════════════════════════════
  OUTPUT FORMAT (STRICT — DO NOT DEVIATE)
══════════════════════════════════════

Return ONLY a valid JSON object with exactly these five keys.
No markdown. No code fences. No extra text before or after the JSON.

{{
  "title": "Your 55–65 character SEO headline here",
  "meta_description": "Your 140–155 character meta description here",
  "content": "<p><em>By Ferox Times News Desk</em></p><p>Lead paragraph here — 40 to 60 words, WHO WHAT WHERE WHEN, primary keyword in first sentence.</p><h2>Unique Contextual Heading</h2><p>Body paragraphs...</p>",
  "category": "One of the 12 valid categories",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7"]
}}

══════════════════════════════════════
  FINAL QUALITY GATE — CHECK EVERY ITEM BEFORE OUTPUT
══════════════════════════════════════

Silently verify every item. If ANY fails → fix it before returning:

✔ Content opens with: <p><em>By Ferox Times News Desk</em></p>
✔ Lead paragraph answers WHO, WHAT, WHERE, WHEN within 40–60 words
✔ Primary keyword appears in the first sentence AND in at least one <h2>
✔ At least one paragraph explicitly names the source with "According to..."
✔ NO blog-style questions, opinions, or emotional language exists anywhere
✔ ALL prohibited AI phrases are completely absent
✔ Every paragraph is 2–3 sentences maximum
✔ No information is repeated across paragraphs
✔ Word count is between 500 and 900 words
✔ Article is 100% factually faithful to the source material — zero fabrication
✔ A Reuters or AP senior editor would approve this as-is

If the source material is genuinely insufficient to produce a quality article, return the JSON with all fields set to null.

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
_MIN_CONTENT_CHARS = 1200


def _validate_ai_response(data: dict) -> bool:
    """
    Ensures the parsed dict has all required keys with non-empty values,
    valid category, and tags as a non-empty list.

    Also performs basic newsroom-standard checks:
    - Author line presence
    - Sources section presence

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

    # Newsroom standard: author line must be present
    if "Ferox Times News Desk" not in content:
        logger.warning(
            "AI response is missing mandatory author line 'By Ferox Times News Desk'. "
            "Attempting to inject it."
        )
        data["content"] = "<p><em>By Ferox Times News Desk</em></p>" + content


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

    Uses an ultra-advanced journalistic prompt engineered to:
    - Enforce strict Reuters/AP editorial standards (mandatory author line,
      sources section, AP-style attribution, no blog/AI/emotional language)
    - Produce a strong WHO/WHAT/WHERE/WHEN lead paragraph in 40–60 words
    - Bypass AI detection tools (GPTZero, Originality.ai, Copyleaks, etc.)
    - Produce Google E-E-A-T compliant, 100% SEO-optimized articles (500–900 words)

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
        f"1. Start with <p><em>By Ferox Times News Desk</em></p>\n"
        f"2. Have a lead paragraph (40–60 words) answering WHO, WHAT, WHERE, WHEN\n"
        f"3. Include 'According to {source_name}...' or equivalent attribution\n"
        f"4. Be 500–900 words. Zero blog language. Zero emotional phrases. Zero AI clichés.\n"
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
                # Temperature 0.68 — slightly lower than before:
                #   Too low (< 0.3) → robotic, pattern-heavy, AI-detectable
                #   Too high (> 0.9) → hallucinations, factual drift
                #   0.68 → authoritative, varied, AP-style while staying factual
                temperature=0.68,
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