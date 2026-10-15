"""Phase 1: territory + distributor endpoints return the Day-0 numbers the docs promise."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_territory_summary():
    t = client.get("/territory/summary").json()
    assert (t["name"], t["asm_name"], t["distributors"]) == ("Kolkata North", "Rahul Sen", 86)
    assert t["secondary_fytd_l"] == 1840.0                       # ₹18.4 Cr
    assert round(t["yoy_growth"] * 100, 1) == 9.2
    assert round(t["focus_share_q2"] * 100) == 31
    assert t["joined_last_scheme"] == 39                         # 45% — the bar to beat
    assert t["scheme_name"] == "Festive Scheme · Oct 2026"
    assert (t["company_distributors"], t["company_territories"]) == (1104, 14)
    assert sum(t["cohorts"].values()) == 86


def test_distributor_360_maa_tara():
    d = client.get("/distributors/DST-0001").json()
    assert d["name"] == "Maa Tara Distributors" and d["owner_name"] == "Biswajit Das" and d["town"] == "Barasat"
    assert d["key_account"] is True and d["cohort"] == "Scheme-hesitant"
    assert d["secondary_fytd_l"] == 38.2 and d["target_l"] == 7.8
    assert d["language_on_file"] == "Bengali"
    assert len(d["billing"]) == 18 and len(d["history"]) == 3


def test_annapurna_is_english_on_file():
    # The persona discovers Bengali later; on Day 0 the API only knows the file.
    assert client.get("/distributors/DST-0007").json()["language_on_file"] == "English"


def test_distributor_search_and_scope():
    assert client.get("/distributors").json()["total"] == 86
    assert client.get("/distributors", params={"q": "pal brothers"}).json()["items"][0]["distributor_id"] == "DST-0005"
    outside = client.get("/distributors/DST-0500")
    assert outside.status_code == 404                             # not in Rahul's territory
