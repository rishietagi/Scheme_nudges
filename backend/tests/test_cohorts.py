"""Phase 1: the cohort agent re-applies cohorts.yaml and matches the provided assignments, reasons included."""
from fastapi.testclient import TestClient

from app.db.conn import connect
from app.engines.cohorts import assign_all
from app.main import app

client = TestClient(app)


def test_engine_reproduces_every_assignment_and_reason():
    con = connect()
    try:
        ours = assign_all(con)
        stored = {r[0]: (r[1], r[2]) for r in con.execute("SELECT distributor_id, cohort, reasons FROM world.cohort_assignments")}
    finally:
        con.close()
    assert len(ours) == 1104
    bad = [d for d, a in ours.items() if (a.cohort, " · ".join(a.reasons)) != stored[d]]
    assert not bad, bad[:5]


def test_cohort_cards():
    body = client.get("/cohorts").json()
    assert body["rule_version"] == "v2.0"
    cards = {c["name"]: c for c in body["cohorts"]}
    assert [c["name"] for c in body["cohorts"]] == ["Champions", "Growth builders", "Scheme-hesitant", "At-risk", "Dormant"]
    assert {n: c["count"] for n, c in cards.items()} == {
        "Champions": 14, "Growth builders": 22, "Scheme-hesitant": 19, "At-risk": 18, "Dormant": 13}
    # Joined the last scheme (Monsoon) by cohort: 93 / 68 / 21 / 39 / 0 %
    pct = {n: round(100 * c["joined_last_scheme"] / c["count"]) for n, c in cards.items()}
    assert pct == {"Champions": 93, "Growth builders": 68, "Scheme-hesitant": 21, "At-risk": 39, "Dormant": 0}
    assert cards["Scheme-hesitant"]["tag"] == "Explain"


def test_cohort_members_start_with_the_anchors():
    body = client.get("/cohorts/Scheme-hesitant/distributors").json()
    assert body["total"] == 19
    assert body["items"][0]["name"] == "Maa Tara Distributors"
    assert body["items"][0]["reasons"] == ["Billing +3% YoY (healthy)", "Joined 1 of the last 3 schemes"]
    assert client.get("/cohorts/Nope/distributors").status_code == 404
