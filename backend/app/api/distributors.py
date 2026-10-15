"""Distributor list + Distributor 360 (Day-0 profile; this cycle's journey and persona arrive in later phases)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db import queries
from app.db.conn import db
from app.models import Distributor360, DistributorList, DistributorRow

router = APIRouter(prefix="/distributors", tags=["distributors"])


def to_row(r: dict) -> DistributorRow:
    return DistributorRow(
        distributor_id=r["distributor_id"],
        name=r["name"],
        owner_name=r["owner_name"],
        town=r["town"],
        classification=r["classification"],
        language_on_file=r["preferred_language"],
        cohort=r["cohort"],
        reasons=r["reasons"],
        secondary_fytd_l=r["secondary_fytd_l"],
        yoy_growth=r["yoy_growth"],
        joined_last_scheme=bool(r["joined_last_scheme"]),
        target_l=r["target_l"],
    )


@router.get("", response_model=DistributorList)
def list_distributors(q: str | None = None, cohort: str | None = None, day: float | None = None) -> DistributorList:
    with db() as con:
        rows = queries.distributors(con)
    if cohort:
        rows = [r for r in rows if r["cohort"] == cohort]
    if q:
        needle = q.lower()
        rows = [r for r in rows if needle in r["name"].lower() or needle in r["town"].lower() or needle in r["owner_name"].lower()]
    return DistributorList(day=day or 0.0, cohort=cohort, total=len(rows), items=[to_row(r) for r in rows])


@router.get("/{distributor_id}", response_model=Distributor360)
def get_distributor(distributor_id: str, day: float | None = None) -> Distributor360:
    with db() as con:
        d = queries.distributor(con, distributor_id)
    if d is None:
        raise HTTPException(404, "Distributor not found in Kolkata North")
    return Distributor360(
        day=day or 0.0,
        language_on_file=d.pop("preferred_language"),
        key_account=d["classification"] == "A",
        **d,
    )
