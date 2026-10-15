"""Loop simulator: run lifecycle and the clock.

The timeline is computed ahead, segment by segment, and every row carries its sim time; `loop_runs.current_day`
is the reveal pointer every page reads up to.
  reset            -> Day 0–7 (nudges, replies, flags, reminder, early joins)
  reach Day 7 10:00 -> follow-up plan (uses Keep/Drop decisions so far)
  plan decided     -> Day 8–30 (deliveries, calls, joins, October sales, personas)
"""
from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timezone

from app.agents import loop_graph
from app.agents.nodes import PLAN_AT, emit, pending, possessive, run_row
from app.db import queries
from app.simulation.behaviour import CTA_AT, LAST, NUDGE_AT, REMINDER_AT, SURVEY_CLOSE
from app.simulation.clock import day_label
from app.simulation.scenarios import SCENARIOS

LOCK = threading.RLock()
BOUNDARIES = [NUDGE_AT, REMINDER_AT, PLAN_AT, CTA_AT, LAST]


class SimError(ValueError):
    pass


# ------------------------------------------------------------------------------------------------ runs
def active(con: sqlite3.Connection) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM loop_runs WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1").fetchone()


def reset(con: sqlite3.Connection, seed: int, scenario: str, autopilot: bool) -> str:
    if scenario not in SCENARIOS:
        raise SimError(f"Unknown scenario {scenario!r}")
    with LOCK:
        run_id = uuid.uuid4().hex[:12]
        con.execute("UPDATE loop_runs SET is_active = 0")
        con.execute(
            "INSERT INTO loop_runs (run_id, seed, scenario, autopilot, scheme_id, current_day, stage, created_at) "
            "VALUES (?,?,?,?,?,0,'NUDGE',?)",
            (run_id, seed, scenario, int(autopilot), queries.CURRENT_SCHEME, datetime.now(timezone.utc).isoformat()),
        )
        loop_graph.run(con, run_id, "day0")
        con.commit()
        return run_id


def ensure_run(con: sqlite3.Connection, seed: int, scenario: str, autopilot: bool) -> sqlite3.Row:
    run = active(con)
    if run is None:
        reset(con, seed, scenario, autopilot)
        run = active(con)
    return run


def set_autopilot(con: sqlite3.Connection, run_id: str, on: bool) -> None:
    with LOCK:
        con.execute("UPDATE loop_runs SET autopilot = ? WHERE run_id = ?", (int(on), run_id))
        run = run_row(con, run_id)
        if on and run["plan_built"] and not run["segment_b_built"]:
            loop_graph.run(con, run_id, "execute")
        con.commit()


# ------------------------------------------------------------------------------------------------ clock
def gate(con: sqlite3.Connection, run: sqlite3.Row) -> float:
    """How far the pointer may go: Day 7 10:00 while the plan waits for approval."""
    if run["plan_built"] and not run["segment_b_built"] and pending(con, run["run_id"]):
        return PLAN_AT
    return LAST


def advance(con: sqlite3.Connection, run_id: str, to_day: float) -> float:
    with LOCK:
        run = run_row(con, run_id)
        day = max(run["current_day"], min(float(to_day), LAST))
        if not run["plan_built"] and day >= PLAN_AT:
            con.execute("UPDATE loop_runs SET current_day = ? WHERE run_id = ?", (PLAN_AT, run_id))
            loop_graph.run(con, run_id, "plan")
            run = run_row(con, run_id)
        day = min(day, gate(con, run))
        if run["plan_built"] and not run["segment_b_built"] and day > PLAN_AT:
            # Decisions stay open until the clock moves on; then Day 8–30 is played out from them.
            loop_graph.run(con, run_id, "execute")
            run = run_row(con, run_id)
        con.execute("UPDATE loop_runs SET current_day = ?, stage = ? WHERE run_id = ?", (round(day, 6), stage(con, run, day), run_id))
        con.commit()
        return day


def next_stage(con: sqlite3.Connection, run_id: str) -> float:
    cur = run_row(con, run_id)["current_day"]
    target = next((b for b in BOUNDARIES if b > cur + 1e-9), LAST)
    return advance(con, run_id, target)


def stage(con: sqlite3.Connection, run: sqlite3.Row, day: float) -> str:
    if day < NUDGE_AT:
        return "NUDGE"
    if day < REMINDER_AT:
        return "COLLECT"
    if day < PLAN_AT:
        return "REMINDER"
    if day < CTA_AT:
        return "APPROVAL" if run["plan_built"] and pending(con, run["run_id"]) else "PLAN"
    if day < CTA_AT + 1:
        return "SEND_CTA"
    if day < LAST:
        return "CONVERT"
    return "LEARN"


STATUS = {
    "NUDGE": "Ready to send the nudge",
    "COLLECT": "Survey open",
    "REMINDER": "Survey open · reminder sent",
    "APPROVAL": "Waiting for your approval",
    "PLAN": "Approved · goes out Day 8",
    "SEND_CTA": "Follow-ups sent",
    "CONVERT": "Follow-ups sent",
    "LEARN": "Results ready · loop closed",
}


# ------------------------------------------------------------------------------------------------ decisions
def _after_decision(con: sqlite3.Connection, run_id: str) -> None:
    # Keep the Individual-attention parent in step with its people.
    kids = [r[0] for r in con.execute("SELECT status FROM cta_plan WHERE run_id = ? AND group_type = 'individual'", (run_id,))]
    if kids:
        parent = "Pending" if "Pending" in kids else ("Rejected" if all(k == "Rejected" for k in kids) else "Approved")
        con.execute("UPDATE cta_plan SET status = ? WHERE run_id = ? AND group_type = 'individual_group'", (parent, run_id))


def decide(con: sqlite3.Connection, run_id: str, row_id: str, decision: str) -> None:
    if decision not in ("Approved", "Rejected"):
        raise SimError("decision must be Approved or Rejected")
    with LOCK:
        run = run_row(con, run_id)
        if not run["plan_built"]:
            raise SimError("The follow-up plan is ready on Day 7")
        if run["segment_b_built"]:
            raise SimError("Follow-ups have already gone out")
        row = con.execute("SELECT * FROM cta_plan WHERE run_id = ? AND row_id = ?", (run_id, row_id)).fetchone()
        if row is None:
            raise SimError(f"No plan row {row_id!r}")
        day = run["current_day"]
        targets = ("individual",) if row["group_type"] == "individual_group" else ()
        if targets:
            con.execute("UPDATE cta_plan SET status = ?, decided_at = ? WHERE run_id = ? AND group_type = 'individual'",
                        (decision, day, run_id))
        con.execute("UPDATE cta_plan SET status = ?, decided_at = ? WHERE run_id = ? AND row_id = ?", (decision, day, run_id, row_id))
        verb = "approved" if decision == "Approved" else "rejected"
        what = f"the follow-up for {row['group_name']}" if row["group_type"] != "individual_group" else "every personal follow-up"
        rows = [row_id] + ([r[0] for r in con.execute("SELECT row_id FROM cta_plan WHERE run_id = ? AND group_type = 'individual'",
                                                       (run_id,))] if targets else [])
        emit(con, run_id, day, decision.upper(), "You", f"Rahul {verb} {what}", row["distributor_id"], payload={"row_ids": rows})
        _after_decision(con, run_id)
        con.commit()


def add_custom_group(con: sqlite3.Connection, run_id: str, name: str, member_ids: list[str], cta_code: str | None) -> str:
    """The ASM hand-picks distributors for their own follow-up. Planned like a cohort; appears as its own row."""
    from app.engines.cta_planner import catalogue

    with LOCK:
        run = run_row(con, run_id)
        if run["segment_b_built"]:
            raise SimError("Follow-ups have already gone out")
        if cta_code is not None and cta_code not in catalogue():
            raise SimError(f"Unknown follow-up {cta_code!r}")
        known = {r["distributor_id"] for r in queries.distributors(con)}
        ids = [d for d in dict.fromkeys(member_ids) if d in known]
        if not ids:
            raise SimError("Pick at least one distributor")
        name = name.strip() or "Custom group"
        day = run["current_day"]
        emit(con, run_id, day, "CUSTOM_GROUP", "You", f"Rahul made a custom group “{name}” with {len(ids)} distributors",
             payload={"name": name, "member_ids": ids, "cta_code": cta_code})
        if run["plan_built"]:
            loop_graph.run(con, run_id, "plan")
            _after_decision(con, run_id)
        con.commit()
        return name


def approve_high_confidence(con: sqlite3.Connection, run_id: str, minimum: float = 0.7) -> int:
    with LOCK:
        run = run_row(con, run_id)
        if not run["plan_built"] or run["segment_b_built"]:
            raise SimError("No follow-up plan is waiting for approval")
        ids = [r[0] for r in con.execute(
            "SELECT row_id FROM cta_plan WHERE run_id = ? AND status = 'Pending' AND group_type != 'individual_group' "
            "AND confidence >= ?", (run_id, minimum))]
        day = run["current_day"]
        for rid in ids:
            con.execute("UPDATE cta_plan SET status = 'Approved', decided_at = ? WHERE run_id = ? AND row_id = ?", (day, run_id, rid))
        emit(con, run_id, day, "APPROVED", "You", f"Rahul approved {len(ids)} follow-ups with {round(minimum * 100)}%+ confidence",
             payload={"row_ids": ids})
        _after_decision(con, run_id)
        con.commit()
        return len(ids)


def flag_decision(con: sqlite3.Connection, run_id: str, response_id: str, decision: str) -> None:
    if decision not in ("Keep", "Drop"):
        raise SimError("decision must be Keep or Drop")
    with LOCK:
        run = run_row(con, run_id)
        row = con.execute(
            "SELECT s.distributor_id, d.name, s.submitted_at FROM survey_responses s JOIN world.distributors d USING (distributor_id) "
            "WHERE s.run_id = ? AND s.response_id = ?", (run_id, response_id)).fetchone()
        if row is None or row["submitted_at"] > run["current_day"]:
            raise SimError("No such response yet")
        day = run["current_day"]
        con.execute("UPDATE sanity_flags SET asm_decision = ?, decided_at = ? WHERE run_id = ? AND response_id = ?",
                    (decision, day, run_id, response_id))
        verb = "kept" if decision == "Keep" else "dropped"
        emit(con, run_id, day, "FLAG_DECISION", "You", f"Rahul {verb} {possessive(row['name'])} flagged answers", row["distributor_id"])
        con.commit()


# ------------------------------------------------------------------------------------------------ state
def counters(con: sqlite3.Connection, run_id: str, day: float) -> dict[str, int]:
    one = lambda sql, *a: con.execute(sql, (run_id, *a)).fetchone()[0]  # noqa: E731
    return {
        "sent": one("SELECT COUNT(DISTINCT distributor_id) FROM nudges WHERE run_id = ? AND kind = 'nudge' AND sent_at <= ?", day),
        "replied": one("SELECT COUNT(DISTINCT distributor_id) FROM survey_responses WHERE run_id = ? AND submitted_at <= ?", day),
        "flagged": one("SELECT COUNT(DISTINCT s.distributor_id) FROM sanity_flags g JOIN survey_responses s USING (run_id, response_id) "
                       "WHERE g.run_id = ? AND g.severity = 'red' AND s.submitted_at <= ?", day),
        "joined": one("SELECT COUNT(*) FROM enrolments WHERE run_id = ? AND sim_day <= ?", day),
        "follow_ups": one("SELECT COUNT(DISTINCT distributor_id) FROM cta_deliveries WHERE run_id = ? AND sent_at <= ?", day),
        "beat_prediction": one("SELECT COUNT(*) FROM october_sales WHERE run_id = ? AND hit_prediction = 1 AND ? >= ?", day, LAST),
    }


def state(con: sqlite3.Connection, run_id: str) -> dict:
    run = run_row(con, run_id)
    day = run["current_day"]
    st = stage(con, run, day)
    waiting = bool(run["plan_built"] and not run["segment_b_built"] and pending(con, run_id))
    top_pending = con.execute(
        "SELECT COUNT(*) FROM cta_plan WHERE run_id = ? AND status = 'Pending' AND group_type != 'individual'", (run_id,)).fetchone()[0]
    c = counters(con, run_id, day)
    status = STATUS[st]
    if st in ("COLLECT", "REMINDER"):
        status = f"Survey open · {c['replied']} replied" if day < SURVEY_CLOSE else "Survey closed · plan ready at 10:00"
    return {
        "run_id": run_id, "seed": run["seed"], "scenario": run["scenario"], "autopilot": bool(run["autopilot"]),
        "day": day, "day_label": day_label(day), "stage": st, "status_text": status,
        "waiting_for_approval": waiting, "pending_rows": top_pending if waiting else 0, "counters": c,
    }


def events(con: sqlite3.Connection, run_id: str, day: float, after_day: float = -1.0, since_id: int = 0,
           limit: int = 300, feed_only: bool = True) -> list[dict]:
    rows = con.execute(
        f"""SELECT event_id, sim_day, type, agent, distributor_id, text FROM events
            WHERE run_id = ? AND sim_day <= ? AND (sim_day > ? OR event_id > ?) {"AND feed = 1" if feed_only else ""}
            ORDER BY sim_day DESC, event_id DESC LIMIT ?""",
        (run_id, day, after_day, since_id, limit)).fetchall()
    return [dict(r) for r in rows]
