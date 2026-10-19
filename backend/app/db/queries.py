"""Read queries over the Day-0 world. Never touches the hidden traits table (only app/simulation/traits.py may)."""
from __future__ import annotations

import json
import sqlite3

from app.content.terms import trade_terms
from app.db.conn import connect
from app.engines.cohorts import Assignment, assign_all
from app.rules.loader import CohortRules, effective_cohort_rules

# The app is logged in as Rahul Sen, ASM of Kolkata North.
ASM_ID = "ASM-01"
TERRITORY_ID = "TER-01"
CURRENT_SCHEME = "SCH-2627-FES"
LAST_SCHEME = "SCH-2627-MON"
Q2_MONTHS = ("2026-07", "2026-08", "2026-09")


_SNAPSHOTS: dict[str, dict[str, Assignment]] = {}


def snapshot_cohorts(con: sqlite3.Connection, run_id: str) -> CohortRules:
    """At Reset: fix this run's cohorts with the rules in force now (saved edits included)."""
    rules = effective_cohort_rules(con)
    rows = [(run_id, a.distributor_id, a.cohort, int(a.high_potential), int(a.high_performance), a.potential_l,
             a.performance_score, json.dumps(a.pillars), " · ".join(a.reasons))
            for a in assign_all(con, rules=rules).values()]
    con.executemany("INSERT OR REPLACE INTO run_cohorts VALUES (?,?,?,?,?,?,?,?,?)", rows)
    con.execute("INSERT OR REPLACE INTO run_config VALUES (?,?,?)", (run_id, "cohorts", rules.model_dump_json()))
    return rules


def effective_survey(con: sqlite3.Connection):
    from app.db.config_store import get_config
    from app.engines.survey_generator import SurveySettings, clean, default_settings

    saved = get_config(con, "survey")
    return clean(SurveySettings.model_validate(saved)) if saved else default_settings()


def snapshot_survey(con: sqlite3.Connection, run_id: str, rules: CohortRules) -> None:
    """At Reset: generate this cycle's questionnaire per cohort with the survey settings in force now."""
    from app.engines.survey_generator import generate

    s = effective_survey(con)
    qs = generate(s, [c.name for c in rules.cohorts], {c.name: c.definition for c in rules.cohorts})
    blob = {"settings": s.model_dump(), "questionnaires": {c: [q.model_dump() for q in v] for c, v in qs.items()}}
    con.execute("INSERT OR REPLACE INTO run_config VALUES (?,?,?)", (run_id, "survey", json.dumps(blob, ensure_ascii=False)))
    _SURVEYS.pop(run_id, None)


_SURVEYS: dict[str, dict] = {}


def run_survey(con: sqlite3.Connection, run_id: str | None = None) -> dict:
    """{cohort: [GenQuestion]} the run sent (generated with the defaults if the run predates the generator)."""
    from app.engines.survey_generator import GenQuestion, generate

    rid = run_id or _active_run(con)
    if rid in _SURVEYS:
        return _SURVEYS[rid]
    row = con.execute("SELECT json FROM run_config WHERE run_id = ? AND key = 'survey'", (rid,)).fetchone() if rid else None
    if row:
        out = {c: [GenQuestion.model_validate(q) for q in v] for c, v in json.loads(row[0])["questionnaires"].items()}
    else:
        rules = run_rules(con, rid)
        out = generate(effective_survey(con), [c.name for c in rules.cohorts], mode="mock")
    if rid:
        _SURVEYS[rid] = out
    return out


def run_rules(con: sqlite3.Connection, run_id: str | None = None) -> CohortRules:
    """The cohort rules a run started with (the current rules if there's no run yet)."""
    rid = run_id or _active_run(con)
    row = con.execute("SELECT json FROM run_config WHERE run_id = ? AND key = 'cohorts'", (rid,)).fetchone() if rid else None
    return CohortRules.model_validate(json.loads(row[0])) if row else effective_cohort_rules(con)


def _active_run(con: sqlite3.Connection) -> str | None:
    row = con.execute("SELECT run_id FROM loop_runs WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1").fetchone()
    return row[0] if row else None


def cohorts(con: sqlite3.Connection | None = None) -> dict[str, Assignment]:
    """Cohort agent output for every distributor, as fixed for the active run (cohorts don't change mid-cycle)."""
    own = con is None
    con = con or connect()
    try:
        rid = _active_run(con)
        if rid in _SNAPSHOTS:
            return _SNAPSHOTS[rid]
        rows = con.execute("SELECT * FROM run_cohorts WHERE run_id = ?", (rid,)).fetchall() if rid else []
        if not rows:
            return assign_all(con, rules=effective_cohort_rules(con))
        tags = {c.name: c.tag for c in run_rules(con, rid).cohorts}
        out = {r["distributor_id"]: Assignment(r["distributor_id"], r["cohort"], tags.get(r["cohort"], ""),
                                               r["reasons"].split(" · "), bool(r["high_potential"]),
                                               bool(r["high_performance"]), r["potential_l"], r["performance_score"],
                                               json.loads(r["pillars_json"]))
               for r in rows}
        _SNAPSHOTS[rid] = out
        return out
    finally:
        if own:
            con.close()


def territory(con: sqlite3.Connection) -> dict:
    t = con.execute(
        """SELECT t.territory_id, t.name, a.name AS asm_name, z.name AS zone
           FROM world.territories t JOIN world.asms a USING (asm_id) JOIN world.zones z USING (zone_id)
           WHERE t.territory_id = ?""",
        (TERRITORY_ID,),
    ).fetchone()
    agg = con.execute(
        """SELECT COUNT(*) n, SUM(f.secondary_fytd_l) fy, SUM(f.secondary_ly_same_period_l) ly,
                  SUM(f.joined_last_scheme) joined_last
           FROM world.distributor_features f JOIN world.distributors d USING (distributor_id)
           WHERE d.territory_id = ?""",
        (TERRITORY_ID,),
    ).fetchone()
    focus = con.execute(
        f"""SELECT SUM(b.focus_revenue_l) / SUM(b.secondary_value_l)
            FROM world.billing_monthly b JOIN world.distributors d USING (distributor_id)
            WHERE d.territory_id = ? AND b.month IN ({",".join("?" * len(Q2_MONTHS))})""",
        (TERRITORY_ID, *Q2_MONTHS),
    ).fetchone()[0]
    scheme = con.execute("SELECT scheme_id, name, rules_text FROM world.schemes WHERE scheme_id = ?", (CURRENT_SCHEME,)).fetchone()
    last = con.execute("SELECT name FROM world.schemes WHERE scheme_id = ?", (LAST_SCHEME,)).fetchone()
    company = con.execute("SELECT (SELECT COUNT(*) FROM world.distributors), (SELECT COUNT(*) FROM world.territories)").fetchone()
    return {
        "territory_id": t["territory_id"],
        "name": t["name"],
        "zone": t["zone"],
        "asm_name": t["asm_name"],
        "distributors": agg["n"],
        "secondary_fytd_l": round(agg["fy"], 1),
        "yoy_growth": round(agg["fy"] / agg["ly"] - 1, 4),
        "focus_share_q2": round(focus, 4),
        "joined_last_scheme": agg["joined_last"],
        "last_scheme_name": last["name"],
        "scheme_id": scheme["scheme_id"],
        "scheme_name": scheme["name"],
        "scheme_rules": trade_terms(scheme["rules_text"]),
        "company_distributors": company[0],
        "company_territories": company[1],
    }


def distributors(con: sqlite3.Connection) -> list[dict]:
    """Every Kolkata North distributor with the Day-0 fields the UI lists."""
    rows = con.execute(
        """SELECT d.distributor_id, d.name, d.owner_name, d.town, d.classification, d.preferred_language,
                  f.secondary_fytd_l, f.yoy_growth, f.past_schemes_joined, f.joined_last_scheme,
                  t.target_l, t.predicted_sales_if_enrolled_l, t.baseline_forecast_l
           FROM world.distributors d
           JOIN world.distributor_features f USING (distributor_id)
           JOIN world.scheme_targets t ON t.distributor_id = d.distributor_id AND t.scheme_id = ?
           WHERE d.territory_id = ?
           ORDER BY d.distributor_id""",
        (CURRENT_SCHEME, TERRITORY_ID),
    ).fetchall()
    c = cohorts(con)
    return [{**dict(r), "cohort": c[r["distributor_id"]].cohort, "reasons": c[r["distributor_id"]].reasons,
             "high_potential": c[r["distributor_id"]].high_potential,
             "high_performance": c[r["distributor_id"]].high_performance,
             "potential_l": c[r["distributor_id"]].potential_l,
             "performance_score": c[r["distributor_id"]].performance_score} for r in rows]


def distributor(con: sqlite3.Connection, distributor_id: str) -> dict | None:
    d = con.execute(
        """SELECT d.distributor_id, d.name, d.owner_name, d.town, d.classification, d.partner_since,
                  d.preferred_language, d.reply_window, d.phone_masked, d.channel,
                  f.secondary_fytd_l, f.yoy_growth, f.qoq_growth, f.focus_share_q2, f.unique_skus_sep,
                  f.days_since_last_invoice, f.past_schemes_joined,
                  t.baseline_forecast_l, t.target_l, t.stretch_target_l, t.predicted_sales_if_enrolled_l, t.reward_text
           FROM world.distributors d
           JOIN world.distributor_features f USING (distributor_id)
           JOIN world.scheme_targets t ON t.distributor_id = d.distributor_id AND t.scheme_id = ?
           WHERE d.distributor_id = ? AND d.territory_id = ?""",
        (CURRENT_SCHEME, distributor_id, TERRITORY_ID),
    ).fetchone()
    if d is None:
        return None
    months = con.execute(
        "SELECT month, secondary_value_l FROM world.billing_monthly WHERE distributor_id = ? ORDER BY month",
        (distributor_id,),
    ).fetchall()
    history = con.execute(
        """SELECT s.name, h.enrolled, h.achieved FROM world.scheme_history h JOIN world.schemes s USING (scheme_id)
           WHERE h.distributor_id = ? ORDER BY s.start_date""",
        (distributor_id,),
    ).fetchall()
    a = cohorts(con)[distributor_id]
    return {
        **dict(d),
        "reward_text": trade_terms(d["reward_text"]),
        "cohort": a.cohort,
        "cohort_tag": a.tag,
        "reasons": a.reasons,
        "billing": [{"month": m["month"], "secondary_l": m["secondary_value_l"]} for m in months],
        "history": [{"scheme": h["name"], "enrolled": bool(h["enrolled"]), "achieved": bool(h["achieved"])} for h in history],
    }
