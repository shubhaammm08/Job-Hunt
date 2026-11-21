"""Avatar pack integration tests (alohe/avatars, MIT).

Covers the picker UI, persistence, reset-to-initials behaviour, mobile fit,
and the vendored 133-image asset set.
"""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
GUI_INDEX = ROOT / "gui" / "index.html"
ROOT_INDEX = ROOT / "index.html"
AVATAR_DIR = ROOT / "gui" / "avatars"

STYLES = ["vibrent", "upstream", "memo", "notion", "toon", "bluey", "teams", "3d"]


def test_avatar_assets_and_markup():
    """All 133 PNGs, attribution, picker markup, and default avatar exist."""
    pngs = sorted(AVATAR_DIR.glob("*.png"))
    assert len(pngs) == 133, f"Expected 133 avatars, found {len(pngs)}"

    for name in ("vibrent_1.png", "upstream_22.png", "memo_35.png", "3d_5.png"):
        assert (AVATAR_DIR / name).is_file(), f"Missing avatar asset {name}"

    attribution = (AVATAR_DIR / "ATTRIBUTION.md").read_text(encoding="utf-8")
    assert "alohe/avatars" in attribution
    assert "MIT" in attribution

    for path in (GUI_INDEX, ROOT_INDEX):
        content = path.read_text(encoding="utf-8")
        assert 'id="avatar-picker-modal"' in content, f"Avatar picker missing in {path.name}"
        assert "AVATAR_STYLES" in content, f"Avatar catalog missing in {path.name}"
        assert 'id="profile-avatar"' in content, f"Profile avatar missing in {path.name}"
        assert 'id="rail-brand-avatar"' in content, f"Rail avatar missing in {path.name}"
        assert 'id="mobile-brand-avatar"' in content, f"Mobile avatar missing in {path.name}"

    profile = json.loads((ROOT / "profile.example.json").read_text(encoding="utf-8"))
    assert profile.get("avatar") == "vibrent_1"


def test_avatar_picker_select_persist_and_reset():
    """Picking an avatar updates every avatar slot and survives a reload."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(ROOT_INDEX.as_uri(), wait_until="domcontentloaded")
        page.wait_for_selector(".job-card", timeout=5000)

        page.evaluate("localStorage.removeItem('jobhunt_avatar'); openAvatarPicker();")
        page.wait_for_selector("#avatar-picker-modal.open")
        assert page.eval_on_selector_all(".avatar-style-tab", "els => els.length") == 8

        total = 0
        for style in STYLES:
            page.click(f'#avatar-style-tabs [data-style="{style}"]')
            page.wait_for_timeout(40)
            total += page.eval_on_selector_all(".avatar-option", "els => els.length")
        assert total == 133, f"Expected 133 selectable avatars, found {total}"

        page.click('#avatar-style-tabs [data-style="memo"]')
        page.wait_for_timeout(100)
        page.click('.avatar-option[data-avatar="memo_12"]')
        page.wait_for_timeout(150)

        assert page.evaluate("localStorage.getItem('jobhunt_avatar')") == "memo_12"
        assert page.evaluate("document.documentElement.classList.contains('has-user-avatar')") is True
        assert "memo_12.png" in page.evaluate(
            "getComputedStyle(document.documentElement).getPropertyValue('--user-avatar-url')"
        )
        for selector in ("#rail-brand-avatar", "#mobile-brand-avatar", "#profile-avatar"):
            bg = page.evaluate(f"getComputedStyle(document.querySelector('{selector}')).backgroundImage")
            assert "memo_12.png" in bg, f"{selector} did not receive the selected avatar"

        page.reload(wait_until="domcontentloaded")
        page.wait_for_selector(".job-card", timeout=5000)
        page.wait_for_timeout(200)
        assert page.evaluate("document.documentElement.classList.contains('has-user-avatar')") is True
        assert "memo_12.png" in page.evaluate(
            "getComputedStyle(document.documentElement).getPropertyValue('--user-avatar-url')"
        )

        page.evaluate("openAvatarPicker(); resetAvatar();")
        page.wait_for_timeout(150)
        assert page.evaluate("localStorage.getItem('jobhunt_avatar')") == "initials"
        assert page.evaluate("document.documentElement.classList.contains('has-user-avatar')") is False
        assert page.evaluate(
            "getComputedStyle(document.documentElement).getPropertyValue('--user-avatar-url').trim()"
        ) == ""

        context.close()
        browser.close()


def test_avatar_background_is_cover_on_all_slots():
    """Regression: later background shorthands must not crop profile/mobile avatars."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        viewports = [
            (1440, 900, ("#profile-avatar", "#rail-brand-avatar", "#mobile-brand-avatar")),
            (390, 844, ("#profile-avatar", "#mobile-brand-avatar")),
        ]
        for width, height, slots in viewports:
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()
            page.goto(ROOT_INDEX.as_uri(), wait_until="domcontentloaded")
            page.wait_for_selector(".job-card", timeout=5000)
            page.evaluate("localStorage.removeItem('jobhunt_avatar')")
            page.reload(wait_until="domcontentloaded")
            page.wait_for_selector(".job-card", timeout=5000)
            page.wait_for_timeout(150)

            for selector in slots:
                style = page.evaluate(
                    """sel => {
                        const cs = getComputedStyle(document.querySelector(sel));
                        return {image: cs.backgroundImage, size: cs.backgroundSize, position: cs.backgroundPosition};
                    }""",
                    selector,
                )
                assert "vibrent_1.png" in style["image"], f"{selector} missing default avatar"
                assert style["size"] == "cover", (
                    f"{selector} avatar is cropped (background-size={style['size']})"
                )
                assert style["position"] in ("center", "50% 50%"), (
                    f"{selector} avatar is not centered (background-position={style['position']})"
                )
            context.close()
        browser.close()


def test_avatar_picker_fits_mobile_viewport():
    """The picker stays inside a 390x844 viewport without horizontal overflow."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        page.goto(ROOT_INDEX.as_uri(), wait_until="domcontentloaded")
        page.wait_for_selector(".job-card", timeout=5000)

        page.click("#mobile-brand-avatar")
        page.wait_for_selector("#avatar-picker-modal.open")
        page.wait_for_timeout(150)

        box = page.query_selector(".avatar-picker-card").bounding_box()
        assert box is not None
        assert box["x"] >= 0 and box["x"] + box["width"] <= 391
        assert box["y"] >= 0 and box["y"] + box["height"] <= 845
        assert page.evaluate("document.documentElement.scrollWidth") <= 390

        columns = page.evaluate(
            "getComputedStyle(document.querySelector('.avatar-grid')).gridTemplateColumns.split(' ').length"
        )
        assert columns >= 2

        context.close()
        browser.close()
