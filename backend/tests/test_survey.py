"""Phase 3: Survey page data — per cohort/language, time-aware, red flags out until kept."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def reset_to(day):
    client.post("/sim/reset", json={"seed": 42, "autopilot": False})
    client.post("/sim/advance", json={"to_day": day})


def test_questions_per_cohort_and_language():
    reset_to(7)
    en = client.get("/survey/questions", params={"cohort": "Scheme-hesitant"}).json()
    assert en["example_distributor"] == "Maa Tara Distributors" and "₹7.8 L" in en["nudge_text"] and "Rahul" in en["nudge_text"]
    assert en["members"] == 19 and en["nudge_sent"]
    q6 = next(q for q in en["questions"] if q["id"] == "Q6")
    assert [o["value"] for o in q6["options"]] == ["Simpler explanation", "Explanation in Bengali", "Lower target", "Better margin"]
    assert q6["tag"] == "For this cohort"
    bn = client.get("/survey/questions", params={"cohort": "Scheme-hesitant", "lang": "Bengali"}).json()
    q1 = bn["questions"][0]
    assert [o["value"] for o in q1["options"]][0] == "I've enrolled"          # stored values stay the five intents
    assert q1["options"][0]["label"] == "আমি যোগ দিয়েছি" and "রাহুল" in bn["nudge_text"]
    dormant = client.get("/survey/questions", params={"cohort": "Dormant", "lang": "Hindi"}).json()
    assert "राहुल" in dormant["nudge_text"]
    assert client.get("/survey/questions", params={"cohort": "Nope"}).status_code == 404


def test_results_are_time_aware_and_add_up():
    reset_to(7)
    r = client.get("/survey/results").json()
    assert r["closed"] and r["total"] == 86
    assert r["replies_by_day"][-1] == r["replied"] and len(r["replies_by_day"]) == 8
    assert r["replies_by_day"] == sorted(r["replies_by_day"])
    s = r["sanity"]
    assert s["clean"] + s["check"] + s["flagged"] == r["replied"] and s["flagged"] == len(r["flagged"])
    assert sum(r["intents"].values()) + r["left_out"] + r["no_reply"] == 86
    assert r["left_out"] == s["flagged"]
    assert any(f["name"] == "Ruplekha Traders" and f["reason"].startswith("19 seconds") for f in r["flagged"])
    assert all(x["pct"] is None or 0 <= x["pct"] <= 1 for x in r["ratings"]) and r["themes"]
    early = client.get("/survey/results", params={"day": 0.3}).json()
    assert not early["sent"] and early["replied"] == 0
    d2 = client.get("/survey/results", params={"day": 2.0}).json()
    assert len(d2["replies_by_day"]) == 3 and d2["replied"] <= r["replied"]


def test_keep_brings_a_flagged_answer_back_into_the_numbers():
    reset_to(7)
    before = client.get("/survey/results").json()
    ru = next(f for f in before["flagged"] if f["name"] == "Ruplekha Traders")
    assert client.post(f"/survey/flags/{ru['response_id']}", json={"decision": "Keep"}).status_code == 200
    after = client.get("/survey/results").json()
    assert after["left_out"] == before["left_out"] - 1
    assert after["intents"]["I've enrolled"] == before["intents"]["I've enrolled"] + 1
    assert next(f for f in after["flagged"] if f["name"] == "Ruplekha Traders")["decision"] == "Keep"
    assert client.post("/survey/flags/nope:1", json={"decision": "Drop"}).status_code == 409
