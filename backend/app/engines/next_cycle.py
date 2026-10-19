"""Next quarter: re-apply the cohort 2×2 to performance data refreshed with this cycle's October results, and take the
dealer score per cohort as the baseline to beat. Code only; the simulator's hidden traits are never read here."""
from __future__ import annotations

import sqlite3
from collections import defaultdict

from app.db import queries
from app.db.run_queries import Fact
from app.engines.cohorts import assign
from app.rules.loader import CohortRules

KEEP_SCHEMES = ("SCH-2627-SUM", "SCH-2627-MON")      # the last 3 schemes become Summer, Monsoon, Festive


def refreshed_features(con: sqlite3.Connection, fs: dict[str, Fact], sales: dict[str, dict]) -> dict[str, dict]:
    """Day-0 features moved on by one cycle: October joins the sales growth, Festive joins scheme qualification.
    Business potential (geography) and delivery OTIF stay as they were."""
    feats = {r["distributor_id"]: dict(r) for r in con.execute(
        "SELECT f.*, d.town FROM world.distributor_features f JOIN world.distributors d USING (distributor_id) "
        "WHERE d.territory_id = ?", (queries.TERRITORY_ID,))}
    kept: dict[str, int] = defaultdict(int)
    for did, sid, achieved in con.execute("SELECT distributor_id, scheme_id, achieved FROM world.scheme_history"):
        if sid in KEEP_SCHEMES:
            kept[did] += achieved
    out = {}
    for did, f in feats.items():
        g = dict(f)
        s = sales.get(did)
        qualified = bool(fs[did].enrol) and bool(s and s["hit_prediction"])
        g["schemes_qualified_last3"] = kept[did] + int(qualified)
        if s:
            ly_oct = s["baseline_l"] / (1 + f["yoy_growth"]) if f["yoy_growth"] > -1 else s["baseline_l"]
            g["yoy_growth"] = (f["secondary_fytd_l"] + s["actual_l"]) / (f["secondary_ly_same_period_l"] + ly_oct) - 1
        out[did] = g
    return out


def next_quarter(con: sqlite3.Connection, fs: dict[str, Fact], sales: dict[str, dict], rules: CohortRules) -> dict:
    feats = refreshed_features(con, fs, sales)
    names = {did: f.name for did, f in fs.items()}
    new = {did: assign(g, rules).cohort for did, g in feats.items()}
    moves: dict[tuple[str, str], list[str]] = defaultdict(list)
    for did in sorted(new):
        if new[did] != fs[did].cohort:
            moves[(fs[did].cohort, new[did])].append(names[did])

    def dealer(group: list[Fact]) -> float | None:
        vals = [f.latest["answers"]["DEALER_SCORE"] for f in group
                if f.counted and "DEALER_SCORE" in (f.latest or {}).get("answers", {})]
        return round(sum(vals) / len(vals), 1) if vals else None

    cohorts = []
    for c in rules.cohorts:
        members = [f for f in fs.values() if f.cohort == c.name]
        cohorts.append({"name": c.name, "color": c.color, "now": len(members), "next": sum(v == c.name for v in new.values()),
                        "dealer_score": dealer(members)})
    return {
        "cohorts": cohorts,
        "dealer_score": dealer(list(fs.values())),
        "moves": [{"from_cohort": f, "to_cohort": t, "count": len(n), "names": n[:3]}
                  for (f, t), n in sorted(moves.items(), key=lambda x: (-len(x[1]), x[0]))],
        "moved": sum(len(n) for n in moves.values()),
        "next_cohorts": new,
    }
