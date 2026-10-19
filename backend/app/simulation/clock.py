"""Sim clock. Day 0 = Thu 1 Oct 2026, 00:00. `sim_day` is a float 0–30."""
from __future__ import annotations

from datetime import datetime, timedelta

DAY0 = datetime(2026, 10, 1)
LAST_DAY = 30.0

# (stage, starts at sim day) — see SIMULATION_SPEC §2
STAGES = [
    ("NUDGE", 0.0),
    ("COLLECT", 0.0),
    ("REMINDER", 3.0),
    ("PLAN", 7.0),
    ("APPROVAL", 7.0),
    ("SEND_CTA", 8.0),
    ("CONVERT", 8.0),
    ("RESULTS", 30.0),
    ("LEARN", 30.0),
]

# The four steps of the loop stepper shown on every main page.
LOOP_STEPS = [
    {"key": "nudge", "label": "Cohorts + survey", "day": 0},
    {"key": "plan", "label": "Next best actions", "day": 7},
    {"key": "send", "label": "Actions sent", "day": 8},
    {"key": "results", "label": "Results + refresh", "day": 30},
]


def to_datetime(sim_day: float) -> datetime:
    return DAY0 + timedelta(days=sim_day)


def day_label(sim_day: float) -> str:
    """'Day 9 · Sat 10 Oct'."""
    d = to_datetime(sim_day)
    return f"Day {int(sim_day)} · {d:%a} {d.day} {d:%b}"


def time_label(sim_day: float) -> str:
    """'13:05'."""
    return f"{to_datetime(sim_day):%H:%M}"


def at(day: int, hh: int = 0, mm: int = 0) -> float:
    """Sim day for a given day + clock time, e.g. at(0, 10) = Day 0 10:00."""
    return day + (hh * 60 + mm) / 1440
