"""Edge case visual verification: checks empty filter states and invalid CSV uploads."""

import os
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "screenshots"))


def test_edge_cases():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1366, "height": 768})

        page.goto("http://localhost:8501", timeout=30000)
        page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=15000)
        time.sleep(2)

        # 1. Switch to Upload CSV mode without file
        page.locator('text="Upload CSV File"').click()
        time.sleep(2)
        upload_prompt_shot = os.path.join(OUTPUT_DIR, "06_upload_prompt_empty.png")
        page.screenshot(path=upload_prompt_shot)
        print(f"Captured: {upload_prompt_shot}")

        # 2. Upload an invalid CSV (simulated via file chooser)
        invalid_csv_path = os.path.join(os.path.dirname(__file__), "invalid_sample.csv")
        with open(invalid_csv_path, "w") as f:
            f.write("bad_column_1,bad_column_2\n123,456\n")

        file_input = page.locator('input[type="file"]')
        if file_input.is_visible() or True:
            file_input.set_input_files(invalid_csv_path)
            time.sleep(2)
            page.wait_for_selector('.warning-box', timeout=5000)
            upload_err_shot = os.path.join(OUTPUT_DIR, "07_upload_validation_error.png")
            page.screenshot(path=upload_err_shot)
            print(f"Captured: {upload_err_shot}")

        # Clean up temp file
        if os.path.exists(invalid_csv_path):
            os.remove(invalid_csv_path)

        browser.close()
    print("Edge case visual check completed successfully!")


if __name__ == "__main__":
    test_edge_cases()
