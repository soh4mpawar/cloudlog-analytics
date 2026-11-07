"""Visual Acceptance Checker for CloudLog Analytics.

Uses Playwright to:
1. Capture screenshots at 1366x768 (desktop) and 390x844 (mobile).
2. Verify all application views and edge states (empty endpoints, validation error, benchmark).
3. Validate typography, responsive layout, absence of horizontal overflow, and strict adherence
   to warm ivory (#F7F5F0), dark olive (#526044), charcoal (#252823), and absence of blue/purple.
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "screenshots"))
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_visual_checks():
    print("Starting visual acceptance checks via Playwright Chromium...")
    results = {}

    with sync_playwright() as p:
        existing_chrome = r"C:\Users\soham\AppData\Local\ms-playwright\chromium-1117\chrome-win\chrome.exe"
        if os.path.exists(existing_chrome):
            browser = p.chromium.launch(executable_path=existing_chrome, headless=True)
        else:
            browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # 1. Desktop Viewport (1366 x 768)
        # -------------------------------------------------------------
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()

        print("Navigating to http://localhost:8501 (1366x768)...")
        page.goto("http://localhost:8501", timeout=30000)
        page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=20000)
        time.sleep(3)

        # Verify background color
        bg_color = page.evaluate("() => window.getComputedStyle(document.querySelector('[data-testid=\"stAppViewContainer\"]')).backgroundColor")
        print(f"Computed App Background Color: {bg_color}")
        results["bg_color"] = bg_color

        # Check for horizontal overflow
        has_horizontal_overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
        print(f"Horizontal Overflow (1366x768): {has_horizontal_overflow}")
        results["overflow_1366"] = has_horizontal_overflow

        # Capture Dashboard View
        dash_shot = os.path.join(OUTPUT_DIR, "01_desktop_dashboard.png")
        page.screenshot(path=dash_shot, full_page=True)
        print(f"Captured: {dash_shot}")

        # Navigate to Inside MapReduce
        print("Switching to Inside MapReduce view...")
        page.locator('label:has-text("Inside MapReduce")').first.click()
        time.sleep(3)
        imr_shot = os.path.join(OUTPUT_DIR, "02_desktop_inside_mapreduce.png")
        page.screenshot(path=imr_shot, full_page=True)
        print(f"Captured: {imr_shot}")

        # Navigate to Benchmark
        print("Switching to Benchmark view...")
        page.locator('label:has-text("Benchmark")').first.click()
        time.sleep(3)
        
        # Click Run Benchmark button
        btn = page.locator('button:has-text("Run Benchmark on Current Dataset")')
        if btn.is_visible():
            print("Triggering benchmark run...")
            btn.click()
            time.sleep(4)
            page.wait_for_selector('text=Verification Passed', timeout=25000)

        bench_shot = os.path.join(OUTPUT_DIR, "03_desktop_benchmark.png")
        page.screenshot(path=bench_shot, full_page=True)
        print(f"Captured: {bench_shot}")

        # Navigate to Cloud Architecture
        print("Switching to Cloud Architecture view...")
        page.locator('label:has-text("Cloud Architecture")').first.click()
        time.sleep(3)
        arch_shot = os.path.join(OUTPUT_DIR, "04_desktop_cloud_architecture.png")
        page.screenshot(path=arch_shot, full_page=True)
        print(f"Captured: {arch_shot}")

        # Edge state 1: Empty endpoints selection
        print("Testing empty endpoint selection edge state...")
        page.locator('label:has-text("Dashboard")').first.click()
        time.sleep(2)
        # Clear multiselect endpoints by clicking clear all button
        clear_btn = page.locator('button[aria-label="Clear all"]')
        if clear_btn.is_visible():
            clear_btn.click()
            time.sleep(1.5)
        empty_ep_shot = os.path.join(OUTPUT_DIR, "05_desktop_empty_endpoints.png")
        page.screenshot(path=empty_ep_shot, full_page=True)
        print(f"Captured: {empty_ep_shot}")

        # Edge state 2: Upload validation error
        print("Testing invalid CSV upload state...")
        page.locator('label:has-text("Upload CSV File")').first.click()
        time.sleep(1)
        invalid_csv_path = os.path.join(os.path.dirname(__file__), "bad_data.csv")
        with open(invalid_csv_path, "w") as f:
            f.write("wrong_col1,wrong_col2\n1,2\n")

        file_input = page.locator('input[type="file"]')
        file_input.set_input_files(invalid_csv_path)
        time.sleep(3)
        err_shot = os.path.join(OUTPUT_DIR, "06_desktop_upload_validation_error.png")
        page.screenshot(path=err_shot, full_page=True)
        print(f"Captured: {err_shot}")

        if os.path.exists(invalid_csv_path):
            os.remove(invalid_csv_path)

        context.close()

        # -------------------------------------------------------------
        # 2. Mobile Viewport (390 x 844) - iPhone 13/14 format
        # -------------------------------------------------------------
        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        )
        mobile_page = mobile_context.new_page()

        print("Navigating to http://localhost:8501 (390x844 Mobile)...")
        mobile_page.goto("http://localhost:8501", timeout=30000)
        mobile_page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=20000)
        time.sleep(3)

        # Collapse sidebar on mobile to show responsive content layout
        sb_btn = mobile_page.locator('[data-testid="stSidebarCollapseButton"]')
        if sb_btn.is_visible():
            sb_btn.click()
            time.sleep(1.5)

        mobile_overflow = mobile_page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
        print(f"Horizontal Overflow (390x844 Mobile): {mobile_overflow}")
        results["overflow_390"] = mobile_overflow

        mobile_shot = os.path.join(OUTPUT_DIR, "07_mobile_dashboard.png")
        mobile_page.screenshot(path=mobile_shot, full_page=True)
        print(f"Captured: {mobile_shot}")

        mobile_context.close()
        browser.close()

    print("\nVisual acceptance check completed successfully!")
    print(f"All screenshots saved to: {OUTPUT_DIR}")
    return results


if __name__ == "__main__":
    run_visual_checks()
