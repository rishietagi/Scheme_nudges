"""Run one full loop (autopilot) and print the calibration numbers.  python scripts/sim_report.py [seed] [scenario]"""
from __future__ import annotations

import os
import statistics
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("LLM_MODE", "mock")


def report(seed: int, scenario: str = "typical", con=None) -> dict:
    from app.db.conn import connect
    from app.db.run_queries import facts
    from app.simulation import engine

    own = con is None
    con = con or connect(Path(tempfile.mkdtemp()) / "runs.sqlite")
    run_id = engine.reset(con, seed, scenario, autopilot=True)
    engine.advance(con, run_id, 7.0)
    d7 = facts(con, run_id, 7.0)
    engine.advance(con, run_id, 30)
    d30 = facts(con, run_id, 30)
    one = lambda sql: con.execute(sql, (run_id,)).fetchone()[0]  # noqa: E731
    flags = con.execute("""SELECT s.distributor_id, MAX(g.severity='red') red FROM sanity_flags g
                            JOIN survey_responses s USING (run_id, response_id) WHERE g.run_id=? GROUP BY s.response_id""",
                        (run_id,)).fetchall()
    red = len({f[0] for f in flags if f[1]})
    amber = len({f[0] for f in flags if not f[1]} - {f[0] for f in flags if f[1]})
    replied = [f for f in d7.values() if f.replied]
    hours = [(f.responses[0]["submitted_at"] - f.nudge_at) * 24 for f in replied]
    personas = con.execute("SELECT * FROM personas WHERE run_id=?", (run_id,)).fetchall()
    out = {
        "replied": len(replied),
        "median_h": round(statistics.median(hours), 1),
        "red": red, "amber": amber, "clean": len(replied) - red - amber,
        "intents": dict(Counter(f.latest["q1_intent"] for f in replied)),
        "joined_d7": sum(1 for f in d7.values() if f.enrol),
        "joined_d30": sum(1 for f in d30.values() if f.enrol),
        "beat": one("SELECT COUNT(*) FROM october_sales WHERE run_id=? AND hit_prediction=1"),
        "plan_rows": [(r[0], r[1], r[2], r[3], r[4]) for r in con.execute(
            "SELECT group_name, members, cta_code, confidence, priority FROM cta_plan WHERE run_id=? AND group_type!='individual' ORDER BY sort_order",
            (run_id,))],
        "individual": one("SELECT COUNT(*) FROM cta_plan WHERE run_id=? AND group_type='individual'"),
        "bengali_switch": sum(p["language_changed"] and p["language"] == "Bengali" for p in personas),
        "prefer_call": sum(p["prefers"] == "ASM call" for p in personas),
        "evening": sum(p["best_time"] == "Evening" for p in personas),
        "visit": sum(p["prefers"] == "ASM visit" for p in personas),
        "run_id": run_id,
    }
    if own:
        con.close()
    return out


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    for k, v in report(seed, sys.argv[2] if len(sys.argv) > 2 else "typical").items():
        print(f"{k:16} {v}")
