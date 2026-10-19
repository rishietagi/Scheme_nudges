"""The cohort agent places everyone on the business-potential × performance 2×2 (rules/cohorts.yaml v4); thresholds,
weights and pillar targets are editable and apply from the next cycle."""
from collections import Counter

from fastapi.testclient import TestClient

from app.db.conn import connect
from app.engines.cohorts import PILLARS, assign, assign_all, pillar_scores, score
from app.main import app
from app.rules.loader import cohort_rules

client = TestClient(app)
KN = {"Invest / Expand": 21, "Replace / Reassess": 23, "Protect": 21, "Exit / Watchlist": 21}


def _features() -> dict:
    con = connect()
    try:
        return {r["distributor_id"]: dict(r) for r in con.execute(
            "SELECT f.*, d.town FROM world.distributor_features f JOIN world.distributors d USING (distributor_id) "
            "WHERE d.territory_id = 'TER-01'")}
    finally:
        con.close()


def test_engine_matches_the_generated_data():
    con = connect()
    try:
        everyone = assign_all(con)
        stored = dict(con.execute("SELECT distributor_id, cohort FROM world.cohort_assignments"))
    finally:
        con.close()
    assert len(everyone) == 1104
    assert sum(a.cohort != stored[d] for d, a in everyone.items()) <= 3        # rounding at the line only


def test_two_by_two():
    rules = cohort_rules()
    kn = {d: assign(f) for d, f in _features().items()}
    assert Counter(a.cohort for a in kn.values()) == KN
    cells = {c.name: (c.cell.high_potential, c.cell.high_performance) for c in rules.cohorts}
    for a in kn.values():
        assert (a.high_potential, a.high_performance) == cells[a.cohort]
        assert a.high_potential == (a.potential_l >= 4.5) and a.high_performance == (a.performance_score >= 50)
        assert set(a.pillars) == set(PILLARS) and all(0 <= v <= 100 for v in a.pillars.values())
    anchors = {"DST-0001": "Replace / Reassess", "DST-0009": "Invest / Expand", "DST-0008": "Invest / Expand",
               "DST-0010": "Replace / Reassess", "DST-0011": "Replace / Reassess"}
    assert {d: kn[d].cohort for d in anchors} == anchors
    maa = kn["DST-0001"]
    assert maa.reasons[0] == "High potential: ₹15.7 L/month in Barasat" and maa.reasons[1].startswith("Performance 34/100")
    assert maa.pillars["schemes"] == 0 and round(maa.pillars["growth"]) == 50


def test_score_is_the_weighted_pillars():
    f = _features()["DST-0001"]
    rules = cohort_rules()
    p = pillar_scores(f, rules)
    assert score(p, rules) == round(sum(p.values()) / 4, 1)                    # 25% each by default
    heavy = rules.with_overrides(weights={"growth": 0, "schemes": 0, "focus": 50, "delivery": 50})
    assert score(p, heavy) == round((p["focus"] + p["delivery"]) / 2, 1)
    assert rules.with_overrides(weights={"growth": 1, "schemes": 1, "focus": 1, "delivery": 1}).weights["growth"].value == 25


def test_thresholds_move_people():
    rules = cohort_rules().with_overrides({"performance_high": 60, "nope": 1})
    kn = Counter(assign(f, rules).cohort for f in _features().values())
    assert kn["Replace / Reassess"] + kn["Exit / Watchlist"] > KN["Replace / Reassess"] + KN["Exit / Watchlist"]
    assert sum(kn.values()) == 86
    assert cohort_rules().with_overrides({"potential_high": 99}).thresholds["potential_high"].value == 20   # clamped


def test_cohort_cards_and_scatter():
    client.post("/sim/reset", json={"seed": 42})
    body = client.get("/cohorts").json()
    assert body["rule_version"] == "v4.0" and "NielsenIQ" in body["benchmark"]
    assert [c["name"] for c in body["cohorts"]] == ["Invest / Expand", "Replace / Reassess", "Protect", "Exit / Watchlist"]
    assert {c["name"]: c["count"] for c in body["cohorts"]} == KN
    rr = next(c for c in body["cohorts"] if c["name"] == "Replace / Reassess")
    assert rr["high_potential"] and not rr["high_performance"] and rr["kpis"]["potential_l"] > rr["kpis"]["current_l"]
    assert len(body["points"]) == 86 and body["potential_high"] == 4.5 and body["performance_high"] == 50
    assert [w["key"] for w in body["weights"]] == PILLARS and sum(w["value"] for w in body["weights"]) == 100
    assert "₹4.5 L/month" in body["potential"]["rule"]


def test_cohort_members_and_scorecard():
    client.post("/sim/reset", json={"seed": 42})
    body = client.get("/cohorts/Replace%20%2F%20Reassess/distributors").json()
    assert body["total"] == 23 and body["items"][0]["name"] == "Maa Tara Distributors"
    assert client.get("/cohorts/Nope/distributors").status_code == 404
    card = client.get("/distributors/DST-0001").json()["scorecard"]
    assert card["potential"]["town"] == "Barasat" and card["potential"]["high"]
    assert abs(card["potential"]["town_potential_l"] * card["potential"]["coverage_share"] - card["potential"]["potential_l"]) < 0.05
    assert [p["key"] for p in card["pillars"]] == PILLARS and card["score"] < card["threshold"]
    assert abs(sum(p["score"] * p["weight"] for p in card["pillars"]) / 100 - card["score"]) < 0.2


def test_saved_rules_apply_from_the_next_cycle():
    client.post("/sim/reset", json={"seed": 42})
    preview = client.post("/config/cohorts/preview", json={"weights": {"growth": 10, "schemes": 10, "focus": 40, "delivery": 40}}).json()
    assert preview["customised"] and preview["moves"]
    assert not client.get("/config/cohorts").json()["customised"]             # preview saves nothing

    saved = client.put("/config/cohorts", json={"thresholds": {"performance_high": 60},
                                               "definitions": {"Protect": "Small market, run well."}}).json()
    assert saved["customised"] and saved["current_run_differs"]
    assert {c["name"]: c["count"] for c in client.get("/cohorts").json()["cohorts"]} == KN   # running cycle keeps its cohorts

    client.post("/sim/reset", json={"seed": 42})
    after = client.get("/cohorts").json()
    assert {c["name"]: c["count"] for c in after["cohorts"]} != KN and after["performance_high"] == 60
    assert next(c for c in after["cohorts"] if c["name"] == "Protect")["description"] == "Small market, run well."

    assert not client.delete("/config/cohorts").json()["customised"]
    client.post("/sim/reset", json={"seed": 42})
    assert {c["name"]: c["count"] for c in client.get("/cohorts").json()["cohorts"]} == KN
