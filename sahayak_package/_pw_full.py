import os
import time
from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"
os.makedirs("_pw_shots", exist_ok=True)


def answer_turn(page, text, wait_rounds=25):
    typed = page.locator('input[aria-label="Or type the reply instead"]')
    typed.click()
    typed.fill(text)
    typed.press("Enter")
    for _ in range(wait_rounds):
        page.wait_for_timeout(2000)
        body = page.inner_text("body")
        if "Thinking" not in body:
            break


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 2600})
        page.goto(URL)
        page.wait_for_selector("text=Sahayak", timeout=20000)
        time.sleep(1)
        page.click("text=Start Call")
        page.wait_for_selector("text=Call in Progress", timeout=15000)
        time.sleep(1)

        answer_turn(page, "My name is Ramesh")
        answer_turn(page, "I live in a village near Kharagpur")
        answer_turn(
            page,
            "My wife is seven months pregnant and we lost our crop in the rain, we have no savings",
        )
        for i in range(3):
            body = page.inner_text("body")
            if "processed successfully" in body or "Caller intake" not in body:
                break
            answer_turn(page, "No, that's everything, thank you.")

        print("Waiting for pipeline...")
        found = False
        for i in range(50):
            page.wait_for_timeout(5000)
            body = page.inner_text("body")
            if "processed successfully" in body or "Pipeline failed" in body:
                found = True
                print(f"done after ~{(i+1)*5}s")
                break

        page.wait_for_timeout(5000)
        page.screenshot(path="_pw_shots/full_result.png", full_page=True)
        if not found:
            print("TIMED OUT")
            page.screenshot(path="_pw_shots/full_result_timeout.png", full_page=True)
        browser.close()


if __name__ == "__main__":
    main()
