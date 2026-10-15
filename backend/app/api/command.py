"""Command centre: four tiles, 'Needs you today' (≤ 3), an Emami AI summary and progress by cohort — as of a day."""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.nodes import PLAN_AT, pending
from app.api.sim import run_id
from app.db import queries
from app.db.conn import db
from app.db.run_queries import facts
from app.engines.cohorts import COLOR, DISPLAY_ORDER
from app.llm.client import complete
from app.models import CommandView, CohortProgress, NeedItem, SummaryLine, Tile
from app.simulation import engine
from app.simulation.behaviour import CTA_AT, LAST, NUDGE_AT, SURVEY_CLOSE
from app.simulation.clock import day_label

router = APIRouter(prefix="/command", tags=["command"])


class Summary(BaseModel):
    lines: list[str]


def _join(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _mostly(counter: Counter, k: int = 2) -> str:
    return _join([c for c, _ in counter.most_common(k)]) if counter else ""


@router.get("", response_model=CommandView)
def command(day: float | None = None) -> CommandView:
    with db() as con:
        rid = run_id(con)
        st = engine.state(con, rid)
        d = st["day"] if day is None else max(0.0, min(day, st["day"]))
        t = queries.territory(con)
        fs = list(facts(con, rid, d).values())
        run = con.execute("SELECT * FROM loop_runs WHERE run_id = ?", (rid,)).fetchone()
        plan_rows = [dict(r) for r in con.execute("SELECT * FROM cta_plan WHERE run_id = ?", (rid,))] if run["plan_built"] and d >= PLAN_AT else []
        waiting = bool(plan_rows) and d < CTA_AT and pending(con, rid) > 0 and d <= PLAN_AT + 1e-6
        upcoming = [dict(r) for r in con.execute(
            "SELECT c.*, d.name FROM asm_calls c JOIN world.distributors d USING (distributor_id) WHERE c.run_id = ? AND c.sim_day > ? "
            "ORDER BY c.sim_day LIMIT 3", (rid, d))] if run["segment_b_built"] else []
        sales = {r["distributor_id"]: dict(r) for r in con.execute("SELECT * FROM october_sales WHERE run_id = ?", (rid,))} if d >= LAST else {}

    n = len(fs)
    replied = [f for f in fs if f.replied]
    joined = [f for f in fs if f.enrol]
    hour = int((d % 1) * 24)
    greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")

    # ---- tiles
    top = [r for r in plan_rows if r["group_type"] in ("cohort", "custom", "individual_group")]
    people = [r for r in plan_rows if r["group_type"] == "individual"]
    if waiting:
        pend = [r for r in top if r["status"] == "Pending"]
        wait_value, wait_sub = len(pend), f"follow-up groups · {sum(r['members'] for r in pend)} distributors"
    elif not plan_rows:
        wait_value, wait_sub = 0, "the plan is ready on Day 7 at 10:00"
    else:
        wait_value, wait_sub = 0, "all decided · follow-ups go out Day 8" if d < CTA_AT else "follow-ups went out on Day 8"
    if people:
        ia_value = len(people)
    else:
        ia_value = sum(1 for f in fs if not f.enrol and (f.red_flagged or (f.latest and f.latest["q1_intent"] == "Talk to my ASM")))
    tiles = [
        Tile(key="replied", label="Replied to the survey", value=len(replied), sub=f"of {n} · {round(100 * len(replied) / n)}%"),
        Tile(key="joined", label="Joined the scheme so far", value=len(joined),
             sub=f"{round(100 * len(joined) / n)}% · last scheme ended at {round(100 * t['joined_last_scheme'] / n)}%"),
        Tile(key="waiting", label="Waiting for your approval", value=wait_value, sub=wait_sub),
        Tile(key="individual", label="Need individual attention", value=ia_value, sub="asked for you, key accounts, flagged"),
    ]

    # ---- needs you today (≤ 3, most urgent first)
    needs: list[NeedItem] = []
    if d < NUDGE_AT:
        needs.append(NeedItem(tone="orange", title="Send the Festive nudge", sub=f"{n} distributors · one message per cohort at 10:00",
                              href="/simulation", action="Run the loop"))
    if waiting:
        needs.append(NeedItem(tone="orange", title="Approve the follow-up plan", sub=f"{wait_value} groups · goes out tomorrow morning",
                              href="/approvals", action="Open approvals"))
    undecided = [f for f in replied if f.red_flagged and f.decision() is None]
    if undecided and d < CTA_AT:
        first = undecided[0]
        needs.append(NeedItem(tone="red", title=f"Review {len(undecided)} flagged survey answers",
                              sub=f"e.g. {first.name} filled it in {first.latest['survey_seconds']} seconds", href="/survey", action="Review"))
    asked = [f for f in replied if f.latest["q1_intent"] == "Talk to my ASM" and not f.enrol]
    asked.sort(key=lambda f: (f.classification != "A", f.latest["submitted_at"]))
    if asked and d < CTA_AT:
        f = asked[0]
        who = "Key account · " if f.classification == "A" else ""
        needs.append(NeedItem(tone="blue", title=f"Call {f.name}", sub=f"{who}asked to talk to you on Day {int(f.latest['submitted_at'])}",
                              href=f"/distributor?id={f.distributor_id}", action="See chat"))
    for c in upcoming:
        verb = "Visit" if c["kind"] == "visit" else "Call"
        needs.append(NeedItem(tone="blue", title=f"{verb} {c['name']}", sub=f"Booked for {day_label(c['sim_day'])}",
                              href=f"/distributor?id={c['distributor_id']}", action="See chat"))
    if d >= LAST:
        needs.insert(0, NeedItem(tone="orange", title="See what worked this cycle", sub=f"{len(joined)} of {n} joined · results are ready",
                                 href="/results", action="Open results"))
    needs = needs[:3]

    # ---- Emami AI summary: code drafts from the numbers, the LLM only polishes the wording
    by_cohort = {c: [f for f in fs if f.cohort == c] for c in DISPLAY_ORDER}
    if d < NUDGE_AT:
        label = "Emami AI · today"
        draft = [f"The Festive Scheme goes live today.",
                 f"{n} distributors in 5 cohorts get one nudge each at 10:00.",
                 f"Last scheme, {t['joined_last_scheme']} of {n} joined ({round(100 * t['joined_last_scheme'] / n)}%) — the bar to beat."]
        bold = None
    else:
        early = [c for c, g in by_cohort.items() if g and sum(1 for f in g if f.enrol and f.enrol["sim_day"] < 1) / len(g) >= 0.4]
        explain = [f for f in replied if f.latest["q1_intent"] in ("Explain again", "Explain in Bengali")]
        bengali = sum(1 for f in explain if f.latest["q1_intent"] == "Explain in Bengali")
        silent = Counter(f.cohort for f in fs if not f.replied)
        line1 = (f"{_join(early)} mostly joined on Day 0." if early else f"{sum(1 for f in joined if f.enrol['sim_day'] < 1)} joined on Day 0.")
        line2 = (f"{len(explain)} distributors asked for the scheme to be explained again, {bengali} of them in Bengali, mostly "
                 f"{Counter(f.cohort for f in explain).most_common(1)[0][0]}." if explain else "Nobody has asked for an explanation yet.")
        line3 = f"{sum(silent.values())} haven't replied yet, mostly {_mostly(silent)}." if silent else "Everyone has replied."
        draft, bold = [line1, line2, line3], 1
        label = "Emami AI · so far" if d < SURVEY_CLOSE else "Emami AI · first week in short"
        if d >= CTA_AT:
            after = [f for f in joined if f.enrol["sim_day"] >= CTA_AT]
            label = "Emami AI · since the follow-ups"
            draft = [line1, f"{len(after)} joined after the Day-8 follow-ups; {len(joined)} of {n} are in so far.", line3 if d < 7.5 else
                     f"{n - len(joined)} still out, mostly {_mostly(Counter(f.cohort for f in fs if not f.enrol))}."]
            bold = 1
        if d >= LAST:
            label = "Emami AI · the cycle in short"
            beat = sum(1 for s in sales.values() if s["hit_prediction"])
            draft = [f"{len(joined)} of {n} joined, against {t['joined_last_scheme']} last scheme.",
                     f"{beat} of them beat their predicted sales boost.", draft[2]]
            bold = 0
    polished = complete("first_week_summary", {"stage": label, "facts": draft}, Summary, fallback={"lines": draft})
    lines = polished.lines if len(polished.lines) == len(draft) else draft
    summary = [SummaryLine(text=x, bold=i == bold) for i, x in enumerate(lines)]

    progress = [CohortProgress(name=c, color=COLOR[c], distributors=len(g), replied=sum(f.replied for f in g),
                               joined=sum(1 for f in g if f.enrol)) for c, g in by_cohort.items()]
    return CommandView(day=d, day_label=day_label(d), greeting=f"{greeting}, Rahul",
                       eyebrow=f"{t['scheme_name']} · {t['name']} · {n} distributors", tiles=tiles, needs=needs,
                       summary_label=label, summary=summary, cohorts=progress)
