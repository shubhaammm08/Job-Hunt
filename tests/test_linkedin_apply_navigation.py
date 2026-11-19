"""Automated verification suite for LinkedIn Job Post Apply Navigation.

Verifies:
1. R1: Clicking "Apply" / "1-Click Apply" on LinkedIn job posts in the JobHunt dashboard
   navigates directly to the exact corresponding LinkedIn post URL (https://www.linkedin.com/jobs/view/<job_id>)
   in a new tab/window (target="_blank").
2. R2: Dual-environment compatibility:
   - Local development server running via gui/server.py (http://127.0.0.1:PORT).
   - Static GitHub Pages hosting (index.html loaded statically without backend endpoints).
3. Edge cases: IDs with prefixes, search URLs with currentJobId, slug URLs, tracking params,
   and missing/empty URL fields.
"""
from __future__ import annotations

from http.server import HTTPServer
import json
import os
from pathlib import Path
import re
import socket
import sys
import threading
from urllib.parse import urlparse
import pytest
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from gui.server import JobHuntHandler
GUI_INDEX = ROOT_DIR / "gui" / "index.html"
ROOT_INDEX = ROOT_DIR / "index.html"
SEEN_JSON = ROOT_DIR / "seen.json"


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def local_server():
    """Starts a local gui.server.HTTPServer on an ephemeral port."""
    port = get_free_port()
    server = HTTPServer(("127.0.0.1", port), JobHuntHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()


# =============================================================================
# 1. Static HTML Template and Client-side JS Unit Verification
# =============================================================================

def test_html_contains_linkedin_post_url_helpers():
    """Asserts both gui/index.html and root index.html define LinkedIn ID and URL extraction helpers."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        assert html_path.exists(), f"File {html_path} must exist"
        content = html_path.read_text(encoding="utf-8")

        assert "extractLinkedInJobId" in content
        assert "isLinkedInJob" in content
        assert "getLinkedInPostUrl" in content
        assert "https://www.linkedin.com/jobs/view/" in content


def test_card_apply_button_configuration_no_prevent_default():
    """Asserts that the Apply anchor tag retains target='_blank' and does NOT suppress default navigation."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        content = html_path.read_text(encoding="utf-8")

        # The card's .btn-apply-link tag must be an <a> element with target="_blank" and rel="noopener noreferrer"
        assert '<a href="${escapeHtml(targetUrl)}"' in content
        assert 'target="_blank"' in content
        assert 'rel="noopener noreferrer"' in content
        assert 'class="btn-apply-link"' in content

        # event.preventDefault() must NOT be called in the card apply button onclick
        m = re.search(r'<a href="\$\{escapeHtml\(targetUrl\)\}"[^>]*class="btn-apply-link"[^>]*onclick="([^"]*)"', content)
        assert m, f"Card apply link onclick attribute not found in {html_path}"
        onclick_code = m.group(1)
        assert "preventDefault" not in onclick_code, (
            f"Apply link onclick in {html_path} must not call preventDefault: {onclick_code}"
        )
        assert "event.stopPropagation()" in onclick_code
        assert "handleApplyCardLink" in onclick_code


def test_linkedin_url_normalization_rules():
    """Tests the regex extraction logic for all known LinkedIn job URL and ID variations."""
    test_cases = [
        # (raw_id, raw_url, expected_id, expected_url)
        ("linkedin:4488891299", "https://www.linkedin.com/jobs/view/4488891299", "4488891299", "https://www.linkedin.com/jobs/view/4488891299"),
        ("linkedin:4480510917", "https://www.linkedin.com/jobs/view/4480510917?refId=abc&trackingId=xyz", "4480510917", "https://www.linkedin.com/jobs/view/4480510917"),
        ("linkedin:4481408789", "", "4481408789", "https://www.linkedin.com/jobs/view/4481408789"),
        ("linkedin_india:987654321", "https://linkedin.com/jobs/view/987654321", "987654321", "https://www.linkedin.com/jobs/view/987654321"),
        ("linkedin_global:11223344", "https://www.linkedin.com/jobs/view/data-engineer-11223344", "11223344", "https://www.linkedin.com/jobs/view/11223344"),
        ("custom_id", "https://www.linkedin.com/jobs/search/?currentJobId=55667788", "55667788", "https://www.linkedin.com/jobs/view/55667788"),
        ("4488891299", "#", "4488891299", "https://www.linkedin.com/jobs/view/4488891299"),
    ]

    def extract_id(raw_id: str, raw_url: str) -> str:
        s = f"{raw_id} {raw_url}"
        m = (
            re.search(r"linkedin[^:]*:(\d+)", raw_id)
            or re.search(r"/jobs/view/(?:[a-zA-Z0-9\-_]+-)?(\d+)", raw_url)
            or re.search(r"currentJobId=(\d+)", raw_url)
            or re.search(r"^(\d+)$", raw_id)
            or re.search(r"(\d{6,})", s)
        )
        return m.group(1) if m else ""

    for raw_id, raw_url, expected_id, expected_url in test_cases:
        extracted = extract_id(raw_id, raw_url)
        assert extracted == expected_id, f"Failed for id={raw_id}, url={raw_url}: got {extracted}"
        canonical = f"https://www.linkedin.com/jobs/view/{extracted}"
        assert canonical == expected_url


# =============================================================================
# 2. Dual-Environment Deep Browser Verification with Playwright
# =============================================================================

def test_static_github_pages_mode_apply_opens_linkedin_tab():
    """Verifies that in static mode (file:// or GitHub Pages without local backend),
    clicking Apply on a LinkedIn job card directly opens https://www.linkedin.com/jobs/view/<job_id>
    in a new tab (target='_blank').
    """
    assert ROOT_INDEX.exists(), "Root index.html must exist for GitHub Pages"
    file_url = ROOT_INDEX.as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Load static index.html
        page.goto(file_url, wait_until="domcontentloaded")

        # Wait for cards to render
        page.wait_for_selector(".job-card", timeout=5000)

        # Filter by platform: select LinkedIn
        page.select_option("#filter-platform", "linkedin")
        page.wait_for_timeout(300)

        linkedin_cards = page.query_selector_all(".job-card")
        assert len(linkedin_cards) >= 3, f"Expected at least 3 LinkedIn jobs in static data, found {len(linkedin_cards)}"

        for card in linkedin_cards:
            card_id = card.get_attribute("id")
            apply_link = card.query_selector(".btn-apply-link")
            assert apply_link is not None, f"Card {card_id} missing .btn-apply-link"

            href = apply_link.get_attribute("href")
            target = apply_link.get_attribute("target")

            # Must target _blank
            assert target == "_blank", f"Card {card_id} Apply button target is not _blank: {target}"

            # Must navigate directly to https://www.linkedin.com/jobs/view/<job_id>
            assert href.startswith("https://www.linkedin.com/jobs/view/"), (
                f"Card {card_id} Apply button href does not point to LinkedIn post: {href}"
            )
            job_id_num = href.replace("https://www.linkedin.com/jobs/view/", "").split("?")[0].strip("/")
            assert job_id_num.isdigit(), f"Extracted job id from href '{href}' is not numeric"

        # Click the Apply button on the first LinkedIn job and intercept new tab/popup
        first_apply_btn = linkedin_cards[0].query_selector(".btn-apply-link")
        expected_url = first_apply_btn.get_attribute("href")

        with context.expect_page() as new_page_info:
            first_apply_btn.click()

        new_tab = new_page_info.value
        assert new_tab is not None
        assert new_tab.url.startswith("https://www.linkedin.com/jobs/view/") or new_tab.url == expected_url, (
            f"New tab URL '{new_tab.url}' does not match expected LinkedIn URL '{expected_url}'"
        )
        new_tab.close()
        browser.close()


def test_local_server_mode_apply_opens_linkedin_tab(local_server):
    """Verifies that when running on local server via gui/server.py (http://127.0.0.1:PORT),
    clicking Apply on a LinkedIn job card directly opens https://www.linkedin.com/jobs/view/<job_id>
    in a new tab (target='_blank') and does NOT rely on /api/launch-browser or local apps.
    """
    seen_backup = SEEN_JSON.read_text(encoding="utf-8") if SEEN_JSON.exists() else None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Track network requests to verify /api/launch-browser is never invoked for LinkedIn Apply
            launch_browser_requests = []
            page.on("request", lambda req: launch_browser_requests.append(req.url) if "/api/launch-browser" in req.url else None)

            # Load from local server
            page.goto(f"{local_server}/", wait_until="networkidle")

            # Wait for cards to render
            page.wait_for_selector(".job-card", timeout=5000)

            # Filter by platform: select LinkedIn
            page.select_option("#filter-platform", "linkedin")
            page.wait_for_timeout(300)

            linkedin_cards = page.query_selector_all(".job-card")
            assert len(linkedin_cards) >= 3, f"Expected at least 3 LinkedIn jobs in local server mode, found {len(linkedin_cards)}"

            for card in linkedin_cards:
                card_id = card.get_attribute("id")
                apply_link = card.query_selector(".btn-apply-link")
                assert apply_link is not None, f"Card {card_id} missing .btn-apply-link"

                href = apply_link.get_attribute("href")
                target = apply_link.get_attribute("target")

                assert target == "_blank", f"Card {card_id} Apply button target is not _blank: {target}"
                assert href.startswith("https://www.linkedin.com/jobs/view/"), (
                    f"Card {card_id} Apply button href does not point to LinkedIn post: {href}"
                )

            # Click the Apply button on the first LinkedIn job and intercept new tab/popup
            first_apply_btn = linkedin_cards[0].query_selector(".btn-apply-link")
            expected_url = first_apply_btn.get_attribute("href")

            with context.expect_page() as new_page_info:
                first_apply_btn.click()

            new_tab = new_page_info.value
            assert new_tab is not None
            assert new_tab.url.startswith("https://www.linkedin.com/jobs/view/") or new_tab.url == expected_url, (
                f"New tab URL '{new_tab.url}' does not match expected LinkedIn URL '{expected_url}'"
            )
            new_tab.close()

            # Verify /api/launch-browser was not called
            assert len(launch_browser_requests) == 0, (
                f"LinkedIn Apply navigation incorrectly invoked backend endpoint /api/launch-browser: {launch_browser_requests}"
            )

            browser.close()
    finally:
        if seen_backup and SEEN_JSON.exists():
            SEEN_JSON.write_text(seen_backup, encoding="utf-8")


def test_apply_kit_modal_opens_linkedin_tab():
    """Verifies that opening the Apply Kit modal for a LinkedIn job and clicking
    its launch button directly opens https://www.linkedin.com/jobs/view/<job_id> in a new tab.
    """
    file_url = ROOT_INDEX.as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(file_url, wait_until="domcontentloaded")
        page.wait_for_selector(".job-card", timeout=5000)
        page.select_option("#filter-platform", "linkedin")
        page.wait_for_timeout(300)

        # Open Apply Kit for the first LinkedIn job
        kit_btn = page.query_selector(".btn-kit")
        assert kit_btn is not None, "Kit button not found on LinkedIn card"
        kit_btn.click()
        page.wait_for_timeout(300)

        modal = page.query_selector("#modal-apply-kit")
        assert modal is not None and "open" in (modal.get_attribute("class") or ""), "Apply Kit modal failed to open"

        launch_btn = page.query_selector("#kit-launch-btn")
        assert launch_btn is not None, "Modal launch button not found"

        with context.expect_page() as new_page_info:
            launch_btn.click()

        new_tab = new_page_info.value
        assert new_tab is not None
        assert new_tab.url.startswith("https://www.linkedin.com/jobs/view/"), (
            f"Kit modal launch did not navigate to LinkedIn post URL: {new_tab.url}"
        )
        new_tab.close()
        browser.close()


@pytest.mark.parametrize("device_name", ["iPhone 14", "Pixel 7"])
def test_mobile_emulation_apply_opens_linkedin_tab(device_name):
    """Verifies that clicking Apply on mobile device viewports (iOS Safari and Android Chrome)
    opens https://www.linkedin.com/jobs/view/<job_id> in a new tab without popup blocking.
    """
    file_url = ROOT_INDEX.as_uri()
    with sync_playwright() as p:
        device = p.devices[device_name]
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(**device)
        page = context.new_page()

        page.goto(file_url, wait_until="domcontentloaded")
        page.wait_for_selector(".job-card", timeout=5000)
        page.select_option("#filter-platform", "linkedin")
        page.wait_for_timeout(300)

        first_apply_btn = page.query_selector(".btn-apply-link")
        assert first_apply_btn is not None, f"Apply link not found for device {device_name}"
        expected_url = first_apply_btn.get_attribute("href")
        assert expected_url.startswith("https://www.linkedin.com/jobs/view/")

        with context.expect_page() as new_page_info:
            first_apply_btn.click()

        new_tab = new_page_info.value
        assert new_tab is not None
        assert new_tab.url.startswith("https://www.linkedin.com/jobs/view/") or new_tab.url == expected_url
        new_tab.close()
        browser.close()


def test_card_body_click_opens_linkedin_tab():
    """Verifies that clicking the card body (e.g. title area) of a LinkedIn job card
    opens the LinkedIn post URL directly in a new tab without invoking /api/launch-browser.
    """
    file_url = ROOT_INDEX.as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(file_url, wait_until="domcontentloaded")
        page.wait_for_selector(".job-card", timeout=5000)
        page.select_option("#filter-platform", "linkedin")
        page.wait_for_timeout(300)

        card_title = page.query_selector(".job-title")
        assert card_title is not None, "Card title not found"

        with context.expect_page() as new_page_info:
            card_title.click()

        new_tab = new_page_info.value
        assert new_tab is not None
        assert new_tab.url.startswith("https://www.linkedin.com/jobs/view/")
        new_tab.close()
        browser.close()


def test_in_browser_edge_case_job_evaluations():
    """Verifies that client-side helpers properly normalize edge-case jobs in the actual browser environment:
    - empty/missing url
    - search currentJobId url
    - slug view url with tracking parameters
    - regional in.linkedin.com url
    - urn jobPosting identifier
    """
    file_url = ROOT_INDEX.as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(file_url, wait_until="domcontentloaded")

        eval_result = page.evaluate("""() => {
            const testJobs = [
                { job_id: 'linkedin:1234567890', title: 'Job 1', url: '' },
                { job_id: 'li_custom', title: 'Job 2', url: 'https://www.linkedin.com/jobs/search/?currentJobId=9876543210' },
                { job_id: 'linkedin_india:55555555', title: 'Job 3', url: 'https://www.linkedin.com/jobs/view/data-scientist-55555555?refId=abc&trackingId=xyz' },
                { job_id: 'custom_li', title: 'Job 4', platform: 'linkedin', url: 'https://in.linkedin.com/jobs/view/1122334455/' },
                { job_id: 'urn:li:fs_normalized_jobPosting:9988776655', title: 'Job 5', canonical_source: 'linkedin', url: '#' },
            ];
            return testJobs.map(j => ({
                isLI: isLinkedInJob(j),
                postUrl: getLinkedInPostUrl(j)
            }));
        }""")

        expected_ids = ["1234567890", "9876543210", "55555555", "1122334455", "9988776655"]
        assert len(eval_result) == len(expected_ids)
        for i, res in enumerate(eval_result):
            assert res["isLI"] is True, f"Job {i+1} was not recognized as a LinkedIn job"
            assert res["postUrl"] == f"https://www.linkedin.com/jobs/view/{expected_ids[i]}", (
                f"Job {i+1} postUrl mismatch: expected 'https://www.linkedin.com/jobs/view/{expected_ids[i]}', got '{res['postUrl']}'"
            )
        browser.close()
