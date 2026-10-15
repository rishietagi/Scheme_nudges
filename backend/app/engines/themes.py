"""Comment themes for the Survey page. The LLM only *labels* each comment with one allowed theme; code counts.

With no LLM (mock), or for any comment the LLM leaves out, the label falls back to the theme carried by the simulated
comment (the text bank tags every line), so the card always fills.
"""
from __future__ import annotations

from collections import Counter

from pydantic import BaseModel

from app.llm.client import complete
from app.simulation.behaviour import text_bank


class Assignment(BaseModel):
    id: str
    theme: str


class Themes(BaseModel):
    assignments: list[Assignment]


def labels() -> dict[str, str]:
    return {k: v["label"] for k, v in text_bank()["themes"].items()}


def count(comments: list[dict]) -> list[dict]:
    """comments: [{id, text, language, tag}] -> [{theme, label, count}] most common first."""
    if not comments:
        return []
    allowed = labels()
    inputs = {"themes": list(allowed.values()), "comments": [{"id": c["id"], "text": c["text"]} for c in comments]}
    out = complete("comment_themes", inputs, Themes)
    by_label = {v: k for k, v in allowed.items()}
    picked = {a.id: by_label[a.theme] for a in out.assignments if a.theme in by_label}
    themes = Counter(picked.get(c["id"]) or c.get("tag") for c in comments)
    themes.pop(None, None)
    return [{"theme": t, "label": allowed[t], "count": n} for t, n in themes.most_common()]
