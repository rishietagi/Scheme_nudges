"""Persona updater (SIMULATION_SPEC §4): what the system learns about each distributor from behaviour alone.

Works at any sim day (the 360 shows it growing); the Day-30 LEARN step stores it in `personas`.
"""
from __future__ import annotations

from app.db.run_queries import Fact
from app.engines.cta_planner import ASM_FIRST_NAME, SHORT

VOICE_WORDS = ("voice", "ভয়েস")


def hour_phrase(hour: int | None) -> str:
    if hour is None:
        return "at 10 am"
    h12 = hour % 12 or 12
    return f"around {h12} {'am' if hour < 12 else 'pm'}"


def _bucket(hour: int) -> str:
    return "Morning" if hour < 12 else ("Afternoon" if hour < 17 else "Evening")


def compute(f: Fact, day: float) -> dict:
    first = f.responses[0] if f.responses else None
    latest = f.latest
    intents = {r["q1_intent"] for r in f.responses}
    wrote_bengali = any(r["q7_language"] == "Bengali" for r in f.responses)
    wants_voice = "Explain in Bengali" in intents or any(
        r["q7_text"] and any(w in r["q7_text"].lower() for w in VOICE_WORDS) for r in f.responses)

    cta_before_join = None
    if f.enrol and f.enrol["path"] in ("after_cta", "after_asm_call"):
        cta_before_join = f.enrol.get("cta_code")
    bengali_cta = any(d["language"] == "Bengali" for d in f.deliveries)
    joined_after_bengali = cta_before_join is not None and bengali_cta

    language = "Bengali" if ("Explain in Bengali" in intents or wrote_bengali or joined_after_bengali) else f.language_on_file

    best_hour = reply_hours = None
    best_time = None
    if first:
        best_hour = round((first["submitted_at"] % 1) * 24) % 24
        best_time = _bucket(best_hour)
        sent = f.reminder_at if (f.reminder_at and first["submitted_at"] > f.reminder_at) else f.nudge_at
        reply_hours = round((first["submitted_at"] - (sent or 0)) * 24, 1)
    speed = "No reply" if reply_hours is None else ("Fast" if reply_hours < 2 else ("Slow" if reply_hours > 24 else "Normal"))

    called = bool(f.calls)
    if "Talk to my ASM" in intents or (cta_before_join == "ASM_CALL" and called):
        prefers = "ASM call"
    elif wants_voice or cta_before_join == "VOICE_EXPLAINER":
        prefers = "Voice note"
    elif not f.replied and not f.enrol and (any(d["cta_code"] == "RE_NUDGE" for d in f.deliveries)
                                             or any(c["kind"] == "visit" for c in f.calls)):
        prefers = "ASM visit"           # ignored the nudge, the reminder and the re-send (or a visit didn't land)
    else:
        prefers = "WhatsApp text"

    if not f.enrol:
        worked = "Nothing yet"
    elif f.enrol["path"] in ("after_nudge", "self"):
        worked = "The Day-0 nudge"
    elif f.enrol["path"] == "after_asm_call":
        worked = f"{'Visit' if f.calls and f.calls[-1]['kind'] == 'visit' else 'Call'} from {ASM_FIRST_NAME}"
    elif cta_before_join == "VOICE_EXPLAINER":
        worked = f"{language} voice note" if language != "English" else "Voice note"
    else:
        worked = SHORT.get(cta_before_join or "", "Follow-up")

    when = hour_phrase(best_hour)
    margin = latest is not None and latest["q6"] == "Better margin"
    if prefers == "ASM visit":
        nxt = f"Skip WhatsApp — {ASM_FIRST_NAME} visits"
    elif prefers == "ASM call":
        nxt = f"Talk margins first — {ASM_FIRST_NAME} calls {when}" if margin and not f.enrol else f"{ASM_FIRST_NAME} calls {when}"
    elif prefers == "Voice note":
        nxt = f"Send the scheme as a {language} voice note {when}"
    elif not f.replied and not f.enrol:
        nxt = f"{ASM_FIRST_NAME} calls first, then WhatsApp"
    else:
        nxt = f"Send in {language} on WhatsApp {when}"

    return {
        "distributor_id": f.distributor_id,
        "language": language,
        "language_on_file": f.language_on_file,
        "language_changed": language != f.language_on_file,
        "best_time": best_time,
        "best_hour": best_hour,
        "reply_speed": speed,
        "reply_hours": reply_hours,
        "prefers": prefers,
        "what_worked": worked,
        "next_time": nxt,
        "updated_day": day,
    }
