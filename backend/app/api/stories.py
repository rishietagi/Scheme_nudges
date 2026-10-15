"""Per-distributor stories, all derived from run tables as of a day: the WhatsApp conversation (Distributor view),
'Behind the conversation' (from events), the 360 milestones and the persona so far."""
from __future__ import annotations

import json
import math
import sqlite3

from app.agents.nodes import ASM, inr, lang_of
from app.db.run_queries import Fact
from app.engines import persona as persona_engine
from app.engines.cta_planner import SHORT
from app.simulation.clock import day_label, time_label

DESK = {  # auto replies from the (simulated) Emami Distributor Desk
    "thanks": {"English": "Thanks! Five quick questions — it takes a minute.",
               "Bengali": "ধন্যবাদ! পাঁচটা ছোট প্রশ্ন — এক মিনিট লাগবে।",
               "Hindi": "धन्यवाद! पाँच छोटे सवाल — एक मिनट लगेगा।"},
    "I've enrolled": {"English": "Great — you're in. We've noted it in DMS.", "Bengali": "দারুণ — আপনি যোগ দিয়েছেন। DMS-এ লিখে রাখলাম।",
                      "Hindi": "बढ़िया — आप जुड़ गए हैं। DMS में दर्ज कर लिया है।"},
    "I'll enrol": {"English": "Great — reply JOIN whenever you're ready.", "Bengali": "দারুণ — তৈরি হলে JOIN লিখে উত্তর দিন।",
                   "Hindi": "बढ़िया — जब तैयार हों, JOIN लिखकर जवाब दें।"},
    "Explain again": {"English": "Thanks — we'll send a simpler explanation.", "Bengali": "ধন্যবাদ — আরও সহজ করে বুঝিয়ে পাঠাব।",
                      "Hindi": "धन्यवाद — और आसान तरीके से समझाकर भेजेंगे।"},
    "Explain in Bengali": {"English": "Thanks — we'll send it in Bengali.", "Bengali": "ধন্যবাদ — বাংলায় বুঝিয়ে পাঠাব।",
                           "Hindi": "धन्यवाद — बांग्ला में समझाकर भेजेंगे।"},
    "Talk to my ASM": {"English": f"Sure — {ASM} will get in touch.", "Bengali": "অবশ্যই — রাহুল যোগাযোগ করবেন।",
                       "Hindi": "ज़रूर — राहुल संपर्क करेंगे।"},
    "joined": {"English": "You're in the Festive Scheme. Your target is {target}. All the best for October!",
               "Bengali": "আপনি ফেস্টিভ স্কিমে যোগ দিয়েছেন। আপনার টার্গেট {target}। অক্টোবরের জন্য শুভেচ্ছা!",
               "Hindi": "आप फेस्टिव स्कीम से जुड़ गए हैं। आपका टारगेट {target} है। अक्टूबर के लिए शुभकामनाएँ!"},
}
INTENT_LABEL = {
    "Bengali": {"I've enrolled": "আমি যোগ দিয়েছি", "I'll enrol": "আমি যোগ দেব", "Explain again": "আবার বুঝিয়ে বলুন",
                "Explain in Bengali": "বাংলায় বুঝিয়ে বলুন", "Talk to my ASM": "আমার ASM-এর সঙ্গে কথা বলব"},
    "Hindi": {"I've enrolled": "जुड़ चुके हैं", "I'll enrol": "जुड़ना है", "Explain again": "फिर से समझाइए",
              "Explain in Bengali": "बांग्ला में समझाइए", "Talk to my ASM": "ASM से बात करनी है"},
}
INTENTS = ["I've enrolled", "I'll enrol", "Explain again", "Explain in Bengali", "Talk to my ASM"]


def initials(name: str) -> str:
    words = [w for w in name.replace("&", " ").split() if w]
    return "".join(w[0].upper() for w in words[:2])


def _msg(i: int, sender: str, kind: str, day: float, text: str = "", **extra) -> dict:
    return {"id": f"m{i}", "sender": sender, "kind": kind, "sim_day": day, "day_label": day_label(day),
            "time_label": time_label(day), "text": text, **extra}


def label(intent: str, lang: str) -> str:
    return INTENT_LABEL.get(lang, {}).get(intent, intent)


def conversation(con: sqlite3.Connection, run_id: str, f: Fact, day: float) -> list[dict]:
    out: list[tuple[float, str, str, str, dict]] = []
    nudges = {r["kind"]: dict(r) for r in con.execute(
        "SELECT * FROM nudges WHERE run_id = ? AND distributor_id = ? AND sent_at <= ?", (run_id, f.distributor_id, day))}
    lang0 = lang_of(nudges["nudge"]["language"]) if "nudge" in nudges else "English"
    if "nudge" in nudges:
        n = nudges["nudge"]
        out.append((n["sent_at"], "desk", "nudge", n["text"], {"language": lang0, "card": {
            "target": inr(f.target_l), "hit": "+3% margin on focus SKUs", "stretch": inr(f.stretch_l), "beat": "+4% and ₹10,000 bonus"}}))
        out.append((n["sent_at"] + 1e-6, "desk", "quick_replies", {"English": "What would you like to do?",
                    "Bengali": "আপনি কী করতে চান?", "Hindi": "आप क्या करना चाहेंगे?"}[lang0],
                    {"options": [label(i, lang0) for i in INTENTS]}))
    if "reminder" in nudges:
        out.append((nudges["reminder"]["sent_at"], "desk", "text", nudges["reminder"]["text"], {}))

    first = f.responses[0] if f.responses else None
    if first:
        t = first["submitted_at"]
        out.append((t - first["survey_seconds"] / 86400 - 2e-6, "distributor", "text", label(first["q1_intent"], lang0), {"tapped": True}))
        out.append((t - first["survey_seconds"] / 86400 - 1e-6, "desk", "text", DESK["thanks"][lang0], {}))
        answers = [{"q": q, "a": f"{first[k]} of 5"} for q, k in (("Clear", "q2"), ("Helps", "q3"), ("Target", "q4"), ("Payouts", "q5"))
                   if first[k] is not None]
        if first["q6"]:
            answers.append({"q": "Wants", "a": first["q6"]})
        out.append((t, "distributor", "survey", first["q7_text"] or "", {"answers": answers, "seconds": first["survey_seconds"]}))
        reply = DESK.get(first["q1_intent"], {}).get(lang0)
        if reply and not (first["q1_intent"] == "I've enrolled" and not (f.enrol and f.enrol["sim_day"] <= t + 1e-4)):
            out.append((t + 1e-4, "desk", "text", reply, {}))

    for d in f.deliveries:
        kind = "voice" if d["cta_code"] == "VOICE_EXPLAINER" else "text"
        out.append((d["sent_at"], "desk", kind, d["text"] or "", {"language": d["language"], "cta": SHORT[d["cta_code"]]}))
    for c in f.calls:
        what = "Visit from Rahul" if c["kind"] == "visit" else "Voice call with Rahul · 6 min"
        out.append((c["sim_day"], "system", "call", what, {}))
    chat_days = {m["sim_day"] for m in con.execute(
        "SELECT sim_day FROM chat_messages WHERE run_id = ? AND distributor_id = ?", (run_id, f.distributor_id))}
    if f.enrol and f.enrol["sim_day"] in chat_days:
        pass                                       # joined from the chat: the chat itself shows it
    elif f.enrol and f.enrol["path"] != "after_nudge":
        e = f.enrol["sim_day"]
        lang = lang_of(f.deliveries[-1]["language"]) if f.deliveries else lang0
        if f.enrol["path"] in ("after_cta", "self"):
            out.append((e, "distributor", "text", "JOIN", {}))
        out.append((e + 1e-4, "desk", "enrolled", DESK["joined"][lang].format(target=inr(f.target_l)), {"note": "Written to DMS (simulated)"}))
    elif f.enrol:
        out.append((f.enrol["sim_day"] + 2e-4, "desk", "enrolled", DESK["joined"][lang0].format(target=inr(f.target_l)),
                    {"note": "Written to DMS (simulated)"}))

    for m in con.execute("SELECT * FROM chat_messages WHERE run_id = ? AND distributor_id = ? AND sim_day <= ? ORDER BY rowid",
                         (run_id, f.distributor_id, day)):
        out.append((m["sim_day"], m["sender"], "text", m["text"], {"live": True}))

    out = [o for o in out if o[0] <= day + 1e-3]
    out.sort(key=lambda o: o[0])
    return [_msg(i, s, k, d, text, **extra) for i, (d, s, k, text, extra) in enumerate(out)]


def journey(con: sqlite3.Connection, run_id: str, f: Fact, day: float) -> list[dict]:
    """'Behind the conversation': this distributor's events, plus the approval of the row they were in."""
    rows = [dict(r) for r in con.execute(
        "SELECT * FROM events WHERE run_id = ? AND sim_day <= ? AND (distributor_id = ? OR type IN ('APPROVED','REJECTED')) "
        "ORDER BY sim_day, event_id", (run_id, day, f.distributor_id))]
    my_rows = {json.loads(r["payload_json"])["row_id"] for r in rows
               if r["type"] == "PLAN_READY" and r["distributor_id"] == f.distributor_id and r["payload_json"]}
    out = []
    for r in rows:
        payload = json.loads(r["payload_json"]) if r["payload_json"] else {}
        if r["type"] in ("APPROVED", "REJECTED") and r["distributor_id"] != f.distributor_id:
            if not my_rows & set(payload.get("row_ids", [])):
                continue
            r["text"] = ("Approved by autopilot" if r["agent"] == "Autopilot" else
                         f"{ASM} {'approved' if r['type'] == 'APPROVED' else 'rejected'} the follow-up")
        if r["type"] in ("CHECKED", "FLAG"):
            if out and out[-1]["type"] == "REPLY":
                out[-1]["text"] += " · answer passed all sanity checks" if r["type"] == "CHECKED" else f" · {r['text'].split(': ', 1)[-1]}"
            continue
        if r["type"] == "REPLY" and f.responses:
            first = f.responses[0]
            clarity = f" · clarity {first['q2']} of 5" if first["q2"] is not None else ""
            r["text"] = f"Replied: {first['q1_intent']}{clarity}"
        if r["type"] == "ENROLLED":
            rest = r["text"].replace(f.name, "").strip()
            r["text"] = rest[:1].upper() + rest[1:] + " · written to DMS (simulated)"
        if r["type"] == "ASM_CALL":
            r["text"] = r["text"].replace(f" {f.name}", "")
        out.append({"type": r["type"], "agent": r["agent"], "sim_day": r["sim_day"], "day_label": day_label(r["sim_day"]).split(" · ")[0],
                    "time_label": time_label(r["sim_day"]), "text": r["text"]})
    return out


def reply_phrase(h: float | None) -> str:
    if h is None:
        return "No reply yet"
    if h < 1:
        return "Within the hour"
    if h > 24:
        return "After a day or more"
    return f"Within {math.ceil(h)} hours"


def persona_view(f: Fact, day: float) -> dict:
    p = persona_engine.compute(f, day)
    best = persona_engine.hour_phrase(p["best_hour"]).capitalize() if p["best_hour"] is not None else None
    return {
        "language": p["language"],
        "language_on_file": p["language_on_file"],
        "language_changed": p["language_changed"],
        "best_time": best,
        "replies": reply_phrase(p["reply_hours"]),
        "prefers": p["prefers"] if f.replied or f.enrol or f.deliveries else None,
        "what_worked": p["what_worked"] if f.enrol else None,
        "next_time": p["next_time"] if day >= 30 else None,
    }


def milestones(f: Fact, sales: dict | None, day: float) -> list[dict]:
    out = []
    if f.responses:
        r = f.responses[0]
        out.append((r["submitted_at"], f"Asked: {r['q1_intent']}" if r["q1_intent"] != "I've enrolled" else "Said: I've enrolled"))
    elif f.nudge_at is not None and day >= 7:
        out.append((7.0, "Didn't reply to the nudge or the reminder"))
    for d in f.deliveries:
        what = "a voice note" if d["cta_code"] == "VOICE_EXPLAINER" else SHORT[d["cta_code"]].lower()
        out.append((d["sent_at"], f"Got {what} in {d['language']}"))
    for c in f.calls:
        out.append((c["sim_day"], f"{'Visit' if c['kind'] == 'visit' else 'Call'} from {ASM}: {c['outcome'].lower()}"))
    if f.enrol:
        out.append((f.enrol["sim_day"], "Joined the scheme"))
    if sales and day >= 30:
        verdict = "beat" if sales["hit_prediction"] else ("short of" if f.enrol else "vs")
        noun = "prediction" if f.enrol else "forecast"
        ref = sales["predicted_l"] if f.enrol else sales["baseline_l"]
        out.append((30.0, f"{inr(sales['actual_l'])} in October · {verdict} the {inr(ref)} {noun}"))
    out.sort(key=lambda x: x[0])
    return [{"day_label": day_label(d).split(" · ")[0], "time_label": time_label(d) if d % 1 else None, "text": t} for d, t in out]
