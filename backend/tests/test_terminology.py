"""FMCG trade terms: distributors *participate* in a scheme. Stored intent values stay as codes; nothing people read says
"enrol"."""
import re

from fastapi.testclient import TestClient

from app.content.terms import intent_label
from app.main import app
from app.rules.loader import survey_rules

client = TestClient(app)
STORED = ["I've enrolled", "I'll enrol", "Explain again", "Explain in Bengali", "Talk to my ASM"]


def shown_text(obj, key: str | None = None):
    """Every string a person could read: values only (dict keys and stored option `value`s are codes)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from shown_text(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from shown_text(v, key)
    elif isinstance(obj, str) and key not in ("value", "type", "path", "kind"):          # codes, not copy
        yield obj


def test_stored_intents_unchanged_and_labelled():
    assert next(q for q in survey_rules()["questions"] if q["id"] == "Q1")["options"] == STORED
    assert [intent_label(v) for v in STORED] == ["Already participating", "Will participate", "Explain again",
                                                  "Explain in Bengali", "Talk to my ASM"]
    assert intent_label("I've enrolled", "Bengali") == "আমি অংশ নিচ্ছি" and intent_label("I'll enrol", "Hindi") == "शामिल होंगे"


def test_no_enrol_in_anything_people_read():
    client.post("/sim/reset", json={"seed": 42, "autopilot": True})
    client.post("/sim/advance", json={"to_day": 30})
    paths = ["/cohorts", "/survey/results", "/plan", "/results", "/sim/events?limit=1000", "/chat/scenarios",
             "/config/cohorts", "/config/survey"]
    paths += [f"/survey/questions?cohort={c}&lang={l}" for c in ("Develop", "Reassess") for l in ("English", "Bengali", "Hindi")]
    paths += [f"/cohorts/{c}/distributors" for c in ("Invest%20%2F%20Expand", "Replace%20%2F%20Reassess", "Protect",
                                                       "Exit%20%2F%20Watchlist")]
    paths += [f"/distributors/DST-{i:04d}" for i in range(1, 12)] + [f"/chat/DST-{i:04d}" for i in (1, 5, 6)]
    for p in paths:
        bad = [t for t in shown_text(client.get(p).json()) if re.search(r"enrol|sales boost|\bbonus\b", t, re.I)]
        assert not bad, (p, bad[:3])


def test_research_terms_show_up():
    body = client.get("/cohorts").json()
    assert "Emami potential" in body["potential"]["rule"] and "scheme qualification" in body["performance"]["rule"]
    assert "FMCG value +3.0%" in body["benchmark"]
    r = client.get("/survey/results").json()
    assert r["intent_labels"]["I've enrolled"] == "Already participating"
