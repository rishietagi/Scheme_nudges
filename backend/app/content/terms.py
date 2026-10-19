"""Display words for stored values, in FMCG trade terms.

The five scheme intents are stored as the values in rules/survey.yaml ("I've enrolled", "I'll enrol", …) because the
Day-0 data and the rules use them as codes. People read them as Indian FMCG trade does: a distributor *participates*
in a scheme ("Already participating", "Will participate"). Labels live in content/survey_i18n.yaml.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml


@lru_cache
def _i18n() -> dict:
    with open(Path(__file__).with_name("survey_i18n.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def intent_label(value: str | None, lang: str = "English") -> str:
    if value is None:
        return ""
    return _i18n().get(lang, {}).get("options", {}).get(value) or _i18n()["English"]["options"].get(value, value)


def intent_labels(values, lang: str = "English") -> dict[str, str]:
    return {v: intent_label(v, lang) for v in values}


_TRADE = [  # provided Day-0 wording -> FMCG trade terms (slabs; payouts settled as credit notes)
    ("Hit target: ", "Slab 1 (target): "),
    ("Beat it by 25%: ", "Slab 2 (target +25%): "),
    ("Hit the target: ", "Slab 1 (target): "),
    ("a ₹10,000 bonus", "a ₹10,000 credit note"),
    ("₹10,000 bonus", "₹10,000 credit note"),
]


def trade_terms(text: str) -> str:
    """Scheme text from the provided Day-0 data, reworded the way FMCG trade circulars say it."""
    for a, b in _TRADE:
        text = text.replace(a, b)
    return text
