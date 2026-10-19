"""Survey sanity checks (rules/sanity_checks.yaml), run on every response as it arrives.

red   = left out of every number until the ASM keeps it
amber = counted, but listed under "check"
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.rules.loader import sanity_rules

CLARITY = "SCHEME_CLEAR"          # "How clear is the scheme to you?" (if the cohort was asked it)


@dataclass(frozen=True)
class Flag:
    code: str
    severity: str
    label: str


def _catalogue() -> dict[str, dict]:
    return {c["code"]: c for c in sanity_rules()["checks"]}


def _question_texts() -> list[str]:
    from app.engines.survey_generator import bank

    return [q["text"].lower() for q in bank()["questions"]]


def ratings(resp: dict) -> dict[str, int]:
    return {k: v for k, v in (resp.get("answers") or {}).items() if v is not None}


def answered(resp: dict) -> int:
    """Questions answered (the comment doesn't count)."""
    return sum(resp.get(k) not in (None, "") for k in ("q1_intent", "q6")) + len(ratings(resp))


def asked(resp: dict) -> int:
    return resp.get("questions_asked") or answered(resp)


def _junk(text: str) -> bool:
    s = text.strip()
    letters = sum(ch.isalpha() for ch in s)
    if letters < 3:
        return True
    compact = re.sub(r"\s+", "", s.lower())
    if len(set(compact)) <= 2:
        return True
    return s.lower() in _question_texts()


def check(resp: dict, *, enrolled_at_submit: bool, is_duplicate: bool) -> list[Flag]:
    cat = _catalogue()
    hits: list[str] = []
    if resp["survey_seconds"] < 30:
        hits.append("TOO_FAST")
    rated = list(ratings(resp).values())
    if len(rated) >= 3 and len(set(rated)) == 1:
        hits.append("STRAIGHT_LINE")
    if answered(resp) < 3:
        hits.append("INCOMPLETE")
    q1, clear = resp.get("q1_intent"), ratings(resp).get(CLARITY)
    if (q1 == "I've enrolled" and not enrolled_at_submit) or (q1 == "Explain again" and clear is not None and clear >= 4):
        hits.append("CONTRADICTION")
    if is_duplicate:
        hits.append("DUPLICATE")
    if resp.get("q7_text") and _junk(resp["q7_text"]):
        hits.append("JUNK_TEXT")
    return [Flag(c, cat[c]["severity"], cat[c]["label"]) for c in hits]


def status(severities: list[str]) -> str:
    """Clean · Check · Flagged."""
    if "red" in severities:
        return "Flagged"
    if "amber" in severities:
        return "Check"
    return "Clean"


def counts_in_numbers(severities: list[str], decision: str | None) -> bool:
    """Red stays out until kept; Drop removes any response for good."""
    if decision == "Drop":
        return False
    return "red" not in severities or decision == "Keep"


def short_reason(codes: list[str], resp: dict) -> str:
    """'19 seconds · same rating everywhere · says enrolled but isn't' (as on the Survey render)."""
    parts = []
    for c in codes:
        if c == "TOO_FAST":
            parts.append(f"Filled in {resp['survey_seconds']} seconds" if len(codes) == 1 else f"{resp['survey_seconds']} seconds")
        elif c == "STRAIGHT_LINE":
            parts.append("Same rating for every question" if len(codes) == 1 else "same rating everywhere")
        elif c == "INCOMPLETE":
            parts.append(f"answered {answered(resp)} of {asked(resp)} questions")
        elif c == "CONTRADICTION":
            parts.append("says participating but isn't" if resp.get("q1_intent") == "I've enrolled" else "answers don't match")
        elif c == "DUPLICATE":
            parts.append("submitted twice")
        elif c == "JUNK_TEXT":
            parts.append("comment looks like junk")
    text = " · ".join(parts)
    return text[:1].upper() + text[1:]
