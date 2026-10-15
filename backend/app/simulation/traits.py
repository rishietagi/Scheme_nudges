"""The ONLY module that reads the hidden sim_traits table.

Traits drive simulated behaviour; they never leave the simulator (no API response, UI or LLM prompt sees them).
"""
from __future__ import annotations

import sqlite3

from app.simulation import scenarios


def load(con: sqlite3.Connection, territory_id: str, scenario: str) -> dict[str, dict]:
    rows = con.execute(
        """SELECT s.* FROM world.sim_traits s JOIN world.distributors d USING (distributor_id)
           WHERE d.territory_id = ? ORDER BY s.distributor_id""",
        (territory_id,),
    ).fetchall()
    return {r["distributor_id"]: scenarios.apply(scenario, dict(r)) for r in rows}
