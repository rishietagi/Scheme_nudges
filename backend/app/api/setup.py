"""Set-up pages: the business edits cohort rules and the survey here. Saved settings apply from the next cycle (Reset)."""
from __future__ import annotations

import json
from collections import defaultdict

from fastapi import APIRouter

from app.api.cohorts import axes, points
from app.db import queries
from app.db.config_store import clear_config, put_config, saved_at
from app.db.conn import db
from app.engines.cohorts import assign_all
from app.engines.survey_generator import MustAsk, SurveySettings, bank, clean, default_settings, defaults, generate
from app.models import (BankQuestion, CohortConfig, CohortConfigIn, CohortCount, CohortMove, GeneratedQuestion, MustAskOut,
                        SurveyConfig, SurveyConfigIn, ThresholdOut)
from app.rules.loader import CohortRules, cohort_rules, effective_cohort_rules

router = APIRouter(prefix="/config", tags=["set-up"])


def _view(con, rules: CohortRules) -> CohortConfig:
    default = cohort_rules()
    kn = assign_all(con, queries.TERRITORY_ID, rules)
    now = queries.cohorts(con)                    # what the running cycle uses
    kn_rows = queries.distributors(con)
    names = {r["distributor_id"]: r["name"] for r in kn_rows}
    moves: dict[tuple[str, str], list[str]] = defaultdict(list)
    for did, a in sorted(kn.items()):
        if did in now and now[did].cohort != a.cohort:
            moves[(now[did].cohort, a.cohort)].append(names.get(did, did))
    running = queries.run_rules(con)
    return CohortConfig(
        version=rules.version,
        thresholds=[ThresholdOut(key=k, label=t.label, unit=t.unit, value=t.value, default=default.thresholds[k].value,
                                 min=t.min, max=t.max) for k, t in rules.thresholds.items()],
        cohorts=[CohortCount(name=c.name, color=c.color, definition=c.definition, high_potential=c.cell.high_potential,
                             high_performance=c.cell.high_performance, count=sum(a.cohort == c.name for a in kn.values()))
                 for c in rules.cohorts],
        points=points(kn_rows, kn),
        customised=rules.model_dump() != default.model_dump(),
        saved_at=saved_at(con, "cohorts"),
        moves=[CohortMove(from_cohort=f, to_cohort=t, count=len(n), names=n[:5])
               for (f, t), n in sorted(moves.items(), key=lambda x: -len(x[1]))],
        current_run_differs=effective_cohort_rules(con).model_dump() != running.model_dump(),
        **axes(rules),
    )


@router.get("/cohorts", response_model=CohortConfig)
def get_cohort_config() -> CohortConfig:
    with db() as con:
        return _view(con, effective_cohort_rules(con))


@router.post("/cohorts/preview", response_model=CohortConfig)
def preview_cohort_config(body: CohortConfigIn) -> CohortConfig:
    with db() as con:
        return _view(con, cohort_rules().with_overrides(body.thresholds, body.definitions, body.weights))


@router.put("/cohorts", response_model=CohortConfig)
def save_cohort_config(body: CohortConfigIn) -> CohortConfig:
    with db() as con:
        rules = cohort_rules().with_overrides(body.thresholds, body.definitions, body.weights)
        put_config(con, "cohorts", {"thresholds": {k: t.value for k, t in rules.thresholds.items()},
                                    "weights": {k: w.value for k, w in rules.weights.items()},
                                    "definitions": {c.name: c.definition for c in rules.cohorts}})
        return _view(con, rules)


@router.delete("/cohorts", response_model=CohortConfig)
def reset_cohort_config() -> CohortConfig:
    with db() as con:
        clear_config(con, "cohorts")
        return _view(con, cohort_rules())



# ------------------------------------------------------------------------------------------------ survey generator
def _survey_view(con, s: SurveySettings, mode: str | None = None) -> SurveyConfig:
    d = defaults()
    rules = queries.run_rules(con)
    kn = queries.distributors(con)
    counts = {c.name: sum(r["cohort"] == c.name for r in kn) for c in rules.cohorts}
    qs = generate(s, [c.name for c in rules.cohorts], {c.name: c.definition for c in rules.cohorts}, mode=mode)
    running = con.execute("SELECT json FROM run_config WHERE run_id = (SELECT run_id FROM loop_runs WHERE is_active = 1 "
                          "ORDER BY created_at DESC LIMIT 1) AND key = 'survey'").fetchone()
    run_settings = SurveySettings.model_validate(json.loads(running[0])["settings"]) if running else None
    return SurveyConfig(
        use_case=d["use_case"]["name"], use_case_detail=d["use_case"]["detail"],
        questions_per_survey=s.questions_per_survey, min_questions=d["min_questions"], max_questions=d["max_questions"],
        must_ask=[MustAskOut(**m.model_dump()) for m in s.must_ask],
        buckets=bank()["buckets"], use_cases=list(bank()["use_cases"]),
        bank=[BankQuestion(id=q["id"], type=q["type"], bucket=q["bucket"], use_case=q["use_case"], topic=q["topic"],
                           text=q["text"]) for q in bank()["questions"] if q["id"] != "COMMENT"],
        cohorts=[CohortCount(name=c.name, color=c.color, definition=c.definition, high_potential=c.cell.high_potential,
                             high_performance=c.cell.high_performance, count=counts[c.name]) for c in rules.cohorts],
        questionnaires={c: [GeneratedQuestion(**q.model_dump()) for q in v] for c, v in qs.items()},
        customised=s.model_dump() != default_settings().model_dump(),
        saved_at=saved_at(con, "survey"),
        current_run_differs=run_settings is not None and run_settings.model_dump() != queries.effective_survey(con).model_dump(),
    )


def _settings(body: SurveyConfigIn) -> SurveySettings:
    return clean(SurveySettings(questions_per_survey=body.questions_per_survey,
                                must_ask=[MustAsk(**m.model_dump()) for m in body.must_ask]))


@router.get("/survey", response_model=SurveyConfig)
def get_survey_config() -> SurveyConfig:
    with db() as con:
        return _survey_view(con, queries.effective_survey(con), mode="replay")


@router.post("/survey/preview", response_model=SurveyConfig)
def preview_survey_config(body: SurveyConfigIn) -> SurveyConfig:
    with db() as con:
        return _survey_view(con, _settings(body), mode="replay")   # previews never wait on (or spend) live LLM calls


@router.put("/survey", response_model=SurveyConfig)
def save_survey_config(body: SurveyConfigIn) -> SurveyConfig:
    with db() as con:
        s = _settings(body)
        put_config(con, "survey", s.model_dump())
        return _survey_view(con, s)


@router.delete("/survey", response_model=SurveyConfig)
def reset_survey_config() -> SurveyConfig:
    with db() as con:
        clear_config(con, "survey")
        return _survey_view(con, default_settings(), mode="replay")
