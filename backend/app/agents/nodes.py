"""Agent nodes of the loop graph. Each reads/writes run tables and emits `events` rows.

The simulator decides what distributors *do* (app/simulation/behaviour.py); these agents are the product logic that
reacts: send, check, plan, execute, measure, learn. Code makes every number; the LLM only writes message text.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict

from pydantic import BaseModel

from app.db import queries
from app.db.run_queries import Fact, facts
from app.engines import cta_planner, persona, results, sanity_checks
from app.engines.cohorts import DISPLAY_ORDER
from app.llm.client import complete
from app.rules.loader import survey_rules
from app.simulation import behaviour, traits
from app.simulation.behaviour import CTA_AT, LAST, NUDGE_AT, REMINDER_AT
from app.simulation.clock import at

PLAN_AT = at(7, 10)               # Day 7 10:00 — plan ready, approval gate
ASM = cta_planner.ASM_FIRST_NAME
LANGS = ("English", "Bengali", "Hindi")
INTENT_TEXT = {
    "I've enrolled": "said they've enrolled",
    "I'll enrol": "said they'll enrol",
    "Explain again": "asked for the scheme to be explained again",
    "Explain in Bengali": "asked for an explanation in Bengali",
    "Talk to my ASM": f"asked to talk to {ASM}",
}


class Text(BaseModel):
    text: str


class CtaText(BaseModel):
    text: str
    why: str


# ------------------------------------------------------------------------------------------------ helpers
def emit(con: sqlite3.Connection, run_id: str, day: float, type_: str, agent: str, text: str,
         distributor_id: str | None = None, feed: bool = True, payload: dict | None = None) -> None:
    con.execute(
        "INSERT INTO events (run_id, sim_day, type, agent, distributor_id, text, feed, payload_json) VALUES (?,?,?,?,?,?,?,?)",
        (run_id, round(day, 6), type_, agent, distributor_id, text, int(feed), json.dumps(payload) if payload else None),
    )


def flush(con: sqlite3.Connection, run_id: str, buffered: list[tuple]) -> None:
    """Insert buffered events in time order so ids follow the clock within a segment."""
    for e in sorted(buffered, key=lambda e: e[0]):
        emit(con, run_id, *e)


def inr(lakh: float) -> str:
    return f"₹{lakh / 100:.1f} Cr".replace(".0 ", " ") if lakh >= 100 else f"₹{lakh:.1f} L".replace(".0 ", " ")


def rupees(lakh: float) -> str:
    """Indian digit grouping: 0.234 L -> ₹23,400."""
    n = int(round(lakh * 100000, -2))
    s = str(n)
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return "₹" + ",".join(([head] if head else []) + groups + [tail])


def possessive(name: str) -> str:
    return f"{name}'" if name.endswith("s") else f"{name}'s"


ASM_IN = {"Bengali": "রাহুল", "Hindi": "राहुल"}


def fill(template: str, f: Fact, language: str = "English") -> str:
    return template.format(owner_first=f.owner_name.split()[0], target=inr(f.target_l), stretch=inr(f.stretch_l),
                           asm=ASM_IN.get(language, ASM), earn_hit=rupees(f.target_l * 0.03))


def lang_of(language: str) -> str:
    return language if language in LANGS else "English"


def scheme_text(con: sqlite3.Connection) -> str:
    return con.execute("SELECT rules_text FROM world.schemes WHERE scheme_id = ?", (queries.CURRENT_SCHEME,)).fetchone()[0]


def run_row(con: sqlite3.Connection, run_id: str) -> sqlite3.Row:
    return con.execute("SELECT * FROM loop_runs WHERE run_id = ?", (run_id,)).fetchone()


# ------------------------------------------------------------------------------------------------ Day 0
def cohort_agent(state: dict) -> dict:
    con, run_id = state["con"], state["run_id"]
    counts = Counter(f.cohort for f in facts(con, run_id, 0).values())
    mix = " · ".join(f"{c} {counts[c]}" for c in DISPLAY_ORDER)
    emit(con, run_id, 0.0, "COHORTS", "Cohort agent", f"Cohorts set for Kolkata North (rules v2.0): {mix}")
    return state


def nudge_agent(state: dict) -> dict:
    con, run_id = state["con"], state["run_id"]
    fs = facts(con, run_id, 0)
    brief, scheme = survey_rules()["nudge_brief"], scheme_text(con)
    templates: dict[tuple[str, str], str] = {}
    for f in fs.values():
        key = (f.cohort, lang_of(f.language_on_file))
        if key not in templates:
            inputs = {"kind": "nudge", "cohort": f.cohort, "brief": brief[f.cohort], "scheme": scheme, "language": key[1]}
            templates[key] = complete("nudge_message", inputs, Text, fixture_key=f"{key[0]}|{key[1]}").text
    events = []
    for f in fs.values():
        lang = lang_of(f.language_on_file)
        con.execute("INSERT INTO nudges VALUES (?,?,?,?,?,?,?)",
                    (run_id, f.distributor_id, f.cohort, "nudge", lang, NUDGE_AT, fill(templates[(f.cohort, lang)], f, lang)))
        events.append((NUDGE_AT, "NUDGE_SENT", "Nudge agent",
                       f"Sent the {f.cohort} nudge with the October target ({inr(f.target_l)})", f.distributor_id, False))
    for cohort in DISPLAY_ORDER:
        group = [f for f in fs.values() if f.cohort == cohort]
        bn = sum(f.language_on_file == "Bengali" for f in group)
        events.append((NUDGE_AT, "NUDGE_SENT", "Nudge agent",
                       f"Nudge sent to {len(group)} {cohort} distributors ({bn} in Bengali)", None, True))
    flush(con, run_id, events)
    return state


def survey_agent(state: dict) -> dict:
    """Plays every distributor's Day 0–7 behaviour, records replies, runs sanity checks, sends the Day-3 reminder."""
    con, run_id = state["con"], state["run_id"]
    run = run_row(con, run_id)
    hidden = traits.load(con, queries.TERRITORY_ID, run["scenario"])
    fs = facts(con, run_id, 0)
    events: list[tuple] = []
    first_reply: dict[str, float] = {}

    for did, f in fs.items():
        b = behaviour.day0(run["seed"], did, hidden[did], f.cohort)
        if b.enrol_day is not None:
            con.execute("INSERT INTO enrolments VALUES (?,?,?,?,?)", (run_id, did, b.enrol_day, b.enrol_path, None))
            # A hair after the reply that announced it, so the feed reads in order.
            events.append((b.enrol_day + 1e-5, "ENROLLED", "Execution", f"{f.name} joined the scheme", did, True))
        if not b.reply:
            continue
        rp = b.reply
        first_reply[did] = rp.submitted_at
        copies = [rp.submitted_at] + ([rp.duplicate_at] if rp.duplicate_at else [])
        for i, sub in enumerate(copies):
            rid = f"{did}:{i + 1}"
            row = {"response_id": rid, "distributor_id": did, "started_at": sub - rp.survey_seconds / 86400,
                   "submitted_at": sub, "survey_seconds": rp.survey_seconds, "q1_intent": rp.q1, "q2": rp.q2, "q3": rp.q3,
                   "q4": rp.q4, "q5": rp.q5, "q6": rp.q6, "q7_text": rp.q7_text, "q7_language": rp.q7_language,
                   "q7_theme": rp.q7_theme, "is_duplicate": int(len(copies) > 1), "is_latest": int(i == len(copies) - 1)}
            con.execute(
                """INSERT INTO survey_responses VALUES (:run_id,:response_id,:distributor_id,:started_at,:submitted_at,
                   :survey_seconds,:q1_intent,:q2,:q3,:q4,:q5,:q6,:q7_text,:q7_language,:q7_theme,:is_duplicate,:is_latest)""",
                {"run_id": run_id, **row})
            enrolled = b.enrol_day is not None and b.enrol_day <= sub
            flags = sanity_checks.check(row, enrolled_at_submit=enrolled, is_duplicate=i > 0)
            for fl in flags:
                con.execute("INSERT INTO sanity_flags VALUES (?,?,?,?,?,?,?)",
                            (run_id, rid, fl.code, fl.severity, fl.label, None, None))
            if i == 0:
                after = " (after the reminder)" if rp.after_reminder else ""
                events.append((sub, "REPLY", "Survey agent", f"{f.name} {INTENT_TEXT[rp.q1]}{after}", did, True,
                               {"intent": rp.q1}))
            if flags:
                codes = [fl.code for fl in flags]
                red = any(fl.severity == "red" for fl in flags)
                why = sanity_checks.short_reason(codes, row)
                text = f"{possessive(f.name)} survey flagged: {why[:1].lower() + why[1:]}" if red else f"{possessive(f.name)} answers need a look: {why[:1].lower() + why[1:]}"
                events.append((sub, "FLAG", "Survey agent", text, did, True, {"codes": codes, "severity": "red" if red else "amber"}))
            elif i == 0:
                events.append((sub, "CHECKED", "Survey agent", "Answer passed all sanity checks", did, False))

    # Day-3 reminder to everyone who hasn't replied by then, at 10:00 (their persona has no better time yet).
    waiting = [f for did, f in fs.items() if first_reply.get(did, 99) > REMINDER_AT]
    tmpl = {lang: complete("nudge_message", {"kind": "reminder", "scheme": scheme_text(con), "language": lang}, Text,
                           fixture_key=f"reminder|{lang}").text for lang in LANGS}
    for f in waiting:
        lang = lang_of(f.language_on_file)
        con.execute("INSERT INTO nudges VALUES (?,?,?,?,?,?,?)",
                    (run_id, f.distributor_id, f.cohort, "reminder", lang, REMINDER_AT, fill(tmpl[lang], f, lang)))
        events.append((REMINDER_AT, "REMINDER", "Nudge agent", "Sent the Day-3 reminder", f.distributor_id, False))
    events.append((REMINDER_AT, "REMINDER", "Nudge agent", f"Reminder sent to {len(waiting)} distributors who haven't replied yet",
                   None, True))
    flush(con, run_id, events)
    return state


# ------------------------------------------------------------------------------------------------ Day 7
def members_at(con: sqlite3.Connection, run_id: str, day: float) -> tuple[list[cta_planner.Member], dict[str, float]]:
    fs = facts(con, run_id, day)
    members = []
    for f in fs.values():
        latest = f.latest
        members.append(cta_planner.Member(
            f.distributor_id, f.name, f.cohort, f.classification, f.enrol is not None, f.replied,
            latest["q1_intent"] if latest else None, latest["q6"] if latest else None,
            latest["q7_theme"] if latest else None, persona.compute(f, day)["language"], f.red_flagged,
            f.consecutive_down_months, f.uplift_l))
    clean: dict[str, float] = {}
    for c in DISPLAY_ORDER:
        replied = [f for f in fs.values() if f.cohort == c and f.replied]
        clean[c] = round(sum(f.counted for f in replied) / len(replied), 4) if replied else 1.0
    return members, clean


def cta_agent(state: dict) -> dict:
    con, run_id = state["con"], state["run_id"]
    # Rebuilding (e.g. after a custom group is added) keeps every decision already made.
    kept = {r["row_id"]: (r["status"], r["decided_at"]) for r in con.execute(
        "SELECT row_id, status, decided_at FROM cta_plan WHERE run_id = ? AND status != 'Pending'", (run_id,))}
    rebuild = con.execute("SELECT plan_built FROM loop_runs WHERE run_id = ?", (run_id,)).fetchone()[0]
    con.execute("DELETE FROM cta_plan WHERE run_id = ?", (run_id,))
    custom = [json.loads(r[0]) for r in con.execute(
        "SELECT payload_json FROM events WHERE run_id = ? AND type = 'CUSTOM_GROUP' ORDER BY event_id", (run_id,))]
    members, clean = members_at(con, run_id, PLAN_AT)
    rows = cta_planner.plan(members, clean, DISPLAY_ORDER, custom)
    scheme = scheme_text(con)

    def texts(row: cta_planner.PlanRow) -> dict[str, CtaText]:
        out = {}
        for lang in LANGS:
            inputs = {"cta_code": row.cta_code, "cta_label": cta_planner.DISPLAY[row.cta_code], "group": row.group_name,
                      "reason": row.reason, "scheme": scheme, "language": lang}
            out[lang] = complete("cta_message", inputs, CtaText, fixture_key=f"{row.cta_code}|{lang}")
        return out

    def insert(row: cta_planner.PlanRow) -> None:
        t = texts(row) if row.cta_code else None
        con.execute(
            "INSERT INTO cta_plan VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, row.row_id, row.group_type, row.group_name, row.parent_row_id, row.distributor_id, row.cta_code,
             row.cta_variant, row.label, t["English"].text if t else None, t["Bengali"].text if t else None,
             t["Hindi"].text if t else None, len(row.member_ids), json.dumps(row.member_ids), row.confidence, row.priority,
             row.revenue_at_stake_l, row.reason, t["English"].why if t else None, "Pending", PLAN_AT, None, row.sort_order))

    for r in rows:
        insert(r)
        for child in r.children:
            insert(child)
    for row_id, (status, decided_at) in kept.items():
        con.execute("UPDATE cta_plan SET status = ?, decided_at = ? WHERE run_id = ? AND row_id = ?", (status, decided_at, run_id, row_id))
    if rebuild:
        return state
    n_cohort = sum(r.group_type in ("cohort", "custom") for r in rows)
    n_people = sum(len(r.children) for r in rows)
    who = "Autopilot will approve it" if run_row(con, run_id)["autopilot"] else f"Waiting for {ASM}'s approval"
    emit(con, run_id, PLAN_AT, "PLAN_READY", "CTA agent",
         f"Follow-up plan ready: {n_cohort} cohort follow-ups, {n_people} individual. {who}")
    for r in rows:
        for child in r.children:
            emit(con, run_id, PLAN_AT, "PLAN_READY", "CTA agent",
                 f"{child.reason} → Individual attention: {child.label}", child.distributor_id, False)
    con.execute("UPDATE loop_runs SET plan_built = 1 WHERE run_id = ?", (run_id,))
    return state


def pending(con: sqlite3.Connection, run_id: str) -> int:
    return con.execute("SELECT COUNT(*) FROM cta_plan WHERE run_id = ? AND status = 'Pending' AND group_type != 'individual_group'",
                       (run_id,)).fetchone()[0]


def approval_gate(state: dict) -> dict:
    con, run_id = state["con"], state["run_id"]
    if run_row(con, run_id)["autopilot"] and pending(con, run_id):
        con.execute("UPDATE cta_plan SET status = 'Approved', decided_at = ? WHERE run_id = ? AND status = 'Pending'",
                    (PLAN_AT, run_id))
        emit(con, run_id, PLAN_AT, "APPROVED", "Autopilot", "Autopilot approved every follow-up")
    state["decided"] = pending(con, run_id) == 0
    return state


# ------------------------------------------------------------------------------------------------ Day 8 → 30
def execution_agent(state: dict) -> dict:
    con, run_id = state["con"], state["run_id"]
    run = run_row(con, run_id)
    hidden = traits.load(con, queries.TERRITORY_ID, run["scenario"])
    members, _ = members_at(con, run_id, PLAN_AT)
    by_id = {m.distributor_id: m for m in members}
    fs = facts(con, run_id, PLAN_AT)
    plan_rows = [dict(r) for r in con.execute("SELECT * FROM cta_plan WHERE run_id = ? AND group_type != 'individual_group' "
                                              "ORDER BY sort_order", (run_id,))]
    # Personal rows win over cohort rows for the same person.
    row_for: dict[str, dict] = {}
    for r in sorted(plan_rows, key=lambda r: r["group_type"] == "individual"):
        for did in json.loads(r["member_ids_json"]):
            row_for[did] = r

    # ASM calls/visits: Day 9–13, highest priority first, up to 4 a day from 11:00.
    callers = [did for did, r in row_for.items() if r["status"] == "Approved" and r["cta_code"] == "ASM_CALL"]
    callers.sort(key=lambda d: (["High", "Medium", "Low"].index(row_for[d]["priority"]), row_for[d]["group_type"] != "individual",
                                -fs[d].uplift_l))
    call_day = {d: at(9 + i // 4, 11) + (i % 4) * 1.5 / 24 for i, d in enumerate(callers) if 9 + i // 4 <= 13}

    events: list[tuple] = []
    sent = defaultdict(list)
    for did, r in row_for.items():
        f, m = fs[did], by_id[did]
        approved = r["status"] == "Approved"
        lang = lang_of(m.language)
        if approved:
            text = fill(r[{"English": "text_en", "Bengali": "text_bn", "Hindi": "text_hi"}[lang]] or r["text_en"], f, lang)
            con.execute("INSERT INTO cta_deliveries VALUES (?,?,?,?,?,?,?)", (run_id, did, r["row_id"], r["cta_code"], lang, CTA_AT, text))
            sent[r["row_id"]].append(lang)
            what = "a voice note" if r["cta_code"] == "VOICE_EXPLAINER" else cta_planner.SHORT[r["cta_code"]].lower()
            events.append((CTA_AT, "CTA_SENT", "Execution", f"Got {what} in {lang}", did, False))
        cday = call_day.get(did)
        join = behaviour.cta_join(run["seed"], did, hidden[did], approved=approved, matched=r["cta_code"] in cta_planner.matching(m),
                                  renudge_non_responder=r["cta_code"] == "RE_NUDGE" and not m.replied, call_day=cday)
        if cday is not None:
            kind = r["cta_variant"] or "call"
            if join:
                outcome = "Agreed to join"
            elif m.q6 == "Better margin" or m.comment_theme == "margin":
                outcome = "Wants better margins, not the scheme"
            else:
                outcome = "Not now"
            con.execute("INSERT INTO asm_calls VALUES (?,?,?,?,?,?)", (run_id, did, r["row_id"], cday, kind, outcome))
            verb = "visited" if kind == "visit" else "called"
            events.append((cday, "ASM_CALL", "Execution", f"{ASM} {verb} {f.name}: {outcome.lower()}", did, True))
        if join is not None and (cday is None or join > cday):
            path = "after_asm_call" if cday is not None else ("after_cta" if approved else "self")
            con.execute("INSERT INTO enrolments VALUES (?,?,?,?,?)", (run_id, did, join, path, r["cta_code"] if approved else None))
            how = {"after_asm_call": f" after {ASM}'s {'visit' if (r['cta_variant'] == 'visit') else 'call'}",
                   "after_cta": f" after the {cta_planner.SHORT[r['cta_code']].lower()}", "self": ""}[path]
            events.append((join, "ENROLLED", "Execution", f"{f.name} joined the scheme{how}", did, True))

    for r in plan_rows:
        langs = sent.get(r["row_id"])
        if not langs or r["group_type"] == "individual":
            continue
        bn = langs.count("Bengali")
        events.append((CTA_AT, "CTA_SENT", "Execution",
                       f"Follow-up sent to {len(langs)} {r['group_name']}: {cta_planner.SHORT[r['cta_code']].lower()}"
                       + (f" ({bn} in Bengali)" if bn else ""), None, True))
    people = [r for r in plan_rows if r["group_type"] == "individual" and r["status"] == "Approved"]
    if people:
        calls = sum(r["cta_code"] == "ASM_CALL" for r in people)
        events.append((CTA_AT, "CTA_SENT", "Execution",
                       f"{len(people)} personal follow-ups sent · {calls} calls or visits booked for {ASM} (Day 9–13)", None, True))
    flush(con, run_id, events)
    con.execute("UPDATE loop_runs SET segment_b_built = 1 WHERE run_id = ?", (run_id,))
    return state


def results_agent(state: dict) -> dict:
    con, run_id = state["con"], state["run_id"]
    run = run_row(con, run_id)
    hidden = traits.load(con, queries.TERRITORY_ID, run["scenario"])
    fs = facts(con, run_id, LAST)
    sales = {}
    for did, f in fs.items():
        actual = behaviour.october_sales(run["seed"], did, hidden[did], joined_day=f.enrol["sim_day"] if f.enrol else None,
                                         predicted=f.predicted_l, baseline=f.baseline_l, stretch=f.stretch_l)
        hit = int(f.enrol is not None and actual >= f.predicted_l)
        con.execute("INSERT INTO october_sales VALUES (?,?,?,?,?,?)", (run_id, did, f.baseline_l, f.predicted_l, actual, hit))
        sales[did] = {"baseline_l": f.baseline_l, "actual_l": actual, "hit_prediction": hit}
        if f.enrol:
            verdict = f"beat the {inr(f.predicted_l)} prediction" if hit else f"short of the {inr(f.predicted_l)} prediction"
            emit(con, run_id, LAST, "RESULTS", "Results agent", f"{inr(actual)} in October · {verdict}", did, False)
    r = results.compute(fs, sales, queries.territory(con)["joined_last_scheme"])
    pct = round(100 * r["joined"] / r["total"])
    emit(con, run_id, LAST, "RESULTS", "Results agent",
         f"Day-30 results ready: {r['joined']} of {r['total']} joined ({pct}%) · {r['beat_prediction']} beat their predicted sales boost")
    return state


def persona_agent(state: dict) -> dict:
    con, run_id = state["con"], state["run_id"]
    fs = facts(con, run_id, LAST)
    learned = [persona.compute(f, LAST) for f in fs.values()]
    for p in learned:
        con.execute("INSERT INTO personas VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (run_id, p["distributor_id"], p["language"], p["language_on_file"], int(p["language_changed"]), p["best_time"],
                     p["best_hour"], p["reply_speed"], p["reply_hours"], p["prefers"], p["what_worked"], p["next_time"], LAST))
        emit(con, run_id, LAST, "PERSONA", "Persona", f"Learned: {p['next_time']}", p["distributor_id"], False)
    bn = sum(p["language_changed"] and p["language"] == "Bengali" for p in learned)
    call = sum(p["prefers"] == "ASM call" for p in learned)
    evening = sum(p["best_time"] == "Evening" for p in learned)
    visit = sum(p["prefers"] == "ASM visit" for p in learned)
    emit(con, run_id, LAST, "PERSONA", "Persona",
         f"Personas updated: {bn} now get Bengali · {call} prefer a call from {ASM} · {evening} reply best in the evening · "
         f"{visit} to get a visit, not WhatsApp")
    return state
