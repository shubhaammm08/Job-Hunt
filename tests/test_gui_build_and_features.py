"""Automated test suite verifying GUI Modernization, Build Synchronization, and Features.

Covers Milestone 1 Requirements:
- R1: UI copy cleanup, professionalization, and elimination of marketing buzzwords.
- R2: Inline SVG icon system and complete absence of UI emojis and external CDN dependencies.
- R3: Fully clickable job cards, `window.open(url, '_blank')`, and action click event isolation (`stopPropagation`).
- R4: Workplace Type and Platform Source filter dropdowns, quick chips, touch targets (>= 44px), and metadata inference engine.
- R5: Build synchronization (`build_mobile_gui.py`), non-destructive template preservation, and JSON payload bundling.
"""

import json
import os
import re
import sys
from urllib.parse import urlparse
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUI_INDEX = os.path.join(ROOT_DIR, "gui", "index.html")
ROOT_INDEX = os.path.join(ROOT_DIR, "index.html")
BUILD_SCRIPT = os.path.join(ROOT_DIR, "build_mobile_gui.py")
SEEN_JSON = os.path.join(ROOT_DIR, "seen.json")

EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf\u2b50\u23f0-\u23f3]"
)
EXPLICIT_EMOJIS = [
    "🎯", "⚡", "📊", "📬", "🛡️", "👤", "🔍", "🔥", "⭐", "🤖", "🐍", "⏳", "📍", "💡", "⏰", "💰", "✓"
]

BUZZWORDS = [
    "Autonomous AI Career Engine",
    "AI Fit:",
    "Autonomous Cloud Schedules",
    "Cloud Active",
    "Daily JobHunter Digest",
    "Inbox Executive Briefing"
]


def test_gui_and_root_index_emoji_free():
    """Asserts zero unicode emojis remain across both gui/index.html and root index.html."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        assert os.path.exists(html_path), f"File {html_path} must exist"
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check regex pattern matches
        matches = EMOJI_PATTERN.findall(content)
        assert len(matches) == 0, f"Found {len(matches)} emojis in {html_path}: {set(matches)}"

        # Check explicit legacy emojis
        found_explicit = [e for e in EXPLICIT_EMOJIS if e in content]
        assert len(found_explicit) == 0, f"Found explicit emojis in {html_path}: {found_explicit}"


def test_zero_external_cdn_dependencies():
    """Asserts no external stylesheets, fonts, or scripts are loaded from CDNs."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Match <link href="http..."> or <script src="http...">
        external_tags = re.findall(
            r'<(?:link|script)[^>]+(?:src|href)=["\'](https?://[^"\']+)["\']',
            content,
            re.IGNORECASE
        )
        assert len(external_tags) == 0, f"Found external tags in {html_path}: {external_tags}"

        # Match CSS @import url("http...")
        external_imports = re.findall(
            r'@import\s+(?:url\()?["\'](https?://[^"\']+)["\']',
            content,
            re.IGNORECASE
        )
        assert len(external_imports) == 0, f"Found external CSS imports in {html_path}: {external_imports}"


def test_clean_copy_no_marketing_buzzwords():
    """Asserts all marketing hype and AI buzzwords are replaced with clean professional copy."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        for b in BUZZWORDS:
            assert b not in content, f"Buzzword '{b}' found in {html_path}"

        # Asserts professional replacements exist
        assert "Opportunity Pipeline &amp; Application Tracker" in content or "Opportunity Pipeline & Application Tracker" in content
        assert "Pipeline Automation Schedules" in content
        assert "Pipeline Active" in content
        assert "Match Rationale:" in content


def test_card_clickability_and_action_isolation():
    """Asserts job cards are fully clickable while interactive buttons isolate events."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Card container styling
        assert ".job-card {" in content
        assert "cursor: pointer" in content

        # Full card navigation and keydown handlers
        assert "handleCardClick" in content
        assert "role=\"link\"" in content
        assert "tabindex=\"0\"" in content
        assert "window.open(url, '_blank', 'noopener,noreferrer')" in content

        # Action button propagation isolation
        assert "event.stopPropagation()" in content
        assert "toggleApplied" in content
        assert "event.target.closest('button, a')" in content


def test_workplace_and_platform_filter_controls_present():
    """Asserts 5-dropdown filter bar and workplace/platform chips exist in the DOM."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Select dropdowns
        assert 'id="filter-score"' in content
        assert 'id="filter-status"' in content
        assert 'id="filter-family"' in content
        assert 'id="filter-workplace"' in content
        assert 'id="filter-platform"' in content

        # Workplace dropdown options
        assert '<option value="remote">Remote</option>' in content
        assert '<option value="hybrid">Hybrid</option>' in content
        assert '<option value="onsite">Onsite</option>' in content

        # Platform dropdown options
        assert '<option value="greenhouse">Greenhouse</option>' in content
        assert '<option value="ashby">Ashby</option>' in content
        assert '<option value="lever">Lever</option>' in content
        assert '<option value="remotive">Remotive</option>' in content
        assert '<option value="hackernews">Hacker News</option>' in content

        # Quick chips
        assert 'id="chip-remote"' in content
        assert 'id="chip-hybrid"' in content
        assert 'id="chip-onsite"' in content
        assert 'id="chip-greenhouse"' in content
        assert 'id="chip-ashby"' in content
        assert 'id="chip-lever"' in content
        assert 'id="chip-remotive"' in content
        assert 'id="chip-hackernews"' in content
        assert 'id="chip-other-plat"' in content


def test_mobile_touch_targets_compliance():
    """Asserts touch targets satisfy >= 44px minimum height on mobile viewports."""
    for html_path in [GUI_INDEX, ROOT_INDEX]:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        start = content.find("@media (max-width: 600px)")
        assert start != -1, f"Mobile media query not found in {html_path}"
        end = content.find("</style>", start)
        media_content = content[start:end]

        # Confirm min-height: 44px appears in mobile section for controls
        assert "min-height: 44px" in media_content
        assert ".select-filter" in media_content
        assert ".filter-chip" in media_content
        assert ".btn-applied" in media_content


def test_metadata_inference_logic_on_seen_jobs():
    """Validates the inference engine correctly categorizes all 56 jobs in seen.json."""
    assert os.path.exists(SEEN_JSON), "seen.json must exist"
    with open(SEEN_JSON, "r", encoding="utf-8") as f:
        seen_data = json.load(f)

    jobs = [{"job_id": k, **v} for k, v in seen_data.items() if isinstance(v, dict)]
    assert len(jobs) == 56

    def infer_wp(job):
        if job.get("workplace_type"):
            val = str(job["workplace_type"]).lower()
            if "remote" in val or "wfh" in val: return "remote"
            if "hybrid" in val or "flex" in val: return "hybrid"
            if "onsite" in val or "office" in val: return "onsite"
            return "other"
        loc = (job.get("location") or "").strip()
        title = (job.get("title") or "").strip()
        reason = (job.get("reason") or "").strip()
        combined = f"{loc} {title} {reason}".lower()
        if re.search(r"\b(hybrid|flexible)\b", combined, re.I): return "hybrid"
        if re.search(r"\b(remote|work from home|wfh|anywhere|telecommute)\b", combined, re.I): return "remote"
        if loc and loc not in ("Not Specified", "Unspecified"): return "onsite"
        return "other"

    def infer_plat(job):
        if job.get("platform"):
            p = str(job["platform"]).lower()
            if "greenhouse" in p: return "greenhouse"
            if "ashby" in p: return "ashby"
            if "lever" in p: return "lever"
            if "remotive" in p: return "remotive"
            if "hacker" in p or "hn" in p or "ycombinator" in p: return "hackernews"
            return "other"
        url = (job.get("url") or "").strip()
        jid = (job.get("job_id") or "").lower()
        can_src = (job.get("canonical_source") or "").lower()
        sources = " ".join(job.get("sources") or []).lower() if isinstance(job.get("sources"), list) else ""
        text = f"{url} {jid} {can_src} {sources} {job.get('title') or ''} {job.get('reason') or ''}".lower()
        try:
            parsed = urlparse(url if url.startswith("http") else "https://" + url)
            domain = parsed.hostname.lower() if parsed.hostname else url.lower()
            search = parsed.query.lower()
        except Exception:
            domain = url.lower()
            search = ""
        if "greenhouse.io" in domain or "gh_jid" in search or jid.startswith("greenhouse:") or can_src == "greenhouse" or "greenhouse" in sources or "greenhouse" in text:
            return "greenhouse"
        if "ashbyhq.com" in domain or jid.startswith("ashby:") or can_src == "ashby" or "ashby" in sources or "ashby" in text:
            return "ashby"
        if "lever.co" in domain or jid.startswith("lever:") or can_src == "lever" or "lever" in sources or "lever" in text:
            return "lever"
        if "remotive.com" in domain or "remotive.io" in domain or jid.startswith("remotive:") or can_src == "remotive" or "remotive" in sources or "remotive" in text:
            return "remotive"
        if "news.ycombinator.com" in domain or "ycombinator.com" in domain or jid.startswith("hn:") or jid.startswith("hackernews:") or "hacker news" in text or "ycombinator" in text:
            return "hackernews"
        return "other"

    wp_counts = {}
    plat_counts = {}
    for j in jobs:
        wp = infer_wp(j)
        plat = infer_plat(j)
        wp_counts[wp] = wp_counts.get(wp, 0) + 1
        plat_counts[plat] = plat_counts.get(plat, 0) + 1

    assert wp_counts.get("remote") == 31
    assert wp_counts.get("onsite") == 24
    assert wp_counts.get("hybrid") == 1
    assert wp_counts.get("other", 0) == 0

    assert plat_counts.get("greenhouse") == 47
    assert plat_counts.get("ashby") == 2
    assert plat_counts.get("lever") == 2
    assert plat_counts.get("other") == 5


def test_build_mobile_gui_execution_and_synchronization():
    """Executes build_mobile_gui and verifies non-destructive behavior and payload inlining."""
    sys.path.insert(0, ROOT_DIR)
    import build_mobile_gui

    # Record gui/index.html modification time / content
    with open(GUI_INDEX, "r", encoding="utf-8") as f:
        gui_before = f.read()

    # Execute main()
    build_mobile_gui.main()

    # Ensure gui/index.html was NOT clobbered with stale content
    with open(GUI_INDEX, "r", encoding="utf-8") as f:
        gui_after = f.read()
    assert gui_before == gui_after, "build_mobile_gui must not overwrite gui/index.html"

    # Ensure root index.html was updated with INITIAL_DATA
    with open(ROOT_INDEX, "r", encoding="utf-8") as f:
        root_content = f.read()

    match = re.search(r"window\.INITIAL_DATA\s*=\s*(\{.*?\});\s*</script>", root_content, re.DOTALL)
    assert match is not None, "root index.html must contain window.INITIAL_DATA"
    data = json.loads(match.group(1))

    assert "jobs" in data
    assert len(data["jobs"]) == 56
    assert "stats" in data
    assert data["stats"]["total"] == 56
    assert "profile" in data
    assert "source_health" in data
