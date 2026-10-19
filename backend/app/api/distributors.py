"""Distributor list + Distributor 360: Day-0 profile, this cycle's milestones and what we've learned so far."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api import stories
from app.content.terms import intent_label
from app.api.sim import run_id
from app.db import queries
from app.db.conn import db
from app.db.run_queries import Fact, facts
from app.engines.cohorts import PILLARS, raw_values
from app.models import (Distributor360, DistributorList, DistributorRow, Milestone, PersonaView, PillarOut, PotentialOut,
                        Scorecard)
from app.simulation import engine
from app.simulation.clock import day_label

router = APIRouter(prefix="/distributors", tags=["distributors"])


def view_day(con, day: float | None) -> tuple[str, float]:
    rid = run_id(con)
    cur = engine.state(con, rid)["day"]
    return rid, cur if day is None else max(0.0, min(day, cur))


def to_row(r: dict, f: Fact | None = None, day: float = 0.0) -> DistributorRow:
    extra = {}
    if f is not None:
        p = stories.persona_view(f, day)
        extra = dict(intent=intent_label(f.latest["q1_intent"]) if f.latest else None, flagged=f.red_flagged,
                     joined_day=int(f.enrol["sim_day"]) if f.enrol else None, language_now=p["language"],
                     language_changed=p["language_changed"])
    return DistributorRow(
        distributor_id=r["distributor_id"], name=r["name"], owner_name=r["owner_name"], town=r["town"],
        classification=r["classification"], language_on_file=r["preferred_language"], cohort=r["cohort"], reasons=r["reasons"],
        secondary_fytd_l=r["secondary_fytd_l"], yoy_growth=r["yoy_growth"], joined_last_scheme=bool(r["joined_last_scheme"]),
        target_l=r["target_l"], **extra,
    )


@router.get("", response_model=DistributorList)
def list_distributors(q: str | None = None, cohort: str | None = None, day: float | None = None) -> DistributorList:
    with db() as con:
        rid, d = view_day(con, day)
        rows = queries.distributors(con)
        fs = facts(con, rid, d)
    if cohort:
        rows = [r for r in rows if r["cohort"] == cohort]
    if q:
        needle = q.lower()
        rows = [r for r in rows if needle in r["name"].lower() or needle in r["town"].lower() or needle in r["owner_name"].lower()]
    return DistributorList(day=d, cohort=cohort, total=len(rows), items=[to_row(r, fs[r["distributor_id"]], d) for r in rows])


def scorecard(con, distributor_id: str) -> Scorecard:
    """Why this distributor sits in its cohort: the four pillars and the potential of their market, with the numbers."""
    rules = queries.run_rules(con)
    a = queries.cohorts(con)[distributor_id]
    f = dict(con.execute("SELECT f.*, d.town, d.territory_id FROM world.distributor_features f "
                         "JOIN world.distributors d USING (distributor_id) WHERE distributor_id = ?", (distributor_id,)).fetchone())
    tam = con.execute("SELECT SUM(tam_l_month) FROM world.markets WHERE territory_id = ? AND town = ?",
                      (f["territory_id"], f["town"])).fetchone()[0] or 0
    raw = raw_values(f)
    return Scorecard(
        potential=PotentialOut(town=f["town"], town_potential_l=f["town_emami_potential_l_month"], town_tam_l=round(tam, 1),
                               outlets_covered=f["outlets_covered"], coverage_share=f["outlet_coverage_share"],
                               potential_l=f["business_potential_l_month"], current_l=f["current_secondary_l_month"],
                               headroom_l=f["headroom_l_month"], threshold_l=rules.t("potential_high"), high=a.high_potential),
        pillars=[PillarOut(key=k, label=rules.weights[k].label, explain=rules.weights[k].explain, raw=raw[k],
                           score=a.pillars.get(k, 0), weight=rules.weights[k].value) for k in PILLARS],
        score=a.performance_score, threshold=rules.t("performance_high"), high=a.high_performance)


@router.get("/{distributor_id}", response_model=Distributor360)
def get_distributor(distributor_id: str, day: float | None = None) -> Distributor360:
    with db() as con:
        d = queries.distributor(con, distributor_id)
        if d is None:
            raise HTTPException(404, "Distributor not found in Kolkata North")
        rid, vd = view_day(con, day)
        f = facts(con, rid, vd)[distributor_id]
        sales = con.execute("SELECT * FROM october_sales WHERE run_id = ? AND distributor_id = ?", (rid, distributor_id)).fetchone()
        from app.api.chat import this_cycle

        cycle = this_cycle(con, rid, f) if vd >= 7.4 else None
        card = scorecard(con, distributor_id)
    return Distributor360(
        day=vd,
        language_on_file=d.pop("preferred_language"),
        key_account=d["classification"] == "A",
        festive_joined=f.enrol is not None,
        festive_join_label=day_label(f.enrol["sim_day"]).split(" · ")[0] if f.enrol else None,
        this_cycle=cycle,
        milestones=[Milestone(**m) for m in stories.milestones(f, dict(sales) if sales else None, vd)],
        persona=PersonaView(**stories.persona_view(f, vd)),
        scorecard=card,
        **d,
    )
