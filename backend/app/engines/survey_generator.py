"""Survey generator: one questionnaire per cohort.

Order: must-ask for everyone → must-ask for this cohort → Emami AI fills the rest from the CX bank
(rules/survey_bank.yaml), up to the number of questions the business chose. Code picks every question (ranked by the
cohort's focus use cases, spreading across the journey buckets); the LLM only rewords the picked ones and writes a
one-line "why". The optional comment always comes last and doesn't count.
"""
from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache

import yaml
from pydantic import BaseModel, Field

from app.config import settings
from app.engines.cohorts import DISPLAY_ORDER
from app.llm.client import complete

LANGS = ("English", "Bengali", "Hindi")
CORE = {"SCHEME_INTENT", "COMMENT"}           # never picked by the AI (the intent is must-ask; the comment always ends)


class MustAsk(BaseModel):
    id: str
    scope: str = "all"                        # all | a cohort name
    locked: bool = False
    text: str | None = None                   # the business's own wording (custom questions)


class SurveySettings(BaseModel):
    questions_per_survey: int = 7
    must_ask: list[MustAsk] = Field(default_factory=list)


class GenQuestion(BaseModel):
    id: str
    type: str                                 # quick_reply | rating_1_5 | single_choice | open_text
    bucket: str
    use_case: str
    topic: str
    short: str = ""                           # 1–3 words for the phone card and the 360
    text: dict[str, str]                      # language -> wording
    source: str                               # must_all | must_cohort | ai | comment
    why: str | None = None
    locked: bool = False


class _Worded(BaseModel):
    id: str
    text: str
    why: str


class _Wording(BaseModel):
    questions: list[_Worded]


@lru_cache
def bank() -> dict:
    with open(settings.rules_dir / "survey_bank.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def defaults() -> dict:
    with open(settings.rules_dir / "survey_config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def default_settings() -> SurveySettings:
    d = defaults()
    return SurveySettings(questions_per_survey=d["questions_per_survey"], must_ask=[MustAsk(**m) for m in d["must_ask"]])


def by_id() -> dict[str, dict]:
    return {q["id"]: q for q in bank()["questions"]}


def clean(s: SurveySettings) -> SurveySettings:
    """Clamp the count, keep the locked defaults, drop unknown or duplicate entries."""
    d = defaults()
    n = min(d["max_questions"], max(d["min_questions"], s.questions_per_survey))
    known = by_id()
    out: list[MustAsk] = [m for m in default_settings().must_ask if m.locked]
    seen = {(m.id, m.scope) for m in out}
    for m in s.must_ask:
        if (m.id, m.scope) in seen or m.locked or m.id == "COMMENT" or m.scope not in ("all", *DISPLAY_ORDER):
            continue
        text = (m.text or "").strip()
        if m.id not in known:
            if not text:
                continue
            m = MustAsk(id=f"CUSTOM_{sum(x.id.startswith('CUSTOM_') for x in out) + 1}", scope=m.scope, text=text)
        seen.add((m.id, m.scope))
        out.append(MustAsk(id=m.id, scope=m.scope, text=text if m.id.startswith("CUSTOM_") else None))
    return SurveySettings(questions_per_survey=n, must_ask=out)


def _from_bank(q: dict, source: str, locked: bool = False, why: str | None = None) -> GenQuestion:
    return GenQuestion(id=q["id"], type=q["type"], bucket=q["bucket"], use_case=q["use_case"], topic=q["topic"],
                       short=q.get("short", q["topic"]), text={"English": q["text"], "Bengali": q.get("bn", q["text"]), "Hindi": q.get("hi", q["text"])},
                       source=source, why=why, locked=locked)


def _custom(m: MustAsk, source: str) -> GenQuestion:
    return GenQuestion(id=m.id, type="rating_1_5", bucket="Overall", use_case="Business question", topic=m.text or m.id,
                       short="Your question", text={lang: m.text or m.id for lang in LANGS}, source=source)


SPREAD = 3      # each question already on the survey from a use case lowers that use case's next pick by this much


def _pick(cohort: str, taken: set[str], k: int) -> list[dict]:
    """Greedy, deterministic: the cohort's focus use cases first (most important first), spread so one use case
    doesn't take over; within a use case, bank order (the bank lists the most useful question first)."""
    focus = bank()["cohort_focus"].get(cohort, [])
    known = by_id()
    used = Counter(known[t]["use_case"] for t in taken if t in known)
    pool = [q for q in bank()["questions"] if q["id"] not in taken and q["id"] not in CORE and q["id"] != "DEALER_SCORE"]
    picked: list[dict] = []
    for _ in range(min(k, len(pool))):
        def score(i_q: tuple[int, dict]) -> tuple:
            i, q = i_q
            base = 100 if q.get("pick_first") else (10 - focus.index(q["use_case"]) if q["use_case"] in focus else 0)
            return (-(base - SPREAD * used[q["use_case"]]), i)
        _, best = min(enumerate(pool), key=score)
        picked.append(best)
        used[best["use_case"]] += 1
        pool.remove(best)
    return picked


def _why(q: dict, cohort: str) -> str:
    return f"For {cohort}: {bank()['use_cases'][q['use_case']]['why']}"


def _ok(text: str) -> bool:
    return text.endswith("?") and 3 <= len(text.split()) <= 14 and not re.search(r"\d", text)


def generate(s: SurveySettings, cohorts: list[str], definitions: dict[str, str] | None = None,
             mode: str | None = None) -> dict[str, list[GenQuestion]]:
    s = clean(s)
    known = by_id()
    out: dict[str, list[GenQuestion]] = {}
    for cohort in cohorts:
        qs: list[GenQuestion] = []
        for scope, source in (("all", "must_all"), (cohort, "must_cohort")):
            for m in s.must_ask:
                if m.scope == scope and m.id not in {q.id for q in qs}:
                    qs.append(_from_bank(known[m.id], source, m.locked) if m.id in known else _custom(m, source))
        picks = _pick(cohort, {q.id for q in qs}, max(0, s.questions_per_survey - len(qs)))
        fallback = {"questions": [{"id": q["id"], "text": q["text"], "why": _why(q, cohort)} for q in picks]}
        worded = {w.id: w for w in complete(
            "survey_questions",
            {"cohort": cohort, "definition": (definitions or {}).get(cohort, ""), "use_case": defaults()["use_case"],
             "picked": [{"id": q["id"], "topic": q["topic"], "bucket": q["bucket"], "default_text": q["text"]} for q in picks]},
            _Wording, mode=mode, fallback=fallback).questions}
        for q in picks:
            g = _from_bank(q, "ai", why=_why(q, cohort))
            w = worded.get(q["id"])
            if w and _ok(w.text.strip()):
                g.text["English"] = w.text.strip()
                g.why = w.why.strip() or g.why
            qs.append(g)
        qs.append(_from_bank(known["COMMENT"], "comment"))
        out[cohort] = qs
    return out
