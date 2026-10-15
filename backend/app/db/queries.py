"""Read queries over the Day-0 world. Never touches the hidden traits table (only app/simulation/traits.py may)."""
from __future__ import annotations

import sqlite3
from functools import lru_cache

from app.db.conn import connect
from app.engines.cohorts import Assignment, assign_all

# The app is logged in as Rahul Sen, ASM of Kolkata North.
ASM_ID = "ASM-01"
TERRITORY_ID = "TER-01"
CURRENT_SCHEME = "SCH-2627-FES"
LAST_SCHEME = "SCH-2627-MON"
Q2_MONTHS = ("2026-07", "2026-08", "2026-09")


@lru_cache
def cohorts() -> dict[str, Assignment]:
    """Cohort agent output for every distributor (fixed at Day 0 for the whole cycle)."""
    con = connect()
    try:
        return assign_all(con)
    finally:
        con.close()


def territory(con: sqlite3.Connection) -> dict:
    t = con.execute(
        """SELECT t.territory_id, t.name, a.name AS asm_name, z.name AS zone
           FROM world.territories t JOIN world.asms a USING (asm_id) JOIN world.zones z USING (zone_id)
           WHERE t.territory_id = ?""",
        (TERRITORY_ID,),
    ).fetchone()
    agg = con.execute(
        """SELECT COUNT(*) n, SUM(f.secondary_fytd_l) fy, SUM(f.secondary_ly_same_period_l) ly,
                  SUM(f.joined_last_scheme) joined_last
           FROM world.distributor_features f JOIN world.distributors d USING (distributor_id)
           WHERE d.territory_id = ?""",
        (TERRITORY_ID,),
    ).fetchone()
    focus = con.execute(
        f"""SELECT SUM(b.focus_revenue_l) / SUM(b.secondary_value_l)
            FROM world.billing_monthly b JOIN world.distributors d USING (distributor_id)
            WHERE d.territory_id = ? AND b.month IN ({",".join("?" * len(Q2_MONTHS))})""",
        (TERRITORY_ID, *Q2_MONTHS),
    ).fetchone()[0]
    scheme = con.execute("SELECT scheme_id, name, rules_text FROM world.schemes WHERE scheme_id = ?", (CURRENT_SCHEME,)).fetchone()
    last = con.execute("SELECT name FROM world.schemes WHERE scheme_id = ?", (LAST_SCHEME,)).fetchone()
    company = con.execute("SELECT (SELECT COUNT(*) FROM world.distributors), (SELECT COUNT(*) FROM world.territories)").fetchone()
    return {
        "territory_id": t["territory_id"],
        "name": t["name"],
        "zone": t["zone"],
        "asm_name": t["asm_name"],
        "distributors": agg["n"],
        "secondary_fytd_l": round(agg["fy"], 1),
        "yoy_growth": round(agg["fy"] / agg["ly"] - 1, 4),
        "focus_share_q2": round(focus, 4),
        "joined_last_scheme": agg["joined_last"],
        "last_scheme_name": last["name"],
        "scheme_id": scheme["scheme_id"],
        "scheme_name": scheme["name"],
        "scheme_rules": scheme["rules_text"],
        "company_distributors": company[0],
        "company_territories": company[1],
    }


def distributors(con: sqlite3.Connection) -> list[dict]:
    """Every Kolkata North distributor with the Day-0 fields the UI lists."""
    rows = con.execute(
        """SELECT d.distributor_id, d.name, d.owner_name, d.town, d.classification, d.preferred_language,
                  f.secondary_fytd_l, f.yoy_growth, f.past_schemes_joined, f.joined_last_scheme,
                  t.target_l, t.predicted_sales_if_enrolled_l, t.baseline_forecast_l
           FROM world.distributors d
           JOIN world.distributor_features f USING (distributor_id)
           JOIN world.scheme_targets t ON t.distributor_id = d.distributor_id AND t.scheme_id = ?
           WHERE d.territory_id = ?
           ORDER BY d.distributor_id""",
        (CURRENT_SCHEME, TERRITORY_ID),
    ).fetchall()
    c = cohorts()
    return [{**dict(r), "cohort": c[r["distributor_id"]].cohort, "reasons": c[r["distributor_id"]].reasons} for r in rows]


def distributor(con: sqlite3.Connection, distributor_id: str) -> dict | None:
    d = con.execute(
        """SELECT d.distributor_id, d.name, d.owner_name, d.town, d.classification, d.partner_since,
                  d.preferred_language, d.reply_window, d.phone_masked, d.channel,
                  f.secondary_fytd_l, f.yoy_growth, f.qoq_growth, f.focus_share_q2, f.unique_skus_sep,
                  f.days_since_last_invoice, f.past_schemes_joined,
                  t.baseline_forecast_l, t.target_l, t.stretch_target_l, t.predicted_sales_if_enrolled_l, t.reward_text
           FROM world.distributors d
           JOIN world.distributor_features f USING (distributor_id)
           JOIN world.scheme_targets t ON t.distributor_id = d.distributor_id AND t.scheme_id = ?
           WHERE d.distributor_id = ? AND d.territory_id = ?""",
        (CURRENT_SCHEME, distributor_id, TERRITORY_ID),
    ).fetchone()
    if d is None:
        return None
    months = con.execute(
        "SELECT month, secondary_value_l FROM world.billing_monthly WHERE distributor_id = ? ORDER BY month",
        (distributor_id,),
    ).fetchall()
    history = con.execute(
        """SELECT s.name, h.enrolled, h.achieved FROM world.scheme_history h JOIN world.schemes s USING (scheme_id)
           WHERE h.distributor_id = ? ORDER BY s.start_date""",
        (distributor_id,),
    ).fetchall()
    a = cohorts()[distributor_id]
    return {
        **dict(d),
        "cohort": a.cohort,
        "cohort_tag": a.tag,
        "reasons": a.reasons,
        "billing": [{"month": m["month"], "secondary_l": m["secondary_value_l"]} for m in months],
        "history": [{"scheme": h["name"], "enrolled": bool(h["enrolled"]), "achieved": bool(h["achieved"])} for h in history],
    }
