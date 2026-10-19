"""Behaviour model (SIMULATION_SPEC §3): how each simulated distributor reacts.

Pure functions. Each (seed, distributor, purpose) gets its own RNG stream, so changing one thing never reshuffles
everyone. Anchors (rows with scripted_* values) follow their script; see PROJECT_CONTEXT §4.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from app.simulation.clock import at

NUDGE_AT = at(0, 10)          # Day 0 10:00
REMINDER_AT = at(3, 10)       # Day 3 10:00
SURVEY_CLOSE = 7.0            # replies after Day 7 00:00 don't count
CTA_AT = at(8, 10)            # Day 8 10:00
LAST = 30.0

WINDOWS = {"Morning": (9, 12), "Afternoon": (12, 16), "Evening": (17, 21)}
RATING_BASE = {"Invest / Expand": 4.2, "Protect": 3.9, "Replace / Reassess": 3.2, "Exit / Watchlist": 2.9}
Q6_FOR_INTENT = {
    "Explain in Bengali": {"Replace / Reassess": "Explanation in Bengali"},
    "Explain again": {"Replace / Reassess": "Simpler explanation", "Invest / Expand": "Clear slab examples",
                      "Protect": "Clear slab examples"},
    "Talk to my ASM": {"Invest / Expand": "ASM visit", "Replace / Reassess": "ASM visit", "Exit / Watchlist": "Call me"},
}

# Anchor details the script needs beyond the trait columns (PROJECT_CONTEXT §4).
ANCHOR_EXTRA = {
    "DST-0002": {"comment": ("একটা ছোট ভয়েস নোট পাঠান, বাংলায় বুঝিয়ে দিন।", "Bengali", "explain_simple")},
    "DST-0005": {"q6": "Better margin", "comment": ("Scheme is fine, but my margin needs to improve.", "English", "margin")},
    "DST-0009": {"sales": "stretch"},
}


def rng(seed: int, distributor_id: str, purpose: str) -> random.Random:
    return random.Random(f"{seed}:{distributor_id}:{purpose}")


@lru_cache
def text_bank() -> dict:
    with open(Path(__file__).with_name("text_bank.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def is_anchor(t: dict) -> bool:
    return t["scripted_intent"] is not None or t["scripted_note"] is not None


def _clock(r: random.Random, day: int, window: str, spread_h: float = 2.0) -> float:
    lo, _ = WINDOWS[window]
    return day + (lo + r.uniform(0, spread_h)) / 24


def _into_window(r: random.Random, when: float, window: str) -> float:
    """Most people reply inside their usual window; night replies always move to it."""
    lo, hi = WINDOWS[window]
    hour = (when % 1) * 24
    if lo <= hour < hi:
        return when
    if 7 <= hour < 22:
        if hour < lo and r.random() < 0.75:  # their window is later today: wait for it
            return int(when) + (lo + r.uniform(0, 1.5)) / 24
        if hour >= hi and r.random() < 0.25:  # missed today's window: read it tomorrow
            return int(when) + 1 + (lo + r.uniform(0, 1.5)) / 24
        return when
    day = int(when) if hour < 7 else int(when) + 1   # nobody replies at 3 am
    return day + (lo + r.uniform(0, 1.5)) / 24


# ------------------------------------------------------------------------------------------------ Day 0 → 7
@dataclass
class Reply:
    submitted_at: float
    survey_seconds: int
    q1: str | None
    answers: dict[str, int]                 # rating question id -> 1–5 (only the ones answered)
    q6: str | None
    q7_text: str | None
    q7_language: str | None
    q7_theme: str | None
    after_reminder: bool
    asked: int = 0                          # questions on their survey (comment excluded)
    duplicate_at: float | None = None


@dataclass
class Day0:
    reply: Reply | None
    enrol_day: float | None = None          # enrolment before any CTA
    enrol_path: str | None = None           # after_nudge | self
    notes: list[str] = field(default_factory=list)


def reply_time(seed: int, did: str, t: dict) -> tuple[float | None, bool]:
    """(submitted_at, came after the reminder)."""
    if is_anchor(t):
        if t["scripted_response_hours"] is None:
            return None, False
        return NUDGE_AT + t["scripted_response_hours"] / 24, False
    r = rng(seed, did, "reply")
    if r.random() < t["response_prob"]:
        when = _into_window(r, NUDGE_AT + t["median_response_hours"] * r.lognormvariate(0, 0.8) / 24, t["active_window"])
        if when < SURVEY_CLOSE:
            return when, False
    r2 = rng(seed, did, "reply-after-reminder")
    if r2.random() < 0.3 * t["response_prob"]:
        when = _into_window(r2, REMINDER_AT + t["median_response_hours"] * r2.lognormvariate(0, 0.8) / 24, t["active_window"])
        if when < SURVEY_CLOSE:
            return when, True
    return None, False


def intent(seed: int, did: str, t: dict) -> str:
    if t["scripted_intent"]:
        return t["scripted_intent"]
    r = rng(seed, did, "intent")
    if r.random() < t["enrol_prob_day0"]:
        return "I've enrolled"
    if r.random() < t["wants_asm_prob"]:
        return "Talk to my ASM"
    if t["understanding"] < 0.45:
        return "Explain in Bengali" if t["true_language"] == "Bengali" else "Explain again"
    if t["understanding"] < 0.6:
        return "Explain again"
    return "I'll enrol"


def _rate(r: random.Random, mean: float) -> int:
    return int(min(5, max(1, round(mean + r.gauss(0, 0.7)))))


@lru_cache
def answer_model() -> dict:
    with open(Path(__file__).with_name("answer_model.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def _mean(qid: str, t: dict, cohort: str) -> float:
    """How this distributor tends to rate a question (spec §3 for the scheme questions, answer_model for the rest)."""
    if qid == "SCHEME_CLEAR":
        return 1 + 4 * t["understanding"]
    if qid == "SCHEME_HELPS":
        return RATING_BASE.get(cohort, 3.4)
    if qid == "SCHEME_TARGET":
        return RATING_BASE.get(cohort, 3.4) - 0.4
    if qid == "INCENTIVE_PAYOUT":
        return 3.2
    m = answer_model()
    return m["means"].get(qid, m["custom_mean"]) + m["cohort_offset"].get(cohort, 0.0)


def survey(seed: int, did: str, t: dict, cohort: str, q1: str, submitted_at: float, after_reminder: bool,
           questions: list[dict]) -> Reply:
    """Answers the questionnaire this cohort was sent. `questions` = [{id, type}] in order (comment included)."""
    r = rng(seed, did, "survey")
    extra = ANCHOR_EXTRA.get(did, {})
    flags = (t["scripted_flags"] or "").split("|")
    anchor = is_anchor(t)
    low_effort = ("STRAIGHT_LINE" in flags) if anchor else r.random() < t["low_effort_prob"]
    ratings = [q["id"] for q in questions if q["type"] == "rating_1_5"]
    has_choice = any(q["type"] == "single_choice" for q in questions)
    has_comment = any(q["type"] == "open_text" for q in questions)
    asked = sum(q["type"] != "open_text" for q in questions)
    options = _q6_options(cohort)

    if low_effort:
        same = r.choice([3, 4, 5]) if not anchor else 5
        partial = not anchor and r.random() < 0.3
        seconds = t["scripted_survey_seconds"] or r.randint(8, 28)
        comment = (r.choice(text_bank()["junk"]), "English", None) if r.random() < 0.35 and has_comment else None
        if partial:                          # gave up after the first rating
            return Reply(submitted_at, seconds, q1, {ratings[0]: same} if ratings else {}, None,
                         *(comment or (None, None, None)), after_reminder, asked)
        return Reply(submitted_at, seconds, q1, {q: same for q in ratings}, r.choice(options) if has_choice else None,
                     *(comment or (None, None, None)), after_reminder, asked)

    answers = {q: _rate(r, _mean(q, t, cohort)) for q in ratings}
    if len(answers) >= 3 and len(set(answers.values())) == 1:   # careful respondents rarely give one number to everything
        last = ratings[-1]
        answers[last] = max(1, min(5, answers[last] + r.choice([-1, 1])))
    if anchor and q1.startswith("Explain") and "SCHEME_CLEAR" in answers:
        answers["SCHEME_CLEAR"] = 2
    q6 = (extra.get("q6") or Q6_FOR_INTENT.get(q1, {}).get(cohort) or r.choice(options)) if has_choice else None
    seconds = t["scripted_survey_seconds"] or int(round(110 * r.lognormvariate(0, 0.35)))
    if "comment" in extra and has_comment:
        text, lang, theme = extra["comment"]
    elif not anchor and has_comment and r.random() < 0.35:
        theme = _theme(r, q1, answers.get("SCHEME_TARGET", 3), answers.get("INCENTIVE_PAYOUT", 3))
        lang = "Bengali" if t["true_language"] == "Bengali" else "English"
        text = r.choice(text_bank()["themes"][theme]["bn" if lang == "Bengali" else "en"])
    else:
        text = lang = theme = None
    return Reply(submitted_at, seconds, q1, answers, q6, text, lang, theme, after_reminder, asked)


def _q6_options(cohort: str) -> list[str]:
    from app.rules.loader import survey_rules

    q6 = next(q for q in survey_rules()["questions"] if q["id"] == "Q6")
    return q6["options_by_cohort"][cohort]


def _theme(r: random.Random, q1: str, target: int, payouts: int) -> str:
    if q1.startswith("Explain") and r.random() < 0.8:
        return "explain_simple"
    if target <= 2:
        return "target_high"
    if payouts <= 2:
        return "payouts_slow"
    if q1 == "Talk to my ASM" and r.random() < 0.6:
        return "margin"
    themes, weights = ["positive", "stock", "target_high", "payouts_slow", "margin"], [35, 20, 15, 15, 15]
    return r.choices(themes, weights)[0]


def day0(seed: int, did: str, t: dict, cohort: str, questions: list[dict]) -> Day0:
    """Everything this distributor does between the nudge and the Day-7 plan."""
    when, after_reminder = reply_time(seed, did, t)
    if when is None:
        return Day0(reply=None)
    q1 = intent(seed, did, t)
    reply = survey(seed, did, t, cohort, q1, when, after_reminder, questions)
    r = rng(seed, did, "pre-cta")
    if not is_anchor(t) and r.random() < 0.02:
        reply.duplicate_at = when + r.uniform(3, 30) / 1440

    out = Day0(reply=reply)
    scripted = t["scripted_enrol_day"]
    if is_anchor(t):
        if scripted is not None and scripted < 8:
            day = when if scripted == 0 else _clock(r, int(scripted), t["active_window"])
            out.enrol_day, out.enrol_path = max(day, when), ("after_nudge" if q1 == "I've enrolled" else "self")
    elif q1 == "I've enrolled" and r.random() < 0.85:
        out.enrol_day, out.enrol_path = when, "after_nudge"
    elif q1 == "I'll enrol" and r.random() < 0.6:
        out.enrol_day = max(when + 0.05, _clock(r, r.randint(1, 6), t["active_window"]))
        out.enrol_path = "self"
    return out


# ------------------------------------------------------------------------------------------------ Day 8 → 30
def cta_join(
    seed: int, did: str, t: dict, *, approved: bool, matched: bool, renudge_non_responder: bool, call_day: float | None
) -> float | None:
    """Join day after the Day-8 follow-up (or None). `call_day` is set when the follow-up is an ASM call/visit."""
    r = rng(seed, did, "cta")
    scripted = t["scripted_enrol_day"]
    if is_anchor(t) and approved:
        if scripted is None or scripted < 8:
            return None
        return _clock(r, int(scripted), t["active_window"])
    p = t["enrol_prob_after_matching_cta"]
    if not approved:
        p *= 0.2
    elif renudge_non_responder:
        p *= 0.45
    elif not matched:
        p *= 0.4
    if r.random() >= p:
        return None
    day = int(call_day) + 1 if call_day is not None and approved else int(8 + 2 * r.lognormvariate(0, 0.5))
    when = _clock(r, day, t["active_window"])
    if when < CTA_AT + 0.05:                 # can't join before the follow-up lands
        when += 1
    return when if when < LAST else None


def october_sales(seed: int, did: str, t: dict, *, joined_day: float | None, predicted: float, baseline: float, stretch: float) -> float:
    r = rng(seed, did, "sales")
    if joined_day is None:
        return round(baseline * r.uniform(0.92, 1.05), 2)
    if ANCHOR_EXTRA.get(did, {}).get("sales") == "stretch":
        return round(stretch * r.uniform(1.0, 1.05), 2)
    if is_anchor(t):
        return round(predicted * r.uniform(1.03, 1.09), 2)
    p = t["hit_prediction_prob"] * (0.8 if joined_day > 15 else 1.0)
    return round(predicted * (r.uniform(1.0, 1.12) if r.random() < p else r.uniform(0.85, 0.99)), 2)
