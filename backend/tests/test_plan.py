"""Next best actions — rows, time-awareness, accept / modify / reject, custom groups, deciding lets the run continue."""
from urllib.parse import quote

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def at_gate():
    client.post("/sim/reset", json={"seed": 42, "autopilot": False})
    return client.post("/sim/advance", json={"to_day": 30}).json()


def decide(row_id, d="Approved"):
    return client.post(f"/plan/rows/{quote(row_id)}/decision", json={"decision": d})


def modify(row_id, **body):
    return client.post(f"/plan/rows/{quote(row_id)}/modify", json=body)


def test_matrix_rows_match_the_spec():
    s = at_gate()
    assert s["waiting_for_approval"] and s["pending_rows"] == 5
    p = client.get("/plan").json()
    assert p["ready"] and not p["decided"] and p["send_label"] == "Fri 9 Oct"
    names = [r["group_name"] for r in p["rows"]]
    assert set(names) == {"Invest / Expand", "Replace / Reassess", "Protect", "Exit / Watchlist", "Individual attention"}
    ia = next(r for r in p["rows"] if r["group_type"] == "individual_group")
    assert "confidence" not in ia and ia["members"] == len(ia["children"]) == p["individual"]
    assert {"Pal Brothers", "Maa Tara Distributors", "Ruplekha Traders", "Ganguly Traders"} <= {c["group_name"] for c in ia["children"]}
    assert p["not_joined"] == sum(r["members"] for r in p["rows"])
    sh = next(r for r in p["rows"] if r["group_name"] == "Replace / Reassess")
    assert sh["cta_code"] == "VOICE_EXPLAINER" and sh["preview"]["Bengali"] and sh["why"]
    # Cohort (performance) + survey (answers) → next best action: both inputs are shown on the row.
    assert sh["cohort_note"] == "Replace / Reassess · high potential, low performance"
    assert sh["survey_note"].startswith(sh["reason"]) and "lowest rated: Scheme clarity" in sh["survey_note"]
    assert all(r["priority"] in ("High", "Medium", "Low") for r in p["rows"])
    # Every priority explains itself: money at stake and the rank among its peers.
    top = sorted(p["rows"], key=lambda r: -r["revenue_at_stake_l"])
    assert top[0]["priority_note"].endswith("1st of 5 groups → High") and top[0]["priority"] == "High"
    assert all(c["priority_note"].endswith(f"→ {c['priority']}") for c in ia["children"])
    assert sh["template"]["English"] and "{owner_first}" in sh["template"]["English"]
    assert not client.get("/plan", params={"day": 6.9}).json()["ready"]       # nothing to approve before Day 7 10:00


def test_accept_all_then_the_rest_unlocks_day_8():
    at_gate()
    assert decide("cohort:Protect", "Rejected").status_code == 200
    s = client.post("/plan/accept-all").json()
    assert not s["waiting_for_approval"]
    rows = {r["group_name"]: r for r in client.get("/plan").json()["rows"]}
    assert rows["Protect"]["status"] == "Rejected" and rows["Invest / Expand"]["status"] == "Approved"
    assert client.post("/sim/advance", json={"to_day": 30}).json()["day"] == 30
    assert client.get("/plan").json()["sent"]
    assert decide("cohort:Exit / Watchlist").status_code == 409                       # too late once actions went out


def test_modify_changes_the_action_and_what_goes_out():
    at_gate()
    before = next(r for r in client.get("/plan").json()["rows"] if r["group_name"] == "Exit / Watchlist")
    assert before["cta_code"] == "RE_NUDGE" and not before["modified"]
    drafts = {c["code"]: c for c in client.get("/plan/catalogue", params={"row_id": "cohort:Exit / Watchlist"}).json()}
    assert drafts["ASM_CALL"]["description"] and drafts["ASM_CALL"]["template"]["English"]
    assert modify("cohort:Exit / Watchlist", cta_code="ASM_CALL", note="Rahul knows them").status_code == 200
    after = next(r for r in client.get("/plan").json()["rows"] if r["group_name"] == "Exit / Watchlist")
    assert after["cta_code"] == "ASM_CALL" and after["modified"] and after["status"] == "Approved"
    assert after["was_label"] == before["label"] and after["note"] == "Rahul knows them"
    # Only the message changes on another row.
    modify("cohort:Protect", cta_code="QUICK_REMINDER", text_en="Hi {owner_first}, your target is {target}. Reply JOIN.")
    pr = next(r for r in client.get("/plan").json()["rows"] if r["group_name"] == "Protect")
    assert pr["template"]["English"].startswith("Hi {owner_first}") and pr["modified"]
    assert modify("cohort:Protect", cta_code="FREE_GIFT").status_code == 409
    # Restore goes back to Emami AI's suggestion, undecided.
    assert client.post(f"/plan/rows/{quote('cohort:Protect')}/restore").status_code == 200
    pr = next(r for r in client.get("/plan").json()["rows"] if r["group_name"] == "Protect")
    assert not pr["modified"] and pr["status"] == "Pending"
    client.post("/plan/accept-all")
    client.post("/sim/advance", json={"to_day": 30})
    events = client.get("/sim/events", params={"limit": 2000}).json()["events"]
    assert any(e["type"] == "MODIFIED" for e in events)
    worked = {f["cta_code"]: f for f in client.get("/results").json()["results"]["follow_ups"]}
    assert worked["ASM_CALL"]["received"] >= before["members"]                         # the modified action went out


def test_individual_row_decides_everyone_and_people_can_differ():
    at_gate()
    decide("individual", "Approved")
    decide("person:DST-0005", "Rejected")
    ia = next(r for r in client.get("/plan").json()["rows"] if r["group_type"] == "individual_group")
    statuses = {c["distributor_id"]: c["status"] for c in ia["children"]}
    assert statuses["DST-0005"] == "Rejected" and statuses["DST-0001"] == "Approved" and ia["status"] == "Approved"


def test_custom_group_keeps_decisions_and_takes_members_out_of_their_cohort():
    at_gate()
    decide("cohort:Invest / Expand")
    dormant = [c["distributor_id"] for c in client.get("/plan/candidates").json() if c["in_group"] == "Exit / Watchlist"][:3]
    before = next(r for r in client.get("/plan").json()["rows"] if r["group_name"] == "Exit / Watchlist")["members"]
    s = client.post("/plan/custom-group", json={"name": "Barasat belt", "member_ids": dormant, "cta_code": "ASM_CALL"}).json()
    rows = {r["group_name"]: r for r in client.get("/plan").json()["rows"]}
    assert rows["Barasat belt"]["group_type"] == "custom" and rows["Barasat belt"]["members"] == 3
    assert rows["Barasat belt"]["cta_code"] == "ASM_CALL" and rows["Barasat belt"]["status"] == "Pending"
    assert rows["Exit / Watchlist"]["members"] == before - 3 and rows["Invest / Expand"]["status"] == "Approved"
    assert s["pending_rows"] == 5
    assert client.post("/plan/custom-group", json={"name": "x", "member_ids": dormant, "cta_code": "FREE_GIFT"}).status_code == 409
    assert {c["code"] for c in client.get("/plan/catalogue").json()} == {
        "SLAB_PROGRESS", "QUICK_REMINDER", "EXPLAIN_SIMPLE", "VOICE_EXPLAINER", "ASM_CALL", "RE_NUDGE"}


def test_decisions_stay_changeable_until_the_clock_moves():
    at_gate()
    for r in client.get("/plan").json()["rows"]:
        decide(r["row_id"])
    s = client.get("/sim/state").json()
    assert not s["waiting_for_approval"] and s["stage"] == "PLAN" and s["status_text"].startswith("Approved")
    assert decide("cohort:Exit / Watchlist", "Rejected").status_code == 200           # changed my mind — still Day 7
    client.post("/sim/advance", json={"step": "next_stage"})
    assert client.get("/sim/state").json()["day"] > 8
    assert decide("cohort:Exit / Watchlist").status_code == 409
