"""Provider-agnostic LLM wrapper. One entry point: complete(prompt_id, inputs, schema) -> validated Pydantic object.

Modes (LLM_MODE):
  live    call the provider; on failure fall back to cache, then fixture
  record  like live, and cache every success by hash(prompt_id + version + inputs)
  replay  cache only; fixture on a miss (use for the board demo)
  mock    fixtures only, no network (tests, offline)

The LLM writes text only. Inputs must never contain hidden simulator traits — `complete` refuses them.
"""
from __future__ import annotations

import hashlib
import json
import re
import logging
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from app.config import settings

log = logging.getLogger("llm")
HERE = Path(__file__).parent
PROMPTS, CACHE, FIXTURES = HERE / "prompts", HERE / "cache", HERE / "fixtures"
TIMEOUT_S = 15                 # Gemini rejects deadlines under 10 s
T = TypeVar("T", bound=BaseModel)

# Hidden-trait field names that must never reach a prompt.
FORBIDDEN = {
    "true_language", "active_window", "response_prob", "median_response_hours", "understanding", "wants_asm_prob",
    "enrol_prob_day0", "enrol_prob_after_matching_cta", "low_effort_prob", "hit_prediction_prob", "scripted_intent",
    "scripted_response_hours", "scripted_survey_seconds", "scripted_flags", "scripted_enrol_day", "scripted_note",
}


class LeakError(ValueError):
    pass


_cooldown_until = 0.0     # after a 429, skip live calls until the provider's retry time (fail fast to cache/fallback)


def _retry_after(err: Exception) -> float:
    m = re.search(r"retry in ([\d.]+)s|retryDelay': '(\d+)s", str(err))
    return float(next(g for g in m.groups() if g)) if m else 30.0


def _keys(obj) -> set[str]:
    if isinstance(obj, dict):
        return set(obj) | {k for v in obj.values() for k in _keys(v)}
    if isinstance(obj, list):
        return {k for v in obj for k in _keys(v)}
    return set()


@lru_cache
def _prompt(prompt_id: str) -> str:
    return (PROMPTS / f"{prompt_id}.md").read_text(encoding="utf-8")


@lru_cache
def _fixtures(prompt_id: str) -> dict:
    with open(FIXTURES / f"{prompt_id}.json", encoding="utf-8") as f:
        return json.load(f)


def render(prompt_id: str, inputs: dict) -> str:
    return _prompt(prompt_id).replace("{{inputs}}", json.dumps(inputs, ensure_ascii=False, indent=2))


def cache_key(prompt_id: str, inputs: dict) -> str:
    blob = json.dumps({"p": prompt_id, "v": _prompt(prompt_id), "i": inputs}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def _cache_path(prompt_id: str, inputs: dict) -> Path:
    return CACHE / prompt_id / f"{cache_key(prompt_id, inputs)}.json"


def fixture(prompt_id: str, fixture_key: str | None) -> dict:
    fx = _fixtures(prompt_id)
    if fixture_key and fixture_key in fx:
        return fx[fixture_key]
    if fixture_key and "|" in fixture_key:              # e.g. "VOICE_EXPLAINER|Hindi" -> "VOICE_EXPLAINER|English"
        base = fixture_key.split("|")[0] + "|English"
        if base in fx:
            return fx[base]
    return fx["default"]


def _call_provider(prompt: str, schema: type[BaseModel]) -> str:
    if settings.llm_provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL") or None, timeout=TIMEOUT_S)
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt + "\n\nReturn only JSON matching this schema:\n"
                       + json.dumps(schema.model_json_schema())}],
            response_format={"type": "json_object"},
        )
        return r.choices[0].message.content or ""
    from google import genai

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"), http_options={"timeout": TIMEOUT_S * 1000})
    model = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
    config = {"response_mime_type": "application/json", "response_schema": schema, "temperature": 0.4}
    if "2.5" in model:
        config["thinking_config"] = {"thinking_budget": 0}   # short copywriting: thinking only adds latency
    r = client.models.generate_content(model=model, contents=prompt, config=config)
    return r.text or ""


def complete(prompt_id: str, inputs: dict, schema: type[T], fixture_key: str | None = None, mode: str | None = None,
             fallback: dict | None = None) -> T:
    """`fallback` (optional) replaces the fixture: a code-built answer from computed numbers, so text that carries
    numbers is always right even with no LLM."""
    leaked = _keys(inputs) & FORBIDDEN
    if leaked:
        raise LeakError(f"Refusing to send hidden traits to the LLM: {sorted(leaked)}")
    mode = mode or settings.llm_mode
    path = _cache_path(prompt_id, inputs)

    global _cooldown_until
    if mode in ("live", "record") and time.time() >= _cooldown_until:
        prompt = render(prompt_id, inputs)
        for attempt in range(2):                         # one retry
            try:
                out = schema.model_validate_json(_call_provider(prompt, schema))
                if mode == "record":
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(out.model_dump_json(indent=2), encoding="utf-8")
                return out
            except Exception as e:                       # timeouts, 429s, bad JSON: fall back, never break the demo
                log.warning("LLM %s attempt %d failed: %s", prompt_id, attempt + 1, str(e)[:160])
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    _cooldown_until = time.time() + _retry_after(e)
                    break
    if mode != "mock" and path.exists():
        return schema.model_validate_json(path.read_text(encoding="utf-8"))
    if fallback is not None:
        return schema.model_validate(fallback)
    return schema.model_validate(fixture(prompt_id, fixture_key))


def chat_mode() -> str:
    """Live typing in the Distributor view may call the LLM even when the rest of the demo replays from cache."""
    if settings.llm_mode == "mock":
        return "mock"
    return "live" if os.getenv("LLM_CHAT_LIVE", "false").lower() == "true" else settings.llm_mode
