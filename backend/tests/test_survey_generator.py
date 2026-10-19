"""The Survey generator: business controls (count, must-ask by scope) + Emami AI picks from the CX bank only.
Published settings apply from the next cycle, and the loop answers exactly what each cohort was sent."""
from fastapi.testclient import TestClient

from app.engines.cohorts import DISPLAY_ORDER
from app.engines.survey_generator import MustAsk, SurveySettings, by_id, clean, default_settings, generate
from app.main import app

client = TestClient(app)
COUNTED = ("quick_reply", "rating_1_5", "single_choice")


def counted(qs):
    return [q for q in qs if q.type in COUNTED]


def test_defaults_per_cohort():
    out = generate(default_settings(), DISPLAY_ORDER, mode="mock")
    assert list(out) == DISPLAY_ORDER
    for cohort, qs in out.items():
        assert len(counted(qs)) == 7 and qs[-1].id == "COMMENT"
        assert [q.id for q in qs[:2]] == ["SCHEME_INTENT", "DEALER_SCORE"] and qs[0].locked
        assert all(q.id in by_id() for q in qs)                                   # nothing outside the bank
        assert all(q.why and q.why.startswith(f"For {cohort}") for q in qs if q.source == "ai")
        assert len({q.id for q in qs}) == len(qs)
    assert out["Replace / Reassess"][2].id == "SCHEME_CLEAR" and out["Replace / Reassess"][2].source == "must_cohort"
    assert "SCHEME_CLEAR" not in {q.id for q in out["Invest / Expand"] if q.source != "ai"}
    assert {q.use_case for q in out["Protect"] if q.source == "ai"} >= {"Credit"}
    assert generate(default_settings(), DISPLAY_ORDER, mode="mock") == out       # deterministic


def test_business_controls():
    s = SurveySettings(questions_per_survey=10, must_ask=[
        MustAsk(id="CREDIT_TERMS", scope="Exit / Watchlist"),
        MustAsk(id="anything", scope="all", text="How likely are you to recommend Emami?"),
        MustAsk(id="RETURNS", scope="Nope"),                                     # unknown scope: dropped
        MustAsk(id="NOT_A_QUESTION", scope="all"),                               # unknown id, no text: dropped
    ])
    c = clean(s)
    assert c.must_ask[0].id == "SCHEME_INTENT" and c.must_ask[0].locked         # the locked intent can't be removed
    assert [m.id for m in c.must_ask] == ["SCHEME_INTENT", "CREDIT_TERMS", "CUSTOM_1"]
    out = generate(s, DISPLAY_ORDER, mode="mock")
    assert all(len(counted(qs)) == 10 for qs in out.values())
    assert out["Exit / Watchlist"][1].id == "CUSTOM_1" and out["Exit / Watchlist"][2].id == "CREDIT_TERMS"
    assert out["Invest / Expand"][1].text["English"] == "How likely are you to recommend Emami?"
    assert clean(SurveySettings(questions_per_survey=3)).questions_per_survey == 5   # 5–10 only
    assert clean(SurveySettings(questions_per_survey=12)).questions_per_survey == 10


def test_publish_applies_from_the_next_cycle_and_the_loop_answers_it():
    client.post("/sim/reset", json={"seed": 42})
    body = {"questions_per_survey": 5, "must_ask": [{"id": "SCHEME_INTENT", "scope": "all"}, {"id": "STOCK_NORMS", "scope": "Exit / Watchlist"}]}
    preview = client.post("/config/survey/preview", json=body).json()
    assert all(len([q for q in v if q["type"] != "open_text"]) == 5 for v in preview["questionnaires"].values())
    assert not client.get("/config/survey").json()["customised"]

    saved = client.put("/config/survey", json=body).json()
    assert saved["customised"] and saved["current_run_differs"]
    sent = [q["id"] for q in client.get("/survey/questions", params={"cohort": "Exit / Watchlist"}).json()["questions"]]
    assert "DEALER_SCORE" in sent                                                # the running cycle keeps its survey

    client.post("/sim/reset", json={"seed": 42})
    client.post("/sim/advance", json={"to_day": 7})
    sent = [q["id"] for q in client.get("/survey/questions", params={"cohort": "Exit / Watchlist"}).json()["questions"]]
    assert sent[:2] == ["SCHEME_INTENT", "STOCK_NORMS"] and "DEALER_SCORE" not in sent and len(sent) == 6
    r = client.get("/survey/results").json()
    stock = next(x for x in r["ratings"] if x["question"] == "STOCK_NORMS")
    assert stock["asked_in"] == ["Exit / Watchlist"] and stock["answered"] > 0 and r["dealer_score"] is None

    assert not client.delete("/config/survey").json()["customised"]
    client.post("/sim/reset", json={"seed": 42})
