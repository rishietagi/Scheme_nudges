"""Loads the provided rule files (yaml) into Pydantic models. The yaml files are config; code never hard-codes them."""
from __future__ import annotations

from functools import lru_cache

import yaml
from pydantic import BaseModel

from app.config import settings


class Threshold(BaseModel):
    value: float
    min: float
    max: float
    label: str
    unit: str


class Axis(BaseModel):
    label: str
    high: str
    low: str


class Weight(BaseModel):
    value: float
    label: str
    explain: str


class Cell(BaseModel):
    high_potential: bool
    high_performance: bool


class CohortRule(BaseModel):
    name: str
    cell: Cell
    tag: str
    color: str
    definition: str


class CohortRules(BaseModel):
    version: str
    as_of: str
    thresholds: dict[str, Threshold]
    weights: dict[str, Weight]       # growth, schemes, focus, delivery
    axes: dict[str, Axis]            # potential, performance
    cohorts: list[CohortRule]
    benchmark: str = ""

    def t(self, key: str) -> float:
        return self.thresholds[key].value

    def with_overrides(self, thresholds: dict[str, float] | None = None, definitions: dict[str, str] | None = None,
                       weights: dict[str, float] | None = None) -> "CohortRules":
        """A copy with edited thresholds / weights / definitions (unknown keys ignored, values clamped to their range).
        Weights are re-scaled to add up to 100."""
        out = self.model_copy(deep=True)
        for k, v in (thresholds or {}).items():
            if k in out.thresholds:
                t = out.thresholds[k]
                t.value = min(t.max, max(t.min, float(v)))
        if weights:
            new = {k: max(0.0, float(weights.get(k, w.value))) for k, w in out.weights.items()}
            total = sum(new.values()) or 1.0
            for k, w in out.weights.items():
                w.value = round(100 * new[k] / total, 1)
        for c in out.cohorts:
            if definitions and definitions.get(c.name, "").strip():
                c.definition = definitions[c.name].strip()
        return out


def _load(name: str) -> dict:
    with open(settings.rules_dir / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def cohort_rules() -> CohortRules:
    return CohortRules.model_validate(_load("cohorts.yaml"))


def effective_cohort_rules(con) -> CohortRules:
    """The yaml defaults with any edits saved from the Cohort rules page (config table)."""
    from app.db.config_store import get_config

    saved = get_config(con, "cohorts") or {}
    return cohort_rules().with_overrides(saved.get("thresholds"), saved.get("definitions"), saved.get("weights"))


@lru_cache
def survey_rules() -> dict:
    return _load("survey.yaml")


@lru_cache
def sanity_rules() -> dict:
    return _load("sanity_checks.yaml")


@lru_cache
def cta_rules() -> dict:
    return _load("ctas.yaml")
