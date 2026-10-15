"""Cohort agent: applies rules/cohorts.yaml to distributor_features (as of Day 0) and explains each assignment.

`when` expressions are `feature op number`, joined by AND / OR (OR of ANDs), or `otherwise`. First match wins.
Reasons are one plain phrase per clause that held, worded as the generator words them.
"""
from __future__ import annotations

import operator
import re
import sqlite3
from dataclasses import dataclass

from app.rules.loader import cohort_rules

OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq}
CLAUSE = re.compile(r"^\s*([a-z_0-9]+)\s*(>=|<=|==|>|<)\s*(-?[\d.]+)\s*$")

# Display order on screen (rule order is different) + the plain copy and colour key from the renders.
DISPLAY_ORDER = ["Champions", "Growth builders", "Scheme-hesitant", "At-risk", "Dormant"]
COPY = {
    "Champions": "Growing 10%+ and strong on focus SKUs",
    "Growth builders": "Healthy and joins schemes regularly",
    "Scheme-hesitant": "Healthy, but joined 0–1 of the last 3 schemes",
    "At-risk": "Billing down 2+ months or range shrinking",
    "Dormant": "No invoice in the last 30 days",
}
COLOR = {"Champions": "blue", "Growth builders": "cyan", "Scheme-hesitant": "orange", "At-risk": "red", "Dormant": "grey"}


@dataclass(frozen=True)
class Assignment:
    distributor_id: str
    cohort: str
    tag: str
    reasons: list[str]


def _clauses(expr: str) -> list[list[tuple[str, str, float]]]:
    groups = []
    for part in re.split(r"\s+OR\s+", expr.strip()):
        group = []
        for c in re.split(r"\s+AND\s+", part):
            m = CLAUSE.match(c)
            if not m:
                raise ValueError(f"Unsupported cohort rule clause: {c!r}")
            group.append((m[1], m[2], float(m[3])))
        groups.append(group)
    return groups


def _reason(feature: str, f: dict, cohort: str) -> str:
    v = f[feature]
    if feature == "days_since_last_invoice":
        return f"No invoice for {v} days"
    if feature == "consecutive_down_months":
        return f"Billing down {v} months in a row"
    if feature == "sku_range_delta_qoq":
        return f"SKU range shrank by {abs(v):.0f} per month vs last quarter"
    if feature == "yoy_growth":
        return f"Billing {v * 100:+.0f}% YoY" + (" (healthy)" if cohort == "Scheme-hesitant" else "")
    if feature == "focus_share_q2":
        return f"Focus-SKU share {v * 100:.0f}%"
    if feature == "past_schemes_joined":
        return f"Joined {v} of the last 3 schemes"
    return feature.replace("_", " ")


def assign(f: dict) -> tuple[str, str, list[str]]:
    """(cohort, tag, reasons) for one distributor's Day-0 features."""
    for rule in cohort_rules().cohorts:
        if rule.when.strip() == "otherwise":
            return rule.name, rule.tag, [_reason("yoy_growth", f, rule.name), _reason("past_schemes_joined", f, rule.name)]
        held: list[str] = []
        for group in _clauses(rule.when):
            if all(OPS[op](f[feat], val) for feat, op, val in group):
                held += [feat for feat, _, _ in group if feat not in held]
        if held:
            return rule.name, rule.tag, [_reason(feat, f, rule.name) for feat in held]
    raise ValueError("cohorts.yaml has no 'otherwise' rule")


def assign_all(con: sqlite3.Connection, territory_id: str | None = None) -> dict[str, Assignment]:
    sql = "SELECT f.* FROM world.distributor_features f JOIN world.distributors d USING (distributor_id)"
    rows = con.execute(sql + (" WHERE d.territory_id = ?" if territory_id else ""), (territory_id,) if territory_id else ())
    out = {}
    for r in rows:
        cohort, tag, reasons = assign(dict(r))
        out[r["distributor_id"]] = Assignment(r["distributor_id"], cohort, tag, reasons)
    return out
