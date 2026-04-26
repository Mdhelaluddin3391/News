"""
ai_utils.py — Groq AI rewriting engine for the Ferox Times GNews intelligence pipeline.

Input:
  original_title  — Headline from GNews
  raw_text        — Multi-source knowledge base built by importer._build_knowledge_base()
                    (5-8 scraped internet sources, typically 15 000 – 30 000 chars)
  source_name     — Publisher name

Output:
  dict with keys: title, meta_description, content, category, tags

Journalistic Standard: Reuters / AP / BBC newsroom level.
Article Format: Pure news — lead, nut graf, development, context, stakes, voices, outlook.
Article Style:  NEVER blog. NEVER listicle. NEVER opinion. Always third-person news prose.
"""

import json
import logging
import os
import re
import time

from groq import Groq

logger = logging.getLogger(__name__)

# ─── Groq Client Initialisation ───────────────────────────────────────────────
_GROQ_KEY = os.getenv("GROQ_API_KEY")
if not _GROQ_KEY:
    logger.warning("GROQ_API_KEY is not set — AI rewriting will be disabled.")

# Model strategy:
#   Primary  (llama-3.3-70b-versatile) — Best quality, 100k tokens/day free tier.
#   Fallback (llama-3.1-8b-instant)    — Higher rate limit, 500k tokens/day free tier.
_MODEL_PRIMARY  = "llama-3.3-70b-versatile"
_MODEL_FALLBACK = "llama-3.1-8b-instant"


# ─── Master Newsroom Prompt ───────────────────────────────────────────────────

def _build_prompt(original_title: str, source_name: str) -> str:
    """
    Builds the master Groq system prompt for the GNews intelligence pipeline.

    This prompt is engineered to produce publication-ready news articles at
    Reuters/AP/BBC editorial standard from a multi-source knowledge base.
    It enforces strict anti-blog, anti-AI-cliché, and anti-hallucination rules.
    """
    return (
        # ── Role ────────────────────────────────────────────────────────────
        "You are the Chief Foreign Correspondent at Ferox Times, a global digital "
        "news organisation held to the same editorial standards as Reuters, AP, BBC, "
        "and the Financial Times.\n\n"

        # ── Assignment ──────────────────────────────────────────────────────
        f"STORY ASSIGNMENT: {original_title}\n"
        f"ORIGINAL SOURCE: {source_name}\n\n"

        "You have been given a multi-source internet knowledge base assembled from "
        "5-8 live web sources. Your task is to synthesise all available facts and "
        "write a COMPLETE, ORIGINAL, 100%% PUBLICATION-READY news article.\n\n"

        # ── The Iron Rules (Non-Negotiable) ─────────────────────────────────
        "THE IRON RULES — VIOLATING ANY OF THESE DISQUALIFIES THE ARTICLE:\n\n"

        "RULE 1 — PURE NEWS FORMAT ONLY:\n"
        "  This is a newspaper article. It is NOT a blog post. It is NOT a listicle.\n"
        "  It is NOT a how-to guide. It is NOT an opinion piece. It is NOT an essay.\n"
        "  Every paragraph must report a new fact, quote, or development.\n"
        "  If a sentence does not add new information, delete it.\n\n"

        "RULE 2 — ZERO HALLUCINATION:\n"
        "  Every claim, figure, date, name, and statistic must come from the\n"
        "  knowledge base provided. Do not invent any information. Do not guess.\n"
        "  If the exact figure is not in the knowledge base, say 'officials said'\n"
        "  or omit the claim entirely. Accuracy is non-negotiable.\n\n"

        "RULE 3 — THIRD PERSON ONLY:\n"
        "  Never use 'you', 'we', 'our', 'let us', 'readers', 'I', or any\n"
        "  direct address to the audience.\n\n"

        "RULE 4 — BANNED PHRASES (automatic disqualification if used):\n"
        "  Moreover, Furthermore, Additionally, In conclusion, To summarize,\n"
        "  It is important to note, Needless to say, Delves into, A testament to,\n"
        "  Tapestry, Landscape, Ecosystem, Groundbreaking, Game-changing,\n"
        "  Cutting-edge, Robust, Shed light on, Pave the way, Paradigm shift,\n"
        "  Holistic, Synergy, In today's fast-paced world, In the modern era,\n"
        "  Ever-evolving, Unprecedented (use only if a precedent is cited),\n"
        "  Deep dive, Dive in, Let's explore, As mentioned, Notably, Crucially,\n"
        "  Essentially, Interestingly, Surprisingly, Importantly.\n\n"

        "RULE 5 — ATTRIBUTION DISCIPLINE (rotate — never repeat the same phrase twice):\n"
        "  Use these in rotation: officials said | data showed | the filing indicated\n"
        "  | statements confirmed | the announcement read | records showed\n"
        "  | sources said | the document showed | the report found\n"
        "  | authorities stated | the agency confirmed.\n\n"

        "RULE 6 — NUMBERS AND SPECIFICITY:\n"
        "  Numbers make news concrete. Always use figures: '47 percent', '$3.2 billion',\n"
        "  '12 people', not 'nearly half', 'billions', 'many people'.\n\n"

        # ── Article Architecture ─────────────────────────────────────────────
        "ARTICLE ARCHITECTURE — Follow this narrative structure seamlessly.\n"
        "Do NOT label these sections. Blend them like a professional newspaper story.\n"
        "Use HTML tags ONLY: <p> <h2> <h3> <ul> <li> <blockquote> <strong> <em>\n\n"

        "1. THE LEAD PARAGRAPH [MANDATORY — MUST be first]\n"
        "   · 40-65 words. One paragraph. No subheading before it.\n"
        "   · Answers WHO + WHAT + WHERE + WHEN + WHY IT MATTERS NOW.\n"
        "   · First word MUST be a proper noun (name/place/org) or a specific number.\n"
        "   · NEVER start with A / An / The / In / On / At.\n"
        "   · Uses present perfect or simple past tense for immediacy.\n\n"

        "2. NUT GRAF [MANDATORY — immediately after lead]\n"
        "   · 1-2 sentences. Places the story in its larger context.\n"
        "   · Why does this matter beyond today? What pattern or trend does it fit?\n\n"

        "3. CORE DEVELOPMENT [3-5 paragraphs]\n"
        "   · Chronological or logical unfolding of the key facts.\n"
        "   · Use <strong> on ONE critical statistic or figure per section (once).\n"
        "   · Every paragraph introduces a new fact, angle, or development.\n\n"

        "4. STORY-SPECIFIC SUBHEADINGS [<h2> — REQUIRED for articles over 500 words]\n"
        "   · Subheadings must be INTENSELY STORY-SPECIFIC — like a newspaper section header.\n"
        "   · GOOD examples: 'Fed Rate Decision Rattles Asian Markets'\n"
        "                     'IMF Demands Fuel Subsidy Cuts by March'\n"
        "                     'Three Officers Charged in Birmingham Probe'\n"
        "   · BAD examples (BANNED): 'Background', 'Context', 'History',\n"
        "                             'Impact', 'Analysis', 'Key Developments',\n"
        "                             'What This Means', 'Expert Views', 'Outlook'.\n\n"

        "5. HISTORICAL / LEGAL / ECONOMIC CONTEXT [1-2 paragraphs]\n"
        "   · Place the event in context seamlessly within the narrative flow.\n"
        "   · No separate section titled 'Background' or 'History'.\n\n"

        "6. HUMAN STAKES [1-2 paragraphs]\n"
        "   · Who is directly affected? Use concrete numbers.\n"
        "   · Real quotes or official statements in <blockquote> tags.\n\n"

        "7. VOICES AND REACTIONS [1-2 paragraphs]\n"
        "   · Official responses, expert perspectives, countervailing views.\n"
        "   · Use <blockquote> for direct quotes. Attribute precisely.\n\n"

        "8. FUTURE OUTLOOK [MANDATORY — final paragraph]\n"
        "   · Verified upcoming events, deadlines, or next steps from the knowledge base.\n"
        "   · End with a sharp, factual observation — not a moral judgement.\n"
        "   · This must be the LAST paragraph. No summary. No conclusion label.\n\n"

        "MINIMUM CONTENT LENGTH: 750 words of readable prose.\n"
        "MAXIMUM BLOG MARKERS: 0. If there is a tip, list-of-advice, or how-to sentence, delete it.\n\n"

        # ── SEO Metadata Rules ───────────────────────────────────────────────
        "SEO METADATA RULES:\n\n"

        "TITLE (58-68 characters EXACTLY):\n"
        "  · Must contain 1-2 high-intent search keywords people would actually Google.\n"
        "  · Must include a proper noun (name, place, organisation) OR a specific number.\n"
        "  · No question format. No exclamation marks. No sensationalism. No ALL CAPS.\n"
        "  · GOOD: 'Pakistan Raises Interest Rate to 22 Percent Amid IMF Pressure'\n"
        "  · GOOD: 'Apple Cuts iPhone 15 Production by 10 Million Units'\n"
        "  · BAD:  'Shocking Decision That Rocked Pakistan Economy'\n"
        "  · BAD:  'What You Need to Know About the Latest IMF News'\n\n"

        "META DESCRIPTION (148-160 characters EXACTLY):\n"
        "  · Complete sentence. Active voice. No trailing ellipsis.\n"
        "  · Must contain the second most important fact from the story.\n"
        "  · Must be SEO-optimised: include primary keyword naturally.\n\n"

        "CATEGORY — choose EXACTLY ONE:\n"
        "  Technology | World | Politics | Sports | Business |\n"
        "  Entertainment | Science | Health | Environment | Crime | Education | Economy\n\n"

        "TAGS — exactly 7, title-cased, max 4 words each:\n"
        "  · 2 broad topic tags (e.g. 'Interest Rate Hike', 'Nuclear Energy')\n"
        "  · 2 named entity tags (e.g. 'IMF', 'Samsung Electronics')\n"
        "  · 2 issue or event tags (e.g. 'Economic Crisis 2025', 'Peace Talks')\n"
        "  · 1 article type tag — MUST be one of:\n"
        "    Breaking News | Analysis | Report | Feature | Investigation\n\n"

        # ── Output Format ────────────────────────────────────────────────────
        "OUTPUT: Return ONLY a valid JSON object with EXACTLY these five keys.\n"
        "NO markdown code fences. NO preamble text. NO trailing explanation. Pure JSON.\n\n"
        "{{\n"
        '  "title": "Fact-based SEO headline, exactly 58-68 chars",\n'
        '  "meta_description": "Second key fact, SEO optimised, active voice, 148-160 chars",\n'
        '  "content": "<p>Lead paragraph...</p><p>Nut graf...</p><h2>Story-Specific Heading</h2><p>...</p>",\n'
        '  "category": "One valid category from the list",\n'
        '  "tags": ["Broad Tag 1", "Broad Tag 2", "Named Entity", "Named Entity 2", "Issue Tag", "Event Tag", "Report"]\n'
        "}}"
    )


# ─── JSON Extraction Helpers ──────────────────────────────────────────────────

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_json(text: str) -> dict | None:
    """
    Extracts a JSON object from model output using three strategies:
      1. Direct json.loads (clean JSON).
      2. Strip markdown code fence.
      3. Substring between first { and last }.
    Returns None if all strategies fail.
    """
    text = text.strip()

    # Strategy 1
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2
    match = _JSON_BLOCK_RE.search(text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


# ─── Response Validation ──────────────────────────────────────────────────────

_REQUIRED_KEYS = {"title", "meta_description", "content", "category", "tags"}
_VALID_CATEGORIES = {
    "Technology", "World", "Politics", "Sports", "Business",
    "Entertainment", "Science", "Health", "Environment",
    "Crime", "Education", "Economy",
}

# Minimum content length for a credible news article (≈700 words ≈ ~2500 chars with HTML)
_MIN_CONTENT_CHARS = 2000


def _validate_ai_response(data: dict) -> bool:
    """
    Validates the parsed AI response for completeness and quality.
    Logs a descriptive warning for each failure point.
    Returns False if any check fails; True if all pass.
    """
    if not isinstance(data, dict):
        logger.warning("[Validate] AI response is not a dict — type: %s", type(data))
        return False

    if not _REQUIRED_KEYS.issubset(data.keys()):
        missing = _REQUIRED_KEYS - data.keys()
        logger.warning("[Validate] Missing required keys: %s", missing)
        return False

    title = str(data.get("title", "")).strip()
    if len(title) < 20:
        logger.warning("[Validate] Title too short (%d chars): '%s'", len(title), title)
        return False

    content = str(data.get("content", "")).strip()
    if len(content) < _MIN_CONTENT_CHARS:
        logger.warning(
            "[Validate] Content too short: %d chars (min %d). AI may not have followed the prompt.",
            len(content), _MIN_CONTENT_CHARS,
        )
        return False

    meta = str(data.get("meta_description", "")).strip()
    if len(meta) < 80:
        logger.warning("[Validate] meta_description too short: %d chars (min 80).", len(meta))
        return False

    tags = data.get("tags")
    if not isinstance(tags, list) or len(tags) < 3:
        logger.warning("[Validate] Insufficient tags: %s", tags)
        return False

    # Auto-correct invalid category (don't hard-fail, just warn + fix)
    if data.get("category") not in _VALID_CATEGORIES:
        logger.warning(
            "[Validate] Invalid category '%s' — defaulting to 'World'.", data.get("category")
        )
        data["category"] = "World"

    return True


# ─── Public API ───────────────────────────────────────────────────────────────

def rewrite_article_with_ai(
    original_title: str,
    raw_text: str,
    source_name: str,
    max_retries: int = 3,
) -> dict | None:
    """
    Generates a complete, publication-ready news article from the multi-source
    knowledge base built by importer._build_knowledge_base().

    This is the core AI engine for the Ferox Times auto-import pipeline.
    It receives 15 000 – 30 000 chars of pre-researched, multi-source material
    and returns a fully written, SEO-optimised newsroom-standard article.

    Parameters
    ----------
    original_title : str  — GNews headline (used for attribution and prompt context).
    raw_text       : str  — Full multi-source knowledge base from the research phase.
    source_name    : str  — Original publisher name (e.g. 'BBC News').
    max_retries    : int  — Groq retry attempts on transient errors (default: 3).

    Returns
    -------
    dict | None
        On success: {"title", "meta_description", "content", "category", "tags"}
        On failure: None  (caller skips article gracefully)
    """
    if not _GROQ_KEY:
        logger.error("[Groq] GROQ_API_KEY not configured — skipping AI rewrite.")
        return None

    if not raw_text or len(raw_text.strip()) < 300:
        logger.warning(
            "[Groq] Knowledge base too short (%d chars) for '%s' — skipping.",
            len(raw_text) if raw_text else 0,
            original_title,
        )
        return None

    system_prompt = _build_prompt(original_title, source_name)

    # Truncate knowledge base to safe context window size.
    # llama-3.3-70b has 128k context; we send up to 20k chars of research.
    knowledge_base_truncated = raw_text[:20000]

    user_content = (
        f"STORY ASSIGNMENT: {original_title}\n\n"
        f"{'═' * 70}\n"
        f"MULTI-SOURCE KNOWLEDGE BASE\n"
        f"(Synthesise ONLY facts from the sources below. Zero hallucination.)\n"
        f"{'═' * 70}\n\n"
        f"{knowledge_base_truncated}\n\n"
        f"{'═' * 70}\n"
        f"FINAL REMINDERS:\n"
        f"1. Lead paragraph: WHO + WHAT + WHERE + WHEN in 40-65 words. First word = proper noun.\n"
        f"2. Minimum 750 words of pure news prose — no blog, no lists, no tips.\n"
        f"3. All subheadings (<h2>) MUST be story-specific — never generic labels.\n"
        f"4. Return ONLY valid JSON. No markdown. No preamble. No explanation.\n"
        f"{'═' * 70}"
    )

    client = Groq(api_key=_GROQ_KEY)
    used_model = _MODEL_PRIMARY
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "[Groq] Attempt %d/%d for '%s' [model=%s]…",
                attempt, max_retries, original_title[:70], used_model,
            )

            response = client.chat.completions.create(
                model=used_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=0.35,   # Low temperature = factual, structured output
                max_tokens=5000,    # Enough for a 900-1200 word article in HTML
            )

            raw_response = response.choices[0].message.content
            data = _extract_json(raw_response)

            if data is None:
                logger.error(
                    "[Groq] JSON extraction failed on attempt %d for '%s'. "
                    "Raw output (first 400 chars): %s",
                    attempt, original_title[:60], raw_response[:400],
                )
                last_error = "JSON extraction failed"
                time.sleep(2 * attempt)
                continue

            if not _validate_ai_response(data):
                logger.error(
                    "[Groq] Validation failed on attempt %d [model=%s] for '%s'. "
                    "Content: %d chars | Category: '%s' | Tags: %d.",
                    attempt, used_model, original_title[:60],
                    len(str(data.get("content", ""))),
                    data.get("category"),
                    len(data.get("tags", [])) if isinstance(data.get("tags"), list) else 0,
                )
                last_error = "Validation failed"
                time.sleep(3 * attempt)
                continue

            # ── Enforce field length constraints ───────────────────────────
            data["title"]            = str(data["title"]).strip()[:250]
            data["meta_description"] = str(data["meta_description"]).strip()[:160]
            data["category"]         = str(data["category"]).strip()[:100]
            data["tags"]             = [
                str(t).strip()[:50]
                for t in data["tags"][:8]
                if str(t).strip()
            ]
            if not data["tags"]:
                data["tags"] = ["News"]

            logger.info(
                "✅ [Groq] Article written: '%s' [%s] | %d chars | %d tags | model=%s | attempt %d/%d",
                data["title"], data["category"],
                len(data["content"]), len(data["tags"]),
                used_model, attempt, max_retries,
            )
            return data

        except Exception as exc:
            last_error = str(exc)

            # ── Rate limit (429) → switch to fallback model immediately ───
            if "429" in str(exc) and used_model == _MODEL_PRIMARY:
                logger.warning(
                    "[Groq] Primary model '%s' rate-limited for '%s'. "
                    "Auto-switching to fallback '%s'.",
                    _MODEL_PRIMARY, original_title[:60], _MODEL_FALLBACK,
                )
                used_model = _MODEL_FALLBACK
                time.sleep(2)
                continue  # Retry immediately with fallback

            logger.warning(
                "[Groq] Attempt %d/%d failed [model=%s] for '%s': %s",
                attempt, max_retries, used_model, original_title[:60], exc,
            )
            if attempt < max_retries:
                backoff = 5 * attempt
                logger.info("[Groq] Retrying in %ds…", backoff)
                time.sleep(backoff)

    logger.error(
        "❌ [Groq] All %d attempts exhausted for '%s'. Last error: %s",
        max_retries, original_title[:60], last_error,
    )
    return None