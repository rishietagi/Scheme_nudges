"""Phase 2: the product engines on their own — sanity checks, the LLM wrapper, and the no-leak guard on prompts."""
import json

import pytest
from pydantic import BaseModel

from app.engines import sanity_checks
from app.llm import client
from app.simulation import engine
from app.config import settings
from tests.test_simulator import fresh


def resp(**kw):
    base = {"survey_seconds": 110, "q1_intent": "I'll enrol", "q2": 4, "q3": 3, "q4": 4, "q5": 2, "q6": "Stock on time", "q7_text": None}
    return {**base, **kw}


def codes(r, enrolled=False, dup=False):
    return [f.code for f in sanity_checks.check(r, enrolled_at_submit=enrolled, is_duplicate=dup)]


def test_sanity_rules():
    assert codes(resp()) == []
    assert codes(resp(survey_seconds=19, q1_intent="I've enrolled", q2=5, q3=5, q4=5, q5=5)) == ["TOO_FAST", "STRAIGHT_LINE", "CONTRADICTION"]
    assert codes(resp(q3=None, q4=None, q5=None, q6=None)) == ["INCOMPLETE"]
    assert codes(resp(q1_intent="Explain again", q2=4)) == ["CONTRADICTION"]
    assert codes(resp(q1_intent="I've enrolled"), enrolled=True) == []
    assert codes(resp(), dup=True) == ["DUPLICATE"]
    assert codes(resp(q7_text="....")) == ["JUNK_TEXT"]
    assert codes(resp(q7_text="aaaa")) == ["JUNK_TEXT"]
    assert codes(resp(q7_text="আমার ইনসেনটিভ এখনও পাইনি।")) == []
    assert sanity_checks.short_reason(["TOO_FAST", "STRAIGHT_LINE", "CONTRADICTION"], resp(survey_seconds=19, q1_intent="I've enrolled")) \
        == "19 seconds · same rating everywhere · says enrolled but isn't"
    assert sanity_checks.short_reason(["INCOMPLETE"], resp(q3=None, q4=None, q5=None, q6=None)) == "Answered 2 of 6 questions"


def test_red_stays_out_until_kept():
    assert not sanity_checks.counts_in_numbers(["red"], None)
    assert sanity_checks.counts_in_numbers(["red"], "Keep")
    assert sanity_checks.counts_in_numbers(["amber"], None)
    assert not sanity_checks.counts_in_numbers(["amber"], "Drop")


class Out(BaseModel):
    text: str


def test_llm_mock_uses_fixtures_and_falls_back():
    r = client.complete("nudge_message", {"cohort": "Scheme-hesitant", "language": "Bengali"}, Out, fixture_key="Scheme-hesitant|Bengali")
    assert "{target}" in r.text and "ফেস্টিভ" in r.text
    assert client.complete("nudge_message", {}, Out, fixture_key="nope").text            # default fixture


def test_llm_replay_reads_the_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(client, "CACHE", tmp_path)
    inputs = {"cohort": "Dormant", "language": "English"}
    path = client._cache_path("nudge_message", inputs)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"text": "cached line"}), encoding="utf-8")
    assert client.complete("nudge_message", inputs, Out, mode="replay").text == "cached line"
    assert client.complete("nudge_message", {"other": 1}, Out, mode="replay", fixture_key="Dormant|English").text.startswith("Namaskar")


def test_llm_refuses_hidden_traits():
    with pytest.raises(client.LeakError):
        client.complete("nudge_message", {"language": "English", "member": {"true_language": "Bengali"}}, Out)


def test_no_prompt_in_a_full_run_contains_hidden_traits(monkeypatch):
    seen = []
    real = client.complete

    def spy(prompt_id, inputs, schema, fixture_key=None, mode=None):
        seen.append(client.render(prompt_id, inputs))
        return real(prompt_id, inputs, schema, fixture_key, mode)

    import app.agents.nodes as nodes
    monkeypatch.setattr(nodes, "complete", spy)
    con = fresh()
    rid = engine.reset(con, settings.sim_seed, "typical", autopilot=True)
    engine.advance(con, rid, 30)
    notes = [r[0] for r in con.execute("SELECT scripted_note FROM world.sim_traits WHERE scripted_note IS NOT NULL")]
    assert seen
    for prompt in seen:
        assert not any(k in prompt for k in client.FORBIDDEN)
        assert not any(n in prompt for n in notes)
