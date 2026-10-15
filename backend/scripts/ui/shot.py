"""Screenshot pages with Playwright and report console errors.  python shot.py out_dir url[@WxH] ..."""
import sys

from playwright.sync_api import sync_playwright

out = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch()
    for i, arg in enumerate(sys.argv[2:]):
        url, _, size = arg.partition("@")
        w, h = (int(x) for x in (size or "1440x1000").split("x"))
        page = b.new_page(viewport={"width": w, "height": h})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        name = f"{out}/p{i}.png"
        page.screenshot(path=name, full_page=True)
        print(name, url, "errors:", errors or "none")
        page.close()
    b.close()
