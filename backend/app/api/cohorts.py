"""Cohort endpoints: the business-potential × performance 2×2 (rules/cohorts.yaml v4), fixed at Reset for the cycle."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.distributors import to_row, view_day
from app.db import queries
from app.db.conn import db
from app.db.run_queries import facts
from app.engines.cohorts import DISPLAY_ORDER, PILLARS, Assignment, describe
from app.models import AxisInfo, CohortCard, CohortKpis, CohortList, CohortPoint, DistributorList, WeightOut
from app.rules.loader import CohortRules, cohort_rules

router = APIRouter(prefix="/cohorts", tags=["cohorts"])


def axes(rules: CohortRules) -> dict:
    """Axis labels, plain-word rules, thresholds and weights — shared with the Cohort rules page."""
    words = describe(rules)
    pa, pe = rules.axes["potential"], rules.axes["performance"]
    default = cohort_rules()
    return dict(
        potential=AxisInfo(label=pa.label, high=pa.high, low=pa.low, rule=words["potential"]),
        performance=AxisInfo(label=pe.label, high=pe.high, low=pe.low, rule=words["performance"]),
        pillars_rule=words["pillars"], benchmark=words["benchmark"],
        potential_high=rules.t("potential_high"), performance_high=rules.t("performance_high"),
        weights=[WeightOut(key=k, label=rules.weights[k].label, explain=rules.weights[k].explain,
                           value=rules.weights[k].value, default=default.weights[k].value) for k in PILLARS],
    )


def points(rows: list[dict], assigned: dict[str, Assignment]) -> list[CohortPoint]:
    return [CohortPoint(distributor_id=r["distributor_id"], name=r["name"], town=r["town"],
                        cohort=assigned[r["distributor_id"]].cohort, potential_l=round(assigned[r["distributor_id"]].potential_l, 2),
                        score=assigned[r["distributor_id"]].performance_score) for r in rows]


def kpis(con, ids: list[str], assigned: dict[str, Assignment]) -> CohortKpis | None:
    if not ids:
        return None
    marks = ",".join("?" * len(ids))
    r = con.execute(f"SELECT SUM(secondary_fytd_l) fy, SUM(current_secondary_l_month) cur FROM world.distributor_features "
                    f"WHERE distributor_id IN ({marks})", ids).fetchone()
    a = [assigned[i] for i in ids]
    return CohortKpis(potential_l=round(sum(x.potential_l for x in a), 1), current_l=round(r["cur"], 1),
                      avg_score=round(sum(x.performance_score for x in a) / len(a), 1),
                      pillars={k: round(sum(x.pillars[k] for x in a) / len(a), 1) for k in PILLARS},
                      billing_fytd_l=round(r["fy"], 1))


@router.get("", response_model=CohortList)
def list_cohorts(day: float | None = None) -> CohortList:
    with db() as con:
        rules = queries.run_rules(con)
        rows = queries.distributors(con)
        assigned = queries.cohorts(con)
        rid, d = view_day(con, day)
        fs = facts(con, rid, d)
        cards = []
        for c in rules.cohorts:
            ids = [r["distributor_id"] for r in rows if r["cohort"] == c.name]
            cards.append(CohortCard(
                name=c.name, tag=c.tag, description=c.definition, color=c.color, count=len(ids),
                joined_last_scheme=sum(r["cohort"] == c.name and r["joined_last_scheme"] for r in rows),
                joined_festive=sum(1 for f in fs.values() if f.cohort == c.name and f.enrol),
                replied=sum(1 for f in fs.values() if f.cohort == c.name and f.replied),
                high_potential=c.cell.high_potential, high_performance=c.cell.high_performance,
                kpis=kpis(con, ids, assigned)))
        pts = points(rows, assigned)
    return CohortList(day=d, rule_version=rules.version, cohorts=cards, points=pts, **axes(rules))


@router.get("/{name:path}/distributors", response_model=DistributorList)
def cohort_members(name: str, day: float | None = None) -> DistributorList:
    if name not in DISPLAY_ORDER:
        raise HTTPException(404, f"Unknown cohort {name!r}")
    with db() as con:
        rows = [r for r in queries.distributors(con) if r["cohort"] == name]
        rid, d = view_day(con, day)
        fs = facts(con, rid, d)
    return DistributorList(day=d, cohort=name, total=len(rows), items=[to_row(r, fs[r["distributor_id"]], d) for r in rows])
