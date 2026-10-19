"""CTA planner (rules/ctas.yaml): one follow-up per cohort for members not enrolled by Day 7, plus personal
follow-ups for the Individual attention list. Code picks every CTA and computes confidence and priority;
the LLM only writes the message text and the one-line "why".
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from app.rules.loader import cta_rules

ASM_FIRST_NAME = "Rahul"

# Plain follow-up lines, as worded on the approval-matrix render.
DISPLAY = {
    "SLAB_PROGRESS": "Show how close they are to the next slab",
    "QUICK_REMINDER": "Quick reminder with their personal target",
    "EXPLAIN_SIMPLE": "Simple explainer card with an earnings example",
    "VOICE_EXPLAINER": "Voice note + simple card, in their language",
    "ASM_CALL": f"{ASM_FIRST_NAME} calls within 48 hours",
    "RE_NUDGE": "Short re-send at their usual reply time",
}
# Short names for the Day-30 "Which follow-up worked?" card.
SHORT = {
    "SLAB_PROGRESS": "Slab progress",
    "QUICK_REMINDER": "Quick reminder",
    "EXPLAIN_SIMPLE": "Simple explainer card",
    "VOICE_EXPLAINER": "Voice note + simple card",
    "ASM_CALL": f"Call or visit from {ASM_FIRST_NAME}",
    "RE_NUDGE": "Re-send",
}


@dataclass
class Member:
    distributor_id: str
    name: str
    cohort: str
    classification: str
    enrolled: bool                    # enrolled by Day 7
    replied: bool
    intent: str | None                # latest Q1
    q6: str | None
    comment_theme: str | None
    language: str                     # persona language at Day 7
    red_flagged: bool
    consecutive_down_months: int
    uplift_l: float                   # predicted if enrolled − baseline
    high_potential: bool = False      # big market (Invest / Expand, Replace / Reassess)
    high_performance: bool = False    # performing (Invest / Expand, Protect)


@dataclass
class PlanRow:
    row_id: str
    group_type: str                   # cohort | individual_group | individual | custom
    group_name: str
    cta_code: str | None
    label: str
    member_ids: list[str]
    confidence: float | None
    revenue_at_stake_l: float
    reason: str
    cta_variant: str | None = None
    distributor_id: str | None = None
    parent_row_id: str | None = None
    priority: str = "Low"
    sort_order: int = 0
    children: list["PlanRow"] = field(default_factory=list)


def catalogue() -> list[str]:
    return list(cta_rules()["ctas"])


def need(m: Member) -> str:
    """The CTA this member's own answers point to."""
    if not m.replied:
        # Big market but under-delivering (Replace / Reassess) is worth a call from Rahul; others get a re-send.
        return "ASM_CALL" if m.high_potential and not m.high_performance else "RE_NUDGE"
    if m.intent == "Explain in Bengali":
        return "VOICE_EXPLAINER"
    if m.intent == "Explain again":
        return "VOICE_EXPLAINER" if m.language == "Bengali" else "EXPLAIN_SIMPLE"
    if m.intent == "Talk to my ASM":
        return "ASM_CALL"
    return "QUICK_REMINDER"            # I'll enrol, or said enrolled but isn't


def matching(m: Member) -> set[str]:
    """Follow-ups that fit this member's need (SIMULATION_SPEC §3 'CTA effect')."""
    if not m.replied:
        ok = {"RE_NUDGE"}
        if not m.high_performance or m.classification == "A":
            ok.add("ASM_CALL")
        return ok
    ok = {
        "Explain in Bengali": {"VOICE_EXPLAINER"},
        "Explain again": {"EXPLAIN_SIMPLE", "VOICE_EXPLAINER"},
        "Talk to my ASM": {"ASM_CALL"},
        "I'll enrol": {"QUICK_REMINDER", "SLAB_PROGRESS"},
        "I've enrolled": {"QUICK_REMINDER", "ASM_CALL"},
    }.get(m.intent or "", set())
    if m.classification == "A":
        ok = ok | {"ASM_CALL"}
    return set(ok)


def _personal(m: Member) -> tuple[str, str | None, str, str, float] | None:
    """(cta, variant, label, reason, confidence) if this member needs individual attention, else None."""
    margin = m.q6 == "Better margin" or m.comment_theme == "margin"
    if m.red_flagged:
        reason = "Survey flagged · says participating but isn't" if m.intent == "I've enrolled" else "Survey flagged"
        return "ASM_CALL", "call", f"{ASM_FIRST_NAME} calls to check", reason, 0.80
    if m.intent == "Talk to my ASM":
        who = "Key account · asked to talk to you" if m.classification == "A" else "Asked to talk to you"
        label = f"{ASM_FIRST_NAME} calls about margins" if margin else f"{ASM_FIRST_NAME} calls"
        return "ASM_CALL", "call", label, who, 0.90
    if m.classification == "A":
        n = need(m)
        if n == "VOICE_EXPLAINER":
            lang = "Bengali " if m.language == "Bengali" else ""
            asked = "asked for Bengali" if m.intent == "Explain in Bengali" else "asked to explain again"
            return n, None, f"{lang}voice note + card".capitalize(), f"Key account · {asked}", 0.86
        if n == "EXPLAIN_SIMPLE":
            return n, None, f"Simple card + {ASM_FIRST_NAME} calls", "Key account · asked to explain again", 0.78
        if n == "QUICK_REMINDER":
            return n, None, "Reminder with their target", "Key account · not participating yet", 0.78
        return "ASM_CALL", "call", f"{ASM_FIRST_NAME} calls", "Key account · no reply", 0.74
    if not m.high_performance and not m.replied and m.consecutive_down_months >= 4 and m.classification in ("A", "B"):
        return "ASM_CALL", "visit", f"{ASM_FIRST_NAME} visits this week", "Under-delivering, sales falling · no reply", 0.72
    return None


EXPLAIN = ("VOICE_EXPLAINER", "EXPLAIN_SIMPLE")


def _cohort_cta(group: list[Member], order: list[str]) -> tuple[str, int]:
    """Most common need wins. Both explainers answer "explain it again", so they count together; the voice note
    is used when most of those asking speak Bengali."""
    needs = Counter("EXPLAIN" if need(m) in EXPLAIN else need(m) for m in group)
    rank = lambda c: order.index("VOICE_EXPLAINER" if c == "EXPLAIN" else c)  # noqa: E731
    top = min(needs, key=lambda c: (-needs[c], rank(c)))
    if top != "EXPLAIN":
        return top, needs[top]
    askers = [m for m in group if need(m) in EXPLAIN]
    bengali = sum(m.language == "Bengali" for m in askers)
    return ("VOICE_EXPLAINER" if bengali * 2 >= len(askers) else "EXPLAIN_SIMPLE"), len(askers)


def _cohort_reason(cta: str, n: int, m: int, cohort: str, members: list[Member]) -> str:
    if cta == "QUICK_REMINDER":
        return f"{n} of {m} said “Will participate”"
    if cta in ("VOICE_EXPLAINER", "EXPLAIN_SIMPLE"):
        return f"{n} of {m} asked for it to be explained again"
    if cta == "RE_NUDGE":
        return f"{n} of {m} never replied"
    if cta == "ASM_CALL":
        silent = sum(not x.replied for x in members)
        under = members and members[0].high_potential and not members[0].high_performance
        return f"Big market, under-delivering; {silent} didn't reply" if under else f"{n} of {m} asked for a call"
    return f"{n} of {m} point to this"


def _tertiles(rows: list[PlanRow]) -> None:
    ranked = sorted(rows, key=lambda r: -r.revenue_at_stake_l)
    k = len(ranked)
    for i, r in enumerate(ranked):
        r.priority = "High" if i < math.ceil(k / 3) else ("Medium" if i < math.ceil(2 * k / 3) else "Low")


def plan(members: list[Member], clean_share: dict[str, float], cohort_order: list[str],
         custom_groups: list[dict] | None = None) -> list[PlanRow]:
    """All plan rows in display order. Individual people hang under the Individual attention row (children)."""
    order = catalogue()
    open_ = [m for m in members if not m.enrolled]
    custom_ids = {d for g in (custom_groups or []) for d in g["member_ids"]}

    people: list[PlanRow] = []
    for m in open_:
        if m.distributor_id in custom_ids:
            continue
        p = _personal(m)
        if p:
            cta, variant, label, reason, conf = p
            people.append(PlanRow(f"person:{m.distributor_id}", "individual", m.name, cta, label, [m.distributor_id],
                                  conf, round(m.uplift_l, 2), reason, variant, m.distributor_id, "individual"))
    in_person = {p.distributor_id for p in people}

    rows: list[PlanRow] = []
    for cohort in cohort_order:
        group = [m for m in open_ if m.cohort == cohort and m.distributor_id not in in_person | custom_ids]
        if not group:
            continue
        cta, n = _cohort_cta(group, order)
        rows.append(PlanRow(f"cohort:{cohort}", "cohort", cohort, cta, DISPLAY[cta], [m.distributor_id for m in group],
                            round(n / len(group) * clean_share.get(cohort, 1.0), 2),
                            round(sum(m.uplift_l for m in group), 2), _cohort_reason(cta, n, len(group), cohort, group)))

    by_id = {m.distributor_id: m for m in members}
    for i, g in enumerate(custom_groups or []):
        group = [by_id[d] for d in g["member_ids"] if d in by_id and not by_id[d].enrolled]
        if not group:
            continue
        needs = Counter(need(m) for m in group)
        cta = g.get("cta_code") or min(needs, key=lambda c: (-needs[c], order.index(c)))
        n = sum(cta in matching(m) for m in group)
        rows.append(PlanRow(f"custom:{i + 1}", "custom", g["name"], cta, DISPLAY[cta], [m.distributor_id for m in group],
                            round(n / len(group), 2), round(sum(m.uplift_l for m in group), 2),
                            f"Hand-picked · {n} of {len(group)} fit this follow-up"))

    if people:
        _tertiles(people)
        people.sort(key=lambda p: (["High", "Medium", "Low"].index(p.priority), -(p.confidence or 0), -p.revenue_at_stake_l))
        for i, p in enumerate(people):
            p.sort_order = i
        rows.append(PlanRow("individual", "individual_group", "Individual attention", None, "Personal follow-ups (see list)",
                            [p.distributor_id for p in people if p.distributor_id], None,
                            round(sum(p.revenue_at_stake_l for p in people), 2),
                            "Asked for you, key accounts, flagged answers", children=people))

    _tertiles(rows)
    rows.sort(key=lambda r: -r.revenue_at_stake_l)
    for i, r in enumerate(rows):
        r.sort_order = i
    return rows
