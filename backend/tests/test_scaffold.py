"""Phase 0: health endpoint, sim state and the sim clock's dates."""
from fastapi.testclient import TestClient

from app.main import app
from app.simulation.clock import at, day_label, time_label

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["world_db"] is True


def test_sim_state_after_reset():
    s = client.post("/sim/reset", json={}).json()
    assert s["day_label"] == "Day 0 · Thu 1 Oct" and s["stage"] == "NUDGE" and s["counters"]["sent"] == 0
    assert client.get("/sim/state").json()["run_id"] == s["run_id"]
    assert [x["label"] for x in s["steps"]] == ["Nudge + survey", "Plan + approve", "Follow-ups sent", "Results + learn"]


def test_day_labels_have_correct_weekdays():
    assert day_label(0) == "Day 0 · Thu 1 Oct"
    assert day_label(7) == "Day 7 · Thu 8 Oct"
    assert day_label(8) == "Day 8 · Fri 9 Oct"
    assert day_label(9.4) == "Day 9 · Sat 10 Oct"
    assert day_label(30) == "Day 30 · Sat 31 Oct"
    assert time_label(at(0, 13, 5)) == "13:05"
