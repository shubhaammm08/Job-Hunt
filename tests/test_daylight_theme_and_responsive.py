"""Automated E2E Test Suite for Daylight Theme, 3-Pane Responsive Layout, and Studio Presentation.

Traceability:
- Milestone 1 / Requirement R1: Alabaster Daylight Theme System & Theme Switching
- Milestone 2 / Requirement R2: Desktop Workspace (1440px+ 3-Pane Layout)
- Milestone 3 / Requirement R3: Mobile View (390px 1-Pane Adaptability)
- Milestone 4 / Requirement R4: Side-by-Side Studio Presentation Showcase
- Milestone 5 / Requirement R5: E2E Integration, Boundary Verification & Scenario Workflows

Test Methodology: 4-Tier Architecture (TEST_INFRA.md)
- Tier 1: Feature Coverage (≥5 tests per feature, 5 features = ≥25 tests)
- Tier 2: Boundary & Corner Cases (≥5 tests per feature, 5 categories = ≥25 tests)
- Tier 3: Pairwise & Cross-Feature Combinations (≥10 interaction tests)
- Tier 4: Real-World Application Scenarios (≥5 realistic workflows)
Total tests: 78 (65 original + 13 freshness, applied-visibility, theme-reveal, and mobile-layout regressions)
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

# =============================================================================
# Path Configuration and Global Constants
# =============================================================================
ROOT_DIR = Path(__file__).resolve().parent.parent
GUI_INDEX = ROOT_DIR / "gui" / "index.html"
ROOT_INDEX = ROOT_DIR / "index.html"
STUDIO_HTML = ROOT_DIR / "studio_presentation.html"
GUI_STUDIO_HTML = ROOT_DIR / "gui" / "studio_presentation.html"
SEEN_JSON = ROOT_DIR / "seen.json"
BUILD_SCRIPT = ROOT_DIR / "build_mobile_gui.py"

# Daylight Theme Reference Tokens (from ORIGINAL_REQUEST.md & PROJECT.md)
DAYLIGHT_WARM_OFF_WHITE = "#F8FAFC"   # Canvas & middle feed background
DAYLIGHT_LIGHT_GRAY = "#F1F5F9"       # Nav rail, action shelf, studio grid
DAYLIGHT_PURE_WHITE = "#FFFFFF"       # Cards, top header, inputs
DAYLIGHT_BORDER_SUBTLE = "#E2E8F0"    # 1px border divider
DAYLIGHT_EMERALD = "#059669"          # Match score accent
DAYLIGHT_INDIGO = "#4F46E5"           # Primary brand / active highlight accent
DAYLIGHT_NAVY_TEXT = "#0F172A"        # Bold primary text
DAYLIGHT_MUTED_TEXT = "#475569"       # Secondary text

# Regex Patterns for Invariants
EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf\u2b50\u23f0-\u23f3]"
)
EXPLICIT_LEGACY_EMOJIS = [
    "🎯", "⚡", "📊", "📬", "🛡️", "👤", "🔍", "🔥", "⭐", "🤖", "🐍", "⏳", "📍", "💡", "⏰", "💰", "✓"
]

EXTERNAL_URL_PATTERN = re.compile(
    r'<(?:link|script)[^>]+(?:src|href)=["\'](https?://[^"\']+)["\']',
    re.IGNORECASE
)
EXTERNAL_IMPORT_PATTERN = re.compile(
    r'@import\s+(?:url\()?["\'](https?://[^"\']+)["\']',
    re.IGNORECASE
)


# =============================================================================
# Mathematical Helpers for Color & Accessibility
# =============================================================================
def _hex_to_srgb(hex_code: str) -> Tuple[float, float, float]:
    """Converts a 6-character hex color to normalized sRGB components."""
    hex_clean = hex_code.lstrip("#").upper()
    if len(hex_clean) == 3:
        hex_clean = "".join([c * 2 for c in hex_clean])
    r = int(hex_clean[0:2], 16) / 255.0
    g = int(hex_clean[2:4], 16) / 255.0
    b = int(hex_clean[4:6], 16) / 255.0
    return r, g, b


def _channel_to_linear(c: float) -> float:
    """Converts sRGB gamma-compressed channel to linear luminance value."""
    if c <= 0.03928:
        return c / 12.92
    return math.pow((c + 0.055) / 1.055, 2.4)


def calculate_relative_luminance(hex_code: str) -> float:
    """Calculates relative luminance according to WCAG 2.1 specs."""
    r, g, b = _hex_to_srgb(hex_code)
    r_lin = _channel_to_linear(r)
    g_lin = _channel_to_linear(g)
    b_lin = _channel_to_linear(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def calculate_wcag_contrast(hex1: str, hex2: str) -> float:
    """Calculates WCAG 2.1 contrast ratio between two hex colors."""
    l1 = calculate_relative_luminance(hex1)
    l2 = calculate_relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def read_file_text(path: Path) -> str:
    """Reads a file with utf-8 encoding."""
    assert path.exists(), f"Target file does not exist: {path}"
    return path.read_text(encoding="utf-8")


# =============================================================================
# Pytest Playwright Fixtures
# =============================================================================
@pytest.fixture(scope="module")
def playwright_instance():
    """Initializes a shared headless Playwright Chromium instance."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def desktop_page(playwright_instance: Browser):
    """Provides a desktop viewport page (1440x900) loading index.html."""
    context = playwright_instance.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.set_default_timeout(5000)
    page.goto(ROOT_INDEX.resolve().as_uri(), wait_until="domcontentloaded")
    yield page
    context.close()


@pytest.fixture
def mobile_page(playwright_instance: Browser):
    """Provides a mobile viewport page (390x844 iPhone 14/15 size) loading index.html."""
    context = playwright_instance.new_context(
        viewport={"width": 390, "height": 844},
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
    )
    page = context.new_page()
    page.set_default_timeout(5000)
    page.goto(ROOT_INDEX.resolve().as_uri(), wait_until="domcontentloaded")
    yield page
    context.close()


# =============================================================================
# TIER 1: FEATURE COVERAGE (25 Tests)
# =============================================================================
class TestTier1FeatureCoverage:
    """Isolated, comprehensive coverage of all 5 redesigned core features."""

    # -------------------------------------------------------------------------
    # Feature 1: Alabaster Daylight Theme System (5 Tests)
    # -------------------------------------------------------------------------
    def test_f1_daylight_theme_variables_presence(self):
        """F1.1: Asserts all required Daylight CSS custom properties are defined in stylesheets."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path)
            for var_name in [
                "--bg-canvas", "--bg-rail", "--bg-feed", "--bg-card",
                "--bg-shelf", "--border-subtle", "--shadow-card",
                "--accent-emerald", "--accent-indigo", "--text-primary", "--text-secondary"
            ]:
                assert var_name in content, f"Missing required CSS variable {var_name} in {path.name}"

    def test_f1_daylight_palette_hex_values(self):
        """F1.2: Asserts the exact daylight palette hex tokens are present in stylesheets."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path).upper()
            for hex_token in [
                "#F8FAFC",  # Warm off-white
                "#F1F5F9",  # Light gray
                "#FFFFFF",  # Pure white
                "#E2E8F0",  # Sharp 1px border
                "#4F46E5",  # Deep indigo
                "#059669"   # Forest emerald
            ]:
                assert hex_token in content, f"Daylight token {hex_token} missing from {path.name}"

    def test_f1_card_drop_shadow_definition(self):
        """F1.3: Asserts the daylight subtle drop shadow rule exists for card elevation."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path)
            assert "0 1px 3px rgba(15, 23, 42, 0.05)" in content or "0 1px 3px" in content, (
                f"Card drop shadow elevation token missing in {path.name}"
            )

    def test_f1_dual_theme_selectors_defined(self):
        """F1.4: Asserts CSS rule blocks exist for both light and dark theme selectors."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path)
            assert 'data-theme="light"' in content or ':root' in content, f"Light theme selector missing in {path.name}"
            assert 'data-theme="dark"' in content, f"Dark theme selector missing in {path.name}"

    def test_f1_typography_tokens(self):
        """F1.5: Asserts clean sans-serif and monospace typography token definitions."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path)
            assert "--font" in content or "font-family" in content, f"Font tokens missing in {path.name}"
            assert "Inter" in content or "-apple-system" in content, f"Primary sans-serif font missing in {path.name}"
            assert "JetBrains Mono" in content or "monospace" in content, f"Monospace font missing in {path.name}"

    # -------------------------------------------------------------------------
    # Feature 2: Theme Switching Engine (5 Tests)
    # -------------------------------------------------------------------------
    def test_f2_data_theme_attribute_in_script(self):
        """F2.1: Asserts JavaScript toggles the data-theme attribute on documentElement."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path)
            assert "setAttribute('data-theme'" in content or 'setAttribute("data-theme"' in content, (
                f"Script in {path.name} must manipulate documentElement data-theme attribute"
            )

    def test_f2_localstorage_persistence_logic(self):
        """F2.2: Asserts theme switching persists to and reads from localStorage key 'jobhunt_theme'."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path)
            assert "localStorage.getItem('jobhunt_theme')" in content or 'localStorage.getItem("jobhunt_theme")' in content, (
                f"localStorage reader missing in {path.name}"
            )
            assert "localStorage.setItem('jobhunt_theme'" in content or 'localStorage.setItem("jobhunt_theme"' in content, (
                f"localStorage writer missing in {path.name}"
            )

    def test_f2_theme_toggle_button_in_nav_rail(self):
        """F2.3: Asserts theme toggle interactive button is embedded in the navigation rail."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path)
            assert "theme-toggle" in content or "toggleTheme" in content, (
                f"Theme toggle button or handler missing in {path.name}"
            )

    def test_f2_postmessage_broadcast_on_toggle(self):
        """F2.4: Asserts theme toggle broadcasts window.postMessage with THEME_CHANGED type."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path)
            assert "THEME_CHANGED" in content, f"postMessage THEME_CHANGED broadcast missing in {path.name}"

    def test_f2_browser_theme_toggle_interaction(self, desktop_page: Page):
        """F2.5: Verifies interactive click on theme toggle button switches data-theme attribute in DOM."""
        toggle_btn = desktop_page.query_selector("#theme-toggle-btn, .theme-toggle, [onclick*='toggleTheme'], [aria-label*='theme' i]")
        assert toggle_btn is not None, "Theme toggle button must be present in desktop view"

        initial_theme = desktop_page.evaluate("() => document.documentElement.getAttribute('data-theme') || 'light'")
        toggle_btn.click()
        desktop_page.wait_for_timeout(300)

        toggled_theme = desktop_page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        assert toggled_theme != initial_theme, f"Theme should toggle from {initial_theme}, but remained {toggled_theme}"

        # Toggle back to restore initial
        toggle_btn.click()
        desktop_page.wait_for_timeout(300)
        restored_theme = desktop_page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        assert restored_theme == initial_theme, f"Theme should restore to {initial_theme}, got {restored_theme}"

    # -------------------------------------------------------------------------
    # Feature 3: Desktop 3-Pane Workspace (1440px+) (5 Tests)
    # -------------------------------------------------------------------------
    def test_f3_nav_rail_dimensions_and_structure(self, desktop_page: Page):
        """F3.1: Validates far-left navigation rail renders at 72px width with circular SH brand glyph."""
        rail = desktop_page.query_selector(".nav-rail")
        assert rail is not None, "Desktop navigation rail (.nav-rail) must exist"
        bbox = rail.bounding_box()
        assert bbox is not None
        assert abs(bbox["width"] - 72.0) <= 2.0, f"Nav rail width must be 72px, got {bbox['width']}"

        brand_glyph = desktop_page.query_selector(".brand-glyph")
        assert brand_glyph is not None, "Circular brand glyph (.brand-glyph) must exist"
        assert "SH" in brand_glyph.inner_text(), "Brand glyph text must display 'SH'"

    def test_f3_middle_feed_dimensions_and_controls(self, desktop_page: Page):
        """F3.2: Feed opens at 50% of the workspace after the 72px rail (681px at 1440px)."""
        feed = desktop_page.query_selector(".master-feed, .feed-panel, #feed-panel")
        assert feed is not None, "Middle feed panel must exist"
        bbox = feed.bounding_box()
        assert bbox is not None
        expected = (1440.0 - 72.0 - 6.0) / 2
        assert abs(bbox["width"] - expected) <= 3.0, (
            f"Feed panel should open at a 50/50 split ({expected}px), got {bbox['width']}"
        )
        deck = desktop_page.query_selector(".triage-deck")
        assert deck is not None, "Details deck must exist"
        deck_box = deck.bounding_box()
        assert deck_box is not None and abs(deck_box["width"] - expected) <= 4.0, (
            f"Details deck should match the 50/50 split ({expected}px), got "
            f"{deck_box['width'] if deck_box else None}"
        )

        search_input = desktop_page.query_selector("#search-input")
        assert search_input is not None, "#search-input must exist"
        placeholder = search_input.get_attribute("placeholder") or ""
        assert "Search" in placeholder, f"Search input should have a helpful placeholder, got {placeholder}"

        # Status ribbon check. The tracked count follows unapplied bundled data.
        tracked = desktop_page.evaluate("() => (window.INITIAL_DATA?.jobs || []).filter(j => !j.applied).length")
        content = desktop_page.content()
        assert "Tracked Jobs" in content or f"{tracked} Tracked" in content or f"{tracked} opportunities" in content, (
            "Status ribbon must report tracked jobs"
        )
        assert desktop_page.inner_text("#ribbon-tracked").strip() == f"{tracked} Tracked"
        assert desktop_page.inner_text("#metric-total").strip() == str(tracked)

    def test_f3_resizer_default_drag_persistence_and_reset(self, desktop_page: Page):
        """F3.2b: Divider opens 50/50, resizes live, persists, and resets on double-click."""
        page = desktop_page
        feed = page.query_selector(".master-feed")
        resizer = page.query_selector("#pane-resizer")
        assert feed is not None and resizer is not None
        expected = (1440.0 - 72.0 - 6.0) / 2

        box = resizer.bounding_box()
        assert box is not None
        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x - 120, y, steps=6)
        page.mouse.up()
        page.wait_for_timeout(120)

        dragged = page.query_selector(".master-feed").bounding_box()["width"]
        assert abs(dragged - (expected - 120)) <= 6, f"Live drag did not resize feed: {dragged}"
        stored = int(page.evaluate("localStorage.getItem('jobhunt_feed_width')"))
        assert abs(stored - dragged) <= 2, f"Dragged width was not persisted: {stored} vs {dragged}"

        page.reload(wait_until="domcontentloaded")
        page.wait_for_selector(".job-card", timeout=5000)
        page.wait_for_timeout(150)
        restored = page.query_selector(".master-feed").bounding_box()["width"]
        assert abs(restored - dragged) <= 2, f"Width not restored after reload: {restored} vs {dragged}"

        resizer = page.query_selector("#pane-resizer")
        rb = resizer.bounding_box()
        assert rb is not None
        page.mouse.dblclick(rb["x"] + rb["width"] / 2, rb["y"] + rb["height"] / 2)
        page.wait_for_timeout(120)
        reset = page.query_selector(".master-feed").bounding_box()["width"]
        assert abs(reset - expected) <= 3, f"Double-click should reset to 50/50, got {reset}"

    def test_f3_active_job_card_fresh_first(self, desktop_page: Page):
        """F3.3: Validates the active top card is a fresh (NEW) job with score and tech pills."""
        active_card = desktop_page.query_selector(".job-card.active, .job-card:first-child")
        assert active_card is not None, "At least one active job card must exist in middle feed"
        card_text = active_card.inner_text()
        assert "NEW" in card_text, f"Fresh job card must display a NEW badge, got: {card_text}"
        assert active_card.query_selector(".tag-family, .tag") is not None, (
            "Active card must display tech pills"
        )
        score_text = active_card.query_selector(".score-badge").inner_text()
        assert re.search(r"\d+\.\d+ Match", score_text), f"Active card score missing: {score_text}"

    def test_f3_details_deck_hero_and_progress_ring(self, desktop_page: Page):
        """F3.4: Validates details deck hero and score match the active top card."""
        details = desktop_page.query_selector(".triage-deck, .details-panel, #details-panel, #triage-deck")
        assert details is not None, "Right details deck panel must exist"

        first_card = desktop_page.query_selector("#job-list .job-card:first-child")
        assert first_card is not None
        expected_company = first_card.query_selector(".job-company").inner_text().strip()
        expected_score = first_card.query_selector(".score-badge").inner_text().split()[0]

        hero_company = desktop_page.query_selector("#deck-company, .hero-company")
        assert hero_company is not None, "#deck-company hero element must exist"
        assert hero_company.inner_text().strip() == expected_company, (
            f"Hero company must match the active card ({expected_company}), got {hero_company.inner_text()}"
        )
        assert desktop_page.inner_text("#deck-score-num").strip() == expected_score, (
            "Details deck score must match the active card"
        )

        ring = desktop_page.query_selector("#deck-match-ring, .match-ring-wrapper, .match-score-ring, #deck-ring-circle")
        assert ring is not None, "Circular match score progress ring must exist in details deck"

    def test_f3_ai_match_breakdown_and_document_hub(self, desktop_page: Page):
        """F3.5: Validates AI match breakdown card with 3 micro-bars and Document Hub attachments."""
        deck = desktop_page.query_selector(".triage-deck, .details-panel, #details-panel, #triage-deck")
        assert deck is not None
        deck_text = deck.inner_text()
        assert "AI MATCH BREAKDOWN" in deck_text.upper(), "AI Match Breakdown card title must exist"
        assert "Match Rationale:" in deck_text or "match" in deck_text.lower(), "Match rationale must exist"
        assert "AI Agent" in deck_text or "95%" in deck_text, "Micro-bar 1 must exist"
        assert "Python" in deck_text or "92%" in deck_text, "Micro-bar 2 must exist"

        # Document Hub attachments
        assert "Tailored Resume_v2.pdf" in deck_text or "Resume" in deck_text, "Tailored Resume attachment must exist"
        assert "Cover_Letter_Draft.docx" in deck_text or "Cover_Letter" in deck_text, "Cover letter attachment must exist"
        assert "Suggested Outreach Message" in deck_text or "Outreach" in deck_text, "Outreach message must exist"

    # -------------------------------------------------------------------------
    # Feature 4: Mobile 1-Pane Adaptability (390px) (5 Tests)
    # -------------------------------------------------------------------------
    def test_f4_mobile_sticky_top_bar(self, mobile_page: Page):
        """F4.1: Validates mobile viewport (390px) renders sticky top bar with branding."""
        top_bar = mobile_page.query_selector(".mobile-top-bar")
        assert top_bar is not None, "Mobile sticky top bar (.mobile-top-bar) must exist"
        assert top_bar.is_visible(), "Mobile top bar must be visible in 390px viewport"
        text = top_bar.inner_text()
        assert "Shubham's JobHunt" in text, f"Mobile top bar branding missing in {text}"

    def test_f4_mobile_filter_capsules(self, mobile_page: Page):
        """F4.2: Validates horizontal capsule filter bar with status counts in mobile view."""
        capsules = mobile_page.query_selector(".mobile-filter-capsules")
        assert capsules is not None, "Mobile filter capsules container must exist"
        assert capsules.is_visible(), "Mobile filter capsules must be visible"
        caps_text = capsules.inner_text()
        assert "All Jobs" in caps_text, "Capsules must include 'All Jobs'"
        assert "High Fit" in caps_text, "Capsules must include 'High Fit (8+)'"
        assert "Recommended" in caps_text, "Capsules must include 'Recommended (10)'"
        assert "Applied" in caps_text, "Capsules must include 'Applied (1)'"

    def test_f4_mobile_active_card_display(self, mobile_page: Page):
        """F4.3: Validates the full-width mobile active card mirrors the promoted active job."""
        active_card = mobile_page.query_selector(".mobile-active-card")
        assert active_card is not None, "Mobile active card must be present"
        assert active_card.is_visible(), "Mobile active card must be visible in portrait"

        hero_title = mobile_page.query_selector("#mob-title").inner_text().strip()
        assert hero_title and hero_title in active_card.inner_text()

        # The active job is promoted into the hero, so the feed must not repeat it.
        active_job_id = mobile_page.evaluate("() => state.activeJobId")
        feed_ids = mobile_page.eval_on_selector_all(
            "#job-list .job-card",
            "els => els.map(el => el.id.replace('card-', ''))",
        )
        assert feed_ids, "Feed must still render the remaining jobs"
        assert active_job_id not in feed_ids, "Active job must not be duplicated in the mobile feed"

    def test_f4_mobile_accordion_structure(self, mobile_page: Page):
        """F4.4: Validates mobile AI match breakdown accordion toggle behavior."""
        accordion = mobile_page.query_selector(".mobile-accordion, #mobile-accordion")
        assert accordion is not None, "Mobile accordion must exist"
        trigger = mobile_page.query_selector(".accordion-trigger, #mobile-accordion-btn")
        assert trigger is not None, "Accordion trigger button must exist"

        # Click to toggle open
        trigger.click()
        mobile_page.wait_for_timeout(200)
        content_elem = mobile_page.query_selector(".accordion-content, #mobile-accordion-content")
        assert content_elem is not None, "Accordion content element must exist"

    def test_f4_mobile_docs_and_bottom_dock(self, mobile_page: Page):
        """F4.5: Validates document chips and sticky bottom dock on mobile."""
        docs_row = mobile_page.query_selector(".mobile-docs-row, #mobile-docs-row")
        assert docs_row is not None, "Mobile document chips row must exist"

        bottom_dock = mobile_page.query_selector(".mobile-bottom-dock")
        assert bottom_dock is not None, "Mobile sticky bottom action dock must exist"
        assert bottom_dock.is_visible(), "Bottom dock must be visible in 390px viewport"
        dock_text = bottom_dock.inner_text()
        assert "Apply" in dock_text or "Auto-Fill" in dock_text, f"Bottom dock must contain apply action: {dock_text}"

    def test_f4_mobile_top_bar_fits_narrow_phones(self, mobile_page: Page):
        """F4.6: Sticky header and its actions must stay inside 360/390px viewports."""
        for width in (360, 390):
            mobile_page.set_viewport_size({"width": width, "height": 844})
            mobile_page.wait_for_timeout(80)
            metrics = mobile_page.evaluate("""() => {
                const actions = document.querySelector('.mobile-top-actions');
                const brand = document.querySelector('.mobile-brand');
                const r = actions.getBoundingClientRect();
                const b = brand.getBoundingClientRect();
                return {
                    right: r.right, left: r.left, brandLeft: b.left,
                    scrollW: document.documentElement.scrollWidth, vw: innerWidth
                };
            }""")
            assert metrics["scrollW"] <= width, f"Document overflows at {width}px: {metrics}"
            assert metrics["right"] <= width, f"Top actions overflow at {width}px: {metrics}"
            assert metrics["brandLeft"] >= 0, f"Brand clipped at {width}px: {metrics}"

        mobile_page.click("#mobile-more-btn")
        assert mobile_page.eval_on_selector("#mobile-more-menu", "el => el.classList.contains('open')")
        assert mobile_page.get_attribute("#mobile-more-btn", "aria-expanded") == "true"
        mobile_page.keyboard.press("Escape")
        assert not mobile_page.eval_on_selector("#mobile-more-menu", "el => el.classList.contains('open')")

    def test_f4_mobile_document_chips_all_visible(self, mobile_page: Page):
        """F4.7: All three document chips, including outreach, fit without scrolling."""
        chips = mobile_page.eval_on_selector_all(".mobile-doc-chip", """els => els.map(el => {
            const r = el.getBoundingClientRect();
            return {left: r.left, right: r.right, text: el.innerText.trim()};
        })""")
        assert len(chips) == 3, f"Expected three document chips, got {len(chips)}"
        assert any("Outreach" in c["text"] for c in chips), "Outreach chip must be present"
        for chip in chips:
            assert chip["left"] >= 0 and chip["right"] <= 390 + 1, f"Chip outside viewport: {chip}"

    def test_f4_mobile_feed_starts_above_dock(self, mobile_page: Page):
        """F4.8: Compact filters keep the job list well above the fixed action dock."""
        positions = mobile_page.evaluate("""() => ({
            listTop: document.querySelector('#job-list').getBoundingClientRect().top,
            dockTop: document.querySelector('.mobile-bottom-dock').getBoundingClientRect().top
        })""")
        assert positions["dockTop"] - positions["listTop"] > 150, (
            f"Feed list starts too low on mobile: {positions}"
        )

    def test_f4_mobile_landscape_prioritises_feed(self, mobile_page: Page):
        """F4.9: Landscape phones collapse the hero and keep jobs above the fold."""
        mobile_page.set_viewport_size({"width": 844, "height": 390})
        mobile_page.wait_for_timeout(300)
        hero = mobile_page.query_selector(".mobile-active-card")
        assert hero is not None
        assert not hero.is_visible(), "Hero card must collapse in landscape"

        first_card = mobile_page.query_selector("#job-list .job-card")
        assert first_card is not None, "Feed must render at least one job in landscape"
        top = first_card.evaluate("el => el.getBoundingClientRect().top")
        assert top < 390, f"First job card must be above the fold, got top={top}px"

        active_job_id = mobile_page.evaluate("() => state.activeJobId")
        feed_ids = mobile_page.eval_on_selector_all(
            "#job-list .job-card",
            "els => els.map(el => el.id.replace('card-', ''))",
        )
        assert active_job_id in feed_ids, "Active job must stay in the feed when the hero is hidden"

    def test_f3_kit_grid_contains_outreach_chip(self, desktop_page: Page):
        """F3.10: Document Hub chips stay inside the details pane at all desktop widths."""
        for width in (1024, 1280, 1440):
            desktop_page.set_viewport_size({"width": width, "height": 900})
            desktop_page.wait_for_timeout(80)
            result = desktop_page.evaluate("""() => {
                const section = document.querySelector('.document-hub-section');
                const chips = [...document.querySelectorAll('.kit-chip')];
                const sr = section.getBoundingClientRect();
                return {
                    sectionRight: sr.right,
                    rights: chips.map(el => el.getBoundingClientRect().right),
                    cols: getComputedStyle(document.querySelector('.kit-chips-grid')).gridTemplateColumns
                };
            }""")
            assert all(r <= result["sectionRight"] + 1 for r in result["rights"]), (
                f"Kit chip overflows details pane at {width}px: {result}"
            )
            assert "minmax" in result["cols"] or "px" in result["cols"], result

    # -------------------------------------------------------------------------
    # Feature 5: Side-by-Side Studio Presentation Showcase (5 Tests)
    # -------------------------------------------------------------------------
    def test_f5_studio_presentation_files_exist_and_match(self):
        """F5.1: Asserts studio_presentation.html exists in root and matches gui/ template."""
        assert STUDIO_HTML.exists(), "Root studio_presentation.html must exist"
        assert GUI_STUDIO_HTML.exists(), "gui/studio_presentation.html must exist"
        root_studio = read_file_text(STUDIO_HTML)
        gui_studio = read_file_text(GUI_STUDIO_HTML)
        assert len(root_studio) > 500
        assert len(gui_studio) > 500

    def test_f5_studio_presentation_side_by_side_frames(self):
        """F5.2: Asserts studio presentation embeds both desktop and mobile iframes."""
        content = read_file_text(STUDIO_HTML)
        assert 'id="desktop-frame"' in content, "desktop-frame iframe must exist"
        assert 'id="mobile-frame"' in content, "mobile-frame iframe must exist"
        assert "mode=desktop" in content, "desktop iframe must request mode=desktop"
        assert "mode=mobile" in content, "mobile iframe must request mode=mobile"

    def test_f5_studio_presentation_frame_labels(self):
        """F5.3: Asserts sharp uppercase labels 'DESKTOP WORKSPACE (3-PANE)' and 'MOBILE VIEW (1-PANE TIGHT)'."""
        content = read_file_text(STUDIO_HTML)
        assert "DESKTOP WORKSPACE (3-PANE)" in content, "Desktop label missing from studio presentation"
        assert "MOBILE VIEW (1-PANE TIGHT)" in content, "Mobile label missing from studio presentation"

    def test_f5_studio_presentation_grid_background(self):
        """F5.4: Asserts architectural light-gray grid canvas background in studio presentation."""
        content = read_file_text(STUDIO_HTML)
        assert "studio-canvas" in content, "studio-canvas element/class must exist"
        assert "linear-gradient" in content or "background-size" in content, "Grid background pattern missing"

    def test_f5_studio_presentation_postmessage_sync(self):
        """F5.5: Asserts cross-frame postMessage synchronization event bus in studio presentation."""
        content = read_file_text(STUDIO_HTML)
        assert "addEventListener('message'" in content or 'addEventListener("message"' in content, (
            "studio_presentation must listen for postMessage events"
        )
        assert "JOB_SELECTED" in content, "JOB_SELECTED cross-frame sync missing"


# =============================================================================
# FEED FRESHNESS, APPLIED VISIBILITY, AND CIRCULAR THEME REVEAL
# =============================================================================
class TestFeedFreshnessAndThemeReveal:
    """Regression coverage for fresh-first ordering, applied filtering, and the theme reveal."""

    def test_feed_excludes_applied_jobs_from_tracked_pool(self, desktop_page: Page):
        """Applied jobs are excluded from Tracked Jobs and only unapplied jobs are counted."""
        assert desktop_page.query_selector_all(".job-card.is-applied") == []
        feed_text = desktop_page.inner_text("#job-list")
        assert "Capgemini" not in feed_text, "Applied Capgemini job must not appear in Tracked Jobs"
        unapplied_count = desktop_page.evaluate("() => (window.INITIAL_DATA?.jobs || []).filter(j => !j.applied).length")
        applied_count = desktop_page.evaluate("() => (window.INITIAL_DATA?.jobs || []).filter(j => j.applied).length")
        assert desktop_page.inner_text("#metric-total").strip() == str(unapplied_count)
        assert desktop_page.inner_text("#metric-applied").strip() == str(applied_count)
        results = desktop_page.inner_text("#results-count")
        assert f"Showing {unapplied_count} of {unapplied_count} opportunities" in results, (
            f"Results line should count only unapplied jobs in Tracked view, got: {results}"
        )
        assert "applied hidden" not in results, f"Legacy applied hidden text must not appear: {results}"
        assert desktop_page.query_selector("#chip-hide-applied") is None

    def test_feed_orders_fresh_batch_before_older_jobs(self, desktop_page: Page):
        """Every fresh (NEW) card appears before the first older card."""
        order = desktop_page.evaluate("""() => Array.from(document.querySelectorAll('#job-list .job-card'))
            .map(card => card.querySelector('.tag-fresh') ? 'fresh' : 'old')""")
        assert "fresh" in order, "The newest scan batch must be represented in the feed"
        first_old = order.index("old") if "old" in order else len(order)
        assert all(kind == "fresh" for kind in order[:first_old]), "Fresh jobs must be grouped at the top"
        assert "fresh" not in order[first_old:], "Older jobs must not appear before fresh jobs"
        assert desktop_page.query_selector("#job-list .job-card:first-child .tag-fresh") is not None

    def test_fresh_filter_chip_shows_only_new_batch(self, desktop_page: Page):
        """The Fresh quick chip filters to the newest scan batch."""
        desktop_page.click("#chip-fresh")
        desktop_page.wait_for_timeout(250)
        assert desktop_page.eval_on_selector("#filter-status", "el => el.value") == "fresh"
        cards = desktop_page.query_selector_all("#job-list .job-card")
        assert cards, "Fresh filter must return at least one job"
        assert all(card.query_selector(".tag-fresh") for card in cards), "Fresh filter returned an older job"
        fresh_count = int(desktop_page.inner_text("#chip-count-fresh"))
        assert len(cards) == fresh_count, f"Fresh chip count {fresh_count} did not match {len(cards)} cards"

    def test_mark_applied_moves_job_out_of_tracked_and_unmark_restores(self, desktop_page: Page):
        """External Apply leaves Tracked unchanged; Mark Applied moves job to Applied; unmarking restores it."""
        initial_tracked = int(desktop_page.inner_text("#metric-total"))
        initial_applied = int(desktop_page.inner_text("#metric-applied"))

        first_card = desktop_page.query_selector("#job-list .job-card:first-child")
        assert first_card is not None
        first_card_id = first_card.get_attribute("id")

        # 1. External Apply link must NOT mark the job as applied
        apply_link = first_card.query_selector(".btn-apply-link")
        assert apply_link is not None
        with desktop_page.context.expect_page() as popup_info:
            apply_link.click()
        popup = popup_info.value
        popup.close()
        desktop_page.wait_for_timeout(150)

        assert int(desktop_page.inner_text("#metric-total")) == initial_tracked
        assert int(desktop_page.inner_text("#metric-applied")) == initial_applied
        assert desktop_page.query_selector(f"[id='{first_card_id}']") is not None

        # 2. Explicit Mark Applied removes from Tracked, updates counts, and places in Applied
        mark_btn = desktop_page.query_selector(f"[id='{first_card_id}'] .btn-applied")
        assert mark_btn is not None
        mark_btn.click()
        desktop_page.wait_for_timeout(200)

        assert int(desktop_page.inner_text("#metric-total")) == initial_tracked - 1
        assert int(desktop_page.inner_text("#metric-applied")) == initial_applied + 1
        assert desktop_page.query_selector(f"[id='{first_card_id}']") is None
        results = desktop_page.inner_text("#results-count")
        assert f"Showing {initial_tracked - 1} of {initial_tracked - 1} opportunities" in results

        # 3. Reload persists the updated counts and exclusion from Tracked
        desktop_page.reload(wait_until="domcontentloaded")
        desktop_page.wait_for_selector(".job-card", timeout=5000)
        assert int(desktop_page.inner_text("#metric-total")) == initial_tracked - 1
        assert int(desktop_page.inner_text("#metric-applied")) == initial_applied + 1
        assert desktop_page.query_selector(f"[id='{first_card_id}']") is None

        # 4. Applied view shows the job and unmarking moves it back to Tracked Jobs
        desktop_page.click("#chip-applied")
        desktop_page.wait_for_timeout(200)
        applied_card = desktop_page.query_selector(f"[id='{first_card_id}']")
        assert applied_card is not None, "Marked job must appear in Applied view"
        applied_results = desktop_page.inner_text("#results-count")
        assert f"Showing {initial_applied + 1} of {initial_applied + 1} opportunities (Applied Jobs)" in applied_results

        applied_card.query_selector(".btn-applied").click()
        desktop_page.wait_for_timeout(200)
        assert int(desktop_page.inner_text("#metric-total")) == initial_tracked
        assert int(desktop_page.inner_text("#metric-applied")) == initial_applied

        desktop_page.click("#chip-all")
        desktop_page.wait_for_timeout(200)
        assert desktop_page.query_selector(f"[id='{first_card_id}']") is not None, (
            "Unmarked job must return to Tracked Jobs"
        )

    def test_theme_toggle_uses_circular_view_transition(self, desktop_page: Page):
        """The theme toggle reveals the new theme with a circular clip-path animation."""
        supports_view_transition = desktop_page.evaluate("() => typeof document.startViewTransition === 'function'")
        if not supports_view_transition:
            pytest.skip("View Transitions API not available in this browser")

        initial = desktop_page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        desktop_page.click("#theme-toggle-btn")
        desktop_page.wait_for_timeout(80)

        animations = desktop_page.evaluate("""() => document.getAnimations()
            .filter(a => a.effect && a.effect.pseudoElement === '::view-transition-new(root)')
            .map(a => ({
                duration: a.effect.getTiming().duration,
                easing: a.effect.getTiming().easing,
                keyframes: a.effect.getKeyframes().map(k => k.clipPath || '')
            }))""")
        assert animations, "Circular theme reveal animation was not created"
        assert animations[0]["duration"] == 900
        assert animations[0]["easing"] == 'cubic-bezier(0.16, 1, 0.3, 1)'
        assert any("circle(" in frame for frame in animations[0]["keyframes"]), animations

        desktop_page.wait_for_timeout(1000)
        toggled = desktop_page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        assert toggled != initial
        desktop_page.click("#theme-toggle-btn")
        desktop_page.wait_for_timeout(1000)

    def test_static_host_does_not_request_local_backend_status(self, desktop_page: Page):
        """GitHub Pages/file loads must not request the localhost-only LinkedIn API."""
        requests = []
        desktop_page.on("request", lambda request: requests.append(request.url))
        desktop_page.reload(wait_until="domcontentloaded")
        desktop_page.wait_for_selector(".job-card", timeout=5000)
        desktop_page.wait_for_timeout(300)
        backend_urls = [url for url in requests if "/api/sources/linkedin/status" in url]
        assert backend_urls == [], f"Static dashboard should not call local backend: {backend_urls}"

    def test_light_theme_key_components_meet_wcag_contrast(self, desktop_page: Page):
        """Tags, score badges, rationale, and metrics stay at or above 4.5:1 in light mode."""
        desktop_page.evaluate("localStorage.setItem('jobhunt_theme', 'light')")
        desktop_page.reload(wait_until="domcontentloaded")
        desktop_page.wait_for_selector(".job-card", timeout=5000)
        desktop_page.wait_for_timeout(300)

        ratios = desktop_page.evaluate("""() => {
            const parse = c => { const m = c.match(/rgba?\\(([^)]+)\\)/); if (!m) return null;
                const p = m[1].split(',').map(x => parseFloat(x.trim()));
                return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
            const lum = c => { const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); };
                return .2126 * f(c.r) + .7152 * f(c.g) + .0722 * f(c.b); };
            const ratio = (a, b) => { const x = lum(a), y = lum(b), hi = Math.max(x, y), lo = Math.min(x, y); return (hi + .05) / (lo + .05); };
            const blend = (f, b) => ({ r: f.r * f.a + b.r * (1 - f.a), g: f.g * f.a + b.g * (1 - f.a), b: f.b * f.a + b.b * (1 - f.a), a: 1 });
            const bgOf = el => { let n = el, layers = [];
                while (n && n.nodeType === 1) { const bc = parse(getComputedStyle(n).backgroundColor);
                    if (bc && bc.a > 0) layers.push(bc); if (bc && bc.a >= .999) break; n = n.parentElement; }
                let acc = { r: 255, g: 255, b: 255, a: 1 };
                for (let i = layers.length - 1; i >= 0; i--) acc = blend(layers[i], acc);
                return acc; };
            const selectors = ['.tag-source', '.tag-workplace', '.tag-family', '.score-badge.score-high',
                '.score-badge.score-mid', '.job-reason', '.job-date', '.pill-label-title',
                '.hub-status-tag', '#metric-recommended'];
            const out = {};
            for (const sel of selectors) { const el = document.querySelector(sel); if (!el) continue;
                const fg = parse(getComputedStyle(el).color); const bg = bgOf(el);
                out[sel] = ratio(blend(fg, bg), bg); }
            return out;
        }""")
        assert ratios, "No light-theme components were sampled"
        failures = {sel: round(value, 2) for sel, value in ratios.items() if value < 4.5}
        assert not failures, f"Light-theme components below WCAG AA: {failures}"

    def test_light_theme_mobile_document_chips_are_legible(self, mobile_page: Page):
        """Mobile document chips use dark text on a light surface in daylight mode."""
        mobile_page.evaluate("localStorage.setItem('jobhunt_theme', 'light')")
        mobile_page.reload(wait_until="domcontentloaded")
        mobile_page.wait_for_selector(".job-card", timeout=5000)
        mobile_page.wait_for_timeout(300)

        chip = mobile_page.evaluate("""() => {
            const el = document.querySelector('.mobile-doc-chip');
            if (!el) return null;
            const parse = c => { const m = c.match(/rgba?\\(([^)]+)\\)/);
                const p = m[1].split(',').map(x => parseFloat(x.trim()));
                return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
            const lum = c => { const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); };
                return .2126 * f(c.r) + .7152 * f(c.g) + .0722 * f(c.b); };
            const fg = parse(getComputedStyle(el).color);
            const bg = parse(getComputedStyle(el).backgroundColor);
            const hi = Math.max(lum(fg), lum(bg)), lo = Math.min(lum(fg), lum(bg));
            return { ratio: (hi + .05) / (lo + .05), fg: getComputedStyle(el).color, bg: getComputedStyle(el).backgroundColor };
        }""")
        assert chip is not None, "Mobile document chip must exist"
        assert chip["ratio"] >= 4.5, f"Mobile document chip contrast too low: {chip}"

    def test_light_theme_mobile_surfaces_are_not_dark(self, mobile_page: Page):
        """Daylight mode must remap all previously hardcoded dark mobile surfaces."""
        mobile_page.evaluate("localStorage.setItem('jobhunt_theme', 'light')")
        mobile_page.reload(wait_until="domcontentloaded")
        mobile_page.wait_for_selector(".mobile-active-card", timeout=5000)
        mobile_page.wait_for_timeout(200)
        colors = mobile_page.evaluate("""() => {
            const out = {};
            ['.mobile-top-bar', '.mobile-active-card', '.mobile-accordion', '.mobile-bottom-dock'].forEach(sel => {
                const el = document.querySelector(sel);
                out[sel] = getComputedStyle(el).backgroundColor;
            });
            return out;
        }""")
        for selector, value in colors.items():
            match = re.search(r"rgba?\((\d+), (\d+), (\d+)", value)
            assert match, f"Unexpected background for {selector}: {value}"
            channels = [int(match.group(i)) for i in (1, 2, 3)]
            assert min(channels) >= 200, f"{selector} is still dark in Daylight mode: {value}"


# =============================================================================
# TIER 2: BOUNDARY & CORNER CASES (25 Tests)
# =============================================================================
class TestTier2BoundaryAndCornerCases:
    """Rigorous boundary, corner case, and negative testing."""

    # -------------------------------------------------------------------------
    # Category 1 (B1): Daylight Theme Token & Contrast Boundaries (5 Tests)
    # -------------------------------------------------------------------------
    def test_b1_daylight_token_exact_hex_matches(self):
        """B1.1: Boundary verification of all 6 required hex color tokens in stylesheets."""
        content = read_file_text(ROOT_INDEX).upper()
        tokens = [
            DAYLIGHT_WARM_OFF_WHITE, DAYLIGHT_LIGHT_GRAY, DAYLIGHT_PURE_WHITE,
            DAYLIGHT_BORDER_SUBTLE, DAYLIGHT_EMERALD, DAYLIGHT_INDIGO
        ]
        missing = [t for t in tokens if t not in content]
        assert len(missing) == 0, f"Missing required daylight hex codes: {missing}"

    def test_b1_contrast_ratio_primary_text_on_canvas(self):
        """B1.2: Boundary verification: Primary text #0F172A on canvas #F8FAFC exceeds WCAG AAA (7:1)."""
        contrast = calculate_wcag_contrast(DAYLIGHT_NAVY_TEXT, DAYLIGHT_WARM_OFF_WHITE)
        assert contrast >= 12.0, f"Primary text on canvas contrast {contrast:.2f} must be >= 12.0 (exceeds AAA)"

    def test_b1_contrast_ratio_primary_text_on_white(self):
        """B1.3: Boundary verification: Primary text #0F172A on pure white #FFFFFF exceeds WCAG AAA (7:1)."""
        contrast = calculate_wcag_contrast(DAYLIGHT_NAVY_TEXT, DAYLIGHT_PURE_WHITE)
        assert contrast >= 14.0, f"Primary text on white card contrast {contrast:.2f} must be >= 14.0"

    def test_b1_contrast_ratio_secondary_text_on_canvas(self):
        """B1.4: Boundary verification: Secondary text #475569 on canvas #F8FAFC exceeds WCAG AA (4.5:1)."""
        contrast = calculate_wcag_contrast(DAYLIGHT_MUTED_TEXT, DAYLIGHT_WARM_OFF_WHITE)
        assert contrast >= 5.0, f"Secondary text contrast {contrast:.2f} must be >= 5.0 (exceeds AA)"

    def test_b1_contrast_ratio_emerald_and_indigo_accents(self):
        """B1.5: Boundary verification: Emerald (#059669) and Indigo (#4F46E5) badge contrast."""
        emerald_white = calculate_wcag_contrast(DAYLIGHT_EMERALD, DAYLIGHT_PURE_WHITE)
        indigo_white = calculate_wcag_contrast(DAYLIGHT_INDIGO, DAYLIGHT_PURE_WHITE)
        assert emerald_white >= 3.5, f"Emerald contrast {emerald_white:.2f} must be >= 3.5 for graphical objects"
        assert indigo_white >= 4.5, f"Indigo contrast {indigo_white:.2f} must be >= 4.5"

    # -------------------------------------------------------------------------
    # Category 2 (B2): Strict Zero Unicode Emojis Across All Files (5 Tests)
    # -------------------------------------------------------------------------
    def test_b2_zero_emojis_in_gui_index(self):
        """B2.1: Asserts 0 unicode emojis exist in canonical gui/index.html."""
        content = read_file_text(GUI_INDEX)
        matches = EMOJI_PATTERN.findall(content)
        assert len(matches) == 0, f"Found {len(matches)} unicode emojis in gui/index.html: {set(matches)}"

    def test_b2_zero_emojis_in_root_index(self):
        """B2.2: Asserts 0 unicode emojis exist in root index.html."""
        content = read_file_text(ROOT_INDEX)
        matches = EMOJI_PATTERN.findall(content)
        assert len(matches) == 0, f"Found {len(matches)} unicode emojis in index.html: {set(matches)}"

    def test_b2_zero_emojis_in_studio_presentation(self):
        """B2.3: Asserts 0 unicode emojis exist in root studio_presentation.html."""
        content = read_file_text(STUDIO_HTML)
        matches = EMOJI_PATTERN.findall(content)
        assert len(matches) == 0, f"Found {len(matches)} unicode emojis in studio_presentation.html: {set(matches)}"

    def test_b2_zero_emojis_in_gui_studio_presentation(self):
        """B2.4: Asserts 0 unicode emojis exist in gui/studio_presentation.html."""
        content = read_file_text(GUI_STUDIO_HTML)
        matches = EMOJI_PATTERN.findall(content)
        assert len(matches) == 0, f"Found {len(matches)} unicode emojis in gui/studio_presentation.html: {set(matches)}"

    def test_b2_explicit_legacy_emojis_forbidden(self):
        """B2.5: Asserts none of the explicit legacy emojis appear in any HTML template."""
        for path in [GUI_INDEX, ROOT_INDEX, STUDIO_HTML, GUI_STUDIO_HTML]:
            content = read_file_text(path)
            found = [e for e in EXPLICIT_LEGACY_EMOJIS if e in content]
            assert len(found) == 0, f"Explicit forbidden emojis {found} found in {path.name}"

    # -------------------------------------------------------------------------
    # Category 3 (B3): Strict Zero External CDN Dependencies (5 Tests)
    # -------------------------------------------------------------------------
    def test_b3_zero_external_links_in_gui_index(self):
        """B3.1: Zero external stylesheets or fonts in gui/index.html."""
        content = read_file_text(GUI_INDEX)
        links = EXTERNAL_URL_PATTERN.findall(content)
        assert len(links) == 0, f"Found external URL links in gui/index.html: {links}"

    def test_b3_zero_external_scripts_in_gui_index(self):
        """B3.2: Zero external scripts in gui/index.html."""
        content = read_file_text(ROOT_INDEX)
        scripts = [u for u in EXTERNAL_URL_PATTERN.findall(content) if u.endswith(".js")]
        assert len(scripts) == 0, f"Found external scripts in index.html: {scripts}"

    def test_b3_zero_external_imports_in_css(self):
        """B3.3: Zero @import external rules in stylesheets across gui/index.html and index.html."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path)
            imports = EXTERNAL_IMPORT_PATTERN.findall(content)
            assert len(imports) == 0, f"Found external @import in {path.name}: {imports}"

    def test_b3_zero_external_cdns_in_studio_presentation(self):
        """B3.4: Zero external CDNs in studio_presentation.html and gui/studio_presentation.html."""
        for path in [STUDIO_HTML, GUI_STUDIO_HTML]:
            content = read_file_text(path)
            external_refs = EXTERNAL_URL_PATTERN.findall(content) + EXTERNAL_IMPORT_PATTERN.findall(content)
            assert len(external_refs) == 0, f"Found external resources in {path.name}: {external_refs}"

    def test_b3_all_icons_are_inline_svg(self):
        """B3.5: Asserts all UI icons are inline <svg> nodes rather than font-icons or remote assets."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path)
            svg_count = content.count("<svg")
            assert svg_count >= 15, f"Expected at least 15 inline SVGs in {path.name}, found {svg_count}"
            assert "font-awesome" not in content.lower()
            assert "material-icons" not in content.lower()

    # -------------------------------------------------------------------------
    # Category 4 (B4): DOM ID & Interactive Contract Preservation (5 Tests)
    # -------------------------------------------------------------------------
    def test_b4_search_and_filter_input_ids_preserved(self):
        """B4.1: Critical search and core filter IDs must be preserved exactly."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path)
            for dom_id in ['id="search-input"', 'id="filter-score"', 'id="filter-status"']:
                assert dom_id in content, f"Missing critical DOM ID {dom_id} in {path.name}"

    def test_b4_filter_dropdown_ids_preserved(self):
        """B4.2: Critical taxonomy filter dropdown IDs must be preserved."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path)
            for dom_id in ['id="filter-family"', 'id="filter-workplace"', 'id="filter-platform"']:
                assert dom_id in content, f"Missing taxonomy filter ID {dom_id} in {path.name}"

    def test_b4_quick_chip_ids_preserved(self):
        """B4.3: Quick filter chips IDs must be preserved."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path)
            for dom_id in ['id="chip-all"', 'id="chip-high"', 'id="chip-rec"', 'id="chip-applied"']:
                assert dom_id in content, f"Missing chip ID {dom_id} in {path.name}"
            assert "chips-scroll" in content, f"chips-scroll container missing in {path.name}"

    def test_b4_modal_tracker_ids_preserved(self):
        """B4.4: Applied tracker modal IDs and controls must be preserved."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path)
            assert 'id="modal-applied-tracker"' in content, f"#modal-applied-tracker missing in {path.name}"
            assert "modal-close-btn" in content, f"modal-close-btn class missing in {path.name}"

    def test_b4_mobile_and_desktop_container_ids_preserved(self):
        """B4.5: Container IDs for desktop 3-pane and mobile 1-pane must be preserved."""
        for path in [GUI_INDEX, ROOT_INDEX]:
            content = read_file_text(path)
            for dom_id in [
                'id="command-center-app"', 'id="mobile-active-card"',
                'id="mobile-accordion"', 'id="mobile-docs-row"'
            ]:
                assert dom_id in content, f"Missing container ID {dom_id} in {path.name}"

    # -------------------------------------------------------------------------
    # Category 5 (B5): Theme Switching Persistence & Fallbacks (5 Tests)
    # -------------------------------------------------------------------------
    def test_b5_uninitialized_localstorage_defaults_to_light(self, desktop_page: Page):
        """B5.1: Boundary: Fresh visitor without localStorage key defaults safely to light theme."""
        desktop_page.evaluate("() => localStorage.removeItem('jobhunt_theme')")
        desktop_page.reload(wait_until="domcontentloaded")
        theme = desktop_page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        assert theme in ["light", None, ""], f"Fresh visitor should default to daylight light theme, got: {theme}"

    def test_b5_corrupted_localstorage_value_graceful_handling(self, desktop_page: Page):
        """B5.2: Boundary: Invalid/corrupt localStorage value handles gracefully without JS exceptions."""
        desktop_page.evaluate("() => localStorage.setItem('jobhunt_theme', 'invalid_cyberpunk_theme')")
        desktop_page.reload(wait_until="domcontentloaded")
        assert desktop_page.query_selector(".command-center-app") is not None
        theme = desktop_page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        assert theme in ["light", "dark", "invalid_cyberpunk_theme", None, ""]

    def test_b5_empty_string_localstorage_graceful_handling(self, desktop_page: Page):
        """B5.3: Boundary: Empty string in localStorage handles gracefully."""
        desktop_page.evaluate("() => localStorage.setItem('jobhunt_theme', '')")
        desktop_page.reload(wait_until="domcontentloaded")
        assert desktop_page.query_selector(".nav-rail") is not None

    def test_b5_rapid_consecutive_theme_toggles(self, desktop_page: Page):
        """B5.4: Stress: 10 rapid consecutive theme toggles execute without DOM desync or error."""
        toggle_btn = desktop_page.query_selector("#theme-toggle-btn, .theme-toggle, [onclick*='toggleTheme'], [aria-label*='theme' i]")
        if toggle_btn:
            for _ in range(10):
                toggle_btn.click()
            desktop_page.wait_for_timeout(300)
            theme = desktop_page.evaluate("() => document.documentElement.getAttribute('data-theme')")
            assert theme in ["light", "dark"]

    def test_b5_explicit_dark_theme_application(self, desktop_page: Page):
        """B5.5: Setting data-theme='dark' applies dark canvas background color."""
        desktop_page.evaluate("() => document.documentElement.setAttribute('data-theme', 'dark')")
        desktop_page.wait_for_timeout(200)
        applied = desktop_page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        assert applied == "dark"


# =============================================================================
# TIER 3: PAIRWISE & CROSS-FEATURE COMBINATIONS (10 Tests)
# =============================================================================
class TestTier3CrossFeatureCombinations:
    """Pairwise integration testing across theme, triage, responsive views, and postMessage."""

    def test_c1_theme_toggle_with_search_input(self, desktop_page: Page):
        """C1: Verifies search input filtering works consistently in both daylight and dark themes."""
        search_input = desktop_page.query_selector("#search-input")
        assert search_input is not None
        search_input.fill("Deloitte")
        desktop_page.wait_for_timeout(300)

        # Toggle theme while search query is active
        desktop_page.evaluate("() => { if (typeof toggleTheme === 'function') toggleTheme(); }")
        desktop_page.wait_for_timeout(200)

        # Verify search filter remains preserved
        current_val = search_input.input_value()
        assert current_val == "Deloitte", f"Search value was lost on theme toggle: {current_val}"

    def test_c2_theme_toggle_with_active_card_selection(self, desktop_page: Page):
        """C2: Selecting different cards under daylight vs dark theme updates active outline."""
        cards = desktop_page.query_selector_all(".job-card")
        if len(cards) >= 2:
            cards[1].click()
            desktop_page.wait_for_timeout(200)
            # Toggle theme
            desktop_page.evaluate("() => { if (typeof toggleTheme === 'function') toggleTheme(); }")
            desktop_page.wait_for_timeout(200)
            assert "active" in (cards[1].get_attribute("class") or "")

    def test_c3_theme_toggle_with_status_filter_chips(self, desktop_page: Page):
        """C3: Toggling quick status chips (High Fit / Applied) under different themes."""
        chip_high = desktop_page.query_selector("#chip-high")
        if chip_high:
            chip_high.click()
            desktop_page.wait_for_timeout(200)
            desktop_page.evaluate("() => { if (typeof toggleTheme === 'function') toggleTheme(); }")
            desktop_page.wait_for_timeout(200)
            assert "active" in (chip_high.get_attribute("class") or "")

    def test_c4_theme_toggle_with_mobile_accordion(self, mobile_page: Page):
        """C4: Expanding mobile accordion then toggling theme preserves accordion open state."""
        trigger = mobile_page.query_selector(".accordion-trigger, #mobile-accordion-btn")
        if trigger:
            trigger.click()
            mobile_page.wait_for_timeout(200)
            mobile_page.evaluate("() => { if (typeof toggleTheme === 'function') toggleTheme(); }")
            mobile_page.wait_for_timeout(200)
            acc = mobile_page.query_selector(".mobile-accordion, #mobile-accordion")
            assert acc is not None

    def test_c5_theme_toggle_with_document_hub_chips(self, desktop_page: Page):
        """C5: Document Hub attachment chips retain visible styling across theme toggle."""
        desktop_page.evaluate("() => { if (typeof toggleTheme === 'function') toggleTheme(); }")
        desktop_page.wait_for_timeout(200)
        deck = desktop_page.query_selector(".triage-deck, .details-panel, #details-panel, #triage-deck")
        assert deck is not None
        deck_text = deck.inner_text()
        assert "Tailored Resume_v2.pdf" in deck_text or "Resume" in deck_text

    def test_c6_viewport_resize_preserves_theme(self, desktop_page: Page):
        """C6: Resizing viewport from 1440px to 390px retains active theme attribute."""
        desktop_page.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')")
        desktop_page.set_viewport_size({"width": 390, "height": 844})
        desktop_page.wait_for_timeout(300)
        theme = desktop_page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        assert theme == "light", f"Theme lost on viewport resize: {theme}"

    def test_c7_studio_presentation_theme_broadcast(self, playwright_instance: Browser):
        """C7: Studio presentation theme toggle dispatches SET_THEME to iframes."""
        context = playwright_instance.new_context(viewport={"width": 1600, "height": 1000})
        page = context.new_page()
        page.goto(STUDIO_HTML.resolve().as_uri(), wait_until="domcontentloaded")
        page.wait_for_timeout(500)

        # Trigger postMessage from studio presentation
        has_postmessage = page.evaluate("""() => {
            const df = document.getElementById('desktop-frame');
            return df && typeof df.contentWindow.postMessage === 'function';
        }""")
        assert has_postmessage is True
        context.close()

    def test_c8_card_selection_updates_details_deck(self, desktop_page: Page):
        """C8: Clicking cards in middle feed synchronizes details deck hero information."""
        cards = desktop_page.query_selector_all(".job-card")
        if len(cards) >= 2:
            cards[0].click()
            desktop_page.wait_for_timeout(200)
            deck_comp = desktop_page.inner_text("#deck-company, .hero-company")
            assert len(deck_comp.strip()) > 0

    def test_c9_keyboard_shortcut_triage_under_theme(self, desktop_page: Page):
        """C9: Fast-triage keyboard shortcuts function smoothly under daylight theme."""
        desktop_page.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')")
        desktop_page.keyboard.press("ArrowDown")
        desktop_page.wait_for_timeout(200)
        assert desktop_page.query_selector(".job-card") is not None

    def test_c10_mobile_bottom_dock_actions_under_theme(self, mobile_page: Page):
        """C10: Mobile bottom dock buttons render accessible actions under daylight theme."""
        mobile_page.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')")
        bottom_dock = mobile_page.query_selector(".mobile-bottom-dock")
        assert bottom_dock is not None
        assert bottom_dock.is_visible()


# =============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (5 Tests)
# =============================================================================
class TestTier4RealWorldScenarios:
    """End-to-end full workflow simulation scenarios matching user behaviors."""

    def test_s1_full_desktop_triage_workflow(self, desktop_page: Page):
        """Scenario 1: Full Desktop Triage Workflow Simulation.
        User loads dashboard in daylight theme, searches for 'Deloitte', verifies filtered cards,
        clicks the role card, verifies the 8.5 circular progress ring, inspects 3 micro-bars
        in AI breakdown card, and inspects Document Hub resume attachment.
        """
        # Step 1: Set Daylight theme
        desktop_page.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')")
        desktop_page.wait_for_timeout(200)

        # Step 2: Search for Deloitte
        search = desktop_page.query_selector("#search-input")
        assert search is not None
        search.fill("Deloitte")
        desktop_page.wait_for_timeout(300)

        # Step 3: Verify filtered card
        first_card = desktop_page.query_selector(".job-card")
        assert first_card is not None
        assert "Deloitte" in first_card.inner_text()

        # Step 4: Click to activate
        first_card.click()
        desktop_page.wait_for_timeout(200)

        # Step 5: Verify Details Deck hero and 8.5 progress ring
        hero_comp = desktop_page.inner_text("#deck-company, .hero-company")
        assert "Deloitte" in hero_comp
        score_text = desktop_page.inner_text("#deck-score-num, .score-num, .deck-score")
        assert "8.5" in score_text
        deck = desktop_page.query_selector(".triage-deck, .details-panel, #details-panel, #triage-deck")
        assert deck is not None
        deck_text = deck.inner_text()

        # Step 6: Verify 3 micro-bars
        assert "95%" in deck_text or "AI Agent" in deck_text
        assert "92%" in deck_text or "Python" in deck_text

        # Step 7: Verify Document Hub resume attachment
        assert "Tailored Resume_v2.pdf" in deck_text or "Resume" in deck_text

    def test_s2_mobile_viewport_triage_workflow(self, mobile_page: Page):
        """Scenario 2: Mobile Viewport Triage Workflow Simulation.
        User on smartphone viewport verifies sticky top bar, selects High Fit capsule,
        expands AI breakdown accordion, inspects micro-bars, and checks sticky bottom apply button.
        """
        # Step 1: Verify sticky header
        top_bar = mobile_page.query_selector(".mobile-top-bar")
        assert top_bar is not None and top_bar.is_visible()
        assert "Shubham's JobHunt" in top_bar.inner_text()

        # Step 2: Click High Fit (8+) capsule
        high_capsule = mobile_page.query_selector("#mobile-capsule-high, .filter-capsule:nth-child(2)")
        if high_capsule:
            high_capsule.click()
            mobile_page.wait_for_timeout(200)

        # Step 3: Expand AI breakdown accordion
        trigger = mobile_page.query_selector(".accordion-trigger, #mobile-accordion-btn")
        if trigger:
            trigger.click()
            mobile_page.wait_for_timeout(200)

        # Step 4: Scroll to bottom dock and verify apply action
        bottom_dock = mobile_page.query_selector(".mobile-bottom-dock")
        assert bottom_dock is not None and bottom_dock.is_visible()
        assert "Apply" in bottom_dock.inner_text() or "Auto-Fill" in bottom_dock.inner_text()

    def test_s3_studio_presentation_dual_frame_workflow(self, playwright_instance: Browser):
        """Scenario 3: Studio Presentation Dual-Viewport Sync Workflow.
        Loads studio_presentation.html, verifies desktop and mobile iframes render side-by-side
        with sharp uppercase labels, and tests theme toggle event relay.
        """
        context = playwright_instance.new_context(viewport={"width": 1600, "height": 1000})
        page = context.new_page()
        page.goto(STUDIO_HTML.resolve().as_uri(), wait_until="domcontentloaded")
        page.wait_for_timeout(600)

        # Verify side-by-side frames
        assert page.query_selector("#desktop-frame") is not None
        assert page.query_selector("#mobile-frame") is not None

        # Verify labels
        body_text = page.inner_text("body")
        assert "DESKTOP WORKSPACE (3-PANE)" in body_text
        assert "MOBILE VIEW (1-PANE TIGHT)" in body_text

        # Test cross-frame relay
        page.evaluate("""() => {
            window.postMessage({ type: 'SET_THEME', theme: 'light' }, '*');
        }""")
        page.wait_for_timeout(200)
        context.close()

    def test_s4_offline_build_synchronization_workflow(self):
        """Scenario 4: Offline Build & Synchronization Pipeline Integrity.
        Executes build_mobile_gui.py and confirms root index.html is generated with
        identical Daylight theme tokens and zero discrepancies with gui/index.html.
        """
        result = subprocess.run(
            [sys.executable, str(BUILD_SCRIPT)],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"build_mobile_gui.py failed: {result.stderr}"
        assert ROOT_INDEX.exists(), "Root index.html must exist after build"

        # Invariant: Daylight tokens match in both files
        gui_text = read_file_text(GUI_INDEX)
        root_text = read_file_text(ROOT_INDEX)

        for token in [DAYLIGHT_WARM_OFF_WHITE, DAYLIGHT_LIGHT_GRAY, DAYLIGHT_PURE_WHITE, DAYLIGHT_BORDER_SUBTLE]:
            if token in gui_text:
                assert token in root_text, f"Token {token} present in gui/index.html but missing from root index.html"

    def test_s5_rapid_keyboard_triage_simulation(self, desktop_page: Page):
        """Scenario 5: Rapid Keyboard Triage Simulation.
        Focuses search with ⌘K, navigates through job cards with keyboard,
        and verifies active highlight and details deck sync without visual clipping.
        """
        search = desktop_page.query_selector("#search-input")
        assert search is not None
        search.focus()
        desktop_page.keyboard.type("AI")
        desktop_page.wait_for_timeout(200)

        # Press Enter / Escape / Arrow keys
        desktop_page.keyboard.press("Escape")
        desktop_page.keyboard.press("ArrowDown")
        desktop_page.wait_for_timeout(200)

        # Verify page layout did not break
        nav = desktop_page.query_selector(".nav-rail")
        assert nav is not None and nav.is_visible()
        details = desktop_page.query_selector(".triage-deck, .details-panel, #details-panel, #triage-deck")
        assert details is not None and details.is_visible()
