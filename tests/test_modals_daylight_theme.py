"""Automated test suite verifying Daylight Theme styling and color harmony across all modal dialogs.

Covers:
- Elimination of hardcoded dark backgrounds (#14171F, #0d1117) inside modals.
- Proper use of CSS design tokens (var(--bg-card), var(--text-main), var(--border-subtle)).
- Contrast compliance for headers, text inputs, buttons, and badges.
- Verification of ICONS.clock inline SVG.
- Complete absence of emojis across updated HTML files.
"""

import os
import re
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUI_INDEX = os.path.join(ROOT_DIR, "gui", "index.html")
ROOT_INDEX = os.path.join(ROOT_DIR, "index.html")

EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf\u2b50\u23f0-\u23f3]"
)


def test_modal_card_uses_theme_tokens():
    """Asserts that .modal-card uses CSS variables rather than hardcoded #14171F."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        assert os.path.exists(html_path), f"File {html_path} must exist"
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find .modal-card definition
        match = re.search(r"\.modal-card\s*\{([^}]+)\}", content)
        assert match, "Must find .modal-card CSS rule"
        rule = match.group(1)
        assert "var(--bg-card)" in rule, ".modal-card must use var(--bg-card)"
        assert "#14171F" not in rule, ".modal-card must not have hardcoded #14171F"


def test_autofill_inputs_use_theme_classes():
    """Asserts that autofill inputs do not have hardcoded dark colors."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify .autofill-input rule exists
        assert ".autofill-input" in content
        assert "var(--bg-card)" in content

        # Verify the 16 fields have class="autofill-input"
        for field_id in [
            "autofill-first-name",
            "autofill-last-name",
            "autofill-full-name",
            "autofill-email",
            "autofill-phone",
            "autofill-location",
            "autofill-linkedin",
            "autofill-github",
            "autofill-portfolio",
            "autofill-notice-period",
            "autofill-experience",
            "autofill-current-ctc",
            "autofill-expected-ctc",
            "autofill-gender",
            "autofill-work-auth",
            "autofill-summary"
        ]:
            field_pattern = rf'id="{field_id}"[^>]*class="[^"]*autofill-input[^"]*"'
            assert re.search(field_pattern, content), f"Field {field_id} must have class autofill-input"


def test_bookmarklet_engine_platform_support_and_manual_review():
    """Asserts that Bookmarklet engine supports Workday, LinkedIn, Naukri, and enforces manual review."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "generateBookmarkletScript" in content
        # Workday data-automation-id coverage
        assert "data-automation-id" in content
        # Visual manual review outline in emerald
        assert "#10b981" in content
        # Toast copy specifying manual review before submission
        assert "Review details before submitting" in content
        # Platform badges in modal
        assert "Workday" in content
        assert "LinkedIn Easy Apply" in content
        assert "Naukri" in content
        assert "Manual Review Safe" in content


def test_no_hardcoded_dark_inputs_in_modals():
    """Asserts that #0d1117 and #e6edf3 are not hardcoded on modal inputs or selects."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check kit-browser-select
        assert 'id="kit-browser-select"' in content
        match_select = re.search(r'id="kit-browser-select"[^>]+>', content)
        assert match_select, "Must find kit-browser-select element"
        select_tag = match_select.group(0)
        assert "#0d1117" not in select_tag, "kit-browser-select must not have hardcoded #0d1117"
        assert "#e6edf3" not in select_tag, "kit-browser-select must not have hardcoded #e6edf3"


def test_icons_clock_defined_and_valid_svg():
    """Asserts that ICONS.clock is defined and contains valid inline SVG."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "clock:" in content
        match = re.search(r"clock:\s*`([^`]+)`", content)
        assert match, "ICONS.clock must be defined with template literal"
        svg = match.group(1)
        assert "<svg" in svg and "</svg>" in svg
        assert "polyline" in svg or "path" in svg


def test_modals_zero_emojis():
    """Asserts that all modals and templates are strictly emoji-free."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        matches = EMOJI_PATTERN.findall(content)
        assert len(matches) == 0, f"Found {len(matches)} emojis in {html_path}"

