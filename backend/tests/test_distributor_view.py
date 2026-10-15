"""Phase 5: Distributor view (conversation + agents' timeline + live chat), Command centre and the 360 — time-aware."""
from fastapi.testclient import TestClient

from app.agents.chat_graph import detect_language, keyword_intent, safe
from app.main import app

client = TestClient(app)


def run_to(day, autopilot=True):
    client.post("/sim/reset", json={"seed": 42, "autopilot": autopilot})
    client.post("/sim/advance", json={"to_day": day})


def test_maa_tara_story_on_the_phone_and_behind_it():
    run_to(30)
    v = client.get("/chat/DST-0001", params={"day": 9.9}).json()
    kinds = [(m["sender"], m["kind"]) for m in v["messages"]]
    assert kinds[:2] == [("desk", "nudge"), ("desk", "quick_replies")]
    assert ("distributor", "survey") in kinds and ("desk", "voice") in kinds and kinds[-1] == ("desk", "enrolled")
    tapped = next(m for m in v["messages"] if m.get("tapped"))
    assert tapped["text"] == "বাংলায় বুঝিয়ে বলুন" and tapped["day_label"].startswith("Day 0")
    voice = next(m for m in v["messages"] if m["kind"] == "voice")
    assert voice["language"] == "Bengali" and voice["time_label"] == "10:00"
    agents = [j["agent"] for j in v["journey"]]
    assert agents[:3] == ["Nudge agent", "Survey agent", "CTA agent"] and "Execution" in agents
    assert any("Individual attention" in j["text"] for j in v["journey"])
    assert v["language"] == "Bengali" and v["best_time"] == "Around 1 pm" and v["this_cycle"] == "Personal follow-up"
    early = client.get("/chat/DST-0001", params={"day": 0.2}).json()
    assert early["messages"] == [] and early["journey"] == []


def test_scenarios_describe_what_happened():
    run_to(30)
    s = {x["distributor_id"]: x["subtitle"] for x in client.get("/chat/scenarios").json()}
    assert s["DST-0001"] == "Asked for Bengali → voice note → joined"
    assert s["DST-0006"].startswith("19-second survey") and s["DST-0006"].endswith("joined")
    assert s["DST-0005"] == "Asked for Rahul → call → margin issue"


def test_live_chat_joins_and_answers_in_their_language():
    run_to(9.6)
    v = client.post("/chat/DST-0002/message", json={"text": "আমি যোগ দিতে চাই"}).json()
    assert v["messages"][-2]["text"] == "আমি যোগ দিতে চাই" and "₹6.3 L" in v["messages"][-1]["text"]
    assert sum(m["kind"] == "enrolled" for m in v["messages"]) == 0               # the chat itself shows the join
    d = client.get("/distributors/DST-0002").json()
    assert d["festive_joined"] and d["festive_join_label"] == "Day 9"
    v = client.post("/chat/DST-0002/message", json={"text": "what is my target"}).json()
    assert v["messages"][-1]["text"].startswith("Your October target is ₹6.3 L")
    v = client.post("/chat/DST-0010/message", json={"text": "please ask Rahul to call me"}).json()
    assert "Rahul" in v["messages"][-1]["text"] and any("asked for a call" in j["text"] for j in v["journey"])
    run_to(0.1)
    assert client.post("/chat/DST-0001/message", json={"text": "hi"}).status_code == 409


def test_chat_helpers():
    assert detect_language("আমি যোগ দেব", "English") == "Bengali" and detect_language("जुड़ना है", "English") == "Hindi"
    assert keyword_intent("JOIN") == "join" and keyword_intent("explain in bangla") == "explain_bengali"
    assert keyword_intent("can Rahul call me") == "talk_to_asm" and keyword_intent("হুম") == "other"
    assert not safe("Your target is \textsuperscript{x}", {"target": "₹6.3 L"})
    assert not safe("line one\nline two", {})
    assert not safe("Your target is ₹9.9 L.", {"target": "₹6.3 L"})
    assert safe("Your target is ₹6.3 L; reach ₹7.9 L for +4% and ₹10,000.", {"target": "₹6.3 L", "stretch": "₹7.9 L"})


def test_command_centre_follows_the_loop():
    run_to(0, autopilot=False)
    c = client.get("/command").json()
    assert c["greeting"] == "Good morning, Rahul" and c["needs"][0]["title"] == "Send the Festive nudge"
    client.post("/sim/advance", json={"to_day": 30})                              # stops at the Day-7 gate
    c = client.get("/command").json()
    tiles = {t["key"]: t for t in c["tiles"]}
    assert tiles["replied"]["value"] == 60 and tiles["joined"]["value"] == 27
    assert tiles["waiting"]["value"] == 6 and tiles["individual"]["value"] == 11
    assert [n["title"] for n in c["needs"]][:1] == ["Approve the follow-up plan"] and len(c["needs"]) <= 3
    assert c["summary_label"] == "Emami AI · first week in short" and len(c["summary"]) == 3
    assert sum(p["distributors"] for p in c["cohorts"]) == 86
    assert client.get("/command", params={"day": 3}).json()["tiles"][0]["value"] < 60


def test_360_is_time_aware():
    run_to(30)
    d30 = client.get("/distributors/DST-0007").json()
    assert d30["festive_joined"] and d30["persona"]["language"] == "Bengali" and d30["persona"]["language_changed"]
    assert d30["persona"]["next_time"] and d30["milestones"][-1]["text"].startswith("₹")
    d0 = client.get("/distributors/DST-0007", params={"day": 0.1}).json()
    assert not d0["festive_joined"] and d0["persona"]["language"] == "English" and d0["persona"]["next_time"] is None
    rows = client.get("/cohorts/Scheme-hesitant/distributors").json()["items"]
    an = next(r for r in rows if r["distributor_id"] == "DST-0007")
    assert an["intent"] == "Explain in Bengali" and an["joined_day"] == 9 and an["language_changed"]
    sh = next(c for c in client.get("/cohorts").json()["cohorts"] if c["name"] == "Scheme-hesitant")
    assert sh["joined_festive"] >= 10 and sh["replied"] <= 19
