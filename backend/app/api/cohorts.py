"""Cohort endpoints. Cohorts are fixed at Day 0 for the whole cycle (rules/cohorts.yaml)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.distributors import to_row, view_day
from app.db import queries
from app.db.run_queries import facts
from app.db.conn import db
from app.engines.cohorts import COLOR, COPY, DISPLAY_ORDER
from app.models import CohortCard, CohortList, DistributorList
from app.rules.loader import cohort_rules

router = APIRouter(prefix="/cohorts", tags=["cohorts"])


@router.get("", response_model=CohortList)
def list_cohorts(day: float | None = None) -> CohortList:
    rules = cohort_rules()
    tags = {r.name: r.tag for r in rules.cohorts}
    with db() as con:
        rows = queries.distributors(con)
        rid, d = view_day(con, day)
        fs = facts(con, rid, d)
    cards = [
        CohortCard(
            name=c,
            tag=tags[c],
            description=COPY[c],
            color=COLOR[c],
            count=sum(r["cohort"] == c for r in rows),
            joined_last_scheme=sum(r["cohort"] == c and r["joined_last_scheme"] for r in rows),
            joined_festive=sum(1 for f in fs.values() if f.cohort == c and f.enrol),
            replied=sum(1 for f in fs.values() if f.cohort == c and f.replied),
        )
        for c in DISPLAY_ORDER
    ]
    return CohortList(day=d, rule_version=rules.version, cohorts=cards)


@router.get("/{name}/distributors", response_model=DistributorList)
def cohort_members(name: str, day: float | None = None) -> DistributorList:
    if name not in DISPLAY_ORDER:
        raise HTTPException(404, f"Unknown cohort {name!r}")
    with db() as con:
        rows = [r for r in queries.distributors(con) if r["cohort"] == name]
        rid, d = view_day(con, day)
        fs = facts(con, rid, d)
    return DistributorList(day=d, cohort=name, total=len(rows), items=[to_row(r, fs[r["distributor_id"]], d) for r in rows])
