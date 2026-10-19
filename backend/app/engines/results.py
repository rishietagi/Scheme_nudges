"""Day-30 results: the five plain questions (PROJECT_CONTEXT §9). Code computes every number."""
from __future__ import annotations

import statistics

from app.content.terms import intent_labels
from app.db.run_queries import Fact
from app.engines.cohorts import DISPLAY_ORDER as COHORTS
from app.engines.cta_planner import SHORT
from app.rules.loader import survey_rules
from app.simulation.behaviour import CTA_AT


def intents() -> list[str]:
    return next(q for q in survey_rules()["questions"] if q["id"] == "Q1")["options"]


def compute(facts: dict[str, Fact], sales: dict[str, dict], last_scheme_joined: int) -> dict:
    fs = list(facts.values())
    joined = [f for f in fs if f.enrol]

    # 1. Did they join?
    by_cohort = [{"cohort": c, "joined": sum(1 for f in joined if f.cohort == c), "total": sum(1 for f in fs if f.cohort == c)}
                 for c in COHORTS]

    # 2. Did joining pay off?
    hit = [f for f in joined if sales.get(f.distributor_id, {}).get("hit_prediction")]

    def lift(group: list[Fact]) -> float | None:
        base = sum(sales[f.distributor_id]["baseline_l"] for f in group if f.distributor_id in sales)
        act = sum(sales[f.distributor_id]["actual_l"] for f in group if f.distributor_id in sales)
        return round(act / base - 1, 4) if base else None

    # 3. How fast did they react?
    def bucket(f: Fact) -> str:
        if not f.enrol:
            return "Never"
        d = f.enrol["sim_day"]
        return "Same day" if d < 1 else ("First week" if d < CTA_AT else "After follow-up")

    speed = {b: sum(bucket(f) == b for f in fs) for b in ["Same day", "First week", "After follow-up", "Never"]}
    first_reply_h = [round((f.responses[0]["submitted_at"] - (f.nudge_at or 0)) * 24, 2) for f in fs if f.responses]
    join_after = [f.enrol["sim_day"] - CTA_AT for f in joined if f.enrol["sim_day"] >= CTA_AT]

    # 4. What did they ask for on Day 0?
    asked = {i: sum(1 for f in fs if f.latest and f.latest["q1_intent"] == i) for i in intents()}
    asked["No reply"] = sum(1 for f in fs if not f.replied)

    # 5. Which follow-up worked?
    received: dict[str, set] = {}
    for f in fs:
        for d in f.deliveries:
            received.setdefault(d["cta_code"], set()).add(f.distributor_id)
    worked = []
    for code, ids in received.items():
        j = sum(1 for d in ids if facts[d].enrol and facts[d].enrol["path"] in ("after_cta", "after_asm_call")
                and facts[d].enrol.get("cta_code") == code)
        worked.append({"cta_code": code, "label": SHORT[code], "received": len(ids), "joined": j,
                       "rate": round(j / len(ids), 4) if ids else 0})
    worked.sort(key=lambda w: -w["rate"])

    return {
        "joined": len(joined),
        "total": len(fs),
        "last_scheme_joined": last_scheme_joined,
        "joined_by_cohort": by_cohort,
        "beat_prediction": len(hit),
        "fell_short": len(joined) - len(hit),
        "sales_lift_joined": lift(joined),
        "sales_lift_not_joined": lift([f for f in fs if not f.enrol]),
        "speed": speed,
        "median_first_reply_hours": round(statistics.median(first_reply_h), 1) if first_reply_h else None,
        "median_join_days_after_follow_up": round(statistics.median(join_after), 1) if join_after else None,
        "asked": asked,
        "asked_labels": {**intent_labels(intents()), "No reply": "No reply"},
        "follow_ups": worked,
    }
