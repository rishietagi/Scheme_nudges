"""The closed loop as a LangGraph graph.

State is tiny ({run_id, step, con}); the run tables are the real state, so re-invoking after the ASM approves simply
continues the loop (no checkpointer needed).

  start ─┬─ day0 ─→ cohort_agent → nudge_agent → survey_agent → END
         ├─ plan ─→ cta_agent → approval_gate ─┬─ waiting → END
         │                                     └─ decided → execution_agent → results_agent → persona_agent → END
         └─ execute ─→ approval_gate (same branch as above)
"""
from __future__ import annotations

import sqlite3
from functools import lru_cache
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents import nodes


class LoopState(TypedDict, total=False):
    run_id: str
    step: str                 # day0 | plan | execute
    con: Any
    decided: bool


@lru_cache
def graph():
    g = StateGraph(LoopState)
    for name in ("cohort_agent", "nudge_agent", "survey_agent", "cta_agent", "approval_gate", "execution_agent",
                 "results_agent", "persona_agent"):
        g.add_node(name, getattr(nodes, name))
    g.add_conditional_edges(START, lambda s: s["step"], {"day0": "cohort_agent", "plan": "cta_agent", "execute": "approval_gate"})
    g.add_edge("cohort_agent", "nudge_agent")
    g.add_edge("nudge_agent", "survey_agent")
    g.add_edge("survey_agent", END)
    g.add_edge("cta_agent", "approval_gate")
    g.add_conditional_edges("approval_gate", lambda s: "go" if s.get("decided") else "wait", {"go": "execution_agent", "wait": END})
    g.add_edge("execution_agent", "results_agent")
    g.add_edge("results_agent", "persona_agent")
    g.add_edge("persona_agent", END)
    return g.compile()


def run(con: sqlite3.Connection, run_id: str, step: str) -> LoopState:
    return graph().invoke({"run_id": run_id, "step": step, "con": con})
