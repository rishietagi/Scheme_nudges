"""Phase 6: Day-30 results (five questions add up), what we learned, and Apply to next scheme."""
from fastapi.testclient import TestClient

from app.agents.nodes import polish_next_time
from app.main import app

client = TestClient(app)


def run(day=30):
    client.post("/sim/reset", json={"seed": 42, "autopilot": True})
    client.post("/sim/advance", json={"to_day": day})


def test_not_ready_before_day_30():
    run(20)
    r = client.get("/results").json()
    assert not r["ready"] and r["joined_so_far"] > 0 and r["results"] is None
    assert client.post("/results/apply").status_code == 409


def test_the_five_questions_add_up():
    run()
    r = client.get("/results").json()
    x = r["results"]
    assert r["headline"] == f"{x['joined']} of 86 joined. Up from 45% last time."
    assert sum(c["joined"] for c in x["joined_by_cohort"]) == x["joined"] and sum(c["total"] for c in x["joined_by_cohort"]) == 86
    assert x["beat_prediction"] + x["fell_short"] == x["joined"] and x["sales_lift_joined"] > x["sales_lift_not_joined"]
    assert sum(x["speed"].values()) == 86 and x["speed"]["Never"] == 86 - x["joined"]
    assert sum(x["asked"].values()) == 86
    assert all(0 <= f["joined"] <= f["received"] for f in x["follow_ups"])
    rates = [f["rate"] for f in x["follow_ups"]]
    assert rates == sorted(rates, reverse=True)
    assert len(r["learned"]) == 3 and any("13 of 19" in l["text"] or "joined" in l["text"] for l in r["learned"])
    assert [c["label"] for c in r["chips"]] == ["now get Bengali", "prefer a call from Rahul", "reply best in the evening",
                                                "to get a visit, not WhatsApp"]


def test_apply_to_next_scheme_saves_every_persona():
    run()
    preview = client.post("/results/apply").json()
    assert [p["name"] for p in preview] == ["Maa Tara Distributors", "Annapurna Distributors", "Nabadiganta Enterprises"]
    assert preview[0]["next_time"] == "Send the scheme as a Bengali voice note around 1 pm"
    assert preview[2]["next_time"] == "Skip WhatsApp — Rahul visits"
    assert client.get("/results").json()["applied"]
    assert client.post("/results/apply").status_code == 200                      # idempotent
    assert len(client.get("/results/applied").json()) == 3


def test_next_time_polish_cannot_change_language_or_time(monkeypatch):
    import app.agents.nodes as nodes
    from app.agents.nodes import NextTime

    base = {"next_time": "Send the scheme as a Bengali voice note around 1 pm", "language": "Bengali", "best_time": "Afternoon",
            "prefers": "Voice note", "what_worked": "Bengali voice note"}
    monkeypatch.setattr(nodes, "complete", lambda *a, **k: NextTime(next_time="Send an English text at 9 am"))
    assert polish_next_time(base) == base["next_time"]
    monkeypatch.setattr(nodes, "complete", lambda *a, **k: NextTime(next_time="Share it as a Bengali voice note around 1 pm."))
    assert polish_next_time(base) == "Share it as a Bengali voice note around 1 pm"
