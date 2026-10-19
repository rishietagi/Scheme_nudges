"""Phase 2: the loop simulator — determinism, calibration, anchors, time-awareness, the approval gate (SIMULATION_SPEC §9)."""
import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from app.agents.nodes import PLAN_AT
from app.config import settings
from app.db.conn import connect
from app.db.run_queries import facts
from app.simulation import engine
from app.simulation.behaviour import CTA_AT
from scripts.find_seed import TARGETS, metrics
from scripts.sim_report import report

RUN_TABLES = ["events", "nudges", "survey_responses", "sanity_flags", "cta_plan", "cta_deliveries", "asm_calls",
              "enrolments", "october_sales", "personas"]


def fresh():
    return connect(Path(tempfile.mkdtemp()) / "runs.sqlite")


def full_run(seed=None, scenario="typical", reject=()):
    con = fresh()
    rid = engine.reset(con, seed or settings.sim_seed, scenario, autopilot=False)
    engine.advance(con, rid, 30)
    for row_id in reject:
        engine.decide(con, rid, row_id, "Rejected")
    for (row_id,) in con.execute("SELECT row_id FROM cta_plan WHERE run_id=? AND status='Pending' AND group_type!='individual_group'", (rid,)):
        engine.decide(con, rid, row_id, "Approved")
    engine.advance(con, rid, 30)
    return con, rid


def table_hash(con, rid) -> str:
    h = hashlib.sha256()
    for t in RUN_TABLES:
        cols = [r[1] for r in con.execute(f"PRAGMA main.table_info({t})") if r[1] not in ("run_id", "event_id")]
        rows = con.execute(f"SELECT {', '.join(cols)} FROM {t} WHERE run_id=? ORDER BY {', '.join(cols[:4])}", (rid,)).fetchall()
        h.update(repr([tuple(r) for r in rows]).encode())
    return h.hexdigest()


@pytest.fixture(scope="module")
def default_run():
    return full_run()


# ------------------------------------------------------------------------------------------------ determinism
def test_same_seed_same_decisions_identical_tables(default_run):
    con, rid = default_run
    con2, rid2 = full_run()
    assert table_hash(con, rid) == table_hash(con2, rid2)


def test_different_seed_differs(default_run):
    con, rid = default_run
    con2, rid2 = full_run(seed=settings.sim_seed + 1)
    assert table_hash(con, rid) != table_hash(con2, rid2)


# ------------------------------------------------------------------------------------------------ calibration
def test_default_seed_lands_inside_every_band():
    m = metrics(report(settings.sim_seed))
    outside = {k: (m[k], (lo, hi)) for k, (_, lo, hi) in TARGETS.items() if not lo <= m[k] <= hi}
    assert not outside, outside


# ------------------------------------------------------------------------------------------------ anchors
def test_anchors_behave_as_scripted(default_run):
    con, rid = default_run
    f = facts(con, rid, 30)
    persona = {r["distributor_id"]: dict(r) for r in con.execute("SELECT * FROM personas WHERE run_id=?", (rid,))}
    plan = {r["distributor_id"]: dict(r) for r in con.execute("SELECT * FROM cta_plan WHERE run_id=? AND group_type='individual'", (rid,))}
    flags = lambda d: sorted(x["code"] for x in f[d].latest_flags())  # noqa: E731
    join_day = lambda d: int(f[d].enrol["sim_day"]) if f[d].enrol else None  # noqa: E731
    hours = lambda d: round((f[d].responses[0]["submitted_at"] - f[d].nudge_at) * 24, 2)  # noqa: E731

    # Maa Tara: Explain in Bengali after 3 h → key account → Bengali voice note Day 8 → joins Day 9 → Bengali voice note ~1 pm
    mt = "DST-0001"
    assert f[mt].latest["q1_intent"] == "Explain in Bengali" and hours(mt) == 3.0 and not flags(mt)
    assert plan[mt]["cta_code"] == "VOICE_EXPLAINER"
    assert [d["language"] for d in f[mt].deliveries] == ["Bengali"] and f[mt].deliveries[0]["sent_at"] == CTA_AT
    assert join_day(mt) == 9 and f[mt].enrol["path"] == "after_cta"
    assert persona[mt]["language"] == "Bengali" and persona[mt]["prefers"] == "Voice note"
    assert persona[mt]["next_time"] == "Send the scheme as a Bengali voice note around 1 pm"
    # Sarkar & Sons: Explain again after 26 h, asks for a Bengali voice note, joins Day 10
    assert f["DST-0002"].latest["q1_intent"] == "Explain again" and hours("DST-0002") == 26.0
    assert "ভয়েস" in f["DST-0002"].latest["q7_text"] and join_day("DST-0002") == 10
    assert persona["DST-0002"]["prefers"] == "Voice note"
    # Ruplekha: 19 s, all 5s, says enrolled but isn't → red flag → ASM call → joins Day 15
    ru = "DST-0006"
    assert f[ru].latest["survey_seconds"] == 19 and set(f[ru].latest["answers"].values()) == {5} and len(f[ru].latest["answers"]) >= 3
    assert flags(ru) == ["CONTRADICTION", "STRAIGHT_LINE", "TOO_FAST"] and f[ru].red_flagged
    assert plan[ru]["cta_code"] == "ASM_CALL" and join_day(ru) == 15 and f[ru].enrol["path"] == "after_asm_call"
    # Pal Brothers: Talk to my ASM in 1.5 h, key account, ASM call, never joins — margin, not scheme
    pb = "DST-0005"
    assert f[pb].latest["q1_intent"] == "Talk to my ASM" and hours(pb) == 1.5 and plan[pb]["cta_code"] == "ASM_CALL"
    assert f[pb].enrol is None and f[pb].calls and "margin" in f[pb].calls[0]["outcome"]
    # Annapurna: English on file, asks for Bengali, joins Day 9, persona switches to Bengali
    an = "DST-0007"
    assert f[an].language_on_file == "English" and f[an].latest["q1_intent"] == "Explain in Bengali" and join_day(an) == 9
    assert persona[an]["language"] == "Bengali" and persona[an]["language_changed"] == 1
    # Debnath: I'll enrol, joins Day 5 before any follow-up
    assert f["DST-0004"].latest["q1_intent"] == "I'll enrol" and join_day("DST-0004") == 5 and f["DST-0004"].enrol["path"] == "self"
    # Shree Durga + Bose: enrolled within the hour; beat the prediction; Bose hits the stretch slab
    sales = {r["distributor_id"]: dict(r) for r in con.execute("SELECT * FROM october_sales WHERE run_id=?", (rid,))}
    for d, h in (("DST-0008", 0.7), ("DST-0009", 0.4)):
        assert f[d].latest["q1_intent"] == "I've enrolled" and hours(d) == h and join_day(d) == 0 and sales[d]["hit_prediction"]
    assert sales["DST-0009"]["actual_l"] >= f["DST-0009"].stretch_l
    # Ganguly: no reply → individual attention → visit → still no join
    assert not f["DST-0010"].replied and plan["DST-0010"]["cta_variant"] == "visit" and f["DST-0010"].enrol is None
    # Nabadiganta: no reply, ignores the reminder → stays out → try an ASM visit
    nb = "DST-0011"
    assert not f[nb].replied and f[nb].reminder_at and f[nb].enrol is None
    assert persona[nb]["prefers"] == "ASM visit" and persona[nb]["next_time"] == "Skip WhatsApp — Rahul visits"


# ------------------------------------------------------------------------------------------------ the clock
def test_reset_sends_nothing_yet():
    con = fresh()
    rid = engine.reset(con, settings.sim_seed, "typical", autopilot=False)
    s = engine.state(con, rid)
    assert s["day"] == 0 and s["stage"] == "NUDGE" and s["counters"]["sent"] == 0
    assert [e["type"] for e in engine.events(con, rid, 0)] == ["COHORTS"]


def test_pauses_for_approval_then_continues():
    con = fresh()
    rid = engine.reset(con, settings.sim_seed, "typical", autopilot=False)
    assert engine.advance(con, rid, 30) == PLAN_AT
    s = engine.state(con, rid)
    assert s["waiting_for_approval"] and s["stage"] == "APPROVAL" and s["pending_rows"] >= 5
    first = con.execute("SELECT row_id FROM cta_plan WHERE run_id=? AND status='Pending' AND group_type='cohort'", (rid,)).fetchone()[0]
    engine.decide(con, rid, first, "Approved")
    assert engine.advance(con, rid, 30) == PLAN_AT                     # the rest still need a decision
    for (row_id,) in con.execute("SELECT row_id FROM cta_plan WHERE run_id=? AND status='Pending' AND group_type!='individual_group'", (rid,)):
        engine.decide(con, rid, row_id, "Approved")
    assert engine.advance(con, rid, 30) == 30


def test_autopilot_runs_straight_through():
    con = fresh()
    rid = engine.reset(con, settings.sim_seed, "typical", autopilot=True)
    assert engine.advance(con, rid, 30) == 30
    assert engine.state(con, rid)["stage"] == "LEARN"


def test_next_stage_walks_the_loop():
    con = fresh()
    rid = engine.reset(con, settings.sim_seed, "typical", autopilot=True)
    stages = []
    for _ in range(5):
        engine.next_stage(con, rid)
        stages.append(engine.state(con, rid)["stage"])
    assert stages == ["COLLECT", "REMINDER", "APPROVAL", "SEND_CTA", "LEARN"] or stages == ["COLLECT", "REMINDER", "PLAN", "SEND_CTA", "LEARN"]


# ------------------------------------------------------------------------------------------------ time-aware
def test_numbers_at_a_day_are_sql_over_rows_up_to_that_day(default_run):
    con, rid = default_run
    for day in (0.5, 3.0, 6.9):
        replied = con.execute("SELECT COUNT(DISTINCT distributor_id) FROM survey_responses WHERE run_id=? AND submitted_at<=?",
                              (rid, day)).fetchone()[0]
        assert engine.counters(con, rid, day)["replied"] == replied
        assert sum(f.replied for f in facts(con, rid, day).values()) == replied
        assert all(e["sim_day"] <= day for e in engine.events(con, rid, day))
    assert engine.counters(con, rid, 3.0)["follow_ups"] == 0 and engine.counters(con, rid, 29.9)["beat_prediction"] == 0


# ------------------------------------------------------------------------------------------------ decisions matter
def test_rejecting_a_cohort_cta_lowers_its_joins():
    approve, rid_a = full_run()
    reject, rid_r = full_run(reject=["cohort:Replace / Reassess"])
    joins = lambda con, rid: sum(1 for f in facts(con, rid, 30).values() if f.cohort == "Replace / Reassess" and f.enrol)  # noqa: E731
    assert joins(reject, rid_r) < joins(approve, rid_a)


def test_dropping_a_flag_is_recorded_and_kept_out():
    con = fresh()
    rid = engine.reset(con, settings.sim_seed, "typical", autopilot=False)
    engine.advance(con, rid, 1.0)
    rp = facts(con, rid, 1.0)["DST-0006"].latest
    engine.flag_decision(con, rid, rp["response_id"], "Drop")
    f = facts(con, rid, 1.0)["DST-0006"]
    assert f.decision() == "Drop" and not f.counted
    assert facts(con, rid, 0.5)["DST-0006"].decision() is None            # not decided yet at an earlier day


# ------------------------------------------------------------------------------------------------ scenarios
def test_scenarios_move_the_numbers_but_not_the_anchors():
    base = report(settings.sim_seed)
    low = report(settings.sim_seed, "low_response")
    great = report(settings.sim_seed, "great_uptake")
    messy = report(settings.sim_seed, "messy_survey")
    assert low["replied"] < base["replied"]
    assert great["joined_d30"] > base["joined_d30"]
    assert messy["red"] > base["red"]
    for scenario in ("low_response", "messy_survey", "great_uptake"):
        con = fresh()
        rid = engine.reset(con, settings.sim_seed, scenario, autopilot=True)
        engine.advance(con, rid, 30)
        f = facts(con, rid, 30)
        assert f["DST-0001"].latest["q1_intent"] == "Explain in Bengali" and int(f["DST-0001"].enrol["sim_day"]) == 9
        assert f["DST-0006"].red_flagged and f["DST-0005"].enrol is None


def test_plan_rows_use_only_catalogue_ctas(default_run):
    from app.engines.cta_planner import catalogue

    con, rid = default_run
    codes = {r[0] for r in con.execute("SELECT cta_code FROM cta_plan WHERE run_id=? AND group_type!='individual_group'", (rid,))}
    assert codes <= set(catalogue())
    for (members_json, members) in con.execute("SELECT member_ids_json, members FROM cta_plan WHERE run_id=?", (rid,)):
        assert len(json.loads(members_json)) == members


def test_hosted_copy_can_open_on_a_finished_cycle():
    """SIM_START_DAY (hosted review copy): a fresh server builds the default run, plays it to that day with every
    suggestion accepted, then hands control back (autopilot off) so Reset → Play still works."""
    con = fresh()
    object.__setattr__(settings, "sim_start_day", 30.0)
    try:
        run = engine.ensure_run(con, settings.sim_seed, "typical", autopilot=False)
    finally:
        object.__setattr__(settings, "sim_start_day", 0.0)
    s = engine.state(con, run["run_id"])
    assert s["day"] == 30 and not s["autopilot"] and s["counters"]["joined"] == 50
