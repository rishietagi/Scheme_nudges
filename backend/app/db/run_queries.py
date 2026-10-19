"""What the app knows about each distributor in a run, as of a sim day. Every time filter lives here.

Only public Day-0 fields + run tables — never the hidden traits.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from app.db import queries
from app.engines.sanity_checks import counts_in_numbers


@dataclass
class Fact:
    distributor_id: str
    name: str
    owner_name: str
    town: str
    cohort: str
    classification: str
    language_on_file: str
    consecutive_down_months: int
    baseline_l: float
    predicted_l: float
    stretch_l: float
    target_l: float
    high_potential: bool = False                             # potential axis of the 2×2
    high_performance: bool = False                           # performance axis of the 2×2
    nudge_at: float | None = None
    reminder_at: float | None = None
    responses: list[dict] = field(default_factory=list)      # submitted by `day`, oldest first
    flags: dict[str, list[dict]] = field(default_factory=dict)  # response_id -> flags
    enrol: dict | None = None
    deliveries: list[dict] = field(default_factory=list)
    calls: list[dict] = field(default_factory=list)

    @property
    def latest(self) -> dict | None:
        latest = [r for r in self.responses if r["is_latest"]]
        return latest[-1] if latest else (self.responses[-1] if self.responses else None)

    @property
    def replied(self) -> bool:
        return bool(self.responses)

    def latest_flags(self) -> list[dict]:
        return self.flags.get(self.latest["response_id"], []) if self.latest else []

    def decision(self) -> str | None:
        return next((f["asm_decision"] for f in self.latest_flags() if f["asm_decision"]), None)

    @property
    def red_flagged(self) -> bool:
        return any(f["severity"] == "red" for f in self.latest_flags())

    @property
    def counted(self) -> bool:
        """Does the latest response count in survey numbers?"""
        return self.latest is not None and counts_in_numbers([f["severity"] for f in self.latest_flags()], self.decision())

    @property
    def uplift_l(self) -> float:
        return self.predicted_l - self.baseline_l


def facts(con: sqlite3.Connection, run_id: str, day: float) -> dict[str, Fact]:
    out: dict[str, Fact] = {}
    down = dict(con.execute(
        "SELECT f.distributor_id, f.consecutive_down_months FROM world.distributor_features f "
        "JOIN world.distributors d USING (distributor_id) WHERE d.territory_id = ?", (queries.TERRITORY_ID,)).fetchall())
    stretch = dict(con.execute("SELECT distributor_id, stretch_target_l FROM world.scheme_targets WHERE scheme_id = ?",
                               (queries.CURRENT_SCHEME,)).fetchall())
    for r in queries.distributors(con):
        did = r["distributor_id"]
        out[did] = Fact(did, r["name"], r["owner_name"], r["town"], r["cohort"], r["classification"], r["preferred_language"],
                        down[did], r["baseline_forecast_l"], r["predicted_sales_if_enrolled_l"], stretch[did], r["target_l"],
                        high_potential=r["high_potential"], high_performance=r["high_performance"])

    for n in con.execute("SELECT distributor_id, kind, sent_at FROM nudges WHERE run_id = ? AND sent_at <= ?", (run_id, day)):
        setattr(out[n["distributor_id"]], "nudge_at" if n["kind"] == "nudge" else "reminder_at", n["sent_at"])
    for s in con.execute("SELECT * FROM survey_responses WHERE run_id = ? AND submitted_at <= ? ORDER BY submitted_at",
                         (run_id, day)):
        resp = dict(s)
        resp["answers"] = json.loads(resp.pop("answers_json") or "{}")
        out[s["distributor_id"]].responses.append(resp)
    # A duplicate only becomes "latest" once its second copy has arrived by `day`.
    for f in out.values():
        if f.responses and not any(x["is_latest"] for x in f.responses):
            f.responses[-1]["is_latest"] = 1
    for fl in con.execute(
        """SELECT g.*, s.distributor_id FROM sanity_flags g JOIN survey_responses s USING (run_id, response_id)
           WHERE g.run_id = ? AND s.submitted_at <= ?""", (run_id, day)):
        flag = dict(fl)
        if flag["decided_at"] is not None and flag["decided_at"] > day:
            flag["asm_decision"] = None
        out[fl["distributor_id"]].flags.setdefault(fl["response_id"], []).append(flag)
    for e in con.execute("SELECT * FROM enrolments WHERE run_id = ? AND sim_day <= ?", (run_id, day)):
        out[e["distributor_id"]].enrol = dict(e)
    for d in con.execute("SELECT * FROM cta_deliveries WHERE run_id = ? AND sent_at <= ? ORDER BY sent_at", (run_id, day)):
        out[d["distributor_id"]].deliveries.append(dict(d))
    for c in con.execute("SELECT * FROM asm_calls WHERE run_id = ? AND sim_day <= ? ORDER BY sim_day", (run_id, day)):
        out[c["distributor_id"]].calls.append(dict(c))
    return out
