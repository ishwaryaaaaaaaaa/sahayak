import os
import time
from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"
os.makedirs("_pw_shots", exist_ok=True)


def shot(page, name):
    page.screenshot(path=f"_pw_shots/{name}.png", full_page=True)
    print(f"screenshot: {name}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 2400})
        errs = []
        page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        page.goto(URL)
        page.wait_for_selector("text=Sahayak", timeout=20000)
        time.sleep(2)
        shot(page, "premium_landing")

        page.click("text=Start Call")
        page.wait_for_selector("text=Call in Progress", timeout=15000)
        time.sleep(2)
        shot(page, "premium_call_panel")
        print("CONSOLE ERRORS:", errs)
        browser.close()


if __name__ == "__main__":
    main()
