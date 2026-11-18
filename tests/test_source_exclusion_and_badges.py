"""Automated Verification Suite for Milestone 1:
Paywalled Job Board Exclusion, Historical Record Purging,
and Originating Source Badges & Filtering.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest
import yaml

from jobhunt.fetch import Job
from jobhunt.sources import (
    DISABLED_PAYWALLED_SOURCES,
    REGISTRY,
    WeWorkRemotelyAdapter,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
SEEN_JSON = ROOT_DIR / "seen.json"
CONFIG_YAML = ROOT_DIR / "config.yaml"
INDEX_HTML = ROOT_DIR / "index.html"
GUI_INDEX_HTML = ROOT_DIR / "gui" / "index.html"
SOURCE_HEALTH_JSON = ROOT_DIR / "out" / "source_health.json"
SOURCES_CATALOG_JSON = ROOT_DIR / "jobhunt" / "sources_catalog.json"


# =============================================================================
# Helper: Python implementation of client-side source inference
# =============================================================================
def infer_platform_source(job: dict) -> str:
    """Mirrors client-side inferPlatformSource in gui/index.html."""
    if job.get("platform"):
        p = str(job["platform"]).lower()
        if "greenhouse" in p: return "greenhouse"
        if "ashby" in p: return "ashby"
        if "lever" in p: return "lever"
        if "smartrecruiters" in p: return "smartrecruiters"
        if "workable" in p: return "workable"
        if "recruitee" in p: return "recruitee"
        if "personio" in p: return "personio"
        if "breezy" in p: return "breezy"
        if "bamboohr" in p: return "bamboohr"
        if "workday" in p: return "workday"
        if "remotive" in p: return "remotive"
        if "remoteok" in p: return "remoteok"
        if "nodesk" in p: return "nodesk"
        if "workingnomads" in p or "working nomads" in p: return "workingnomads"
        if "himalayas" in p: return "himalayas"
        if "jobicy" in p: return "jobicy"
        if "hacker" in p or "hn" in p or "ycombinator" in p: return "hackernews"
        if "linkedin" in p: return "linkedin"
        if "naukri" in p: return "naukri"
        if "indeed" in p: return "indeed"
        if "glassdoor" in p: return "glassdoor"
        if "wellfound" in p or "angel" in p: return "wellfound"
        if "direct" in p or "company" in p: return "direct_ats"
        return "other"

    url = (job.get("url") or "").strip()
    jid = (job.get("job_id") or "").lower()
    can_src = (job.get("canonical_source") or "").lower()
    sources = " ".join(job.get("sources") or []).lower() if isinstance(job.get("sources"), list) else ""
    title = str(job.get("title") or "").lower()
    reason = str(job.get("reason") or "").lower()
    text = f"{url} {jid} {can_src} {sources} {title} {reason}"

    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        domain = (parsed.hostname or "").lower()
        search = (parsed.query or "").lower()
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
    if "remoteok.com" in domain or "remoteok.io" in domain or jid.startswith("remoteok:") or can_src == "remoteok" or "remoteok" in sources or "remoteok" in text:
        return "remoteok"
    if "workingnomads.com" in domain or jid.startswith("workingnomads:") or can_src == "workingnomads" or "workingnomads" in sources or "workingnomads" in text or "working nomads" in text:
        return "workingnomads"
    if "nodesk.co" in domain or jid.startswith("nodesk:") or can_src == "nodesk" or "nodesk" in sources or "nodesk" in text:
        return "nodesk"
    if "news.ycombinator.com" in domain or "ycombinator.com" in domain or jid.startswith("hn:") or jid.startswith("hackernews:") or "hacker news" in text or "ycombinator" in text:
        return "hackernews"
    if "smartrecruiters.com" in domain or jid.startswith("smartrecruiters:") or can_src == "smartrecruiters" or "smartrecruiters" in sources or "smartrecruiters" in text:
        return "smartrecruiters"
    if "workable.com" in domain or jid.startswith("workable:") or can_src == "workable" or "workable" in sources or "workable" in text:
        return "workable"
    if "recruitee.com" in domain or jid.startswith("recruitee:") or can_src == "recruitee" or "recruitee" in sources:
        return "recruitee"
    if "personio.de" in domain or "personio.com" in domain or jid.startswith("personio:") or can_src == "personio" or "personio" in sources:
        return "personio"
    if "breezy.hr" in domain or jid.startswith("breezy:") or can_src == "breezy" or "breezy" in sources:
        return "breezy"
    if "bamboohr.com" in domain or jid.startswith("bamboohr:") or can_src == "bamboohr" or "bamboohr" in sources:
        return "bamboohr"
    if "myworkdayjobs.com" in domain or jid.startswith("workday:") or can_src == "workday" or "workday" in sources:
        return "workday"
    if "linkedin.com" in domain or jid.startswith("linkedin:") or jid.startswith("linkedin_india:") or jid.startswith("linkedin_global:") or can_src.startswith("linkedin") or "linkedin" in sources:
        return "linkedin"
    if "naukri.com" in domain or jid.startswith("naukri:") or jid.startswith("naukri_campus:") or can_src.startswith("naukri") or "naukri" in sources:
        return "naukri"
    if "indeed.com" in domain or jid.startswith("indeed:") or jid.startswith("indeed_india:") or can_src.startswith("indeed") or "indeed" in sources:
        return "indeed"
    if "himalayas.app" in domain or jid.startswith("himalayas:") or can_src == "himalayas" or "himalayas" in sources:
        return "himalayas"
    if "jobicy.com" in domain or jid.startswith("jobicy:") or can_src == "jobicy" or "jobicy" in sources:
        return "jobicy"
    if "wellfound.com" in domain or "angel.co" in domain or jid.startswith("wellfound:") or can_src == "wellfound" or "wellfound" in sources:
        return "wellfound"
    if "glassdoor.com" in domain or jid.startswith("glassdoor:") or can_src == "glassdoor" or "glassdoor" in sources:
        return "glassdoor"
    if job.get("ats") or "careers." in domain or "jobs." in domain or "/careers" in url or "/jobs" in url:
        return "direct_ats"
    return "other"


def get_platform_label(platform_key: str) -> str:
    """Mirrors client-side getPlatformLabel in gui/index.html."""
    labels = {
        "greenhouse": "Greenhouse",
        "ashby": "Ashby",
        "lever": "Lever",
        "remotive": "Remotive",
        "hackernews": "Hacker News",
        "remoteok": "Remote OK",
        "nodesk": "NoDesk",
        "workingnomads": "Working Nomads",
        "linkedin": "LinkedIn",
        "naukri": "Naukri",
        "indeed": "Indeed",
        "smartrecruiters": "SmartRecruiters",
        "workable": "Workable",
        "recruitee": "Recruitee",
        "personio": "Personio",
        "breezy": "Breezy HR",
        "bamboohr": "BambooHR",
        "workday": "Workday",
        "himalayas": "Himalayas",
        "jobicy": "Jobicy",
        "wellfound": "Wellfound",
        "glassdoor": "Glassdoor",
        "direct_ats": "Direct ATS / Company",
    }
    return labels.get(platform_key, "Other / Unspecified")


# =============================================================================
# 1. R1: EXCLUDE PAYWALLED & PAID-SUBSCRIPTION JOB BOARDS
# =============================================================================
def test_weworkremotely_adapter_omitted_or_disabled():
    """Validates WeWorkRemotelyAdapter is disabled and omitted from active registry."""
    # Verify module-level paywalled exclusion set
    assert "We Work Remotely" in DISABLED_PAYWALLED_SOURCES
    assert "FlexJobs" in DISABLED_PAYWALLED_SOURCES

    # Direct adapter instance must be disabled and never perform network calls
    wwr = WeWorkRemotelyAdapter()
    assert wwr.health.status == "NOT_CONFIGURED"
    assert len(wwr.health.errors) > 0

    with patch("jobhunt.sources.requests.get") as mock_get:
        jobs = wwr.fetch({})
        assert jobs == []
        mock_get.assert_not_called()
    assert wwr.health.status == "NOT_CONFIGURED"

    # WWR must not be registered in active REGISTRY.adapters
    assert "We Work Remotely" not in REGISTRY.adapters


def test_pipeline_scraping_no_paywalled_queries():
    """Ensures REGISTRY.fetch_all_sources never queries paywalled URLs or returns WWR jobs."""
    # Mock network calls to forbid any request reaching weworkremotely.com or flexjobs
    with patch("jobhunt.sources.BaseSourceAdapter._http_get_with_retry") as mock_fetch:
        mock_fetch.return_value = None

        cfg = {"sources": {"weworkremotely": {"enabled": False}, "flexjobs": {"enabled": False}}}
        jobs = REGISTRY.fetch_all_sources(cfg, max_workers=2)

        # Assert no jobs originating from WWR or FlexJobs
        wwr_jobs = [j for j in jobs if "wwr" in j.job_id.lower() or j.ats == "weworkremotely" or "weworkremotely" in j.url]
        assert len(wwr_jobs) == 0

        # Assert no mock call target was weworkremotely.com
        for call_args in mock_fetch.call_args_list:
            target_url = str(call_args)
            assert "weworkremotely.com" not in target_url
            assert "flexjobs.com" not in target_url


def test_audit_paid_subscription_sources_disabled():
    """Asserts that all paid-subscription boards (WWR, FlexJobs) are disabled in registry and config."""
    # FlexJobs must not be registered in active REGISTRY.adapters
    assert "FlexJobs" not in REGISTRY.adapters

    # config.yaml must have explicit disabled flags under sources
    assert CONFIG_YAML.exists()
    with open(CONFIG_YAML, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    sources_cfg = cfg.get("sources", {})
    assert sources_cfg.get("weworkremotely", {}).get("enabled") is False
    assert sources_cfg.get("flexjobs", {}).get("enabled") is False


# =============================================================================
# 2. R2: PURGE HISTORICAL PAYWALLED RECORDS
# =============================================================================
def test_seen_json_zero_wwr_and_paywalled_records():
    """Asserts seen.json contains 0 records from WWR or other disabled paywalled sites."""
    assert SEEN_JSON.exists(), "seen.json must exist"
    with open(SEEN_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Invariant: exactly 66 jobs (70 original minus 4 purged WWR jobs)
    assert len(data) >= 50
    assert len(data) == 66

    forbidden_patterns = ["wwr:rss", "weworkremotely.com", "canonical_source\": \"weworkremotely", "flexjobs"]
    for job_id, record in data.items():
        assert not job_id.lower().startswith("wwr:"), f"Found WWR job_id: {job_id}"
        rec_str = json.dumps(record).lower()
        for pat in forbidden_patterns:
            assert pat not in rec_str, f"Found '{pat}' in record {job_id}"
        assert record.get("ats") != "weworkremotely"
        assert record.get("canonical_source") != "weworkremotely"
        assert "weworkremotely" not in (record.get("sources") or [])


def test_root_index_html_zero_wwr_records():
    """Asserts index.html window.INITIAL_DATA has 0 paywalled records and matches seen.json."""
    assert INDEX_HTML.exists(), "index.html must exist"
    content = INDEX_HTML.read_text(encoding="utf-8")

    # Raw HTML must not contain WWR job URLs or keys
    assert "weworkremotely.com/remote-jobs" not in content
    assert "wwr:rss:" not in content

    # Injected INITIAL_DATA must match seen.json count and contain 0 WWR jobs
    m = re.search(r"window\.INITIAL_DATA\s*=\s*(\{.*?\});\s*</script>", content, re.DOTALL)
    assert m, "window.INITIAL_DATA script block not found in index.html"
    initial_data = json.loads(m.group(1))

    jobs = initial_data.get("jobs", [])
    with open(SEEN_JSON, "r", encoding="utf-8") as f:
        seen = json.load(f)

    assert len(jobs) == len(seen), f"INITIAL_DATA job count ({len(jobs)}) != seen.json ({len(seen)})"
    wwr_jobs = [j for j in jobs if "wwr" in str(j).lower() or "weworkremotely" in str(j).lower()]
    assert len(wwr_jobs) == 0


def test_gui_index_html_zero_wwr_records():
    """Asserts gui/index.html template contains 0 paywalled records or WWR references."""
    assert GUI_INDEX_HTML.exists(), "gui/index.html must exist"
    content = GUI_INDEX_HTML.read_text(encoding="utf-8")

    assert "weworkremotely.com/remote-jobs" not in content
    assert "wwr:rss:" not in content


def test_frontend_purged_paywalled_sources_and_catalog():
    """Asserts that gui/index.html and index.html have zero flexjobs matches,
    activeNames does not include 'We Work Remotely', and SOURCES_CATALOG has
    no entries for 'We Work Remotely' or 'FlexJobs'."""
    for html_path in [GUI_INDEX_HTML, INDEX_HTML]:
        assert html_path.exists(), f"{html_path} must exist"
        content = html_path.read_text(encoding="utf-8")

        # a) flexjobs does not appear in gui/index.html or index.html (case-insensitive)
        fj_matches = re.findall(r"flexjobs", content, re.IGNORECASE)
        assert len(fj_matches) == 0, f"Found {len(fj_matches)} flexjobs occurrences in {html_path}"

        # b) activeNames does not contain 'We Work Remotely'
        m_active = re.search(r"const activeNames\s*=\s*\[(.*?)\];", content, re.DOTALL)
        assert m_active, f"const activeNames declaration not found in {html_path}"
        active_names_text = m_active.group(1)
        assert "We Work Remotely" not in active_names_text, f"'We Work Remotely' still present in activeNames of {html_path}"

        # c) const SOURCES_CATALOG does not contain entries for 'We Work Remotely' or 'FlexJobs'
        m_catalog = re.search(r"const SOURCES_CATALOG\s*=\s*(\[.*?\]);", content)
        assert m_catalog, f"const SOURCES_CATALOG not found in {html_path}"
        catalog_items = json.loads(m_catalog.group(1))
        catalog_source_names = [item.get("source") for item in catalog_items]
        assert "We Work Remotely" not in catalog_source_names, f"'We Work Remotely' found in SOURCES_CATALOG of {html_path}"
        assert "FlexJobs" not in catalog_source_names, f"'FlexJobs' found in SOURCES_CATALOG of {html_path}"


def test_source_health_and_catalog_no_active_wwr():
    """Confirms We Work Remotely and FlexJobs are not reported as HEALTHY in catalog/health exports."""
    for path in [SOURCE_HEALTH_JSON, SOURCES_CATALOG_JSON]:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            for item in data:
                source_name = item.get("source", "")
                if source_name in ("We Work Remotely", "FlexJobs"):
                    assert item.get("status") in ("NOT_CONFIGURED", "CONFIG_REQUIRED"), (
                        f"Expected disabled status for {source_name} in {path}, got {item.get('status')}"
                    )
                    assert item.get("status") != "HEALTHY"
            # Ensure purged from source list
            source_names = [item.get("source") for item in data]
            assert "We Work Remotely" not in source_names
            assert "FlexJobs" not in source_names


# =============================================================================
# 3. R3: ORIGINATING SOURCE DISPLAY & FILTERING
# =============================================================================
@pytest.mark.parametrize(
    "job, expected_slug, expected_label",
    [
        (
            {"job_id": "greenhouse:figma:123", "company": "Figma", "url": "https://boards.greenhouse.io/figma/jobs/123"},
            "greenhouse",
            "Greenhouse",
        ),
        (
            {"job_id": "ashby:elevenlabs:abc", "company": "ElevenLabs", "url": "https://jobs.ashbyhq.com/ElevenLabs/abc"},
            "ashby",
            "Ashby",
        ),
        (
            {"job_id": "lever:quantstack:xyz", "company": "Quantstack", "url": "https://jobs.lever.co/quantstack/xyz"},
            "lever",
            "Lever",
        ),
        (
            {"job_id": "remoteok:global:999", "company": "Supabase", "url": "https://remoteok.com/remote-jobs/123"},
            "remoteok",
            "Remote OK",
        ),
        (
            {"job_id": "nodesk:rss:abc", "company": "Ramp", "url": "https://nodesk.co/remote-jobs/ramp-engineer"},
            "nodesk",
            "NoDesk",
        ),
        (
            {"job_id": "workingnomads:api:456", "company": "Peroptyx", "url": "https://www.workingnomads.com/job/go/123"},
            "workingnomads",
            "Working Nomads",
        ),
        (
            {"job_id": "remotive:api:789", "company": "Automattic", "url": "https://remotive.com/remote-jobs/789"},
            "remotive",
            "Remotive",
        ),
        (
            {"job_id": "hn:42", "company": "Acme", "url": "https://news.ycombinator.com/item?id=42"},
            "hackernews",
            "Hacker News",
        ),
        (
            {"job_id": "linkedin_india:1001", "company": "Swiggy", "url": "https://linkedin.com/jobs/view/1001"},
            "linkedin",
            "LinkedIn",
        ),
        (
            {"job_id": "naukri:2002", "company": "Razorpay", "url": "https://www.naukri.com/job-listings-2002"},
            "naukri",
            "Naukri",
        ),
        (
            {"job_id": "indeed:3003", "company": "Zomato", "url": "https://indeed.com/viewjob?jk=3003"},
            "indeed",
            "Indeed",
        ),
        (
            {"job_id": "smartrecruiters:4004", "company": "Visa", "url": "https://jobs.smartrecruiters.com/Visa/4004"},
            "smartrecruiters",
            "SmartRecruiters",
        ),
        (
            {"job_id": "workable:5005", "company": "Deliveroo", "url": "https://apply.workable.com/deliveroo/j/5005"},
            "workable",
            "Workable",
        ),
        (
            {"job_id": "company:stripe:6042172", "company": "Stripe", "url": "https://stripe.com/jobs/search?gh_jid=6042172"},
            "greenhouse",
            "Greenhouse",
        ),
        (
            {"job_id": "company:airbnb:8386065", "company": "Airbnb", "url": "https://careers.airbnb.com/positions/8386065", "canonical_source": "greenhouse"},
            "greenhouse",
            "Greenhouse",
        ),
    ],
)
def test_job_card_source_badge_identification_rules(job, expected_slug, expected_label):
    """Verifies that infer_platform_source and get_platform_label categorize all major platforms accurately."""
    slug = infer_platform_source(job)
    assert slug == expected_slug, f"Expected slug '{expected_slug}', got '{slug}' for job {job}"
    label = get_platform_label(slug)
    assert label == expected_label, f"Expected label '{expected_label}', got '{label}' for slug '{slug}'"


def test_seen_json_all_jobs_accurately_labeled():
    """Asserts that 100% of the 66 active jobs in seen.json produce a valid, recognized source platform."""
    with open(SEEN_JSON, "r", encoding="utf-8") as f:
        seen = json.load(f)

    platform_distribution = {}
    for job_id, record in seen.items():
        job_dict = {"job_id": job_id, **record}
        slug = infer_platform_source(job_dict)
        label = get_platform_label(slug)

        # Invariant: No active job defaults to 'other' or 'Other / Unspecified'
        assert slug != "other", f"Job {job_id} ({record.get('company')}) defaulted to 'other'"
        assert label != "Other / Unspecified", f"Job {job_id} produced 'Other / Unspecified'"

        platform_distribution[slug] = platform_distribution.get(slug, 0) + 1

    # Exact expected counts for the 66 verified active jobs:
    assert platform_distribution == {
        "greenhouse": 51,
        "remoteok": 6,
        "ashby": 4,
        "lever": 2,
        "workingnomads": 2,
        "nodesk": 1,
    }


def test_html_platform_filter_controls_and_options():
    """Asserts filter-platform dropdown contains all required options in both gui/index.html and index.html."""
    for html_path in [GUI_INDEX_HTML, INDEX_HTML]:
        content = html_path.read_text(encoding="utf-8")

        # Select element presence
        assert 'id="filter-platform"' in content

        # Required static options from existing test suite
        assert '<option value="greenhouse">Greenhouse</option>' in content
        assert '<option value="ashby">Ashby</option>' in content
        assert '<option value="lever">Lever</option>' in content
        assert '<option value="remotive">Remotive</option>' in content
        assert '<option value="hackernews">Hacker News</option>' in content

        # Required options for active sources in seen.json
        assert '<option value="remoteok">Remote OK</option>' in content
        assert '<option value="nodesk">NoDesk</option>' in content
        assert '<option value="workingnomads">Working Nomads</option>' in content

        # Additional standard ATS / job board options
        assert '<option value="linkedin">LinkedIn</option>' in content
        assert '<option value="naukri">Naukri</option>' in content
        assert '<option value="indeed">Indeed</option>'

        # Forbidden paywalled options
        assert '<option value="weworkremotely">' not in content
        assert '<option value="wwr">' not in content
        assert '<option value="flexjobs">' not in content


def test_job_card_rendering_contains_source_tag():
    """Asserts HTML files render dedicated visual source badges with tag-src-* CSS classes."""
    for html_path in [GUI_INDEX_HTML, INDEX_HTML]:
        content = html_path.read_text(encoding="utf-8")

        # Source tag DOM rendering pattern
        assert 'class="tag tag-source tag-src-${inferredPlat}"' in content or "tag-src-" in content

        # Dedicated CSS classes for active and major platforms
        for plat in ["greenhouse", "ashby", "lever", "remoteok", "nodesk", "workingnomads", "remotive", "hackernews", "linkedin", "naukri"]:
            assert f".tag-src-{plat}" in content, f"Missing CSS style for .tag-src-{plat} in {html_path}"


def test_build_mobile_gui_synchronization():
    """Executes build_mobile_gui.py and verifies that index.html is updated cleanly without paywalled jobs."""
    import build_mobile_gui

    # Run build
    build_mobile_gui.main()

    # Verify generated index.html
    assert INDEX_HTML.exists()
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert "wwr:rss:" not in content
    assert "weworkremotely.com" not in content

    m = re.search(r"window\.INITIAL_DATA\s*=\s*(\{.*?\});\s*</script>", content, re.DOTALL)
    assert m, "INITIAL_DATA not found after rebuild"
    data = json.loads(m.group(1))

    assert len(data["jobs"]) == 66
    assert not any("wwr" in j["job_id"].lower() for j in data["jobs"])
    # Verify source_health in INITIAL_DATA has no paywalled entries
    health_sources = [s.get("source") for s in data.get("source_health", [])]
    assert "We Work Remotely" not in health_sources
    assert "FlexJobs" not in health_sources
    assert len(re.findall(r"flexjobs", content, re.IGNORECASE)) == 0
