"""Scenarios tweak the hidden traits (SIMULATION_SPEC §7). Anchors stay scripted in every scenario."""
from __future__ import annotations

SCENARIOS = {
    "typical": "Traits as generated",
    "low_response": "Fewer replies (reply chance × 0.6)",
    "messy_survey": "More careless answers (low-effort × 3)",
    "great_uptake": "More joins (all join chances × 1.2)",
}


def apply(scenario: str, t: dict) -> dict:
    t = dict(t)
    if scenario == "low_response":
        t["response_prob"] = t["response_prob"] * 0.6
    elif scenario == "messy_survey":
        t["low_effort_prob"] = min(0.9, t["low_effort_prob"] * 3)
    elif scenario == "great_uptake":
        for k in ("enrol_prob_day0", "enrol_prob_after_matching_cta"):
            t[k] = min(0.98, t[k] * 1.2)
    elif scenario != "typical":
        raise ValueError(f"Unknown scenario {scenario!r}")
    return t
