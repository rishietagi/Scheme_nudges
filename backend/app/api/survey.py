"""Survey page: what we sent (per cohort, per language) and what came back, as of a sim day."""
from __future__ import annotations

import statistics
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.nodes import LANGS, Text, fill, lang_of, scheme_text
from app.api.sim import build_state, run_id
from app.db.conn import db
from app.db.run_queries import facts
from app.engines import sanity_checks, themes
from app.engines.cohorts import DISPLAY_ORDER
from app.llm.client import complete
from app.models import (Choice, FlagItem, Question, RatingItem, SanitySummary, SimState, SurveyQuestions, SurveyResults,
                        ThemeItem)
from app.rules.loader import survey_rules
from app.simulation import engine
from app.simulation.behaviour import NUDGE_AT, SURVEY_CLOSE
from app.simulation.clock import day_label

router = APIRouter(prefix="/survey", tags=["survey"])
RATING_LABELS = {"q2": "It's clear to me", "q3": "It helps my business", "q4": "I can reach my target", "q5": "Happy with payouts"}


@lru_cache
def i18n() -> dict:
    with open(Path(__file__).resolve().parents[1] / "content" / "survey_i18n.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _t(lang: str, kind: str, key: str, default: str) -> str:
    return i18n().get(lang, {}).get(kind, {}).get(key, default) if lang != "English" else default


def _day(con, day: float | None) -> tuple[str, float]:
    rid = run_id(con)
    cur = engine.state(con, rid)["day"]
    return rid, cur if day is None else max(0.0, min(day, cur))


@router.get("/questions", response_model=SurveyQuestions)
def questions(cohort: str = "Scheme-hesitant", lang: Literal["English", "Bengali", "Hindi"] = "English",
              day: float | None = None) -> SurveyQuestions:
    if cohort not in DISPLAY_ORDER:
        raise HTTPException(404, f"Unknown cohort {cohort!r}")
    rules = survey_rules()
    with db() as con:
        rid, d = _day(con, day)
        fs = [f for f in facts(con, rid, d).values() if f.cohort == cohort]
        example = fs[0]
        inputs = {"kind": "nudge", "cohort": cohort, "brief": rules["nudge_brief"][cohort], "scheme": scheme_text(con), "language": lang}
        text = fill(complete("nudge_message", inputs, Text, fixture_key=f"{cohort}|{lang}").text, example, lang)
    bn = sum(lang_of(f.language_on_file) == "Bengali" for f in fs)
    sent = d >= NUDGE_AT
    note = (f"Sent Day 0 · 10:00 to {len(fs)} distributors ({bn} in Bengali)" if sent
            else "Goes out Day 0 · 10:00")
    qs = []
    for q in rules["questions"]:
        opts = q.get("options") or q.get("options_by_cohort", {}).get(cohort) or []
        tag = {"rating_1_5": "1–5", "single_choice": "For this cohort", "open_text": "Optional"}.get(q["type"])
        qs.append(Question(id=q["id"], type=q["type"], text=_t(lang, "questions", q["id"], q["text"]), tag=tag,
                           options=[Choice(value=o, label=_t(lang, "options", o, o)) for o in opts]))
    return SurveyQuestions(day=d, cohort=cohort, language=lang, languages=list(LANGS), cohorts=DISPLAY_ORDER,
                           members=len(fs), example_distributor=example.name, nudge_text=text, nudge_note=note,
                           nudge_sent=sent, questions=qs)


@router.get("/results", response_model=SurveyResults)
def results(day: float | None = None) -> SurveyResults:
    intents = next(q for q in survey_rules()["questions"] if q["id"] == "Q1")["options"]
    with db() as con:
        rid, d = _day(con, day)
        fs = list(facts(con, rid, d).values())
    replied = [f for f in fs if f.replied]
    counted = [f for f in replied if f.counted]

    by_day = []
    for k in range(0, min(7, int(d)) + 1):
        cutoff = min(k + 1, d)
        by_day.append(sum(1 for f in replied if f.responses[0]["submitted_at"] <= cutoff))
    hours = [(f.responses[0]["submitted_at"] - (f.nudge_at or NUDGE_AT)) * 24 for f in replied]

    status = {f.distributor_id: sanity_checks.status([x["severity"] for x in f.latest_flags()]) for f in replied}
    flagged, check = [], []
    for f in sorted(replied, key=lambda f: f.latest["submitted_at"]):
        fl = f.latest_flags()
        if not fl:
            continue
        item = FlagItem(response_id=f.latest["response_id"], distributor_id=f.distributor_id, name=f.name,
                        reason=sanity_checks.short_reason([x["code"] for x in fl], f.latest),
                        codes=[x["code"] for x in fl], decision=f.decision())
        (flagged if status[f.distributor_id] == "Flagged" else check).append(item)

    ratings = []
    for q, label in RATING_LABELS.items():
        vals = [f.latest[q] for f in counted if f.latest[q] is not None]
        ratings.append(RatingItem(question=q.upper(), label=label, pct=round(sum(v >= 4 for v in vals) / len(vals), 4) if vals else None,
                                  answered=len(vals)))

    comments = [{"id": f.latest["response_id"], "text": f.latest["q7_text"], "tag": f.latest["q7_theme"]}
                for f in counted if f.latest["q7_text"] and not any(x["code"] == "JUNK_TEXT" for x in f.latest_flags())]
    return SurveyResults(
        day=d,
        day_label=day_label(d),
        open=d >= NUDGE_AT and d < SURVEY_CLOSE,
        closed=d >= SURVEY_CLOSE,
        sent=d >= NUDGE_AT,
        total=len(fs),
        replied=len(replied),
        replies_by_day=by_day,
        reminder_day=3,
        median_reply_hours=round(statistics.median(hours), 1) if hours else None,
        sanity=SanitySummary(clean=sum(s == "Clean" for s in status.values()), check=sum(s == "Check" for s in status.values()),
                             flagged=sum(s == "Flagged" for s in status.values())),
        flagged=flagged,
        to_check=check,
        intents={i: sum(1 for f in counted if f.latest["q1_intent"] == i) for i in intents},
        no_reply=len(fs) - len(replied),
        left_out=len(replied) - len(counted),
        ratings=ratings,
        themes=[ThemeItem(**t) for t in themes.count(comments)[:3]],
        comments=len(comments),
    )


class FlagDecisionIn(BaseModel):
    decision: Literal["Keep", "Drop"]


@router.post("/flags/{response_id}", response_model=SimState)
def flag_decision(response_id: str, body: FlagDecisionIn) -> SimState:
    with db() as con:
        try:
            engine.flag_decision(con, run_id(con), response_id, body.decision)
        except engine.SimError as e:
            raise HTTPException(409, str(e)) from e
        return build_state(con)
