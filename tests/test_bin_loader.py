"""Unit tests verifying the Application Filling Bin Loader modal and SVG animations."""

import os
import re
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUI_INDEX = os.path.join(ROOT_DIR, "gui", "index.html")
ROOT_INDEX = os.path.join(ROOT_DIR, "index.html")

EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf\u2b50\u23f0-\u23f3]"
)


def test_bin_loader_dom_structure_present():
    """Asserts that the bin loader modal, SVG elements, and telemetry rows are present."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        assert os.path.exists(html_path), f"File {html_path} must exist"
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert 'id="bin-loader-modal"' in content
        assert 'class="bin-loader-overlay"' in content
        assert 'class="bin-loader-card"' in content
        assert 'class="bin-anim-container"' in content
        assert 'class="bin-svg"' in content

        # Check falling documents SVG groups
        assert 'class="doc-anim-left"' in content
        assert 'class="doc-anim-right"' in content
        assert 'class="doc-anim-center"' in content

        # Check bin wireframe and accumulator group
        assert 'id="bin-accumulate-group"' in content
        assert 'id="bin-fill-rect"' in content
        assert '>INTAKE<' in content

        # Check progress bar & telemetry
        assert 'id="bin-progress-bar"' in content
        assert 'id="bin-stage-text"' in content
        assert 'id="bin-telemetry-percent"' in content

        # Check minimize action button
        assert 'class="btn-loader-minimize"' in content
        assert "Run in Background" in content


def test_bin_loader_css_animations():
    """Asserts that the keyframes and responsive styling for the bin loader are defined."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "@keyframes docFallLeft" in content
        assert "@keyframes docFallRight" in content
        assert "@keyframes docFallCenter" in content
        assert "@keyframes binCardPop" in content
        assert ".bin-loader-overlay.open" in content
        assert "backdrop-filter: blur(8px)" in content


def test_bin_loader_js_controllers_wired():
    """Asserts that the JavaScript controller functions and lifecycle hooks are implemented."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "function openBinLoaderModal(" in content
        assert "function updateBinLoaderProgress(" in content
        assert "function getBinLoaderProgress(" in content
        assert "function closeBinLoaderModal(" in content

        # Verify wired in triggerPipelineScan
        assert re.search(r"openBinLoaderModal\(\s*['\"]Ingesting Opportunities['\"]", content)
        assert "updateBinLoaderProgress(" in content

        # Verify wired in applyCurrentJob
        assert re.search(r"openBinLoaderModal\(\s*['\"]Filing Application['\"]", content)


def test_bin_loader_zero_emojis():
    """Asserts that the bin loader implementation contains zero unicode emojis."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        matches = EMOJI_PATTERN.findall(content)
        assert len(matches) == 0, f"Found {len(matches)} emojis in {html_path}"
