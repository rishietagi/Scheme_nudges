#!/usr/bin/env python3
"""
Synthetic data generator — Emami Distributor Experience Platform (POC), closed-loop edition.

Deterministic (SEED=42). Standard library only. Writes the WORLD AS IT IS ON DAY 0 (Thu 1 Oct 2026), the day the
Festive Scheme goes live and the nudge + survey is sent:
  backend/data/emami_dx.sqlite     all tables (tidy, for the app)
  backend/data/csv/                FIVE combined CSVs for people:
      distributors.csv             one row per distributor: hierarchy, profile, market, Day-0 features,
                                   performance pillars + score, business potential, cohort, Festive target
      monthly_performance.csv      distributor x month: primary, secondary, lines, focus sales, retailer
                                   orders, OTIF, fill rate, delivery days
      schemes.csv                  scheme details x each distributor's participation and achievement
      market_potential.csv         town x category: households, outlets, modelled TAM, Emami fair share
      sim_traits.csv               hidden simulator truth (never shown in the app)
  backend/data/summary.json        headline metrics the UI and tests rely on

Cohorts (rules v4.0, mirrored from backend/app/rules/cohorts.yaml) are a 2x2 of BUSINESS POTENTIAL in the
distributor's geography (modelled TAM x Emami fair share x the distributor's outlet coverage) vs DISTRIBUTOR
PERFORMANCE (sales growth vs market, scheme qualification, focus-product share, delivery OTIF).
The five generation "archetypes" below (Champions ... Dormant) only shape the synthetic behaviour; they are not cohorts.

It does NOT generate survey answers, CTAs, enrolments or Day-30 results: the loop SIMULATOR produces those at runtime
from the hidden `sim_traits` table (see docs/SIMULATION_SPEC.md).

Everything here is FICTIONAL: distributors, people, phone numbers, SKUs and numbers.
Kolkata North (ASM Rahul Sen, 86 distributors) is calibrated to docs/PROJECT_CONTEXT.md; the other 13 territories
are realistic but not calibrated.

Run:  python backend/scripts/generate_data.py            (from repo root)
      python backend/scripts/generate_data.py --out somewhere/
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

SEED = 42
DAY0 = date(2026, 10, 1)                 # Thursday · Festive Scheme live, nudge + survey sent
DEMO_TODAY = DAY0                         # kept for backwards compatibility
DATA_AS_OF = date(2026, 9, 30)           # monthly billing is complete through Sep 2026
RULE_VERSION = "v4.0"
KN = "TER-01"                             # Kolkata North

# --------------------------------------------------------------------------- calendar
def _months(y: int, m: int, n: int) -> list[str]:
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out

MONTHS = _months(2025, 4, 18)            # Apr 2025 .. Sep 2026
LY_H1, LY_H2, CY_H1 = MONTHS[0:6], MONTHS[6:12], MONTHS[12:18]
Q1, Q2 = CY_H1[:3], CY_H1[3:]            # Apr-Jun 2026, Jul-Sep 2026
LAST12 = MONTHS[6:18]                    # Oct 2025 .. Sep 2026
SEASON = {4: 1.05, 5: 1.12, 6: 1.05, 7: 0.92, 8: 0.95, 9: 1.02,
          10: 1.10, 11: 1.00, 12: 0.98, 1: 0.95, 2: 0.93, 3: 1.00}

def mnum(ym: str) -> int:
    return int(ym[5:])

COHORTS = ["Champions", "Growth builders", "Scheme-hesitant", "At-risk", "Dormant"]   # generation archetypes only

# --------------------------------------------------------------------------- cohort model v4 (mirror of cohorts.yaml)
V4_COHORTS = ["Invest / Expand", "Protect", "Replace / Reassess", "Exit / Watchlist"]
V4 = dict(potential_high=4.5,            # Rs lakh / month of Emami potential in the distributor's catchment
          performance_high=50.0,         # composite performance score 0-100
          weights=dict(growth=25, schemes=25, focus=25, delivery=25),
          market_growth=0.03,            # NielsenIQ India FMCG value growth, Q1 2026
          focus_target=0.35, otif_floor=70.0, otif_ceiling=95.0)


def pillar_scores(yoy: float, achieved: int, focus: float, otif: float, p: dict = V4) -> dict:
    """0-100 per pillar. 50 on growth = growing with the market; 100 = 10 pts ahead or more."""
    clamp = lambda v: max(0.0, min(100.0, v))  # noqa: E731
    return dict(
        growth=round(clamp(50 + (yoy - p["market_growth"]) * 500), 1),
        schemes=round(100 * achieved / 3, 1),
        focus=round(clamp(100 * focus / p["focus_target"]), 1),
        delivery=round(clamp(100 * (otif - p["otif_floor"]) / (p["otif_ceiling"] - p["otif_floor"])), 1),
    )


def v4_cohort(potential_l: float, score: float, p: dict = V4) -> str:
    hi_pot, hi_perf = potential_l >= p["potential_high"], score >= p["performance_high"]
    return {(True, True): "Invest / Expand", (False, True): "Protect",
            (True, False): "Replace / Reassess", (False, False): "Exit / Watchlist"}[(hi_pot, hi_perf)]

# --------------------------------------------------------------------------- market potential (modelled TAM)
# Synthetic, modelled numbers — not census data. Population per town; Kolkata North sized by hand so the story holds.
KN_TOWN_POP = {
    "Barasat": 290_000, "Dum Dum": 230_000, "Shyambazar": 190_000, "Baranagar": 250_000, "Sodepur": 170_000,
    "Madhyamgram": 200_000, "Panihati": 120_000, "Belgharia": 105_000, "Khardah": 95_000, "Titagarh": 115_000,
    "Barrackpore": 150_000, "Lake Town": 120_000, "Kestopur": 85_000, "Baguiati": 95_000, "Birati": 65_000,
    "Agarpara": 80_000, "Bagbazar": 55_000, "Cossipore": 70_000, "Sinthee": 50_000, "Ultadanga": 75_000,
    "Dunlop": 55_000, "Naihati": 210_000, "Shyamnagar": 90_000,
}
HH_SIZE = 4.3
# category: (penetration, monthly spend per buying household Rs, Emami fair share)
CATEGORIES = {
    "Hair oils & hair care": (0.86, 160, 0.33),
    "Pain balms & rubs": (0.55, 40, 0.40),
    "Antiseptic & winter care": (0.60, 45, 0.30),
    "Skin care & men's grooming": (0.48, 140, 0.15),
    "Ayurvedic & OTC health": (0.40, 70, 0.12),
}
ZONE_SPEND = {"Kolkata": 1.00, "South Bengal": 0.78, "North Bengal": 0.72}
OUTLETS_PER_10K = 46                     # kirana / chemist / cosmetic outlets per 10,000 people
NETWORK_COVERAGE = 0.90                  # share of a town's outlets reached by Emami's distributors

# --------------------------------------------------------------------------- geography
TERRITORIES = [
    # id, name, zone, asm name, distributor count, towns
    ("TER-01", "Kolkata North", "Kolkata", "Rahul Sen", 86,
     ["Barasat", "Dum Dum", "Shyambazar", "Belgharia", "Baranagar", "Sodepur", "Madhyamgram", "Khardah",
      "Titagarh", "Birati", "Agarpara", "Barrackpore", "Bagbazar", "Cossipore", "Sinthee", "Ultadanga",
      "Lake Town", "Kestopur", "Baguiati", "Dunlop", "Panihati", "Naihati", "Shyamnagar"]),
    ("TER-02", "Kolkata South", "Kolkata", "Ananya Mukherjee", 84,
     ["Behala", "Tollygunge", "Jadavpur", "Garia", "Kasba", "Ballygunge", "Bhowanipore", "Thakurpukur", "Joka"]),
    ("TER-03", "Kolkata Central", "Kolkata", "Sourav Banerjee", 78,
     ["Burrabazar", "Sealdah", "Esplanade", "Park Circus", "Entally", "Bowbazar", "Beliaghata", "Salt Lake"]),
    ("TER-04", "Howrah", "South Bengal", "Debashis Roy", 82,
     ["Howrah Maidan", "Shibpur", "Bally", "Liluah", "Santragachi", "Uluberia", "Domjur", "Andul"]),
    ("TER-05", "Hooghly", "South Bengal", "Moumita Chatterjee", 80,
     ["Chinsurah", "Serampore", "Chandannagar", "Arambagh", "Tarakeswar", "Uttarpara", "Bandel", "Singur"]),
    ("TER-06", "South 24 Parganas", "South Bengal", "Arijit Saha", 76,
     ["Baruipur", "Diamond Harbour", "Sonarpur", "Canning", "Budge Budge", "Kakdwip", "Joynagar"]),
    ("TER-07", "Nadia", "South Bengal", "Priyanka Dutta", 74,
     ["Krishnanagar", "Ranaghat", "Kalyani", "Nabadwip", "Santipur", "Chakdaha", "Tehatta"]),
    ("TER-08", "Purba Bardhaman", "South Bengal", "Sandip Mondal", 79,
     ["Bardhaman", "Kalna", "Katwa", "Memari", "Guskara", "Bhatar", "Jamalpur"]),
    ("TER-09", "Paschim Bardhaman", "South Bengal", "Rupam Ghosh", 72,
     ["Asansol", "Durgapur", "Raniganj", "Kulti", "Jamuria", "Andal", "Panagarh"]),
    ("TER-10", "Paschim Medinipur", "South Bengal", "Tanmoy Pal", 77,
     ["Midnapore", "Kharagpur", "Ghatal", "Daspur", "Debra", "Salboni", "Keshiary"]),
    ("TER-11", "Murshidabad", "North Bengal", "Sudipta Biswas", 75,
     ["Berhampore", "Jangipur", "Lalbagh", "Kandi", "Domkal", "Beldanga", "Jiaganj"]),
    ("TER-12", "Malda", "North Bengal", "Kaushik Sarkar", 70,
     ["English Bazar", "Old Malda", "Chanchal", "Gazole", "Harishchandrapur", "Manikchak"]),
    ("TER-13", "Siliguri", "North Bengal", "Nandini Bose", 81,
     ["Siliguri", "Matigara", "Bagdogra", "Naxalbari", "Phansidewa", "Kurseong", "Darjeeling"]),
    ("TER-14", "Jalpaiguri & Cooch Behar", "North Bengal", "Abhijit Barman", 90,
     ["Jalpaiguri", "Cooch Behar", "Dhupguri", "Mainaguri", "Alipurduar", "Dinhata", "Mathabhanga"]),
]
assert sum(t[4] for t in TERRITORIES) == 1104

FIRST_M = ["Biswajit", "Subhas", "Amit", "Pradip", "Tapan", "Sanjay", "Ashok", "Partha", "Gautam", "Sukanta",
           "Ranjit", "Dipankar", "Shyamal", "Tarun", "Prasenjit", "Kalyan", "Manas", "Uttam", "Swapan", "Bikash",
           "Arup", "Niladri", "Sudip", "Anirban", "Debabrata", "Raju", "Haradhan", "Nimai", "Gopal", "Sankar"]
FIRST_F = ["Mita", "Rina", "Sima", "Tanushree", "Moumita", "Sharmila", "Sutapa", "Rupa", "Kakali", "Jhuma"]
SURNAMES = ["Das", "Ghosh", "Bose", "Sen", "Saha", "Pal", "Dutta", "Mondal", "Roy", "Sarkar", "Chatterjee",
            "Banerjee", "Mukherjee", "Biswas", "Debnath", "Kundu", "Nandi", "Halder", "Mitra", "Majumdar",
            "Chakraborty", "Bhattacharya", "Ganguly", "Dey", "Paul", "Sinha", "Basak", "Shaw", "Jana", "Maity",
            "Pramanik", "Bag", "Mallick", "Karmakar", "Adhikari", "Barman"]
DEITIES = ["Maa Durga", "Jagannath", "Loknath", "Tarakeswar", "Ganesh", "Shree Ram", "Radha Krishna",
           "Bhagabati", "Shiv Shakti", "Joy Guru", "Ramakrishna", "Saraswati", "Sri Sai", "Bishwakarma",
           "Maa Sarada", "Bhabani", "Kamakhya", "Gouranga"]
WORDS = ["Uttaran", "Prabhat", "Sonar Bangla", "Nabajiban", "Purbasha", "Ananda", "Sagar", "Prantik", "Aalo",
         "Milan", "Sristi", "Disha", "Pragati", "Sathi", "Bandhan", "Ujjwal", "Barnali", "Agami", "Dishari",
         "Anjali", "Mohona", "Swarnali", "Tirtha", "Bhorer Aalo"]
SUFFIX = ["Distributors", "Traders", "Enterprises", "Agencies", "Distribution", "Marketing", "Trading Co.",
          "Associates", "Stores"]

# --------------------------------------------------------------------------- anchors (Kolkata North)
# cohort, owner, town, FYTD secondary (Rs lakh), QoQ, YoY, Sep unique SKUs, focus share Q2, extra
ANCHORS = {
    "Maa Tara Distributors": dict(cohort="Scheme-hesitant", owner="Biswajit Das", town="Barasat",
        monthly=[6.9, 6.8, 6.6, 5.8, 6.3, 5.8], yoy=0.03, skus=38, focus=0.18, lang="Bengali",
        window="10:00–12:00", since=2017, mood="Frustrated"),
    "Sarkar & Sons": dict(cohort="Scheme-hesitant", owner="Subhas Sarkar", town="Belgharia", fytd=29.6,
        qoq=-0.04, yoy=0.02, skus=44, focus=0.22, lang="Bengali", window="18:00–20:00", since=2012,
        mood="Confused"),
    "Ma Kali Enterprises": dict(cohort="Scheme-hesitant", owner="Gopal Kundu", town="Madhyamgram", fytd=33.1,
        qoq=-0.02, yoy=0.04, skus=41, focus=0.25, lang="Bengali", window="11:00–13:00", since=2015,
        mood="Confused"),
    "Debnath Agencies": dict(cohort="Scheme-hesitant", owner="Uttam Debnath", town="Khardah", fytd=24.8,
        qoq=0.01, yoy=0.01, skus=36, focus=0.19, lang="Bengali", window="17:00–19:00", since=2019,
        mood="Neutral"),
    "Pal Brothers": dict(cohort="Scheme-hesitant", owner="Tapan Pal", town="Agarpara", fytd=41.5,
        qoq=0.03, yoy=0.06, skus=52, focus=0.27, lang="Bengali", window="10:00–12:00", since=2010,
        mood="Confused"),
    "Ruplekha Traders": dict(cohort="Scheme-hesitant", owner="Rina Saha", town="Titagarh", fytd=21.9,
        qoq=-0.06, yoy=0.005, skus=33, focus=0.16, lang="Bengali", window="12:00–14:00", since=2020,
        mood="Frustrated"),
    "Annapurna Distributors": dict(cohort="Scheme-hesitant", owner="Sankar Mitra", town="Birati", fytd=27.4,
        qoq=0.02, yoy=0.03, skus=39, focus=0.24, lang="English", window="09:00–11:00", since=2016,
        mood="Positive"),
    "Shree Durga Agencies": dict(cohort="Growth builders", owner="Amit Ghosh", town="Shyambazar", fytd=52.7,
        qoq=0.14, yoy=0.08, skus=61, focus=0.31, lang="English", window="09:00–11:00", since=2011),
    "Bose Distribution": dict(cohort="Champions", owner="Partha Bose", town="Sodepur", fytd=58.4,
        qoq=0.22, yoy=0.24, skus=72, focus=0.46, lang="English", window="10:00–12:00", since=2008),
    "Ganguly Traders": dict(cohort="At-risk", owner="Prasenjit Ganguly", town="Dum Dum", fytd=26.2,
        qoq=-0.21, yoy=-0.12, skus=34, sku_start=52, focus=0.21, lang="Bengali", window="16:00–18:00",
        since=2013, falling=True),
    "Nabadiganta Enterprises": dict(cohort="Dormant", owner="Shyamal Halder", town="Baranagar", fytd=9.8,
        qoq=-0.38, yoy=-0.35, skus=19, focus=0.17, lang="Bengali", window="11:00–13:00", since=2018,
        last_invoice=date(2026, 8, 20)),
}
KN_COHORT_COUNTS = {"Champions": 14, "Growth builders": 22, "Scheme-hesitant": 19, "At-risk": 18, "Dormant": 13}

# KPI targets for Kolkata North
KN_FYTD_TOTAL_L = 1840.0                 # Rs 18.4 Cr secondary, Apr-Sep 2026
KN_YOY = 0.092
KN_FOCUS_Q2, KN_FOCUS_Q1 = 0.31, 0.29

# --------------------------------------------------------------------------- SKUs
SKU_BASE = [
    ("Cooling Oil", "Hair & Scalp", ["50 ml", "100 ml", "200 ml", "300 ml", "500 ml"]),
    ("Ayurvedic Hair Oil", "Hair & Scalp", ["100 ml", "200 ml", "500 ml"]),
    ("Almond Hair Oil", "Hair & Scalp", ["100 ml", "200 ml", "300 ml"]),
    ("Anti-dandruff Shampoo", "Hair & Scalp", ["sachet 8 ml", "180 ml", "340 ml"]),
    ("Pain Balm", "Pain Relief", ["4 ml", "10 ml", "25 ml", "45 ml"]),
    ("Pain Relief Spray", "Pain Relief", ["35 g", "80 g"]),
    ("Pain Relief Gel", "Pain Relief", ["30 g", "60 g"]),
    ("Joint Care Oil", "Pain Relief", ["50 ml", "100 ml"]),
    ("Antiseptic Cream", "Skin Care", ["9 g", "20 g", "40 g", "80 g", "120 g"]),
    ("Cold Cream", "Skin Care", ["30 ml", "100 ml", "200 ml"]),
    ("Body Lotion", "Skin Care", ["100 ml", "200 ml", "400 ml"]),
    ("Aloe Vera Gel", "Skin Care", ["100 g", "250 g"]),
    ("Men's Face Wash", "Men's Grooming", ["50 g", "100 g"]),
    ("Men's Moisturiser", "Men's Grooming", ["50 g", "100 g"]),
    ("Men's Deo Talc", "Men's Grooming", ["100 g", "200 g"]),
    ("Cooling Talc", "Talc & Powder", ["50 g", "100 g", "200 g", "400 g"]),
    ("Prickly Heat Powder", "Talc & Powder", ["50 g", "150 g", "300 g"]),
    ("Chyawanprash", "Healthcare", ["500 g", "1 kg"]),
    ("Digestive Tablets", "Healthcare", ["30 tabs", "60 tabs"]),
    ("Herbal Cough Syrup", "Healthcare", ["100 ml", "200 ml"]),
    ("Herbal Tonic", "Healthcare", ["200 ml", "450 ml"]),
    ("Neem Soap", "Personal Wash", ["75 g", "125 g", "4 x 75 g"]),
    ("Sandal Soap", "Personal Wash", ["75 g", "125 g", "4 x 75 g"]),
    ("Hand Wash", "Personal Wash", ["200 ml", "750 ml refill"]),
    ("Body Wash", "Personal Wash", ["250 ml"]),
    ("Lip Balm", "Skin Care", ["4.5 g"]),
    ("Fairness-free Day Cream", "Skin Care", ["50 g"]),
    ("Kids Cold Rub", "Healthcare", ["10 g", "25 g"]),
    ("Hair Serum", "Hair & Scalp", ["50 ml", "100 ml"]),
    ("Herbal Kajal", "Skin Care", ["0.35 g"]),
]
FOCUS_NAMES = {
    "Cooling Oil 200 ml", "Pain Balm 10 ml", "Pain Relief Spray 35 g", "Pain Relief Spray 80 g",
    "Pain Relief Gel 30 g", "Men's Face Wash 50 g", "Men's Face Wash 100 g", "Men's Moisturiser 50 g",
    "Body Lotion 200 ml", "Body Lotion 400 ml", "Aloe Vera Gel 100 g", "Anti-dandruff Shampoo 180 ml",
    "Antiseptic Cream 40 g", "Chyawanprash 1 kg", "Herbal Cough Syrup 100 ml", "Hair Serum 50 ml",
    "Body Wash 250 ml", "Hand Wash 750 ml refill", "Joint Care Oil 100 ml", "Kids Cold Rub 25 g",
}


# --------------------------------------------------------------------------- schemes & loop
PAST_SCHEMES = ["SCH-2526-YE", "SCH-2627-SUM", "SCH-2627-MON"]   # "last 3 schemes" for the Scheme-hesitant rule
CURRENT_SCHEME = "SCH-2627-FES"
KN_MONSOON_JOINED = {"Champions": 13, "Growth builders": 15, "Scheme-hesitant": 4, "At-risk": 7, "Dormant": 0}  # 39 = 45%

# Scripted behaviour for the anchor distributors so the demo story is always the same.
# name: (Day-0 quick reply, hours to reply, survey seconds, sanity flags, enrol day, note, true language override)
ANCHOR_SCRIPTS = {
    "Maa Tara Distributors": ("Explain in Bengali", 3.0, 140, None, 9,
                              "Enrols the day after the Bengali explainer CTA (Day 8).", "Bengali"),
    "Sarkar & Sons": ("Explain again", 26.0, 165, None, 10,
                      "Replies late; comment asks for a short Bengali voice note.", "Bengali"),
    "Ma Kali Enterprises": ("Explain again", 6.0, 120, None, 12, None, None),
    "Debnath Agencies": ("I'll enrol", 4.0, 95, None, 5, "Enrols on his own before any CTA.", None),
    "Pal Brothers": ("Talk to my ASM", 1.5, 110, None, None,
                     "Wants better margins, not the scheme: individual attention; does not enrol.", None),
    "Ruplekha Traders": ("I've enrolled", 0.2, 19, "TOO_FAST|STRAIGHT_LINE|CONTRADICTION", 15,
                         "Survey in 19 s, all 5s, says enrolled but is not: red-flagged; ASM call gets her enrolled.", None),
    "Annapurna Distributors": ("Explain in Bengali", 7.0, 130, None, 9,
                               "On file as English but asks for Bengali: persona switches her to Bengali.", "Bengali"),
    "Shree Durga Agencies": ("I've enrolled", 0.7, 85, None, 0,
                             "Enrols within an hour of the nudge and beats his prediction.", None),
    "Bose Distribution": ("I've enrolled", 0.4, 70, None, 0, None, None),
    "Ganguly Traders": (None, None, None, None, None,
                        "Never replies: At-risk, billing down 4 months: individual attention (ASM visit).", None),
    "Nabadiganta Enterprises": (None, None, None, None, None, "Dormant; ignores the nudge and the re-nudge.", None),
}

# =========================================================================== helpers
def r2(x: float) -> float:
    return round(x, 2)

def split(total: float, weights: list[float]) -> list[float]:
    s = sum(weights)
    return [total * w / s for w in weights]

def consecutive_down(series: list[float]) -> int:
    n = 0
    for i in range(len(series) - 1, 0, -1):
        if series[i] < series[i - 1]:
            n += 1
        else:
            break
    return n

def bisect(f, lo: float, hi: float, target: float, it: int = 80) -> float:
    """f increasing in x. Returns x with f(x) ~= target."""
    for _ in range(it):
        mid = (lo + hi) / 2
        if f(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

def weighted_sample(rng: random.Random, items: list, weights: list[float], k: int) -> list:
    items, weights, out = list(items), list(weights), []
    for _ in range(min(k, len(items))):
        tot = sum(weights)
        x, acc = rng.random() * tot, 0.0
        for i, w in enumerate(weights):
            acc += w
            if acc >= x:
                out.append(items.pop(i))
                weights.pop(i)
                break
    return out

def fmt_inr_l(x_l: float) -> str:
    return f"₹{x_l / 100:.1f} Cr" if x_l >= 100 else f"₹{x_l:.1f} L"


# =========================================================================== generator
class Gen:
    def __init__(self, seed: int = SEED):
        self.rng = random.Random(seed)
        self.used_names: set[str] = set(ANCHORS)
        self.t: dict[str, list[dict]] = {k: [] for k in [
            "zones", "territories", "asms", "distributors", "skus", "billing_monthly", "schemes",
            "scheme_history", "scheme_targets", "distributor_features", "cohort_assignments", "sim_traits",
            "markets"]}
        self.d: dict[str, dict] = {}       # distributor id -> working record
        # New data (markets, delivery) uses its own stream so the original tables stay byte-identical.
        self.mrng = random.Random(f"{seed}:markets")

    # ------------------------------------------------------------------ names
    def person(self) -> str:
        first = self.rng.choice(FIRST_F if self.rng.random() < 0.12 else FIRST_M)
        return f"{first} {self.rng.choice(SURNAMES)}"

    def business(self, town: str = "") -> str:
        r = self.rng
        for _ in range(400):
            p = r.random()
            if p < 0.18:
                n = f"{r.choice(DEITIES)} {r.choice(SUFFIX)}"
            elif p < 0.28:
                n = f"{r.choice(SURNAMES)} & Sons"
            elif p < 0.34:
                n = f"{r.choice(SURNAMES)} Brothers"
            elif p < 0.56:
                n = f"{r.choice(SURNAMES)} {r.choice(SUFFIX)}"
            elif p < 0.70:
                n = f"{r.choice(WORDS)} {r.choice(SUFFIX)}"
            elif p < 0.84 and town:
                n = f"{town} {r.choice(SUFFIX)}"
            else:
                n = f"{r.choice(FIRST_M)} {r.choice(SUFFIX)}"
            if n not in self.used_names:
                self.used_names.add(n)
                return n
        raise RuntimeError("ran out of names")

    # ------------------------------------------------------------------ masters
    def masters(self):
        zones = sorted({t[2] for t in TERRITORIES})
        for i, z in enumerate(zones, 1):
            self.t["zones"].append(dict(zone_id=f"ZON-{i:02d}", name=z, state="West Bengal"))
        zid = {z["name"]: z["zone_id"] for z in self.t["zones"]}
        for i, (tid, name, zone, asm, n, towns) in enumerate(TERRITORIES, 1):
            aid = f"ASM-{i:02d}"
            self.t["territories"].append(dict(territory_id=tid, name=name, zone_id=zid[zone], asm_id=aid,
                                              distributor_count=n))
            self.t["asms"].append(dict(asm_id=aid, name=asm, territory_id=tid,
                                       email=f"{asm.split()[0].lower()}.{asm.split()[-1].lower()}@example.com"))
        n = 0
        for base, cat, packs in SKU_BASE:
            for p in packs:
                n += 1
                name = f"{base} {p}"
                self.t["skus"].append(dict(sku_id=f"SKU-{n:03d}", name=name, category=cat, pack=p,
                                           is_active=1, is_focus=int(name in FOCUS_NAMES),
                                           case_size=self.rng.choice([12, 24, 36, 48, 72, 96, 144]),
                                           ptd_price_per_case=r2(self.rng.uniform(450, 4200))))
        # pad / trim to exactly 112 active SKUs, plus 8 discontinued
        while len(self.t["skus"]) < 112:
            n += 1
            b = self.rng.choice(SKU_BASE)
            self.t["skus"].append(dict(sku_id=f"SKU-{n:03d}", name=f"{b[0]} value pack {n}", category=b[1],
                                       pack="value pack", is_active=1, is_focus=0, case_size=24,
                                       ptd_price_per_case=r2(self.rng.uniform(450, 2500))))
        for s in self.t["skus"][112:]:
            s["is_active"] = 0
        for k in range(8):
            n += 1
            b = SKU_BASE[k]
            self.t["skus"].append(dict(sku_id=f"SKU-{n:03d}", name=f"{b[0]} old pack {k + 1}", category=b[1],
                                       pack="discontinued", is_active=0, is_focus=0, case_size=24,
                                       ptd_price_per_case=r2(self.rng.uniform(450, 2500))))
        assert sum(s["is_active"] for s in self.t["skus"]) == 112
        assert sum(s["is_focus"] for s in self.t["skus"]) == 20

    # ------------------------------------------------------------------ distributors
    def distributors(self):
        r = self.rng
        did = 0
        for tid, tname, zone, asm, count, towns in TERRITORIES:
            if tid == KN:
                plan = []
                remaining = dict(KN_COHORT_COUNTS)
                for name, a in ANCHORS.items():
                    plan.append((a["cohort"], name))
                    remaining[a["cohort"]] -= 1
                for c, k in remaining.items():
                    plan += [(c, None)] * k
            else:
                mix = [0.16, 0.26, 0.21, 0.21, 0.16]
                plan = [(r.choices(COHORTS, weights=mix)[0], None) for _ in range(count)]
            r.shuffle(plan)
            # make anchors appear with stable, low ids in Kolkata North for readability
            if tid == KN:
                plan.sort(key=lambda x: (x[1] is None, list(ANCHORS).index(x[1]) if x[1] else 0))
            for cohort, anchor in plan:
                did += 1
                a = ANCHORS.get(anchor, {}) if anchor else {}
                town = a.get("town") or r.choice(towns)
                rec = dict(
                    distributor_id=f"DST-{did:04d}",
                    name=anchor or self.business(town),
                    owner_name=a.get("owner") or self.person(),
                    town=town,
                    territory_id=tid,
                    asm_id=f"ASM-{int(tid[-2:]):02d}",
                    partner_since=a.get("since") or r.randint(2004, 2023),
                    preferred_language=a.get("lang") or (r.choices(["Bengali", "English", "Hindi"],
                                                                     weights=[0.62, 0.30, 0.08])[0]),
                    reply_window=a.get("window") or r.choice(["09:00–11:00", "10:00–12:00", "11:00–13:00",
                                                               "17:00–19:00", "18:00–20:00"]),
                    phone_masked=f"+91 9{r.randint(0, 9)}xxx xx{r.randint(100, 999)}",
                    channel=r.choices(["Urban GT", "Semi-urban GT", "Rural GT"], weights=[0.5, 0.3, 0.2])[0]
                    if tid != KN else r.choices(["Urban GT", "Semi-urban GT"], weights=[0.7, 0.3])[0],
                )
                self.t["distributors"].append(rec)
                self.d[rec["distributor_id"]] = dict(rec=rec, cohort=cohort, anchor=anchor, a=a)

    # ------------------------------------------------------------------ billing
    def _shape_quarter(self, total: float, months: list[str], mode: str) -> list[float]:
        """mode: 'free' (no strictly falling 3-run), 'falling' (strictly falling), 'any'."""
        r = self.rng
        for _ in range(500):
            w = [SEASON[mnum(m)] * r.uniform(0.9, 1.1) for m in months]
            if mode == "falling":
                w = sorted(w, reverse=True)
                w = [w[0] * 1.08, w[1], w[2] * 0.92]
                return split(total, w)
            vals = split(total, w)
            if mode == "free" and vals[2] < vals[1] < vals[0]:
                continue
            return vals
        return split(total, [1, 1, 1.02])

    def billing(self):
        r = self.rng
        for did, x in self.d.items():
            c, a = x["cohort"], x["a"]
            kn = x["rec"]["territory_id"] == KN
            # --- size, growth, momentum
            size = {"Champions": 9.0, "Growth builders": 6.5, "Scheme-hesitant": 5.0, "At-risk": 4.6,
                    "Dormant": 2.2}[c] * r.lognormvariate(0, 0.35)          # avg monthly secondary, lakh
            if not kn:
                size *= 0.62          # keeps other territories in the same range as Kolkata North
            if kn:   # Kolkata North: a mix that lands near +9% YoY before calibration
                size = {"Champions": 12.0, "Growth builders": 7.0, "Scheme-hesitant": 5.0, "At-risk": 4.0,
                        "Dormant": 1.8}[c] * r.lognormvariate(0, 0.3)
                yoy_draw = {"Champions": r.uniform(0.15, 0.35), "Growth builders": r.uniform(0.02, 0.095),
                            "Scheme-hesitant": r.uniform(0.005, 0.09), "At-risk": r.uniform(-0.14, 0.05),
                            "Dormant": r.uniform(-0.42, -0.15)}[c]
            else:
                yoy_draw = {"Champions": r.uniform(0.12, 0.30), "Growth builders": r.uniform(0.01, 0.10),
                            "Scheme-hesitant": r.uniform(0.004, 0.10), "At-risk": r.uniform(-0.22, 0.04),
                            "Dormant": r.uniform(-0.55, -0.20)}[c]
            yoy = a.get("yoy", yoy_draw)
            qoq = a.get("qoq", {"Champions": r.uniform(0.03, 0.22), "Growth builders": r.uniform(-0.03, 0.12),
                                "Scheme-hesitant": r.uniform(-0.12, 0.06), "At-risk": r.uniform(-0.30, -0.08),
                                "Dormant": r.uniform(-0.65, -0.30)}[c])
            at_risk_mode = None
            if c == "At-risk":
                at_risk_mode = "falling" if (a.get("falling") or r.random() < 0.7) else "shrinking"
            # --- current FY H1
            if "monthly" in a:
                cy = list(a["monthly"])
            else:
                fytd = a.get("fytd", size * 6)
                q1 = fytd / (2 + qoq)
                q2 = fytd - q1
                q1v = self._shape_quarter(q1, Q1, "any")
                q2v = self._shape_quarter(q2, Q2, "falling" if at_risk_mode == "falling" else "free")
                if at_risk_mode == "falling" and q1v[2] <= q2v[0]:
                    q1v[2] = q2v[0] * 1.05
                cy = q1v + q2v
            # dormant: last invoice before 13 Sep, Sep billing small or zero
            last_inv = None
            if c == "Dormant":
                last_inv = a.get("last_invoice") or (DAY0 - timedelta(days=r.randint(33, 75)))
                if last_inv < date(2026, 9, 1):
                    moved = cy[5]
                    cy[5] = 0.0
                    if last_inv < date(2026, 8, 1):
                        moved += cy[4]
                        cy[4] = 0.0
                    cy[3] += moved * 0.3          # keep some of it, the rest is simply lost
                else:
                    cy[5] = cy[5] * 0.25
            else:
                last_inv = DAY0 - timedelta(days=r.randint(1, 10))
            x.update(size=size, yoy=yoy, ar_mode=at_risk_mode, last_invoice=last_inv, cy=cy)

        if True:   # calibrate Kolkata North billing
            self._calibrate_kn_billing()

        for did, x in self.d.items():
            c, a = x["cohort"], x["a"]
            cy, yoy = x["cy"], x["yoy"]
            fy = sum(cy)
            ly_noise = [SEASON[mnum(m)] * r.uniform(0.92, 1.08) for m in LY_H1]
            ly_h1 = split(fy / (1 + yoy), ly_noise)
            level = (fy / 6) / (1 + yoy / 2)
            if c == "Dormant":
                level = (fy / 6) * 1.3
            ly_h2 = [level * SEASON[mnum(m)] * r.uniform(0.9, 1.1) for m in LY_H2]
            sec = dict(zip(MONTHS, ly_h1 + ly_h2 + cy))
            x["sec"] = sec
            # --- SKU breadth
            base_sku = a.get("skus") or {"Champions": r.randint(58, 80), "Growth builders": r.randint(42, 66),
                                         "Scheme-hesitant": r.randint(30, 55), "At-risk": r.randint(32, 58),
                                         "Dormant": r.randint(14, 36)}[c]
            sku = {}
            for i, m in enumerate(MONTHS):
                sku[m] = base_sku + r.randint(-3, 3)
            if c == "At-risk" and (x["ar_mode"] == "shrinking" or a.get("sku_start")):
                start = a.get("sku_start", base_sku + r.randint(9, 16))
                end = a.get("skus", base_sku)
                for i, m in enumerate(CY_H1):
                    sku[m] = round(start + (end - start) * i / 5)
                for m in LY_H1 + LY_H2:
                    sku[m] = start + r.randint(-2, 2)
            else:
                q1avg = sum(sku[m] for m in Q1) / 3
                if c == "Growth builders":
                    for m in Q2:
                        sku[m] = max(sku[m], round(q1avg) + r.randint(1, 4))
                else:
                    for m in Q2:
                        sku[m] = max(sku[m], round(q1avg) - 3)
            if "skus" in a:
                sku["2026-09"] = a["skus"]
            for m in MONTHS:
                if sec[m] <= 0:
                    sku[m] = 0
            x["sku"] = sku
            x["base_sku"] = base_sku

        # --- focus share
        for did, x in self.d.items():
            c, a = x["cohort"], x["a"]
            f2 = a.get("focus") or {"Champions": r.uniform(0.37, 0.48), "Growth builders": r.uniform(0.25, 0.34),
                                    "Scheme-hesitant": r.uniform(0.16, 0.29), "At-risk": r.uniform(0.17, 0.30),
                                    "Dormant": r.uniform(0.14, 0.26)}[c]
            x["f2"] = f2
            x["f1"] = max(0.08, f2 - r.uniform(0.0, 0.04))
        self._calibrate_kn_focus()

        for did, x in self.d.items():
            r_ = self.rng
            for m in MONTHS:
                s = x["sec"][m]
                share = x["f2"] if m in Q2 else x["f1"] if m in Q1 else max(0.06, x["f1"] - r_.uniform(0.01, 0.05))
                share_m = max(0.0, share + r_.uniform(-0.012, 0.012)) if m not in Q2 + Q1 else share
                prim = s * r_.uniform(0.95, 1.05) * (1.08 if m.endswith("-09") else 1.0)
                uniq = x["sku"][m]
                focus_cnt = 0 if s <= 0 else max(1, min(20, round(20 * share_m * r_.uniform(1.3, 1.8))))
                self.t["billing_monthly"].append(dict(
                    distributor_id=did, month=m, primary_value_l=r2(prim), secondary_value_l=r2(s),
                    unique_skus_billed=uniq, focus_skus_billed=focus_cnt,
                    focus_revenue_l=r2(s * share_m), focus_revenue_share=round(share_m, 4) if s > 0 else 0,
                    invoice_count=0 if s <= 0 else max(1, round(s * r_.uniform(1.6, 2.4)))))

    def _kn_ids(self) -> list[str]:
        return [d for d, x in self.d.items() if x["rec"]["territory_id"] == KN]

    def _calibrate_kn_billing(self):
        ids = self._kn_ids()
        anchor_total = sum(sum(self.d[i]["cy"]) for i in ids if self.d[i]["anchor"])
        free = [i for i in ids if not self.d[i]["anchor"]]
        free_total = sum(sum(self.d[i]["cy"]) for i in free)
        k = (KN_FYTD_TOTAL_L - anchor_total) / free_total
        for i in free:
            self.d[i]["cy"] = [v * k for v in self.d[i]["cy"]]
        ly_target = KN_FYTD_TOTAL_L / (1 + KN_YOY)
        bounds = {"Champions": (0.11, 0.55), "Growth builders": (0.004, 0.096), "Scheme-hesitant": (0.004, 0.096),
                  "At-risk": (-0.35, 0.06), "Dormant": (-0.70, -0.10)}
        # how much of the calibration shift each cohort absorbs (keeps values away from the cohort bounds)
        weight = {"Champions": 1.0, "Growth builders": 0.15, "Scheme-hesitant": 0.15, "At-risk": 0.3, "Dormant": 0.4}
        base = {i: self.d[i]["yoy"] for i in free}

        def g_of(i, delta):
            c = self.d[i]["cohort"]
            lo, hi = bounds[c]
            return min(hi, max(lo, base[i] + delta * weight[c]))

        def growth(delta):   # overall yoy as function of delta (increasing)
            ly = sum(sum(self.d[i]["cy"]) / (1 + self.d[i]["yoy"]) for i in ids if self.d[i]["anchor"])
            ly += sum(sum(self.d[i]["cy"]) / (1 + g_of(i, delta)) for i in free)
            return KN_FYTD_TOTAL_L / ly - 1

        delta = bisect(growth, -0.6, 0.6, KN_YOY)
        for i in free:
            self.d[i]["yoy"] = g_of(i, delta)
        self.kn_growth_shift = delta
        _ = ly_target

    def _calibrate_kn_focus(self):
        ids = self._kn_ids()
        free = [i for i in ids if not self.d[i]["anchor"]]
        q2w = {i: sum(self.d[i]["cy"][3:]) for i in ids}
        q1w = {i: sum(self.d[i]["cy"][:3]) for i in ids}
        clamp = {"Champions": (0.36, 0.55), "Growth builders": (0.20, 0.34), "Scheme-hesitant": (0.12, 0.30),
                 "At-risk": (0.12, 0.33), "Dormant": (0.10, 0.28)}
        for key, w, target in (("f2", q2w, KN_FOCUS_Q2), ("f1", q1w, KN_FOCUS_Q1)):
            base = {i: self.d[i][key] for i in free}

            def val(delta, key=key, w=w, base=base):
                tot = sum(w.values())
                s = sum(w[i] * self.d[i][key] for i in ids if self.d[i]["anchor"])
                for i in free:
                    lo, hi = clamp[self.d[i]["cohort"]]
                    s += w[i] * min(hi, max(lo, base[i] + delta))
                return s / tot

            delta = bisect(val, -0.2, 0.2, target)
            for i in free:
                lo, hi = clamp[self.d[i]["cohort"]]
                self.d[i][key] = min(hi, max(lo, base[i] + delta))
        for i in ids:   # Q1 share must not exceed Q2 by much for Champions (keeps story simple)
            self.d[i]["f1"] = min(self.d[i]["f1"], self.d[i]["f2"] + 0.01)

    # ------------------------------------------------------------------ schemes & participation
    # ------------------------------------------------------------------ schemes: history + the live one
    def schemes(self):
        rules = {
            "Slab": "Personal purchase target for the period. Hit the target: +3% margin on focus SKUs. "
                    "Beat it by 25%: +4% margin and a ₹10,000 bonus.",
            "Loyalty": "Earn points on every focus-SKU purchase; tier bonus paid at quarter end if 80% of the "
                       "quarterly target is met.",
            "Target": "Single-month target on total purchases; 2% back on achievement.",
        }
        S = [
            ("SCH-2526-YE", "Year-end Push · Mar 2026", "Target", "2026-03-01", "2026-03-31", "Closed"),
            ("SCH-2627-SUM", "Summer Cool Scheme · Apr–Jun 2026", "Slab", "2026-04-01", "2026-06-30", "Closed"),
            ("SCH-2627-MON", "Monsoon Loyalty · Jul–Sep 2026", "Loyalty", "2026-07-01", "2026-09-30", "Closed"),
            ("SCH-2627-FES", "Festive Scheme · Oct 2026", "Slab", "2026-10-01", "2026-10-31",
             "Live · communicated to all distributors on 1 Oct"),
        ]
        for sid, name, typ, start, end, status in S:
            self.t["schemes"].append(dict(scheme_id=sid, name=name, type=typ, start_date=start, end_date=end,
                                          rules_text=rules[typ], status=status,
                                          is_current=int(sid == CURRENT_SCHEME)))

    def past_schemes(self):
        """Enrolment in the last 3 schemes (Emami field 6). Drives the Scheme-hesitant cohort."""
        r = self.rng
        kn = self._kn_ids()
        mon = set()
        for c, k in KN_MONSOON_JOINED.items():
            pool = [i for i in kn if self.d[i]["cohort"] == c]
            must = [i for i in pool if self.d[i]["anchor"] in ("Maa Tara Distributors", "Bose Distribution",
                                                                "Shree Durga Agencies")]
            never = ("Sarkar & Sons", "Pal Brothers", "Ruplekha Traders", "Ganguly Traders")
            rest = [i for i in pool if i not in must and self.d[i]["anchor"] not in never]
            r.shuffle(rest)
            mon |= set((must + rest)[:k])
        ach_p = {"Champions": 0.85, "Growth builders": 0.65, "Scheme-hesitant": 0.5, "At-risk": 0.35, "Dormant": 0.2}
        for i, x in self.d.items():
            c, kn_i = x["cohort"], x["rec"]["territory_id"] == KN
            if kn_i:
                m = i in mon
                if c == "Champions":
                    joined = {"SCH-2526-YE": True, "SCH-2627-SUM": True, "SCH-2627-MON": m}
                elif c == "Growth builders":
                    joined = {"SCH-2526-YE": (r.random() < 0.8) or not m, "SCH-2627-SUM": True, "SCH-2627-MON": m}
                elif c == "Scheme-hesitant":
                    one = None if m else (r.choice(["SCH-2526-YE", "SCH-2627-SUM", None]))
                    joined = {"SCH-2526-YE": one == "SCH-2526-YE", "SCH-2627-SUM": one == "SCH-2627-SUM",
                              "SCH-2627-MON": m}
                elif c == "At-risk":
                    joined = {"SCH-2526-YE": r.random() < 0.6, "SCH-2627-SUM": r.random() < 0.5, "SCH-2627-MON": m}
                else:
                    joined = {"SCH-2526-YE": r.random() < 0.5, "SCH-2627-SUM": r.random() < 0.3, "SCH-2627-MON": False}
            else:
                if c == "Champions":
                    joined = {s: r.random() < 0.92 for s in PAST_SCHEMES}
                    if sum(joined.values()) < 2:
                        joined["SCH-2627-SUM"] = True
                elif c == "Growth builders":
                    joined = {s: r.random() < 0.8 for s in PAST_SCHEMES}
                    while sum(joined.values()) < 2:
                        joined[r.choice(PAST_SCHEMES)] = True
                elif c == "Scheme-hesitant":
                    pick = r.choice(PAST_SCHEMES + [None, None])
                    joined = {s: s == pick for s in PAST_SCHEMES}
                elif c == "At-risk":
                    joined = {s: r.random() < 0.5 for s in PAST_SCHEMES}
                else:
                    joined = {"SCH-2526-YE": r.random() < 0.45, "SCH-2627-SUM": r.random() < 0.3, "SCH-2627-MON": False}
            for sid in PAST_SCHEMES:
                enrolled = bool(joined[sid])
                prog = 0.0
                if enrolled:
                    prog = r.uniform(1.0, 1.25) if r.random() < ach_p[c] else r.uniform(0.45, 0.98)
                if x["anchor"] == "Maa Tara Distributors" and sid == "SCH-2627-MON":
                    prog = 0.71
                self.t["scheme_history"].append(dict(
                    distributor_id=i, scheme_id=sid, enrolled=int(enrolled),
                    progress_pct=round(prog, 3) if enrolled else None,
                    achieved=int(enrolled and prog >= 1.0)))
            x["past_joins"] = sum(1 for s in PAST_SCHEMES if joined[s])
            x["monsoon_joined"] = int(bool(joined["SCH-2627-MON"]))

    # ------------------------------------------------------------------ current scheme: targets + prediction
    def targets(self):
        """Festive Scheme Oct 2026 targets and the sales PREDICTION the Day-30 evaluation compares against."""
        r = self.rng
        upl = {"Champions": (0.08, 0.12), "Growth builders": (0.12, 0.18), "Scheme-hesitant": (0.15, 0.22),
               "At-risk": (0.08, 0.14), "Dormant": (0.05, 0.10)}
        for i, x in self.d.items():
            sec = x["sec"]
            if x["cohort"] == "Dormant":
                active = [sec[m] for m in CY_H1 if sec[m] > 0][-3:] or [0.5]
                baseline = sum(active) / len(active) * 0.5
            else:
                baseline = sum(sec[m] for m in Q2) / 3 * 1.08          # October festive seasonality
            baseline = max(0.3, baseline)
            target = max(0.5, round(baseline * r.uniform(1.12, 1.22), 1))
            u = r.uniform(*upl[x["cohort"]])
            self.t["scheme_targets"].append(dict(
                distributor_id=i, scheme_id=CURRENT_SCHEME, baseline_forecast_l=r2(baseline), target_l=target,
                stretch_target_l=round(target * 1.25, 1), expected_uplift_pct=round(u, 3),
                predicted_sales_if_enrolled_l=r2(baseline * (1 + u)),
                reward_text="Hit target: +3% margin on focus SKUs · Beat it by 25%: +4% margin and ₹10,000 bonus"))

    # ------------------------------------------------------------------ hidden behaviour traits (simulator only)
    def traits(self):
        r = self.rng
        resp = {"Champions": 0.90, "Growth builders": 0.85, "Scheme-hesitant": 0.75, "At-risk": 0.60, "Dormant": 0.35}
        hours = {"Champions": 2, "Growth builders": 3, "Scheme-hesitant": 5, "At-risk": 8, "Dormant": 20}
        under = {"Champions": 0.8, "Growth builders": 0.7, "Scheme-hesitant": 0.4, "At-risk": 0.5, "Dormant": 0.4}
        asm = {"Champions": 0.05, "Growth builders": 0.08, "Scheme-hesitant": 0.12, "At-risk": 0.30, "Dormant": 0.20}
        e0 = {"Champions": 0.75, "Growth builders": 0.55, "Scheme-hesitant": 0.15, "At-risk": 0.25, "Dormant": 0.05}
        e_cta = {"Champions": 0.90, "Growth builders": 0.80, "Scheme-hesitant": 0.65, "At-risk": 0.45, "Dormant": 0.20}
        sales = {"Champions": 0.85, "Growth builders": 0.75, "Scheme-hesitant": 0.70, "At-risk": 0.55, "Dormant": 0.40}
        for i, x in self.d.items():
            c, rec = x["cohort"], x["rec"]
            on_file = rec["preferred_language"]
            if on_file == "Bengali":
                lang = "Bengali" if r.random() < 0.95 else "English"
            elif on_file == "English":
                lang = "Bengali" if r.random() < 0.25 else "English"
            else:
                lang = "Hindi" if r.random() < 0.9 else "Bengali"
            start = int(rec["reply_window"][:2])
            window = "Morning" if start < 12 else ("Afternoon" if start < 16 else "Evening")
            row = dict(
                distributor_id=i, true_language=lang, active_window=window,
                response_prob=round(min(0.98, max(0.05, resp[c] + r.uniform(-0.1, 0.1))), 3),
                median_response_hours=round(hours[c] * r.lognormvariate(0, 0.4), 1),
                understanding=round(min(1, max(0, under[c] + r.uniform(-0.2, 0.2))), 2),
                wants_asm_prob=round(min(0.9, max(0, asm[c] + r.uniform(-0.05, 0.05))), 3),
                enrol_prob_day0=round(min(0.95, max(0, e0[c] + r.uniform(-0.1, 0.1))), 3),
                enrol_prob_after_matching_cta=round(min(0.98, max(0, e_cta[c] + r.uniform(-0.1, 0.1))), 3),
                low_effort_prob=round(0.15 if c == "Dormant" else 0.08, 3),
                hit_prediction_prob=round(min(0.95, max(0.1, sales[c] + r.uniform(-0.1, 0.1))), 3),
                scripted_intent=None, scripted_response_hours=None, scripted_survey_seconds=None,
                scripted_flags=None, scripted_enrol_day=None, scripted_note=None)
            s = ANCHOR_SCRIPTS.get(x["anchor"])
            if s:
                row.update(scripted_intent=s[0], scripted_response_hours=s[1], scripted_survey_seconds=s[2],
                           scripted_flags=s[3], scripted_enrol_day=s[4], scripted_note=s[5])
                if s[6]:
                    row["true_language"] = s[6]
            self.t["sim_traits"].append(row)

    # ------------------------------------------------------------------ features & cohorts (as of Day 0)
    def features(self):
        stored: dict[str, dict] = {}
        for row in self.t["billing_monthly"]:
            stored.setdefault(row["distributor_id"], {})[row["month"]] = row
        for i, x in self.d.items():
            sec = {m: stored[i][m]["secondary_value_l"] for m in MONTHS}      # exactly what is stored
            fy = sum(sec[m] for m in CY_H1)
            ly = sum(sec[m] for m in LY_H1)
            q1, q2 = sum(sec[m] for m in Q1), sum(sec[m] for m in Q2)
            down = consecutive_down([sec[m] for m in CY_H1])
            sku_delta = sum(x["sku"][m] for m in Q2) / 3 - sum(x["sku"][m] for m in Q1) / 3
            fq2 = sum(stored[i][m]["focus_revenue_l"] for m in Q2) / q2 if q2 else 0
            days = (DAY0 - x["last_invoice"]).days
            f = dict(distributor_id=i, as_of=DAY0.isoformat(),
                     secondary_fytd_l=r2(fy), secondary_ly_same_period_l=r2(ly),
                     yoy_growth=round(fy / ly - 1, 4) if ly else None,
                     q1_secondary_l=r2(q1), q2_secondary_l=r2(q2), qoq_growth=round(q2 / q1 - 1, 4) if q1 else None,
                     consecutive_down_months=down, unique_skus_sep=x["sku"]["2026-09"],
                     sku_range_delta_qoq=round(sku_delta, 2), focus_share_q2=round(fq2, 4),
                     last_invoice_date=x["last_invoice"].isoformat(), days_since_last_invoice=days,
                     past_schemes_joined=x["past_joins"], joined_last_scheme=x["monsoon_joined"])
            x["f"] = f
            self.t["distributor_features"].append(f)

    @staticmethod
    def apply_rules(f: dict) -> tuple[str, list[str]]:
        """Mirror of backend/app/rules/cohorts.yaml (first match wins)."""
        if f["days_since_last_invoice"] > 30:
            return "Dormant", [f"No invoice for {f['days_since_last_invoice']} days"]
        reasons = []
        if f["consecutive_down_months"] >= 2:
            reasons.append(f"Billing down {f['consecutive_down_months']} months in a row")
        if f["sku_range_delta_qoq"] <= -5:
            reasons.append(f"SKU range shrank by {abs(f['sku_range_delta_qoq']):.0f} per month vs last quarter")
        if reasons:
            return "At-risk", reasons
        if f["yoy_growth"] > 0.10 and f["focus_share_q2"] > 0.35:
            return "Champions", [f"Billing +{f['yoy_growth'] * 100:.0f}% YoY",
                                 f"Focus-SKU share {f['focus_share_q2'] * 100:.0f}%"]
        if f["yoy_growth"] >= 0 and f["past_schemes_joined"] <= 1:
            return "Scheme-hesitant", [f"Billing +{f['yoy_growth'] * 100:.0f}% YoY (healthy)",
                                       f"Joined {f['past_schemes_joined']} of the last 3 schemes"]
        return "Growth builders", [f"Billing {f['yoy_growth'] * 100:+.0f}% YoY",
                                   f"Joined {f['past_schemes_joined']} of the last 3 schemes"]

    def cohorts(self):
        mism = []
        for i, x in self.d.items():
            c, reasons = self.apply_rules(x["f"])
            if c != x["cohort"]:
                mism.append((i, x["rec"]["territory_id"], x["cohort"], c))
                x["cohort"] = c                       # rules are the source of truth outside KN
        kn_mism = [m for m in mism if m[1] == KN]
        assert not kn_mism, f"Kolkata North cohort mismatches: {kn_mism[:5]}"
        for tid, *_ in TERRITORIES:
            ids = sorted([i for i, x in self.d.items() if x["rec"]["territory_id"] == tid],
                         key=lambda i: -self.d[i]["f"]["secondary_fytd_l"])
            for k, i in enumerate(ids):
                q = k / len(ids)
                self.d[i]["rec"]["classification"] = "A" if q < 0.2 else ("B" if q < 0.6 else "C")
        return mism

    # ------------------------------------------------------------------ markets + catchment potential
    def markets(self):
        """Modelled TAM per town x category, then each distributor's share of its town's outlets."""
        r = self.mrng
        zone_of = {t[0]: t[2] for t in TERRITORIES}
        for tid, tname, zone, asm, n, towns in TERRITORIES:
            for k, town in enumerate(towns):
                if tid == KN:
                    pop = KN_TOWN_POP[town]
                else:
                    big = k == 0 or r.random() < 0.25
                    pop = int(round(r.uniform(180_000, 520_000) if big else r.uniform(35_000, 160_000), -3))
                hh = int(pop / HH_SIZE)
                outlets = int(pop / 10_000 * OUTLETS_PER_10K)
                spend = ZONE_SPEND[zone] * (1.0 if tid == KN else r.uniform(0.9, 1.1))
                for cat, (pen, rs, share) in CATEGORIES.items():
                    tam_l = hh * pen * rs * spend / 1e5                 # Rs lakh per month
                    self.t["markets"].append(dict(
                        territory_id=tid, town=town, zone=zone, population=pop, households=hh, retail_outlets=outlets,
                        category=cat, penetration=pen, monthly_spend_per_hh_rs=round(rs * spend),
                        tam_l_month=r2(tam_l), emami_fair_share=share, emami_potential_l_month=r2(tam_l * share),
                        source="Synthetic, modelled: households x penetration x spend; fair share = Emami target share"))
        town_pot = {}
        for m in self.t["markets"]:
            key = (m["territory_id"], m["town"])
            town_pot[key] = town_pot.get(key, 0) + m["emami_potential_l_month"]
        town_outlets = {(m["territory_id"], m["town"]): m["retail_outlets"] for m in self.t["markets"]}
        # Distributors in a town split its outlets: bigger, older distributors cover more, but not proportionally.
        by_town: dict[tuple, list[str]] = {}
        for i, x in self.d.items():
            by_town.setdefault((x["rec"]["territory_id"], x["rec"]["town"]), []).append(i)
        for key, ids in by_town.items():
            w = {i: max(0.2, self.d[i]["f"]["secondary_fytd_l"]) ** 0.45 * r.uniform(0.7, 1.3) for i in ids}
            tot = sum(w.values())
            for i in ids:
                share = NETWORK_COVERAGE * w[i] / tot
                pot = town_pot[key] * share
                cur = self.d[i]["f"]["q2_secondary_l"] / 3
                self.d[i]["f"].update(
                    town_emami_potential_l_month=r2(town_pot[key]),
                    outlets_covered=int(round(town_outlets[key] * share)),
                    outlet_coverage_share=round(share, 4),
                    business_potential_l_month=r2(pot),
                    current_secondary_l_month=r2(cur),
                    headroom_l_month=r2(pot - cur))
        for k in set(by_town) - set(town_pot):
            pass

    # ------------------------------------------------------------------ delivery to retailers (per month)
    def delivery(self):
        r = self.mrng
        base = {"Champions": 92.0, "Growth builders": 88.5, "Scheme-hesitant": 82.0, "At-risk": 77.0, "Dormant": 71.0}
        anchor_otif = {"Maa Tara Distributors": 79.0, "Bose Distribution": 94.0, "Shree Durga Agencies": 90.5,
                       "Ganguly Traders": 74.0, "Pal Brothers": 86.0, "Nabadiganta Enterprises": 68.0}
        rows = {}
        for row in self.t["billing_monthly"]:
            rows.setdefault(row["distributor_id"], []).append(row)
        for i, x in self.d.items():
            mean = anchor_otif.get(x["anchor"], base[x["cohort"]] + r.uniform(-4, 4))
            for row in rows[i]:
                s = row["secondary_value_l"]
                if s <= 0:
                    row.update(retailer_orders=0, otif_pct=None, fill_rate_pct=None, avg_delivery_days=None)
                    continue
                otif = max(55.0, min(99.0, mean + r.gauss(0, 2.2)))
                row.update(retailer_orders=max(1, round(s * 1e5 / r.uniform(3800, 5200))),
                           otif_pct=round(otif, 1),
                           fill_rate_pct=round(min(99.5, otif + r.uniform(2, 6)), 1),
                           avg_delivery_days=round(1.0 + (96 - otif) / 11 + r.uniform(-0.2, 0.2), 1))

    # ------------------------------------------------------------------ performance pillars + v4 cohort
    def performance(self):
        rows = {}
        for row in self.t["billing_monthly"]:
            rows.setdefault(row["distributor_id"], {})[row["month"]] = row
        achieved = {}
        for h in self.t["scheme_history"]:
            achieved[h["distributor_id"]] = achieved.get(h["distributor_id"], 0) + h["achieved"]
        self.t["cohort_assignments"] = []
        for i, x in self.d.items():
            f = x["f"]
            q2 = [rows[i][m] for m in Q2]
            vol = sum(rr["retailer_orders"] for rr in q2)
            otif = (sum(rr["otif_pct"] * rr["retailer_orders"] for rr in q2 if rr["otif_pct"] is not None) / vol) if vol else V4["otif_floor"] - 10
            f.update(schemes_qualified_last3=achieved.get(i, 0), otif_q2_pct=round(otif, 1))
            sc = pillar_scores(f["yoy_growth"], f["schemes_qualified_last3"], f["focus_share_q2"], f["otif_q2_pct"])
            w = V4["weights"]
            score = round(sum(sc[k] * w[k] for k in w) / sum(w.values()), 1)
            f.update(growth_score=sc["growth"], schemes_score=sc["schemes"], focus_score=sc["focus"],
                     delivery_score=sc["delivery"], performance_score=score)
            c = v4_cohort(f["business_potential_l_month"], score)
            x["v4"] = c
            reasons = [f"{'High' if f['business_potential_l_month'] >= V4['potential_high'] else 'Low'} potential: "
                       f"Rs {f['business_potential_l_month']:.1f} L/month in {x['rec']['town']}",
                       f"Performance {score:.0f}/100 (growth {sc['growth']:.0f} · schemes {sc['schemes']:.0f} · "
                       f"focus {sc['focus']:.0f} · delivery {sc['delivery']:.0f})"]
            self.t["cohort_assignments"].append(dict(distributor_id=i, as_of=DAY0.isoformat(), rule_version=RULE_VERSION,
                                                     cohort=c, reasons=" · ".join(reasons)))

    # ------------------------------------------------------------------ summary
    def summary(self, mism) -> dict:
        kn = self._kn_ids()
        F = {i: self.d[i]["f"] for i in kn}
        fy = sum(F[i]["secondary_fytd_l"] for i in kn)
        ly = sum(F[i]["secondary_ly_same_period_l"] for i in kn)
        q2 = sum(F[i]["q2_secondary_l"] for i in kn)
        f2 = sum(F[i]["q2_secondary_l"] * F[i]["focus_share_q2"] for i in kn) / q2
        cohorts = {c: sum(1 for i in kn if self.d[i]["cohort"] == c) for c in COHORTS}
        mon = {c: sum(1 for i in kn if self.d[i]["cohort"] == c and self.d[i]["monsoon_joined"]) for c in COHORTS}
        T = {t["distributor_id"]: t for t in self.t["scheme_targets"]}
        S = {s["distributor_id"]: s for s in self.t["sim_traits"]}
        anchors = {}
        for i in kn:
            a = self.d[i]["anchor"]
            if a:
                anchors[a] = dict(distributor_id=i, cohort=self.d[i]["v4"], archetype=self.d[i]["cohort"],
                                  business_potential_l_month=F[i]["business_potential_l_month"],
                                  performance_score=F[i]["performance_score"], classification=self.d[i]["rec"]["classification"],
                                  fytd_l=F[i]["secondary_fytd_l"], qoq=F[i]["qoq_growth"], yoy=F[i]["yoy_growth"],
                                  unique_skus_sep=F[i]["unique_skus_sep"], focus_share_q2=F[i]["focus_share_q2"],
                                  past_schemes_joined=F[i]["past_schemes_joined"],
                                  festive_target_l=T[i]["target_l"], festive_predicted_if_enrolled_l=T[i]["predicted_sales_if_enrolled_l"],
                                  on_file_language=self.d[i]["rec"]["preferred_language"],
                                  script=dict(intent=S[i]["scripted_intent"], response_hours=S[i]["scripted_response_hours"],
                                              survey_seconds=S[i]["scripted_survey_seconds"], flags=S[i]["scripted_flags"],
                                              enrol_day=S[i]["scripted_enrol_day"], true_language=S[i]["true_language"]))
        exp_resp = sum(S[i]["response_prob"] for i in kn)
        return {
            "generated_with_seed": SEED, "day0": DAY0.isoformat(), "day7": (DAY0 + timedelta(days=7)).isoformat(),
            "day30": (DAY0 + timedelta(days=30)).isoformat(), "data_as_of": DATA_AS_OF.isoformat(),
            "current_scheme": CURRENT_SCHEME,
            "company": {"distributors": len(self.d), "territories": len(TERRITORIES), "active_skus": 112, "focus_skus": 20,
                        "archetypes": {c: sum(1 for x in self.d.values() if x["cohort"] == c) for c in COHORTS},
                        "cohorts": {c: sum(1 for x in self.d.values() if x["v4"] == c) for c in V4_COHORTS},
                        "rule_mismatches_outside_kn_fixed_by_rules": len(mism)},
            "kolkata_north": {
                "asm": "Rahul Sen", "distributors": len(kn), "archetypes": cohorts,
                "cohorts": {c: sum(1 for i in kn if self.d[i]["v4"] == c) for c in V4_COHORTS},
                "business_potential_l_month": round(sum(F[i]["business_potential_l_month"] for i in kn), 1),
                "current_secondary_l_month": round(sum(F[i]["current_secondary_l_month"] for i in kn), 1),
                "avg_performance_score": round(sum(F[i]["performance_score"] for i in kn) / len(kn), 1),
                "secondary_fytd_l": round(fy, 1), "secondary_fytd_display": fmt_inr_l(fy),
                "yoy_growth_pct": round(100 * (fy / ly - 1), 1), "focus_share_q2_pct": round(100 * f2, 1),
                "joined_last_scheme_monsoon": sum(mon.values()),
                "joined_last_scheme_pct": round(100 * sum(mon.values()) / len(kn), 1),
                "joined_last_scheme_pct_by_cohort": {c: round(100 * mon[c] / cohorts[c]) for c in COHORTS},
                "festive_baseline_forecast_l": round(sum(T[i]["baseline_forecast_l"] for i in kn), 1),
                "festive_predicted_if_all_enrol_l": round(sum(T[i]["predicted_sales_if_enrolled_l"] for i in kn), 1),
                "sim_expected_response_rate_pct": round(100 * exp_resp / len(kn), 1),
                "sim_true_language_bengali": sum(1 for i in kn if S[i]["true_language"] == "Bengali"),
                "on_file_language_bengali": sum(1 for i in kn if self.d[i]["rec"]["preferred_language"] == "Bengali"),
                "anchors": anchors,
            },
        }

    # ------------------------------------------------------------------ run
    def run(self):
        self.masters()
        self.distributors()
        self.billing()
        self.schemes()
        self.past_schemes()
        self.features()
        mism = self.cohorts()
        self.targets()
        self.traits()
        self.delivery()
        self.markets()
        self.performance()
        return self.summary(mism)



# =========================================================================== output
def write(gen: Gen, summary: dict, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    (out / "csv").mkdir(exist_ok=True)
    db = out / "emami_dx.sqlite"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    for name, rows in gen.t.items():
        if not rows:
            continue
        cols = list(rows[0].keys())
        for row in rows:
            for k in row:
                if k not in cols:
                    cols.append(k)

        def typ(c):
            vals = [r_.get(c) for r_ in rows if r_.get(c) is not None]
            if vals and all(isinstance(v, int) for v in vals):
                return "INTEGER"
            if vals and all(isinstance(v, (int, float)) for v in vals):
                return "REAL"
            return "TEXT"

        con.execute(f'CREATE TABLE "{name}" ({", ".join(f"{c} {typ(c)}" for c in cols)})')
        con.executemany(f'INSERT INTO "{name}" VALUES ({",".join("?" * len(cols))})',
                        [[row.get(c) for c in cols] for row in rows])
    con.executescript("""
        CREATE INDEX ix_bill ON billing_monthly(distributor_id, month);
        CREATE INDEX ix_dist_ter ON distributors(territory_id);
        CREATE INDEX ix_hist ON scheme_history(distributor_id);
        CREATE INDEX ix_traits ON sim_traits(distributor_id);
    """)
    con.commit()
    con.close()
    write_csvs(gen, out / "csv")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def _csv(path: Path, rows: list[dict]):
    cols: list[str] = []
    for row in rows:
        for k in row:
            if k not in cols:
                cols.append(k)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def write_csvs(gen: Gen, d: Path):
    """Five combined CSVs (people read these; the app reads the SQLite)."""
    for old in d.glob("*.csv"):
        old.unlink()
    T = gen.t
    zone = {z["zone_id"]: z["name"] for z in T["zones"]}
    ter = {t["territory_id"]: t for t in T["territories"]}
    asm = {a["asm_id"]: a["name"] for a in T["asms"]}
    feat = {f["distributor_id"]: f for f in T["distributor_features"]}
    tgt = {t["distributor_id"]: t for t in T["scheme_targets"]}
    coh = {c["distributor_id"]: c for c in T["cohort_assignments"]}
    rows = []
    for x in T["distributors"]:
        i = x["distributor_id"]
        t = ter[x["territory_id"]]
        f = {k: v for k, v in feat[i].items() if k not in ("distributor_id", "as_of")}
        g = {k: v for k, v in tgt[i].items() if k not in ("distributor_id",)}
        rows.append({"distributor_id": i, "zone": zone[t["zone_id"]], "territory_id": x["territory_id"],
                     "territory": t["name"], "asm": asm[x["asm_id"]],
                     **{k: v for k, v in x.items() if k not in ("distributor_id", "territory_id", "asm_id")},
                     **f, "cohort": coh[i]["cohort"], "cohort_reasons": coh[i]["reasons"],
                     "rule_version": coh[i]["rule_version"], **{f"festive_{k}": v for k, v in g.items()}})
    _csv(d / "distributors.csv", rows)
    _csv(d / "monthly_performance.csv", T["billing_monthly"])
    sch = {s["scheme_id"]: s for s in T["schemes"]}
    _csv(d / "schemes.csv", [{**{f"scheme_{k}" if k != "scheme_id" else k: v for k, v in sch[h["scheme_id"]].items()},
                              "distributor_id": h["distributor_id"], "participated": h["enrolled"],
                              "progress_pct": h["progress_pct"], "qualified": h["achieved"]}
                             for h in T["scheme_history"]])
    _csv(d / "market_potential.csv", T["markets"])
    _csv(d / "sim_traits.csv", T["sim_traits"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--out", type=Path, default=root / "data")
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    gen = Gen(args.seed)
    summary = gen.run()
    write(gen, summary, args.out)
    kn = summary["kolkata_north"]
    print(f"Wrote {args.out / 'emami_dx.sqlite'}")
    print(f"  distributors: {summary['company']['distributors']}  | Kolkata North: {kn['distributors']}  cohorts {kn['cohorts']}")
    print(f"  KN potential Rs {kn['business_potential_l_month']} L/month vs current Rs {kn['current_secondary_l_month']} L/month"
          f" · avg performance {kn['avg_performance_score']}")
    print(f"  FYTD secondary {kn['secondary_fytd_display']} ({kn['yoy_growth_pct']:+}% YoY) · focus share {kn['focus_share_q2_pct']}%")
    print(f"  joined last scheme (Monsoon) {kn['joined_last_scheme_monsoon']} ({kn['joined_last_scheme_pct']}%)")
    print(f"  simulator expected response rate {kn['sim_expected_response_rate_pct']}%")


if __name__ == "__main__":
    main()
