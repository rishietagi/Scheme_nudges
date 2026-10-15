"""Distributor view: the (simulated) WhatsApp conversation, 'Behind the conversation', and live typing."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents import chat_graph
from app.agents.nodes import PLAN_AT, inr
from app.api import stories
from app.api.stories import initials
from app.api.sim import run_id
from app.db.conn import db
from app.db.run_queries import Fact, facts
from app.models import ChatView, JourneyItem, Message, Scenario
from app.simulation import engine

router = APIRouter(prefix="/chat", tags=["chat"])
SCENARIOS = [("DST-0001", "Maa Tara · Bengali", "bengali"), ("DST-0006", "Ruplekha · flagged", "flag"), ("DST-0005", "Pal Brothers · ASM", "call")]
ASKED = {"I've enrolled": "Said enrolled", "I'll enrol": "Will enrol", "Explain again": "Asked to explain again",
         "Explain in Bengali": "Asked for Bengali", "Talk to my ASM": "Asked for Rahul"}


def story_line(f: Fact) -> str:
    """'Asked for Bengali → voice note → joined', from what has happened so far."""
    if not f.responses:
        return "No reply yet"
    first = f.responses[0]
    parts = [ASKED[first["q1_intent"]] if not (f.red_flagged and first["survey_seconds"] < 30) else f"{first['survey_seconds']}-second survey"]
    if f.deliveries:
        code = f.deliveries[-1]["cta_code"]
        parts.append({"VOICE_EXPLAINER": "voice note", "ASM_CALL": "call", "QUICK_REMINDER": "reminder", "EXPLAIN_SIMPLE": "simple card",
                      "RE_NUDGE": "re-send", "SLAB_PROGRESS": "slab update"}[code])
    if f.enrol:
        parts.append("joined")
    elif f.calls and "margin" in (f.calls[-1]["outcome"] or ""):
        parts.append("margin issue")
    return " → ".join(parts)


def this_cycle(con, rid: str, f: Fact) -> str:
    if f.enrol and f.enrol["sim_day"] < PLAN_AT:
        return "Joined before the follow-ups"
    row = con.execute(
        "SELECT group_type, group_name, label FROM cta_plan WHERE run_id = ? AND group_type != 'individual_group' "
        "AND member_ids_json LIKE ?", (rid, f'%"{f.distributor_id}"%')).fetchall()
    if not row:
        return "Not planned yet"
    personal = [r for r in row if r["group_type"] == "individual"]
    return "Personal follow-up" if personal else f"{row[0]['group_name']} follow-up"


def build(con, rid: str, did: str, day: float) -> ChatView:
    fs = facts(con, rid, day)
    if did not in fs:
        raise HTTPException(404, "Distributor not found in Kolkata North")
    f = fs[did]
    p = stories.persona_view(f, day)
    fytd = con.execute("SELECT secondary_fytd_l FROM world.distributor_features WHERE distributor_id = ?", (did,)).fetchone()[0]
    window = con.execute("SELECT reply_window FROM world.distributors WHERE distributor_id = ?", (did,)).fetchone()[0]
    return ChatView(
        day=day,
        distributor_id=did,
        name=f.name,
        owner_name=f.owner_name,
        town=f.town,
        initials=initials(f.name),
        cohort=f.cohort,
        key_account=f.classification == "A",
        language=p["language"],
        language_changed=p["language_changed"],
        billing_fytd=inr(fytd),
        best_time=p["best_time"] or window,
        best_time_learned=p["best_time"] is not None,
        this_cycle=this_cycle(con, rid, f) if day >= PLAN_AT else "Survey stage",
        messages=[Message(**m) for m in stories.conversation(con, rid, f, day)],
        journey=[JourneyItem(**j) for j in stories.journey(con, rid, f, day)],
    )


@router.get("/scenarios", response_model=list[Scenario])
def scenarios(day: float | None = None) -> list[Scenario]:
    with db() as con:
        rid = run_id(con)
        cur = engine.state(con, rid)["day"]
        fs = facts(con, rid, cur if day is None else min(day, cur))
    return [Scenario(distributor_id=d, title=t, icon=i, subtitle=story_line(fs[d])) for d, t, i in SCENARIOS]


@router.get("/{distributor_id}", response_model=ChatView)
def conversation(distributor_id: str, day: float | None = None) -> ChatView:
    with db() as con:
        rid = run_id(con)
        cur = engine.state(con, rid)["day"]
        return build(con, rid, distributor_id, cur if day is None else max(0.0, min(day, cur)))


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)


@router.post("/{distributor_id}/message", response_model=ChatView)
async def send(distributor_id: str, body: MessageIn) -> ChatView:
    def go():
        with db() as con, engine.LOCK:
            rid = run_id(con)
            day = engine.state(con, rid)["day"]
            if distributor_id not in facts(con, rid, day):
                raise HTTPException(404, "Distributor not found in Kolkata North")
            if day < 0.4:
                raise HTTPException(409, "The chat opens once the Day-0 nudge has gone out")
            chat_graph.handle(con, rid, distributor_id, body.text.strip(), day)
            con.commit()
            return build(con, rid, distributor_id, day)

    return await asyncio.to_thread(go)

