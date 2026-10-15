"""Survey sanity checks (rules/sanity_checks.yaml), run on every response as it arrives.

red   = left out of every number until the ASM keeps it
amber = counted, but listed under "check"
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.rules.loader import sanity_rules, survey_rules

RATINGS = ("q2", "q3", "q4", "q5")
ANSWERS = ("q1_intent", "q2", "q3", "q4", "q5", "q6")


@dataclass(frozen=True)
class Flag:
    code: str
    severity: str
    label: str


def _catalogue() -> dict[str, dict]:
    return {c["code"]: c for c in sanity_rules()["checks"]}


def _question_texts() -> list[str]:
    return [q["text"].lower() for q in survey_rules()["questions"]]


def answered(resp: dict) -> int:
    return sum(resp.get(k) not in (None, "") for k in ANSWERS)


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
    ratings = [resp.get(k) for k in RATINGS]
    if all(v is not None for v in ratings) and len(set(ratings)) == 1:
        hits.append("STRAIGHT_LINE")
    if answered(resp) < 3:
        hits.append("INCOMPLETE")
    q1, q2 = resp.get("q1_intent"), resp.get("q2")
    if (q1 == "I've enrolled" and not enrolled_at_submit) or (q1 == "Explain again" and q2 is not None and q2 >= 4):
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
            parts.append(f"answered {answered(resp)} of 6 questions")
        elif c == "CONTRADICTION":
            parts.append("says enrolled but isn't" if resp.get("q1_intent") == "I've enrolled" else "answers don't match")
        elif c == "DUPLICATE":
            parts.append("submitted twice")
        elif c == "JUNK_TEXT":
            parts.append("comment looks like junk")
    text = " · ".join(parts)
    return text[:1].upper() + text[1:]
