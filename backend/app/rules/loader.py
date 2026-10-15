"""Loads the provided rule files (yaml) into Pydantic models. The yaml files are config; code never hard-codes them."""
from __future__ import annotations

from functools import lru_cache

import yaml
from pydantic import BaseModel

from app.config import settings


class CohortRule(BaseModel):
    name: str
    tag: str
    when: str


class CohortRules(BaseModel):
    version: str
    as_of: str
    cohorts: list[CohortRule]


def _load(name: str) -> dict:
    with open(settings.rules_dir / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def cohort_rules() -> CohortRules:
    return CohortRules.model_validate(_load("cohorts.yaml"))


@lru_cache
def survey_rules() -> dict:
    return _load("survey.yaml")


@lru_cache
def sanity_rules() -> dict:
    return _load("sanity_checks.yaml")


@lru_cache
def cta_rules() -> dict:
    return _load("ctas.yaml")
