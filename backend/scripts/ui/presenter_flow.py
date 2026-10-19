"""Drive the Simulation tab like a presenter: Reset → Play → wait for approval → approve → play resumes → Day 30."""
import json
import sys
import urllib.parse
import urllib.request

from playwright.sync_api import sync_playwright

OUT = sys.argv[1]
API = "http://localhost:8000"


def post(path, body=None):
    req = urllib.request.Request(API + path, data=json.dumps(body or {}).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    post("/sim/reset", {"seed": 42, "autopilot": False})        # the presenter flow starts with approvals by hand
    page.goto("http://localhost:3000/simulation")
    page.wait_for_timeout(1500)
    page.get_by_role("button", name="Reset to Day 0").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="1 s").click()
    page.get_by_role("button", name="Play").click()
    page.get_by_text("Waiting for your approval").first.wait_for(timeout=30000)
    page.wait_for_timeout(1200)
    page.screenshot(path=f"{OUT}/flow-approval.png", full_page=True)
    print("gate:", page.locator("text=Day 7").first.inner_text())
    # Modify one suggestion through the UI: Exit / Watchlist -> Rahul calls, with a note; accept the rest.
    page.goto("http://localhost:3000/approvals")
    page.get_by_role("button", name="Modify the suggestion for Exit / Watchlist").click()
    page.get_by_role("radio", name="Rahul calls within 48 hours").click()
    page.get_by_placeholder("e.g. I know them — a call works better").fill("I know these accounts")
    page.wait_for_timeout(600)
    page.screenshot(path=f"{OUT}/flow-modify.png", full_page=False)
    page.get_by_role("button", name="Save and accept").click()
    page.wait_for_timeout(800)
    page.get_by_role("button", name="Accept all remaining").click()
    page.wait_for_timeout(800)
    page.screenshot(path=f"{OUT}/flow-decided.png", full_page=True)
    s = post("/sim/play", {"speed_seconds_per_day": 1})
    print("waiting:", s["waiting_for_approval"], "playing:", s["playing"])
    page.goto("http://localhost:3000/simulation")
    page.get_by_text("Results ready · loop closed").first.wait_for(timeout=40000)
    page.wait_for_timeout(1500)
    page.screenshot(path=f"{OUT}/flow-day30.png", full_page=True)
    print("console errors:", errors or "none")
    b.close()
