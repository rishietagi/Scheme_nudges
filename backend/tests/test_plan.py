"""Phase 4: approval matrix — rows, time-awareness, decisions, custom groups, approving lets the run continue."""
from urllib.parse import quote

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def at_gate():
    client.post("/sim/reset", json={"seed": 42, "autopilot": False})
    return client.post("/sim/advance", json={"to_day": 30}).json()


def decide(row_id, d="Approved"):
    return client.post(f"/plan/rows/{quote(row_id)}/decision", json={"decision": d})


def test_matrix_rows_match_the_spec():
    s = at_gate()
    assert s["waiting_for_approval"] and s["pending_rows"] == 6
    p = client.get("/plan").json()
    assert p["ready"] and not p["decided"] and p["send_label"] == "Fri 9 Oct"
    names = [r["group_name"] for r in p["rows"]]
    assert set(names) == {"Champions", "Growth builders", "Scheme-hesitant", "At-risk", "Dormant", "Individual attention"}
    ia = next(r for r in p["rows"] if r["group_type"] == "individual_group")
    assert ia["confidence"] is None and ia["members"] == len(ia["children"]) == p["individual"]
    assert {"Pal Brothers", "Maa Tara Distributors", "Ruplekha Traders", "Ganguly Traders"} <= {c["group_name"] for c in ia["children"]}
    assert p["not_joined"] == sum(r["members"] for r in p["rows"])
    sh = next(r for r in p["rows"] if r["group_name"] == "Scheme-hesitant")
    assert sh["cta_code"] == "VOICE_EXPLAINER" and sh["preview"]["Bengali"] and sh["why"]
    assert all(r["priority"] in ("High", "Medium", "Low") for r in p["rows"])
    assert not client.get("/plan", params={"day": 6.9}).json()["ready"]       # nothing to approve before Day 7 10:00


def test_approve_all_high_confidence_then_the_rest_unlocks_day_8():
    at_gate()
    s = client.post("/plan/approve-high-confidence", json={"min": 0.7}).json()
    p = client.get("/plan").json()
    pending = [r for r in p["rows"] if r["status"] == "Pending"]
    assert all((r["confidence"] or 0) < 0.7 for r in pending if r["group_type"] != "individual_group")
    assert s["waiting_for_approval"]
    for r in pending:
        decide(r["row_id"], "Rejected" if r["group_name"] == "Champions" else "Approved")
    s = client.get("/sim/state").json()
    assert not s["waiting_for_approval"]
    assert client.post("/sim/advance", json={"to_day": 30}).json()["day"] == 30
    assert client.get("/plan").json()["sent"]
    assert decide("cohort:Dormant").status_code == 409                       # too late once follow-ups went out


def test_individual_row_decides_everyone_and_people_can_differ():
    at_gate()
    decide("individual", "Approved")
    decide("person:DST-0005", "Rejected")
    ia = next(r for r in client.get("/plan").json()["rows"] if r["group_type"] == "individual_group")
    statuses = {c["distributor_id"]: c["status"] for c in ia["children"]}
    assert statuses["DST-0005"] == "Rejected" and statuses["DST-0001"] == "Approved" and ia["status"] == "Approved"


def test_custom_group_keeps_decisions_and_takes_members_out_of_their_cohort():
    at_gate()
    decide("cohort:Growth builders")
    dormant = [c["distributor_id"] for c in client.get("/plan/candidates").json() if c["cohort"] == "Dormant"][:3]
    before = next(r for r in client.get("/plan").json()["rows"] if r["group_name"] == "Dormant")["members"]
    s = client.post("/plan/custom-group", json={"name": "Barasat belt", "member_ids": dormant, "cta_code": "ASM_CALL"}).json()
    rows = {r["group_name"]: r for r in client.get("/plan").json()["rows"]}
    assert rows["Barasat belt"]["group_type"] == "custom" and rows["Barasat belt"]["members"] == 3
    assert rows["Barasat belt"]["cta_code"] == "ASM_CALL" and rows["Barasat belt"]["status"] == "Pending"
    assert rows["Dormant"]["members"] == before - 3 and rows["Growth builders"]["status"] == "Approved"
    assert s["pending_rows"] == 6
    assert client.post("/plan/custom-group", json={"name": "x", "member_ids": dormant, "cta_code": "FREE_GIFT"}).status_code == 409
    assert {c["code"] for c in client.get("/plan/catalogue").json()} == {
        "SLAB_PROGRESS", "QUICK_REMINDER", "EXPLAIN_SIMPLE", "VOICE_EXPLAINER", "ASM_CALL", "RE_NUDGE"}


def test_decisions_stay_changeable_until_the_clock_moves():
    at_gate()
    for r in client.get("/plan").json()["rows"]:
        decide(r["row_id"])
    s = client.get("/sim/state").json()
    assert not s["waiting_for_approval"] and s["stage"] == "PLAN" and s["status_text"].startswith("Approved")
    assert decide("cohort:Dormant", "Rejected").status_code == 200           # changed my mind — still Day 7
    client.post("/sim/advance", json={"step": "next_stage"})
    assert client.get("/sim/state").json()["day"] > 8
    assert decide("cohort:Dormant").status_code == 409
