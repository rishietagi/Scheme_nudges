"""Simulation endpoints (SIMULATION_SPEC §6) + the approval decisions that let the run continue."""
from __future__ import annotations

import asyncio
import json
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.db.conn import db
from app.models import LoopStep, SimEvent, SimEvents, SimState
from app.simulation import engine
from app.simulation.clock import LOOP_STEPS, day_label
from app.simulation.player import SPEEDS, player
from app.simulation.scenarios import SCENARIOS

router = APIRouter(prefix="/sim", tags=["sim"])


class ResetIn(BaseModel):
    seed: int = Field(default_factory=lambda: settings.sim_seed)
    scenario: str = Field(default_factory=lambda: settings.sim_scenario)
    autopilot: bool = Field(default_factory=lambda: settings.sim_autopilot)


class AdvanceIn(BaseModel):
    to_day: float | None = None
    step: Literal["next_stage"] | None = None


class PlayIn(BaseModel):
    speed_seconds_per_day: float = 2


class AutopilotIn(BaseModel):
    on: bool


def run_id(con) -> str:
    return engine.ensure_run(con, settings.sim_seed, settings.sim_scenario, settings.sim_autopilot)["run_id"]


def build_state(con) -> SimState:
    s = engine.state(con, run_id(con))
    return SimState(
        **s,
        playing=player.playing,
        speed_seconds_per_day=player.speed,
        steps=[LoopStep(**x, day_label=day_label(x["day"])) for x in LOOP_STEPS],
    )


def _guard(fn, *args):
    try:
        return fn(*args)
    except engine.SimError as e:
        raise HTTPException(409, str(e)) from e


@router.get("/state", response_model=SimState)
def state() -> SimState:
    with db() as con:
        return build_state(con)


@router.get("/scenarios")
def scenarios() -> dict:
    return {"scenarios": SCENARIOS, "speeds": SPEEDS, "default_seed": settings.sim_seed}


@router.post("/reset", response_model=SimState)
async def reset(body: ResetIn | None = None) -> SimState:
    body = body or ResetIn()
    player.pause()

    def go():
        with db() as con:
            _guard(engine.reset, con, body.seed, body.scenario, body.autopilot)
            return build_state(con)

    return await asyncio.to_thread(go)


@router.post("/advance", response_model=SimState)
async def advance(body: AdvanceIn) -> SimState:
    def go():
        with db() as con:
            rid = run_id(con)
            if body.step == "next_stage":
                engine.next_stage(con, rid)
            elif body.to_day is not None:
                engine.advance(con, rid, body.to_day)
            else:
                raise HTTPException(422, "Give to_day or step")
            return build_state(con)

    return await asyncio.to_thread(go)


@router.post("/play", response_model=SimState)
async def play(body: PlayIn | None = None) -> SimState:
    player.play((body or PlayIn()).speed_seconds_per_day)
    return await asyncio.to_thread(state)


class SpeedIn(BaseModel):
    speed_seconds_per_day: float


@router.post("/speed", response_model=SimState)
async def speed(body: SpeedIn) -> SimState:
    if body.speed_seconds_per_day not in SPEEDS:
        raise HTTPException(422, f"speed must be one of {SPEEDS}")
    player.speed = float(body.speed_seconds_per_day)
    return await asyncio.to_thread(state)


@router.post("/pause", response_model=SimState)
async def pause() -> SimState:
    player.pause()
    return await asyncio.to_thread(state)


@router.post("/autopilot", response_model=SimState)
async def autopilot(body: AutopilotIn) -> SimState:
    def go():
        with db() as con:
            engine.set_autopilot(con, run_id(con), body.on)
            return build_state(con)

    s = await asyncio.to_thread(go)
    player.after_decision(s.waiting_for_approval)
    return s


@router.get("/events", response_model=SimEvents)
def events(after_day: float = -1.0, since_id: int = 0, limit: int = 300, day: float | None = None) -> SimEvents:
    with db() as con:
        rid = run_id(con)
        cur = engine.state(con, rid)["day"]
        rows = engine.events(con, rid, min(day if day is not None else cur, cur), after_day, since_id, limit)
    return SimEvents(run_id=rid, day=cur, events=[_event(e) for e in rows])


def _event(e: dict) -> SimEvent:
    return SimEvent(**e, day_label=day_label(e["sim_day"]), time_label=f"{int(e['sim_day'] % 1 * 1440) // 60:02d}:{int(e['sim_day'] % 1 * 1440) % 60:02d}")


@router.get("/stream")
async def stream(request: Request) -> StreamingResponse:
    """Server-Sent Events: `state` whenever it changes, `events` as new ones become visible."""

    async def gen():
        last_state, last_day, last_id, last_run, idle = None, -1.0, 0, None, 0

        def read():
            with db() as con:
                s = build_state(con)
                rows = engine.events(con, s.run_id, s.day, last_day, last_id) if last_run == s.run_id else \
                    engine.events(con, s.run_id, s.day, limit=60)
                return s, rows

        while not await request.is_disconnected():
            s, rows = await asyncio.to_thread(read)
            if s.run_id != last_run:
                yield "event: reset\ndata: {}\n\n"
                last_run, last_day, last_id = s.run_id, -1.0, 0
            payload = s.model_dump_json()
            if payload != last_state:
                yield f"event: state\ndata: {payload}\n\n"
                last_state = payload
            if rows:
                body = json.dumps([_event(e).model_dump() for e in rows], ensure_ascii=False)
                yield f"event: events\ndata: {body}\n\n"
                last_id = max(last_id, max(e["event_id"] for e in rows))
            last_day = s.day
            idle += 1
            if idle % 30 == 0:
                yield ": keep-alive\n\n"
            await asyncio.sleep(0.3)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
