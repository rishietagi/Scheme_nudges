"""Search seeds for one whose default run (typical, approve-all) lands inside every calibration band
(SIMULATION_SPEC §8), ranked by distance to the targets.   python scripts/find_seed.py [first] [last]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("LLM_MODE", "mock")

from scripts.sim_report import report  # noqa: E402

TARGETS = {  # metric: (target, low, high)
    "replied": (62, 58, 66),
    "red": (4, 2, 7),
    "I've enrolled": (26, 22, 30),
    "I'll enrol": (10, 6, 14),
    "Explain again": (12, 8, 16),
    "Explain in Bengali": (7, 3, 11),
    "Talk to my ASM": (7, 3, 11),
    "joined_d7": (27, 23, 31),
    "joined_d30": (55, 50, 60),
    "beat": (41, 36, 46),
    "median_h": (4, 2, 6),
}


def metrics(r: dict) -> dict:
    return {**{k: r[k] for k in ("replied", "red", "joined_d7", "joined_d30", "beat", "median_h")},
            **{i: r["intents"].get(i, 0) for i in ("I've enrolled", "I'll enrol", "Explain again", "Explain in Bengali", "Talk to my ASM")}}


def score(m: dict) -> tuple[bool, float]:
    inside = all(lo <= m[k] <= hi for k, (_, lo, hi) in TARGETS.items())
    dist = sum(abs(m[k] - t) / max(1, hi - lo) for k, (t, lo, hi) in TARGETS.items())
    return inside, dist


if __name__ == "__main__":
    first, last = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (1, 200)
    found = []
    for seed in range(first, last + 1):
        r = report(seed)
        m = metrics(r)
        inside, dist = score(m)
        if inside:
            found.append((dist, seed, m, r["individual"]))
            print(f"seed {seed:3} inside · distance {dist:.2f} · individual {r['individual']} · {m}", flush=True)
    found.sort()
    print("\nbest:", [(s, round(d, 2), ia) for d, s, _, ia in found[:10]])
