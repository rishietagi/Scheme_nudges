"""Hidden truth stays hidden: no sim_traits column or value ever leaves the simulator."""
import json
from urllib.parse import quote
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.db.conn import connect
from app.main import app

client = TestClient(app)
APP = Path(__file__).resolve().parents[1] / "app"
ALLOWED_READER = APP / "simulation" / "traits.py"


def trait_columns() -> list[str]:
    con = connect()
    try:
        cols = [r[1] for r in con.execute("PRAGMA world.table_info(sim_traits)")]
    finally:
        con.close()
    return [c for c in cols if c != "distributor_id"]


def all_keys(obj) -> set[str]:
    if isinstance(obj, dict):
        return set(obj) | {k for v in obj.values() for k in all_keys(v)}
    if isinstance(obj, list):
        return {k for v in obj for k in all_keys(v)}
    return set()


def responses() -> list:
    client.post("/sim/reset", json={"autopilot": True})
    client.post("/sim/advance", json={"to_day": 30})
    paths = ["/health", "/sim/state", "/sim/events?limit=1000", "/sim/scenarios", "/territory/summary", "/cohorts", "/distributors"]
    paths += [f"/cohorts/{quote(c, safe='')}/distributors" for c in ["Invest / Expand", "Replace / Reassess", "Protect", "Exit / Watchlist"]]
    paths += [f"/distributors/DST-{i:04d}" for i in range(1, 12)]
    paths += ["/config/cohorts", "/config/survey", "/survey/results", "/plan", "/results"]
    return [client.get(p).json() for p in paths]


def test_no_trait_column_in_any_response():
    cols = set(trait_columns())
    assert len(cols) == 16
    for body in responses():
        assert not (all_keys(body) & cols)
        text = json.dumps(body, ensure_ascii=False)
        assert "scripted" not in text and "sim_traits" not in text
        assert "cohort_offset" not in text and "custom_mean" not in text          # simulator-only answer model


def test_no_trait_notes_in_any_response():
    con = connect()
    try:
        notes = [r[0] for r in con.execute("SELECT scripted_note FROM world.sim_traits WHERE scripted_note IS NOT NULL")]
    finally:
        con.close()
    blob = json.dumps(responses(), ensure_ascii=False)
    assert notes and not any(n in blob for n in notes)


def test_only_the_simulator_reads_the_answer_model():
    readers = [p for p in APP.rglob("*.py") if "answer_model" in p.read_text(encoding="utf-8")]
    assert [p.name for p in readers] == ["behaviour.py"], readers


def test_only_the_simulator_reads_sim_traits():
    readers = [p for p in APP.rglob("*.py") if re.search(r"\bsim_traits\b", p.read_text(encoding="utf-8")) and p != ALLOWED_READER]
    assert not readers, readers
