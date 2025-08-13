from __future__ import annotations

import json
from typing import Any, Dict, List
from ..config import settings

# Fixed slide schema (order + canonical titles)
SLIDE_SCHEMA = [
    {"key": "cover",               "title": "Personalized Cover"},
    {"key": "market_opportunity",  "title": "Market Opportunity"},
    {"key": "why_offdeal",         "title": "Why OffDeal"},
    {"key": "positioning",         "title": "Positioning for Maximum Value"},
    {"key": "process_next_steps",  "title": "Process & Next Steps"},
]

class AIUnavailableError(Exception):
    pass

class AIFormatError(Exception):
    pass

def _strip_markup(text: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", "", str(text or ""))
    text = re.sub(r"^[\-\•\*\s]+", "", text).strip()
    return re.sub(r"\s+", " ", text).strip()

def _truncate(text: str, max_chars: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= max_chars else (text[: max_chars - 1].rstrip() + "…")

def _normalize_deck_obj(obj: Dict[str, Any]) -> tuple[list[dict], str]:
    """Coerce model output into an ordered slides array + title."""
    slides_out: List[Dict[str, Any]] = []
    for spec in SLIDE_SCHEMA:
        key = spec["key"]
        canonical = spec["title"]
        node = obj.get(key) or {}

        # Title
        title = _truncate(_strip_markup(node.get("title") or canonical), settings.TITLE_MAX_CHARS)

        # Bullets
        bullets = node.get("bullets") or []
        if not isinstance(bullets, list):
            bullets = []
        clean: List[str] = []
        for b in bullets:
            if not isinstance(b, str):
                continue
            s = _truncate(_strip_markup(b), settings.BULLET_MAX_CHARS)
            if s:
                clean.append(s)
        bullets = clean[: settings.MAX_BULLETS] or ["Content unavailable."]

        # Optional guardrail example: avoid named buyers on positioning
        if key == "positioning":
            import re
            bullets = [re.sub(r"(?i)\b(buyer|acquirer|company)\s*:\s*[\w\-\.\& ]+", "buyer: (generalized)", x) for x in bullets]

        slides_out.append({"title": title, "bullets": bullets})

    deck_title = obj.get("deck_title") or SLIDE_SCHEMA[0]["title"]
    deck_title = _truncate(_strip_markup(deck_title), settings.TITLE_MAX_CHARS) or "OffDeal Pitch"
    return slides_out, deck_title

def _openai_json_response(prompt: str) -> Dict[str, Any] | List[Any]:
    try:
        from openai import OpenAI
    except Exception as e:
        raise AIUnavailableError(f"OpenAI SDK not available: {e!s}")

    if not settings.OPENAI_API_KEY:
        raise AIUnavailableError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        raise AIUnavailableError(f"OpenAI call failed: {e!s}")

def generate_deck_content(prospect: Dict[str, Any]) -> dict:
    """
    Build one prompt for all slides, call OpenAI, normalize, and return:
      {
        "slides": [ {title, bullets[]}, ...schema order... ],
        "deck_title": "<Company> x OffDeal"
      }
    """
    schema_keys = ", ".join([s["key"] for s in SLIDE_SCHEMA])
    prompt = (
        "You will generate content for a 5-slide pitch deck for a business owner considering a sale. "
        f"Return a single JSON object with exactly these keys: {schema_keys}, and 'deck_title'. "
        "Each key must map to an object with 'title' and 'bullets' (a list of 3–5 concise bullet points). "
        "Avoid naming any specific buyers on the positioning slide; keep language generalized and professional.\n\n"
        f"Prospect data:\n{json.dumps(prospect, ensure_ascii=False)}"
    )

    raw = _openai_json_response(prompt)
    slides, deck_title = _normalize_deck_obj(raw)
    return {"slides": slides, "deck_title": deck_title}
