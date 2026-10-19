"""
Independent checks on backend/data/emami_dx.sqlite (the Day-0 world).

Recomputes the headline numbers from the RAW tables (billing, scheme history) rather than trusting summary.json or
distributor_features, and re-applies the cohort rules. Run with pytest, or directly:
    python backend/tests/test_generated_data.py
"""
import hashlib
import sqlite3
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "emami_dx.sqlite"
DAY0 = date(2026, 10, 1)
KN = "TER-01"
CY = [f"2026-{m:02d}" for m in range(4, 10)]
LY = [f"2025-{m:02d}" for m in range(4, 10)]
Q1, Q2 = CY[:3], CY[3:]
PAST = ["SCH-2526-YE", "SCH-2627-SUM", "SCH-2627-MON"]
INTENTS = {"I've enrolled", "I'll enrol", "Explain again", "Explain in Bengali", "Talk to my ASM"}


def q(sql, *args):
    con = sqlite3.connect(DB)
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def kn_ids():
    return [r[0] for r in q("SELECT distributor_id FROM distributors WHERE territory_id=?", KN)]


def billing():
    out = {}
    for d, m, s, u, fr in q("SELECT distributor_id, month, secondary_value_l, unique_skus_billed, focus_revenue_l FROM billing_monthly"):
        out.setdefault(d, {})[m] = (s, u, fr)
    return out


def joins():
    out = {}
    for d, s, e in q("SELECT distributor_id, scheme_id, enrolled FROM scheme_history"):
        if s in PAST:
            out[d] = out.get(d, 0) + e
    return out


def recompute_features():
    b, j = billing(), joins()
    last_inv = dict(q("SELECT distributor_id, last_invoice_date FROM distributor_features"))
    feats = {}
    for d, months in b.items():
        sec = [months[m][0] for m in CY]
        fy, ly = sum(sec), sum(months[m][0] for m in LY)
        down = 0
        for i in range(5, 0, -1):
            if sec[i] < sec[i - 1]:
                down += 1
            else:
                break
        sku_delta = sum(months[m][1] for m in Q2) / 3 - sum(months[m][1] for m in Q1) / 3
        q2 = sum(months[m][0] for m in Q2)
        f2 = sum(months[m][2] for m in Q2) / q2 if q2 else 0
        feats[d] = dict(yoy=fy / ly - 1, down=down, sku_delta=sku_delta, f2=f2, joins=j.get(d, 0),
                        days=(DAY0 - date.fromisoformat(last_inv[d])).days)
    return feats


# Cohort model v4 (backend/app/rules/cohorts.yaml): business potential x distributor performance.
POTENTIAL_HIGH, PERFORMANCE_HIGH, MARKET_GROWTH = 4.5, 50.0, 0.03
KN_COHORTS = {"Invest / Expand": 21, "Protect": 21, "Replace / Reassess": 23, "Exit / Watchlist": 21}


def performance(yoy, qualified, focus, otif):
    c = lambda v: max(0.0, min(100.0, v))  # noqa: E731
    pillars = [c(50 + (yoy - MARKET_GROWTH) * 500), 100 * qualified / 3, c(100 * focus / 0.35), c(100 * (otif - 70) / 25)]
    return sum(pillars) / 4


def rule(potential, score):
    return {(True, True): "Invest / Expand", (False, True): "Protect", (True, False): "Replace / Reassess",
            (False, False): "Exit / Watchlist"}[(potential >= POTENTIAL_HIGH, score >= PERFORMANCE_HIGH)]


# ----------------------------------------------------------------------------- tests
def test_counts():
    assert q("SELECT COUNT(*) FROM distributors")[0][0] == 1104
    assert len(kn_ids()) == 86
    assert q("SELECT COUNT(*) FROM skus WHERE is_active=1")[0][0] == 112
    assert q("SELECT COUNT(*) FROM skus WHERE is_focus=1")[0][0] == 20
    assert DAY0.strftime("%a") == "Thu"
    tables = {r[0] for r in q("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {"zones", "territories", "asms", "distributors", "skus", "billing_monthly", "schemes",
                      "scheme_history", "scheme_targets", "distributor_features", "cohort_assignments", "sim_traits",
                      "markets"}
    assert sorted(p.name for p in (ROOT / "data" / "csv").glob("*.csv")) == [
        "distributors.csv", "market_potential.csv", "monthly_performance.csv", "schemes.csv", "sim_traits.csv"]


def test_cohort_rules_reproduce_assignments():
    """Recompute potential (markets x coverage) and performance (4 pillars from raw rows) and re-apply the 2x2."""
    feats = recompute_features()
    town_pot = dict(q("SELECT territory_id || '|' || town, SUM(emami_potential_l_month) FROM markets GROUP BY 1"))
    cover = {d: (t, town, s) for d, t, town, s in q(
        "SELECT f.distributor_id, d.territory_id, d.town, f.outlet_coverage_share FROM distributor_features f "
        "JOIN distributors d USING (distributor_id)")}
    qualified = {}
    for d, s_, a in q("SELECT distributor_id, scheme_id, achieved FROM scheme_history"):
        qualified[d] = qualified.get(d, 0) + a
    otif = {}
    for d, m, o, n in q("SELECT distributor_id, month, otif_pct, retailer_orders FROM billing_monthly"):
        if m in Q2 and o is not None:
            a, w = otif.get(d, (0.0, 0))
            otif[d] = (a + o * n, w + n)
    stored = dict(q("SELECT distributor_id, cohort FROM cohort_assignments"))
    bad = []
    for d, f in feats.items():
        t, town, share = cover[d]
        pot = town_pot[f"{t}|{town}"] * share
        a, w = otif.get(d, (0, 0))
        score = performance(f["yoy"], qualified.get(d, 0), f["f2"], a / w if w else 60.0)
        if rule(round(pot, 2), round(score, 1)) != stored[d]:
            bad.append(d)
    assert len(bad) <= 3, f"{len(bad)} cohort mismatches (rounding at the line is fine), e.g. {bad[:5]}"
    counts = {}
    for d in kn_ids():
        counts[stored[d]] = counts.get(stored[d], 0) + 1
    assert counts == KN_COHORTS


def test_market_potential_is_modelled_tam():
    rows = q("SELECT households, penetration, monthly_spend_per_hh_rs, tam_l_month, emami_fair_share, emami_potential_l_month "
             "FROM markets")
    for hh, pen, spend, tam, share, pot in rows:
        assert abs(hh * pen * spend / 1e5 - tam) / tam < 0.02 and abs(tam * share - pot) < 0.02
    kn_pot = q("SELECT SUM(business_potential_l_month), SUM(current_secondary_l_month) FROM distributor_features f "
               "JOIN distributors d USING (distributor_id) WHERE d.territory_id = ?", KN)[0]
    assert kn_pot[0] > kn_pot[1] * 1.3                                      # real headroom in the territory
    assert all(0 < v <= 100 for (v,) in q("SELECT otif_pct FROM billing_monthly WHERE otif_pct IS NOT NULL"))


def test_kn_billing_and_focus():
    b, kn = billing(), kn_ids()
    fy = sum(b[d][m][0] for d in kn for m in CY)
    ly = sum(b[d][m][0] for d in kn for m in LY)
    assert abs(fy - 1840) < 1.0, fy                              # Rs 18.4 Cr
    assert abs(100 * (fy / ly - 1) - 9.2) < 0.1
    q2 = sum(b[d][m][0] for d in kn for m in Q2)
    f2 = sum(b[d][m][2] for d in kn for m in Q2) / q2
    assert abs(100 * f2 - 31) < 0.3, f2


def test_kn_last_scheme_participation():
    kn = set(kn_ids())
    mon = [d for d, e in q("SELECT distributor_id, enrolled FROM scheme_history WHERE scheme_id='SCH-2627-MON'") if d in kn and e]
    assert len(mon) == 39                                        # 45% joined the Monsoon scheme


def test_targets_and_prediction():
    rows = q("SELECT baseline_forecast_l, target_l, stretch_target_l, expected_uplift_pct, predicted_sales_if_enrolled_l "
             "FROM scheme_targets WHERE scheme_id='SCH-2627-FES'")
    assert len(rows) == 1104
    for base, tgt, stretch, u, pred in rows:
        assert tgt >= base and stretch > tgt and 0.04 <= u <= 0.23 and pred >= base


def test_sim_traits():
    rows = q("SELECT distributor_id, response_prob, low_effort_prob, scripted_intent FROM sim_traits")
    assert len(rows) == 1104
    kn = set(kn_ids())
    exp = sum(r[1] for r in rows if r[0] in kn) / 86
    assert 0.66 <= exp <= 0.76, exp                             # ~70% expected response
    intents = {r[3] for r in rows if r[3]}
    assert intents <= INTENTS


def test_anchors():
    def one(name):
        return q("SELECT distributor_id FROM distributors WHERE name=?", name)[0][0]
    maa = one("Maa Tara Distributors")
    b = billing()[maa]
    fy = sum(b[m][0] for m in CY)
    qoq = sum(b[m][0] for m in Q2) / sum(b[m][0] for m in Q1) - 1
    assert abs(fy - 38.2) < 0.05 and round(100 * qoq) == -12 and b["2026-09"][1] == 38
    assert q("SELECT cohort FROM cohort_assignments WHERE distributor_id=?", maa)[0][0] == "Replace / Reassess"
    assert q("SELECT cohort FROM cohort_assignments WHERE distributor_id=?", one("Bose Distribution"))[0][0] == "Invest / Expand"
    assert q("SELECT progress_pct FROM scheme_history WHERE distributor_id=? AND scheme_id='SCH-2627-MON'", maa)[0][0] == 0.71
    assert q("SELECT scripted_intent, scripted_enrol_day, true_language FROM sim_traits WHERE distributor_id=?", maa)[0] == \
        ("Explain in Bengali", 9, "Bengali")
    rup = one("Ruplekha Traders")
    assert q("SELECT scripted_survey_seconds, scripted_flags FROM sim_traits WHERE distributor_id=?", rup)[0] == \
        (19, "TOO_FAST|STRAIGHT_LINE|CONTRADICTION")
    pal = one("Pal Brothers")
    assert q("SELECT classification FROM distributors WHERE distributor_id=?", pal)[0][0] == "A"
    nab = one("Nabadiganta Enterprises")
    assert q("SELECT days_since_last_invoice FROM distributor_features WHERE distributor_id=?", nab)[0][0] == 42
    ann = one("Annapurna Distributors")
    assert q("SELECT d.preferred_language, t.true_language FROM distributors d JOIN sim_traits t USING(distributor_id) "
             "WHERE distributor_id=?", ann)[0] == ("English", "Bengali")


def test_referential_integrity():
    ids = {r[0] for r in q("SELECT distributor_id FROM distributors")}
    towns = {r[0] for r in q("SELECT territory_id || '|' || town FROM markets")}
    assert all(f"{t}|{town}" in towns for t, town in q("SELECT territory_id, town FROM distributors"))
    for t in ["billing_monthly", "scheme_history", "scheme_targets", "distributor_features", "cohort_assignments", "sim_traits"]:
        orphans = [r[0] for r in q(f"SELECT DISTINCT distributor_id FROM {t}") if r[0] not in ids]
        assert not orphans, (t, orphans[:3])


def test_deterministic():
    gen = ROOT / "scripts" / "generate_data.py"
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, str(gen), "--out", tmp], check=True, capture_output=True)
        a = sqlite3.connect(DB)
        b = sqlite3.connect(Path(tmp) / "emami_dx.sqlite")
        for (t,) in a.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            ha = hashlib.md5(repr(a.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall()).encode()).hexdigest()
            hb = hashlib.md5(repr(b.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall()).encode()).hexdigest()
            assert ha == hb, t


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {name}: {e}")
    sys.exit(1 if fails else 0)
