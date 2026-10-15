"""Server-side Play/Pause. Ticks the active run's clock; clients follow via /sim/stream.

Stops at the approval gate (unless autopilot) and resumes on its own once the plan is decided.
"""
from __future__ import annotations

import asyncio

from app.db.conn import db
from app.simulation import engine

TICK_S = 0.25
SPEEDS = (1, 2, 5)          # seconds per sim day


class Player:
    def __init__(self) -> None:
        self.task: asyncio.Task | None = None
        self.speed = 2.0
        self.resume_after_approval = False

    @property
    def playing(self) -> bool:
        return self.task is not None and not self.task.done()

    def _tick(self) -> tuple[bool, bool]:
        """(finished, stopped at the gate)."""
        with db() as con:
            run = engine.active(con)
            if run is None:
                return True, False
            target = run["current_day"] + TICK_S / self.speed
            day = engine.advance(con, run["run_id"], target)
            st = engine.state(con, run["run_id"])
            return day >= engine.LAST, st["waiting_for_approval"] and day < target

    async def _loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(TICK_S)
                finished, gated = await asyncio.to_thread(self._tick)
                if finished:
                    break
                if gated:
                    self.resume_after_approval = True
                    break
        finally:
            self.task = None

    def play(self, speed: float | None = None) -> None:
        if speed:
            self.speed = float(speed)
        self.resume_after_approval = False
        if not self.playing:
            self.task = asyncio.get_running_loop().create_task(self._loop())

    def pause(self) -> None:
        self.resume_after_approval = False
        if self.task:
            self.task.cancel()
            self.task = None

    def after_decision(self, still_waiting: bool) -> None:
        """Approving the plan resumes the simulation if it was playing when it hit the gate."""
        if self.resume_after_approval and not still_waiting:
            self.play()


player = Player()
