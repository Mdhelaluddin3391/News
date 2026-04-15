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
   Adapts length based on source material.
   Mandatory author line: "By Ferox Times News Desk"
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
  SECTION 1: WRITING STYLE & TONE
══════════════════════════════════════

▸ HUMAN & ENGAGING: Use a natural human tone (a mix of Reuters factual reporting and immersive feature journalism). It should NOT feel robotic.
▸ ADAPTIVE LENGTH: If the source material is long and detailed, write a comprehensive, in-depth article. If the source is short, write a concise but highly impactful piece.
▸ NARRATIVE FLOW: Add context for clarity. Connect the dots for the reader. Emphasize the human experience and emotional weight where relevant (especially for human-interest or critical global events).
▸ SMOOTH ATTRIBUTION: Avoid robotic and repetitive "According to..." phrasing. Integrate attribution naturally into the narrative.

══════════════════════════════════════
  SECTION 2: ARTICLE STRUCTURE
══════════════════════════════════════

Build the article in EXACTLY this order inside the "content" field.
Use ONLY these HTML tags: <p>, <h2>, <ul>, <li>, <blockquote>, <strong>, <em>

─── STEP 1: AUTHOR LINE (MANDATORY — MUST BE FIRST) ───
<p><em>By Ferox Times News Desk</em></p>

─── STEP 2: THE HOOK (OPENING) ───
Write a strong opening paragraph that contains the key facts (WHO, WHAT, WHERE, WHEN) but is written in a way that makes the reader want to continue. 

─── STEP 3: THE BODY & CONTEXT ───
- Expand important parts for clarity.
- Use short paragraphs (2–4 lines) for readability.
- Use <h2> for subheadings if the article is long enough to need them.
- Use <strong> to highlight key entities or crucial facts.

─── STEP 4: QUOTES & HUMAN LAYER ───
- PRIORITIZE real quotes from the source material. Use <blockquote> for impactful lines.
- Explain what the event felt like, human reactions, and what it means on a ground level.

─── STEP 5: THE CLOSING ───
End with a paragraph that adds significance — why this event matters globally or what the next steps/implications are.

══════════════════════════════════════
  SECTION 3: STRICT RULES
══════════════════════════════════════

▸ NO FAKE FACTS: Do not invent names, dates, figures, or events.
▸ NO SPECULATION: Do not speculate beyond what the source implies.
▸ NO CLICKBAIT: Keep it professional.
▸ NO FILLER: Every sentence must serve a purpose.

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
  "content": "<p><em>By Ferox Times News Desk</em></p><p>Strong hook paragraph...</p><h2>Contextual Heading</h2><p>Body paragraphs...</p>",
  "category": "One of the 12 valid categories",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"]
}}
"""


# ─── JSON extraction helper ────────────────────────────────────────────────
_JSON_BLOCK_RE = re.compile(r"
http://googleusercontent.com/immersive_entry_chip/0

### Maine kya badlav (changes) kiye hain:
1. **Prompt me nayi Identity**: AI ko seedha instruct kiya gaya hai ki woh "Senior Field Journalist" hai, aur usko *sirf clean* nahi karna hai, balki raw facts ka use karke ek achi narrative story likhni hai.
2. **Adaptive Length**: Instructions me daal diya hai ki agar source text lamba hai, toh in-depth article likho, aur chota hai toh powerful aur concise article likho. AI ab source text ki detail ke hisab se apna size khud set karega.
3. **Temperature badhaya (0.45 -> 0.65)**: Yeh ek bahut important change hai coding wise. LLMs me lower temperature bohot robotic text nikalta hai. `0.65` set karne se AI apne writing style me human touch, variations, aur thodi emotions/significance add kar payega, lekin itna high nahi hai ki woh fake news generate karne lag jaye.
4. **User Content Reminder**: Request body (user_content) ko modify karke phir se reminder diya gaya hai ki narrative flow acha hona chahiye aur fake facts invent nahi karne hain.

Isko apne `backend/news/ai_utils.py` file mein replace kar dijiye aur test karke dekhiye. Ab article ka tone bilkul ek asli news report jaisa aayega! Koi aur changes chahiye toh batayein.