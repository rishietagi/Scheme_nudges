"""Next best actions: one per cohort + Individual attention + custom groups. Rahul accepts, modifies or rejects each;
when nothing is pending the run can continue."""
from __future__ import annotations

import asyncio
import json
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.nodes import PLAN_AT, cta_texts, fill, members_at
from app.api.sim import build_state, run_id
from app.content.terms import intent_label
from app.db import queries
from app.db.conn import db
from app.db.run_queries import facts
from app.engines.cta_planner import DISPLAY, catalogue
from app.rules.loader import cta_rules
from app.models import CatalogueItem, Candidate, PlanRow, PlanView, SimState
from app.simulation import engine
from app.simulation.behaviour import CTA_AT
from app.simulation.clock import day_label, to_datetime
from app.simulation.player import player

router = APIRouter(prefix="/plan", tags=["plan"])


def _notes(con, rid: str, fs: dict) -> tuple[dict[str, str], dict[str, str]]:
    """Per cohort: the 2×2 cell in words, and the weakest-rated survey question among its answers that count."""
    rules = queries.run_rules(con, rid)
    pa, pe = rules.axes["potential"], rules.axes["performance"]
    cell = {c.name: f"{c.name} · {(pa.high if c.cell.high_potential else pa.low).lower()}, "
                    f"{(pe.high if c.cell.high_performance else pe.low).lower()}" for c in rules.cohorts}
    labels = {q.id: q.short or q.topic for qs in queries.run_survey(con, rid).values() for q in qs}
    weakest: dict[str, str] = {}
    for c in cell:
        vals: dict[str, list[int]] = {}
        for f in fs.values():
            if f.cohort == c and f.counted:
                for k, v in f.latest["answers"].items():
                    vals.setdefault(k, []).append(v)
        rated = {k: sum(v >= 4 for v in vs) / len(vs) for k, vs in vals.items() if len(vs) >= 3}
        if rated:
            k = min(rated, key=lambda k: (rated[k], k))
            weakest[c] = f"lowest rated: {labels.get(k, k)} ({round(rated[k] * 100)}% gave 4–5)"
    return cell, weakest


ORDINAL = {1: "1st", 2: "2nd", 3: "3rd"}


def _rank_notes(rows: list[PlanRow], unit: str) -> None:
    """Explain each priority: money at stake and its rank among its peers (the rule in cta_planner._tertiles)."""
    ranked = sorted(rows, key=lambda r: -r.revenue_at_stake_l)
    for i, r in enumerate(ranked, 1):
        r.priority_note = (f"₹{r.revenue_at_stake_l:.1f} L at stake · {ORDINAL.get(i, f'{i}th')} of {len(ranked)} {unit} "
                           f"→ {r.priority}")


def _row(r: dict, day: float, example) -> PlanRow:
    decided = r["decided_at"] is None or r["decided_at"] <= day
    status = r["status"] if decided else "Pending"
    preview, template = {}, {}
    if r["cta_code"]:
        for lang, col in (("English", "text_en"), ("Bengali", "text_bn")):
            if r[col]:
                template[lang] = r[col]
                if example is not None:
                    preview[lang] = fill(r[col], example, lang)
    modified = bool(r["modified"]) and decided
    was = json.loads(r["original_json"])["label"] if modified and r["original_json"] else None
    return PlanRow(
        row_id=r["row_id"], group_type=r["group_type"], group_name=r["group_name"], distributor_id=r["distributor_id"],
        cta_code=r["cta_code"], cta_variant=r["cta_variant"], label=r["label"], reason=r["reason"], why=r["why"],
        members=r["members"], priority=r["priority"], status=status, preview=preview, template=template,
        revenue_at_stake_l=r["revenue_at_stake_l"], modified=modified, was_label=was, note=r["note"] if modified else None,
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
        cell, weakest = _notes(con, rid, fs)

    def example(r: dict):
        ids = json.loads(r["member_ids_json"])
        return fs.get(ids[0]) if ids else None

    top = [_row(r, d, example(r)) for r in rows if r["group_type"] in ("cohort", "custom", "individual_group")]
    people = [_row(r, d, example(r)) for r in rows if r["group_type"] == "individual"]
    for t in top:
        if t.group_type == "cohort":
            t.cohort_note = cell.get(t.group_name)
            t.survey_note = " · ".join(x for x in (t.reason, weakest.get(t.group_name)) if x)
    for p in people:
        f = fs.get(p.distributor_id or "")
        p.cohort_note = f.cohort if f else None
    _rank_notes(top, "groups")
    _rank_notes(people, "people")
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
def get_catalogue(row_id: str | None = None) -> list[CatalogueItem]:
    """The actions Rahul can pick from. With a row: Emami AI's draft message for that row under each action."""
    ctas = cta_rules()["ctas"]
    drafts: dict[str, dict[str, str]] = {}
    if row_id:
        with db() as con:
            row = con.execute("SELECT * FROM cta_plan WHERE run_id = ? AND row_id = ?", (run_id(con), row_id)).fetchone()
            if row is None:
                raise HTTPException(404, "No such row")
            for c in catalogue():
                t = cta_texts(con, c, row["group_name"], row["reason"])
                drafts[c] = {"English": t["English"].text, "Bengali": t["Bengali"].text}
    return [CatalogueItem(code=c, label=DISPLAY[c], description=ctas[c]["for"], template=drafts.get(c, {})) for c in catalogue()]


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
                      intent=intent_label(m.intent) if m.intent else None, in_group=where.get(m.distributor_id))
            for m in members if not m.enrolled]


class DecisionIn(BaseModel):
    decision: Literal["Approved", "Rejected"]


class ModifyIn(BaseModel):
    cta_code: str
    text_en: str | None = None
    text_bn: str | None = None
    note: str | None = None


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


@router.post("/rows/{row_id:path}/decision", response_model=SimState)
async def decide(row_id: str, body: DecisionIn) -> SimState:
    return await _act(engine.decide, row_id, body.decision)


@router.post("/rows/{row_id:path}/modify", response_model=SimState)
async def modify(row_id: str, body: ModifyIn) -> SimState:
    return await _act(engine.modify, row_id, body.cta_code, body.text_en, body.text_bn, body.note)


@router.post("/rows/{row_id:path}/restore", response_model=SimState)
async def restore(row_id: str) -> SimState:
    return await _act(engine.restore, row_id)


@router.post("/accept-all", response_model=SimState)
async def accept_all() -> SimState:
    return await _act(engine.accept_all)


@router.post("/custom-group", response_model=SimState)
async def custom_group(body: CustomGroupIn) -> SimState:
    return await _act(engine.add_custom_group, body.name, body.member_ids, body.cta_code)
