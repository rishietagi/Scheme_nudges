"""Territory endpoints (Kolkata North, the logged-in ASM's patch)."""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter

from app.db import queries
from app.db.conn import db
from app.engines.cohorts import DISPLAY_ORDER
from app.models import TerritorySummary

router = APIRouter(prefix="/territory", tags=["territory"])


@router.get("/summary", response_model=TerritorySummary)
def summary(day: float | None = None) -> TerritorySummary:
    with db() as con:
        t = queries.territory(con)
        counts = Counter(d["cohort"] for d in queries.distributors(con))
    return TerritorySummary(day=day or 0.0, **t, cohorts={c: counts[c] for c in DISPLAY_ORDER})
