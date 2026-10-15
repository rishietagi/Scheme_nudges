"""Approval matrix: one CTA per cohort + Individual attention + custom groups. Decisions let the run continue."""
from __future__ import annotations

import asyncio
import json
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.nodes import PLAN_AT, fill, members_at
from app.api.sim import build_state, run_id
from app.db.conn import db
from app.db.run_queries import facts
from app.engines.cta_planner import DISPLAY, catalogue
from app.models import CatalogueItem, Candidate, PlanRow, PlanView, SimState
from app.simulation import engine
from app.simulation.behaviour import CTA_AT
from app.simulation.clock import day_label, to_datetime
from app.simulation.player import player

router = APIRouter(prefix="/plan", tags=["plan"])


def _row(r: dict, day: float, example) -> PlanRow:
    status = r["status"] if r["decided_at"] is None or r["decided_at"] <= day else "Pending"
    preview = {}
    if example is not None and r["cta_code"]:
        for lang, col in (("English", "text_en"), ("Bengali", "text_bn")):
            if r[col]:
                preview[lang] = fill(r[col], example, lang)
    return PlanRow(
        row_id=r["row_id"], group_type=r["group_type"], group_name=r["group_name"], distributor_id=r["distributor_id"],
        cta_code=r["cta_code"], cta_variant=r["cta_variant"], label=r["label"], reason=r["reason"], why=r["why"],
        members=r["members"], confidence=r["confidence"], priority=r["priority"], status=status, preview=preview,
        children=[],
    )


@router.get("", response_model=PlanView)
def get_plan(day: float | None = None) -> PlanView:
    with db() as con:
        rid = run_id(con)
        st = engine.state(con, rid)
        d = st["day"] if day is None else max(0.0, min(day, st["day"]))
        run = con.execute("SELECT * FROM loop_runs WHERE run_id = ?", (rid,)).fetchone()
        send = to_datetime(CTA_AT)
        base = dict(day=d, day_label=day_label(d), plan_day_label=day_label(PLAN_AT), send_label=f"{send:%a} {send.day} {send:%b}")
        if not run["plan_built"] or d < PLAN_AT:
            return PlanView(**base, ready=False, decided=False, sent=False, not_joined=0, individual=0, rows=[])
        fs = facts(con, rid, PLAN_AT)
        rows = [dict(r) for r in con.execute("SELECT * FROM cta_plan WHERE run_id = ? ORDER BY sort_order", (rid,))]

    def example(r: dict):
        ids = json.loads(r["member_ids_json"])
        return fs.get(ids[0]) if ids else None

    top = [_row(r, d, example(r)) for r in rows if r["group_type"] in ("cohort", "custom", "individual_group")]
    people = [_row(r, d, example(r)) for r in rows if r["group_type"] == "individual"]
    for t in top:
        if t.group_type == "individual_group":
            t.children = people
            kids = {p.status for p in people}
            t.status = "Pending" if "Pending" in kids else ("Rejected" if kids == {"Rejected"} else "Approved")
    top.sort(key=lambda t: next(r["sort_order"] for r in rows if r["row_id"] == t.row_id) + (100 if t.group_type == "custom" else 0))
    decided = all(t.status != "Pending" for t in top)
    return PlanView(**base, ready=True, decided=decided, sent=d >= CTA_AT, not_joined=sum(t.members for t in top),
                    individual=len(people), rows=top)


@router.get("/catalogue", response_model=list[CatalogueItem])
def get_catalogue() -> list[CatalogueItem]:
    return [CatalogueItem(code=c, label=DISPLAY[c]) for c in catalogue()]


@router.get("/candidates", response_model=list[Candidate])
def candidates() -> list[Candidate]:
    """Everyone not joined by Day 7 — who a custom group can be made from."""
    with db() as con:
        rid = run_id(con)
        members, _ = members_at(con, rid, PLAN_AT)
        where = {}
        for r in con.execute("SELECT row_id, group_name, group_type, member_ids_json FROM cta_plan WHERE run_id = ?", (rid,)):
            if r["group_type"] != "individual_group":
                for d in json.loads(r["member_ids_json"]):
                    where[d] = "Individual attention" if r["group_type"] == "individual" else r["group_name"]
        towns = {f.distributor_id: f.town for f in facts(con, rid, 0).values()}
    return [Candidate(distributor_id=m.distributor_id, name=m.name, town=towns[m.distributor_id], cohort=m.cohort,
                      intent=m.intent, in_group=where.get(m.distributor_id))
            for m in members if not m.enrolled]


class DecisionIn(BaseModel):
    decision: Literal["Approved", "Rejected"]


class HighConfidenceIn(BaseModel):
    min: float = 0.7


class CustomGroupIn(BaseModel):
    name: str = "Custom group"
    member_ids: list[str] = Field(min_length=1)
    cta_code: str | None = None


async def _act(fn, *args) -> SimState:
    def go():
        with db() as con:
            try:
                fn(con, run_id(con), *args)
            except engine.SimError as e:
                raise HTTPException(409, str(e)) from e
            return build_state(con)

    s = await asyncio.to_thread(go)
    player.after_decision(s.waiting_for_approval)
    return s


@router.post("/rows/{row_id}/decision", response_model=SimState)
async def decide(row_id: str, body: DecisionIn) -> SimState:
    return await _act(engine.decide, row_id, body.decision)


@router.post("/approve-high-confidence", response_model=SimState)
async def approve_high_confidence(body: HighConfidenceIn | None = None) -> SimState:
    return await _act(engine.approve_high_confidence, (body or HighConfidenceIn()).min)


@router.post("/custom-group", response_model=SimState)
async def custom_group(body: CustomGroupIn) -> SimState:
    return await _act(engine.add_custom_group, body.name, body.member_ids, body.cta_code)
