"""Cohort agent: places every distributor on the 2×2 in rules/cohorts.yaml (v4) — business potential of their
geography vs their performance — and explains why in plain words.

Business potential = the Emami potential of their town (modelled TAM × fair share) × the share of the town's outlets
they cover (both from the Day-0 data). Performance = weighted average of four 0–100 pillar scores: sales growth vs
the market, scheme qualification, focus-product share, delivery OTIF. Weights, thresholds and pillar targets are
config; the business edits them on the Cohort rules page.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from app.rules.loader import CohortRules, cohort_rules

_DEFAULT = cohort_rules()
DISPLAY_ORDER = [c.name for c in _DEFAULT.cohorts]
COLOR = {c.name: c.color for c in _DEFAULT.cohorts}
COPY = {c.name: c.definition for c in _DEFAULT.cohorts}
PILLARS = ["growth", "schemes", "focus", "delivery"]


@dataclass(frozen=True)
class Assignment:
    distributor_id: str
    cohort: str
    tag: str
    reasons: list[str]
    high_potential: bool = False
    high_performance: bool = False
    potential_l: float = 0.0
    performance_score: float = 0.0
    pillars: dict = field(default_factory=dict)        # pillar -> score 0–100


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


def pillar_scores(f: dict, rules: CohortRules) -> dict[str, float]:
    """Each pillar on 0–100, from the Day-0 features."""
    t = rules.t
    otif = f.get("otif_q2_pct")
    return {
        "growth": round(_clamp(50 + (f["yoy_growth"] - t("market_growth") / 100) * 500), 1),
        "schemes": round(100 * f["schemes_qualified_last3"] / 3, 1),
        "focus": round(_clamp(100 * f["focus_share_q2"] / (t("focus_target") / 100)), 1),
        "delivery": round(_clamp(100 * ((otif if otif is not None else t("otif_floor")) - t("otif_floor"))
                                 / (t("otif_ceiling") - t("otif_floor"))), 1),
    }


def score(pillars: dict[str, float], rules: CohortRules) -> float:
    w = {k: rules.weights[k].value for k in PILLARS}
    return round(sum(pillars[k] * w[k] for k in PILLARS) / (sum(w.values()) or 1), 1)


def raw_values(f: dict) -> dict[str, str]:
    """The measured value behind each pillar, in plain words."""
    otif = f.get("otif_q2_pct")
    return {
        "growth": f"{f['yoy_growth'] * 100:+.0f}% YoY",
        "schemes": f"{f['schemes_qualified_last3']} of 3 qualified",
        "focus": f"{f['focus_share_q2'] * 100:.0f}% of sales",
        "delivery": f"{otif:.0f}% OTIF" if otif is not None else "no deliveries",
    }


def assign(f: dict, rules: CohortRules | None = None) -> Assignment:
    """One distributor's cohort from their Day-0 features (f also carries `town`)."""
    rules = rules or _DEFAULT
    p = pillar_scores(f, rules)
    s = score(p, rules)
    pot = f["business_potential_l_month"]
    hi_pot, hi_perf = pot >= rules.t("potential_high"), s >= rules.t("performance_high")
    rule = next(c for c in rules.cohorts if (c.cell.high_potential, c.cell.high_performance) == (hi_pot, hi_perf))
    town = f.get("town", "their market")
    reasons = [f"{'High' if hi_pot else 'Low'} potential: ₹{pot:.1f} L/month in {town}",
               f"Performance {s:.0f}/100 ({'at or above' if hi_perf else 'below'} {rules.t('performance_high'):.0f})"]
    weakest = min(PILLARS, key=lambda k: p[k])
    strongest = max(PILLARS, key=lambda k: p[k])
    reasons.append(f"Strongest: {rules.weights[strongest].label.lower()}; weakest: {rules.weights[weakest].label.lower()}")
    return Assignment(f["distributor_id"], rule.name, rule.tag, reasons, hi_pot, hi_perf, pot, s, p)


def assign_all(con: sqlite3.Connection, territory_id: str | None = None,
               rules: CohortRules | None = None) -> dict[str, Assignment]:
    sql = "SELECT f.*, d.town FROM world.distributor_features f JOIN world.distributors d USING (distributor_id)"
    rows = con.execute(sql + (" WHERE d.territory_id = ?" if territory_id else ""), (territory_id,) if territory_id else ())
    return {r["distributor_id"]: assign(dict(r), rules) for r in rows}


def describe(rules: CohortRules) -> dict[str, str]:
    """The 2×2 in plain words, thresholds and weights filled in."""
    t = rules.t
    w = " · ".join(f"{rules.weights[k].label.lower()} {rules.weights[k].value:.0f}%" for k in PILLARS)
    return {
        "potential": f"High potential = ₹{t('potential_high'):g} L/month or more of Emami potential in the distributor's "
                     f"catchment (their town's modelled TAM × Emami fair share × the share of outlets they cover)",
        "performance": f"High performance = a score of {t('performance_high'):.0f}/100 or more. Score = {w}",
        "pillars": f"Growth: 50 = growing with the market (+{t('market_growth'):g}%), +10 pts ahead = 100. "
                   f"Schemes: qualified in N of the last 3. Focus: {t('focus_target'):.0f}% share = 100. "
                   f"Delivery: OTIF {t('otif_floor'):.0f}% = 0, {t('otif_ceiling'):.0f}% = 100.",
        "benchmark": rules.benchmark,
    }
