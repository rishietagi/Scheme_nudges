"""Day-30 results: five plain questions, what we learned, and 'Apply to next scheme' (saves the learned personas)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.nodes import ASM, emit
from app.api.distributors import view_day
from app.api.stories import persona_view
from app.db import queries
from app.db.conn import db
from app.db.run_queries import facts
from app.engines import results as results_engine
from app.engines.cohorts import COLOR
from app.engines.next_cycle import next_quarter
from app.llm.client import complete
from app.models import AppliedProfile, ResultsView, SummaryLine
from app.simulation.behaviour import LAST
from app.simulation.clock import day_label

router = APIRouter(prefix="/results", tags=["results"])
PREVIEW = ["DST-0001", "DST-0007", "DST-0011"]          # Maa Tara · Annapurna · Nabadiganta


class Lines(BaseModel):
    lines: list[str]


def _draft(r: dict, plan_cta: dict[str, str]) -> list[str]:
    """Three lines written by code from the numbers; the LLM may only rephrase them."""
    last = last_scheme_by_cohort()
    best = max(r["joined_by_cohort"], key=lambda c: (c["joined"] - last.get(c["cohort"], 0)) / c["total"])
    cta = plan_cta.get(best["cohort"])
    if cta in ("VOICE_EXPLAINER", "EXPLAIN_SIMPLE"):
        l1 = (f"Explaining the scheme simply, in their own language, moved the {best['cohort']} group: "
              f"{best['joined']} of {best['total']} now participating (last scheme {last.get(best['cohort'], 0)}).")
    else:
        l1 = f"{best['cohort']} moved most: {best['joined']} of {best['total']} participating, up from {last.get(best['cohort'], 0)} last scheme."
    fu = sorted(r["follow_ups"], key=lambda f: f["rate"])
    worst = fu[0] if fu else None
    if worst and worst["cta_code"] == "RE_NUDGE":
        l2 = f"Re-sending to people who never replied didn't work ({worst['joined']} of {worst['received']}). Next time, {ASM} visits them."
    elif worst:
        l2 = f"The weakest action was the {worst['label'].lower()}: {worst['joined']} of {worst['received']} started participating."
    else:
        l2 = "No actions were sent this cycle."
    lift = r["sales_lift_joined"]
    l3 = (f"{r['beat_prediction']} of the {r['joined']} participants beat their predicted uplift; "
          f"their secondary sales ran {lift * 100:+.0f}% vs baseline." if lift is not None else f"{r['beat_prediction']} beat their predicted uplift.")
    return [l1, l2, l3]


def last_scheme_by_cohort() -> dict[str, int]:
    from app.api.cohorts import list_cohorts

    return {c.name: c.joined_last_scheme for c in list_cohorts().cohorts}


@router.get("", response_model=ResultsView)
def get_results(day: float | None = None) -> ResultsView:
    with db() as con:
        rid, d = view_day(con, day)
        run = con.execute("SELECT * FROM loop_runs WHERE run_id = ?", (rid,)).fetchone()
        fs = facts(con, rid, d)
        joined_now = sum(1 for f in fs.values() if f.enrol)
        if d < LAST:
            return ResultsView(day=d, day_label=day_label(d), ready=False, results_day_label=day_label(LAST), joined_so_far=joined_now,
                               total=len(fs), applied=False)
        sales = {r["distributor_id"]: dict(r) for r in con.execute("SELECT * FROM october_sales WHERE run_id = ?", (rid,))}
        t = queries.territory(con)
        plan_cta = {r["group_name"]: r["cta_code"] for r in con.execute(
            "SELECT group_name, cta_code FROM cta_plan WHERE run_id = ? AND group_type = 'cohort'", (rid,))}
        applied_at = con.execute("SELECT MAX(applied_at) FROM next_cycle_profiles WHERE from_run_id = ?", (rid,)).fetchone()[0]
        nq = next_quarter(con, fs, sales, queries.run_rules(con, rid))
        nq.pop("next_cohorts")

    r = results_engine.compute(fs, sales, t["joined_last_scheme"])
    personas = [persona_view(f, d) | {"best_time_bucket": _bucket(f, d)} for f in fs.values()]
    chips = [
        {"value": sum(1 for p in personas if p["language_changed"] and p["language"] == "Bengali"), "label": "now get Bengali"},
        {"value": sum(1 for p in personas if p["prefers"] == "ASM call"), "label": f"prefer a call from {ASM}"},
        {"value": sum(1 for p in personas if p["best_time_bucket"] == "Evening"), "label": "reply best in the evening"},
        {"value": sum(1 for p in personas if p["prefers"] == "ASM visit"), "label": "to get a visit, not WhatsApp"},
    ]
    draft = _draft(r, plan_cta)
    out = complete("results_summary", {"facts": draft}, Lines, fallback={"lines": draft})
    lines = out.lines if len(out.lines) == len(draft) else draft
    pct = round(100 * r["joined"] / r["total"])
    last_pct = round(100 * r["last_scheme_joined"] / r["total"])
    headline = (f"{r['joined']} of {r['total']} are participating. Up from {last_pct}% last time." if pct > last_pct
                else f"{r['joined']} of {r['total']} are participating, against {last_pct}% last time.")
    for c in r["joined_by_cohort"]:
        c["color"] = COLOR[c["cohort"]]
    return ResultsView(day=d, day_label=day_label(d), ready=True, results_day_label=day_label(LAST), joined_so_far=joined_now,
                       total=r["total"], headline=headline, results=r, learned=[SummaryLine(text=x, bold=False) for x in lines],
                       chips=chips, applied=applied_at is not None, applied_at=applied_at, run_scenario=run["scenario"],
                       next_quarter=nq)


def _bucket(f, d) -> str | None:
    from app.engines.persona import compute

    return compute(f, d)["best_time"]


@router.post("/apply", response_model=list[AppliedProfile])
def apply_to_next_scheme() -> list[AppliedProfile]:
    """Save what we learned about each distributor; the next scheme's nudge starts from these profiles."""
    with db() as con:
        rid, d = view_day(con, None)
        if d < LAST:
            raise HTTPException(409, "Results are ready on Day 30")
        rows = [dict(r) for r in con.execute("SELECT * FROM personas WHERE run_id = ?", (rid,))]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for p in rows:
            con.execute("INSERT OR REPLACE INTO next_cycle_profiles VALUES (?,?,?,?,?,?,?)",
                        (p["distributor_id"], p["language"], p["best_hour"], p["prefers"], p["next_time"], rid, now))
        changed = sum(1 for p in rows if p["language_changed"])
        fs = facts(con, rid, d)
        sales = {r["distributor_id"]: dict(r) for r in con.execute("SELECT * FROM october_sales WHERE run_id = ?", (rid,))}
        nq = next_quarter(con, fs, sales, queries.run_rules(con, rid))
        con.execute("INSERT OR REPLACE INTO run_config VALUES (?,?,?)", (rid, "next_cohorts", json.dumps(nq["next_cohorts"])))
        emit(con, rid, d, "PERSONA", "Persona",
             f"Applied to the next cycle: {len(rows)} profiles saved ({changed} language changes) and cohorts refreshed "
             f"({nq['moved']} move). The next nudge starts from them.",
             payload={"profiles": len(rows)})
        names = {r[0]: r[1] for r in con.execute("SELECT distributor_id, name FROM world.distributors WHERE distributor_id IN (?,?,?)", PREVIEW)}
        cohort = {d: a.cohort for d, a in queries.cohorts().items()}
        out = [AppliedProfile(distributor_id=p["distributor_id"], name=names[p["distributor_id"]], cohort=cohort[p["distributor_id"]], language=p["language"],
                              prefers=p["prefers"], next_time=p["next_time"]) for p in rows if p["distributor_id"] in PREVIEW]
    order = {d: i for i, d in enumerate(PREVIEW)}
    return sorted(out, key=lambda a: order[a.distributor_id])


@router.get("/applied", response_model=list[AppliedProfile])
def applied() -> list[AppliedProfile]:
    with db() as con:
        rows = con.execute(
            "SELECT p.*, d.name FROM next_cycle_profiles p JOIN world.distributors d USING (distributor_id) WHERE p.distributor_id IN (?,?,?)",
            PREVIEW).fetchall()
    order = {d: i for i, d in enumerate(PREVIEW)}
    cohort = {d: a.cohort for d, a in queries.cohorts().items()}
    return sorted([AppliedProfile(distributor_id=r["distributor_id"], name=r["name"], cohort=cohort[r["distributor_id"]], language=r["language"], prefers=r["prefers"],
                                  next_time=r["next_time"]) for r in rows], key=lambda a: order[a.distributor_id])

