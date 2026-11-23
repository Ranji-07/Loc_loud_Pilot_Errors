from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import timedelta
from typing import Any

import httpx
from sqlalchemy import select

from ..config import Settings
from ..db import Database
from ..models import ModelCall, utcnow
from .rules import plain_summary

# The 0.5B model is unreliable at reading raw JSON (it invents costs and advice), but faithful at rewording
# short deterministic notes, so it only ever sees the rule-based summary.
PROMPT = (
    "Rewrite these notes for a beginner as short bullet points, one per note. Keep every fact, name and number "
    "exactly as written. Do not add any new facts, numbers or advice.\nNOTES:\n{notes}"
)
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def ungrounded_numbers(text: str, payload: str) -> list[str]:
    """Numbers in the model output that do not occur in the facts (a cheap hallucination check)."""
    known = set(_NUMBER.findall(payload))
    known |= {k.rstrip("0").rstrip(".") for k in known if "." in k}
    return [n for n in _NUMBER.findall(text) if n not in known and n not in {"1", "2", "3"}]


async def summarize(settings: Settings, db: Database, facts: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(facts, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{settings.small_model}|{payload}".encode()).hexdigest()

    if settings.summary_cache_seconds:
        since = utcnow() - timedelta(seconds=settings.summary_cache_seconds)
        with db.session() as s:
            hit = s.scalars(select(ModelCall).where(ModelCall.input_hash == digest, ModelCall.cached.is_(False),
                                                    ModelCall.at >= since).order_by(ModelCall.at.desc())).first()
            if hit:
                s.add(ModelCall(task="usage-summary", provider="cache", model=hit.model, input_hash=digest,
                                cached=True, output=hit.output))
                return {"source": "cache", "model": hit.model, "text": hit.output,
                        "prompt_tokens": 0, "completion_tokens": 0}

    notes = plain_summary(facts)
    t = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(f"{settings.ollama_url}/api/generate", json={
                "model": settings.small_model,
                "prompt": PROMPT.format(notes=notes),
                "stream": False,
                "keep_alive": "2m",
                "options": {"temperature": 0, "num_predict": 180},
            })
            r.raise_for_status()
            body = r.json()
    except (httpx.HTTPError, ValueError) as e:
        return {"source": "rules", "model": None, "text": plain_summary(facts),
                "error": f"Small model unavailable ({type(e).__name__}); showing the rule-based summary"}
    ms = int((time.perf_counter() - t) * 1000)
    text = (body.get("response") or "").strip()
    pt, ct = int(body.get("prompt_eval_count") or 0), int(body.get("eval_count") or 0)
    bad = ungrounded_numbers(text, payload + notes)
    with db.session() as s:
        # Rejected outputs are logged (for token accounting) but marked cached=True so they never serve as cache hits.
        s.add(ModelCall(task="usage-summary", provider="ollama", model=settings.small_model, input_hash=digest,
                        prompt_tokens=pt, completion_tokens=ct, duration_ms=ms, cost_usd=0.0, output=text,
                        cached=bool(bad)))
    if bad or not text:
        return {"source": "rules", "model": settings.small_model, "text": plain_summary(facts),
                "rejected": text, "error": f"Model summary discarded: it contained numbers not in the facts ({', '.join(bad[:5])})"
                if bad else "Model returned an empty summary",
                "prompt_tokens": pt, "completion_tokens": ct, "duration_ms": ms}
    return {"source": "ollama", "model": settings.small_model, "text": text,
            "prompt_tokens": pt, "completion_tokens": ct, "duration_ms": ms}
