"""Playwright interactive verification of Applied state, clickable cards, and tracker hub."""
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML = ROOT_DIR / "index.html"


def test_applied_card_click_and_hub_interaction():
    index_uri = INDEX_HTML.resolve().as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(index_uri, wait_until="domcontentloaded")
        page.wait_for_selector(".job-card", timeout=5000)

        # 1. Elements presence
        assert page.query_selector("#chip-applied") is not None
        assert page.query_selector("#metric-card-applied") is not None
        assert page.query_selector("#modal-applied-tracker") is not None

        # 2. Click on Applied quick filter chip
        page.click("#chip-applied")
        page.wait_for_timeout(300)
        assert page.eval_on_selector("#filter-status", "el => el.value") == "applied"
        assert page.eval_on_selector("#chip-applied", "el => el.classList.contains('active')") is True

        # 3. Click back to All Jobs
        page.click("#chip-all")
        page.wait_for_timeout(300)
        assert page.eval_on_selector("#filter-status", "el => el.value") == "all"

        # 4. Click Applied metric card
        page.click("#metric-card-applied")
        page.wait_for_timeout(300)
        assert page.eval_on_selector("#filter-status", "el => el.value") == "applied"

        # 5. Open Applied Tracker Hub modal
        page.click(".btn-applied-hub-pill")
        page.wait_for_timeout(300)
        assert page.eval_on_selector("#modal-applied-tracker", "el => el.classList.contains('open')") is True

        # 6. Close modal
        page.click("#modal-applied-tracker .modal-close-btn")
        page.wait_for_timeout(300)
        assert page.eval_on_selector("#modal-applied-tracker", "el => el.classList.contains('open')") is False

        browser.close()


def test_applied_toggle_persists_across_page_reloads():
    index_uri = INDEX_HTML.resolve().as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(index_uri, wait_until="domcontentloaded")
        page.wait_for_selector(".job-card", timeout=5000)

        # Find first card that is unapplied
        unapplied_btn = page.query_selector(".btn-applied:not(.active)")
        assert unapplied_btn is not None, "At least one unapplied job button should exist"

        # Click to mark applied
        unapplied_btn.click()
        page.wait_for_timeout(300)

        # Check localStorage directly
        stored = page.evaluate("() => JSON.parse(localStorage.getItem('jobhunt_applied_jobs') || '{}')")
        assert len(stored) >= 1, "localStorage should contain applied jobs"

        # Check that chip-count-applied updated
        applied_count = int(page.inner_text("#chip-count-applied"))
        assert applied_count >= 1

        # Now reload the page (simulating user returning to GitHub Pages)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_selector(".job-card", timeout=5000)

        # Verify applied state is restored from localStorage!
        reloaded_count = int(page.inner_text("#chip-count-applied"))
        assert reloaded_count == applied_count, f"Expected {applied_count} applied jobs after reload, got {reloaded_count}"

        # Verify metric card value matches
        metric_val = int(page.inner_text("#metric-applied"))
        assert metric_val == applied_count

        context.close()
        browser.close()

