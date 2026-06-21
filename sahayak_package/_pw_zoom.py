import time
from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 2400})
        page.goto(URL)
        page.wait_for_selector("text=Sahayak", timeout=20000)
        time.sleep(2)
        page.click("text=Start Call")
        page.wait_for_selector("text=Call in Progress", timeout=15000)
        time.sleep(2)
        page.locator("div.phone-bezel").first.screenshot(path="_pw_shots/phone_zoom.png")
        page.locator("div.pipeline-strip").first.screenshot(path="_pw_shots/pipeline_zoom.png")
        browser.close()


if __name__ == "__main__":
    main()
