"""'Type as distributor': a tiny LangGraph — classify → act (code tools) → reply.

The LLM classifies the message and writes the reply from the tool's result only; code does every action and number.
Without an LLM the keyword classifier and the code-built replies answer in the distributor's language.
"""
from __future__ import annotations

import re
import sqlite3
from functools import lru_cache
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from app.agents.nodes import ASM, emit, inr, rupees
from app.db import queries
from app.db.run_queries import Fact, facts
from app.engines import persona
from app.llm.client import chat_mode, complete
from app.simulation import behaviour, traits
from app.simulation.clock import at, day_label

INTENTS = ["join", "target", "explain", "explain_bengali", "talk_to_asm", "thanks", "other"]
KEYWORDS = [  # (intent, pattern) — first match wins
    ("explain_bengali", r"bangla|bengali|বাংলা"),
    ("talk_to_asm", r"\basm\b|call|rahul|phone|ফোন|রাহুল|কল|कॉल|फोन|राहुल"),
    ("join", r"\bjoin\b|enrol|enroll|sign me|যোগ দে|যোগ দি|জয়েন|जुड़|जॉइन|ज्वाइन"),
    ("target", r"target|how much|kitna|টার্গেট|কত|टारगेट|कितना"),
    ("explain", r"explain|understand|what is|scheme|slab|বুঝ|স্কিম|समझ|स्कीम"),
    ("thanks", r"thank|thanks|\bok\b|ধন্যবাদ|धन्यवाद|शुक्रिया"),
]
REPLIES = {
    ("join", "new"): {"English": "Done, {first} — you're in the Festive Scheme. Your October target is {target}; hit it for +3% margin on focus SKUs.",
                      "Bengali": "হয়ে গেছে, {first} — আপনি ফেস্টিভ স্কিমে যোগ দিয়েছেন। অক্টোবরের টার্গেট {target}; পূরণ করলে ফোকাস SKU-তে +৩% মার্জিন।",
                      "Hindi": "हो गया, {first} जी — आप फेस्टिव स्कीम से जुड़ गए हैं। अक्टूबर का टारगेट {target}; पूरा करने पर फोकस SKU पर +3% मार्जिन।"},
    ("join", "already"): {"English": "You're already in, {first} — you joined on {since}. Your target is {target}.",
                          "Bengali": "আপনি আগেই যোগ দিয়েছেন, {first} — {since}। আপনার টার্গেট {target}।",
                          "Hindi": "आप पहले से जुड़े हैं, {first} जी — {since}। आपका टारगेट {target} है।"},
    ("target", ""): {"English": "Your October target is {target}. Hit it: +3% margin on focus SKUs. Reach {stretch}: +4% and a ₹10,000 bonus.",
                     "Bengali": "অক্টোবরের টার্গেট {target}। পূরণ করলে ফোকাস SKU-তে +৩% মার্জিন। {stretch} হলে +৪% আর ₹১০,০০০ বোনাস।",
                     "Hindi": "अक्टूबर का टारगेट {target}। पूरा करने पर फोकस SKU पर +3% मार्जिन। {stretch} पर +4% और ₹10,000 बोनस।"},
    ("explain", ""): {"English": "In short: buy {target} in October and you earn +3% margin on focus SKUs (about {earn_hit}). Reach {stretch} and it's +4% plus ₹10,000. Reply JOIN to enrol.",
                      "Bengali": "সংক্ষেপে: অক্টোবরে {target}-এর মাল নিলে ফোকাস SKU-তে +৩% মার্জিন (প্রায় {earn_hit})। {stretch} হলে +৪% আর ₹১০,০০০। যোগ দিতে JOIN লিখুন।",
                      "Hindi": "संक्षेप में: अक्टूबर में {target} का माल लें तो फोकस SKU पर +3% मार्जिन (लगभग {earn_hit})। {stretch} पर +4% और ₹10,000। जुड़ने के लिए JOIN लिखें।"},
    ("talk_to_asm", ""): {"English": "Sure — Rahul will call you tomorrow around 11 am.",
                          "Bengali": "অবশ্যই — রাহুল কাল সকাল ১১টা নাগাদ ফোন করবেন।",
                          "Hindi": "ज़रूर — राहुल कल सुबह 11 बजे के आसपास कॉल करेंगे।"},
    ("thanks", ""): {"English": "Happy to help, {first}!", "Bengali": "সাহায্য করতে পেরে ভালো লাগল, {first}!", "Hindi": "मदद करके अच्छा लगा, {first} जी!"},
    ("other", ""): {"English": "I can help with your target, the scheme, joining, or a call from Rahul. What would you like?",
                    "Bengali": "টার্গেট, স্কিম, যোগ দেওয়া বা রাহুলের ফোন — কোনটা নিয়ে সাহায্য চান?",
                    "Hindi": "टारगेट, स्कीम, जुड़ना या राहुल की कॉल — किसमें मदद चाहिए?"},
}


class Intent(BaseModel):
    intent: str


class Reply(BaseModel):
    reply: str


class ChatState(TypedDict, total=False):
    con: Any
    run_id: str
    distributor_id: str
    text: str
    day: float
    language: str
    intent: str
    tool: str
    tool_result: dict
    reply: str


def detect_language(text: str, fallback: str) -> str:
    if re.search(r"[ঀ-৿]", text):
        return "Bengali"
    if re.search(r"[ऀ-ॿ]", text):
        return "Hindi"
    if re.search(r"[A-Za-z]", text):
        return "English"
    return fallback


def keyword_intent(text: str) -> str:
    t = text.lower()
    return next((i for i, pat in KEYWORDS if re.search(pat, t)), "other")


def _fact(state: ChatState) -> Fact:
    return facts(state["con"], state["run_id"], state["day"])[state["distributor_id"]]


def classify(state: ChatState) -> ChatState:
    f = _fact(state)
    state["language"] = detect_language(state["text"], persona.compute(f, state["day"])["language"])
    guess = keyword_intent(state["text"])
    if guess == "other":                      # the LLM only classifies what plain keywords can't (saves free-tier quota)
        out = complete("chat_intent", {"message": state["text"], "intents": INTENTS}, Intent, mode=chat_mode(), fallback={"intent": guess})
        guess = out.intent if out.intent in INTENTS else guess
    state["intent"] = guess
    if state["intent"] == "explain_bengali":
        state["language"] = "Bengali"
    return state


def act(state: ChatState) -> ChatState:
    con, rid, did, day = state["con"], state["run_id"], state["distributor_id"], state["day"]
    f = _fact(state)
    base = {"first_name": f.owner_name.split()[0], "target": inr(f.target_l), "stretch": inr(f.stretch_l),
            "earn_hit": rupees(f.target_l * 0.03), "hit_reward": "+3% margin on focus SKUs", "stretch_reward": "+4% margin and ₹10,000 bonus"}
    intent = state["intent"]
    if intent == "join":
        state["tool"] = "enrol_me"
        if f.enrol:
            state["tool_result"] = {**base, "already": True, "since": day_label(f.enrol["sim_day"])}
        else:
            _enrol(con, rid, f, day)
            state["tool_result"] = {**base, "already": False, "joined_today": True}
    elif intent == "talk_to_asm":
        state["tool"] = "request_asm_call"
        when = at(int(day) + 1, 11)
        con.execute("INSERT INTO asm_calls VALUES (?,?,?,?,?,?)", (rid, did, "chat", when, "call", "Requested in chat"))
        emit(con, rid, day, "ASM_CALL", "Execution", f"{f.name} asked for a call in the chat · booked for {day_label(when)} 11:00", did)
        state["tool_result"] = {**base, "asm": ASM, "when": "tomorrow around 11 am"}
    elif intent in ("target", "explain", "explain_bengali"):
        state["tool"] = "get_my_target" if intent == "target" else "explain_scheme"
        state["tool_result"] = base
    else:
        state["tool"] = "none"
        state["tool_result"] = {"first_name": base["first_name"]}
    return state


def _enrol(con: sqlite3.Connection, rid: str, f: Fact, day: float) -> None:
    """Join from the chat, now. Replaces any later join the run had planned; refreshes Day-30 rows if they exist."""
    con.execute("INSERT OR REPLACE INTO enrolments VALUES (?,?,?,?,?)", (rid, f.distributor_id, day, "self", None))
    emit(con, rid, day, "ENROLLED", "Execution", f"{f.name} joined the scheme from the chat", f.distributor_id)
    if con.execute("SELECT 1 FROM october_sales WHERE run_id = ? AND distributor_id = ?", (rid, f.distributor_id)).fetchone():
        run = con.execute("SELECT seed, scenario FROM loop_runs WHERE run_id = ?", (rid,)).fetchone()
        t = traits.load(con, queries.TERRITORY_ID, run["scenario"])[f.distributor_id]
        actual = behaviour.october_sales(run["seed"], f.distributor_id, t, joined_day=day, predicted=f.predicted_l,
                                         baseline=f.baseline_l, stretch=f.stretch_l)
        con.execute("UPDATE october_sales SET actual_l = ?, hit_prediction = ? WHERE run_id = ? AND distributor_id = ?",
                    (actual, int(actual >= f.predicted_l), rid, f.distributor_id))


def respond(state: ChatState) -> ChatState:
    lang = state["language"]
    r = state["tool_result"]
    key = ("join", "already" if r.get("already") else "new") if state["intent"] == "join" else (
        "explain" if state["intent"] == "explain_bengali" else state["intent"], "")
    template = REPLIES.get(key, REPLIES[("other", "")])[lang if lang in ("English", "Bengali", "Hindi") else "English"]
    draft = template.format(first=r.get("first_name", ""), target=r.get("target", ""), stretch=r.get("stretch", ""),
                            earn_hit=r.get("earn_hit", ""), since=r.get("since", ""))
    inputs = {"language": lang, "message": state["text"], "intent": state["intent"], "tool": state["tool"], "tool_result": r,
              "draft": draft}
    reply = complete("chat_reply", inputs, Reply, mode=chat_mode(), fallback={"reply": draft}).reply
    state["reply"] = reply if safe(reply, r) else draft
    return state


def safe(reply: str, tool_result: dict) -> bool:
    """Use the LLM's wording only if it is one clean paragraph and keeps the exact amounts the tool returned."""
    if not reply.strip() or "\n" in reply or re.search(r"[\\{}<>]|U\+[0-9A-Fa-f]{4}|textsuperscript", reply):
        return False
    amounts = [a.rstrip(".,") for a in re.findall(r"₹[\d,.]+", reply)]
    known = {str(v) for v in tool_result.values()}
    if any(not any(a in k for k in known) and a != "₹10,000" for a in amounts):
        return False                          # an amount the tool never gave
    return "target" not in tool_result or tool_result["target"] in reply or not re.search(r"\d", reply)


@lru_cache
def graph():
    g = StateGraph(ChatState)
    g.add_node("classify", classify)
    g.add_node("act", act)
    g.add_node("respond", respond)
    g.add_edge(START, "classify")
    g.add_edge("classify", "act")
    g.add_edge("act", "respond")
    g.add_edge("respond", END)
    return g.compile()


def handle(con: sqlite3.Connection, run_id: str, distributor_id: str, text: str, day: float) -> ChatState:
    con.execute("INSERT INTO chat_messages VALUES (?,?,?,?,?,?,?)", (run_id, distributor_id, day, "distributor", text, None, None))
    out = graph().invoke({"con": con, "run_id": run_id, "distributor_id": distributor_id, "text": text, "day": day})
    con.execute("INSERT INTO chat_messages VALUES (?,?,?,?,?,?,?)",
                (run_id, distributor_id, day, "desk", out["reply"], out["intent"], out["tool"]))
    name = con.execute("SELECT name FROM world.distributors WHERE distributor_id = ?", (distributor_id,)).fetchone()[0]
    emit(con, run_id, day, "CHAT", "Execution", f"{name} wrote in the chat → {out['intent'].replace('_', ' ')}", distributor_id)
    return out
