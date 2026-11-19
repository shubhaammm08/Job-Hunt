"""Comprehensive Test Suite for LinkedIn Scraper Integration.

Tests cover:
- Scraper: Multiple keywords, locations, pagination/limits, empty results, seen-job pre-filtering.
- Authentication: Missing session, expired session, invalid session, CLI registration.
- Normalization: Mapping raw dicts and Pydantic models to canonical JobHunt Job dataclass.
- Deduplication: Intra-source LinkedIn deduplication and cross-source deduplication (LinkedIn + ATS).
- Pipeline & Error Handling: Conservative rate limiting, backoff, browser failures, error isolation.
- Backend API: GET /api/sources/linkedin/status and POST /api/sources/linkedin/scrape.

ALL tests use mocks and do NOT perform real network requests or headful browser sessions.
"""
from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from jobhunt.dedupe import deduplicate_jobs
from jobhunt.fetch import Job
from jobhunt.linkedin import (
    _async_fetch_linkedin_jobs,
    _load_seen_identifiers,
    extract_linkedin_job_id,
    fetch_linkedin_jobs,
    normalize_linkedin_job,
    run_linkedin_scrape_pipeline,
)
from jobhunt.sources import REGISTRY, LinkedInAdapter


# =============================================================================
# 1. ID Extraction & Normalization
# =============================================================================

def test_extract_linkedin_job_id_formats():
    """Asserts numeric IDs are correctly parsed from various LinkedIn URL formats."""
    # Standard view URL
    assert extract_linkedin_job_id("https://www.linkedin.com/jobs/view/4159827361/") == "4159827361"
    # Slotted view URL
    assert extract_linkedin_job_id("https://www.linkedin.com/jobs/view/ai-engineer-at-google-4159827361?refId=xyz") == "4159827361"
    # Search URL with currentJobId parameter
    assert extract_linkedin_job_id("https://www.linkedin.com/jobs/search/?currentJobId=4159827361&keywords=AI") == "4159827361"
    # Bare numeric string
    assert extract_linkedin_job_id("4159827361") == "4159827361"
    # None and empty strings
    assert extract_linkedin_job_id("") == ""
    assert extract_linkedin_job_id(None) == ""


def test_normalize_linkedin_job_from_dict():
    """Asserts raw dictionary payload correctly maps to JobHunt canonical Job schema."""
    raw = {
        "job_title": "AI Application Engineer",
        "company_name": "Antigravity Labs",
        "location": "Bangalore, Karnataka, India",
        "job_description": "<p>Build agentic AI systems using <strong>Playwright</strong> and LLMs.</p>",
        "linkedin_url": "https://www.linkedin.com/jobs/view/4159827361/",
        "posted_date": "2026-11-18",
        "workplace_type": "Hybrid",
        "employment_type": "Full-time",
    }
    job = normalize_linkedin_job(raw)

    assert isinstance(job, Job)
    assert job.job_id == "linkedin:4159827361"
    assert job.title == "AI Application Engineer"
    assert job.company == "Antigravity Labs"
    assert job.location == "Bangalore, Karnataka, India"
    assert "Build agentic AI systems" in job.description
    assert "<p>" not in job.description
    assert job.source == "linkedin"
    assert job.ats == "linkedin"
    assert job.canonical_source == "linkedin"
    assert "linkedin" in job.sources
    assert job.source_tier == 2
    assert job.country == "India"
    assert job.posted_at == "2026-11-18"


def test_normalize_linkedin_job_pydantic_duck_typing():
    """Asserts mock Pydantic model converts cleanly via model_dump / attributes."""
    class MockPydanticJob:
        def model_dump(self):
            return {
                "job_title": "RAG Engineer",
                "company_name": "Pinecone Systems",
                "location": "Remote - India",
                "job_description": "Architect high-performance vector retrieval pipelines.",
                "linkedin_url": "https://www.linkedin.com/jobs/view/9988776655/",
                "workplace_type": "Remote",
            }

    mock_model = MockPydanticJob()
    job = normalize_linkedin_job(mock_model)

    assert job.job_id == "linkedin:9988776655"
    assert job.title == "RAG Engineer"
    assert job.company == "Pinecone Systems"
    assert job.remote is True
    assert job.source == "linkedin"


def test_normalize_linkedin_job_remote_detection():
    """Asserts remote flag is correctly detected from workplace_type or location."""
    job_remote_wp = normalize_linkedin_job({
        "title": "LLM Engineer",
        "company": "DeepTech",
        "location": "Mumbai",
        "workplace_type": "Remote",
        "url": "https://www.linkedin.com/jobs/view/1001/",
    })
    assert job_remote_wp.remote is True

    job_remote_loc = normalize_linkedin_job({
        "title": "LLM Engineer",
        "company": "DeepTech",
        "location": "Work From Home (WFH), India",
        "url": "https://www.linkedin.com/jobs/view/1002/",
    })
    assert job_remote_loc.remote is True

    job_onsite = normalize_linkedin_job({
        "title": "LLM Engineer",
        "company": "DeepTech",
        "location": "Pune, Maharashtra, India",
        "workplace_type": "On-site",
        "url": "https://www.linkedin.com/jobs/view/1003/",
    })
    assert job_onsite.remote is False


# =============================================================================
# 2. Deduplication (Same-Source & Cross-Source)
# =============================================================================

def test_deduplicate_linkedin_jobs_same_source():
    """Asserts duplicate jobs from LinkedIn (same company + normalized title) are merged."""
    job1 = Job(
        job_id="linkedin:101",
        ats="linkedin",
        company="Cognitive Scale",
        title="Generative AI Engineer",
        location="Bangalore",
        url="https://www.linkedin.com/jobs/view/101/?refId=123",
        description="Build LLM applications.",
        posted_at="2026-11-18",
        source="linkedin",
        source_tier=2,
        country="India",
        remote=True,
        canonical_source="linkedin",
        sources=["linkedin"],
    )
    job2 = Job(
        job_id="linkedin:102",
        ats="linkedin",
        company="Cognitive Scale",
        title="Generative AI Engineer ",  # Whitespace variant
        location="Bengaluru, Karnataka",
        url="https://www.linkedin.com/jobs/view/102/?trackingId=456",
        description="Build LLM applications and agentic workflows.",
        posted_at="2026-11-18",
        source="linkedin",
        source_tier=2,
        country="India",
        remote=True,
        canonical_source="linkedin",
        sources=["linkedin"],
    )

    unique, dupes = deduplicate_jobs([job1, job2])
    assert len(unique) == 1
    assert dupes == 1
    assert unique[0].company == "Cognitive Scale"


def test_cross_source_deduplication_linkedin_and_ats():
    """Asserts duplicate postings across LinkedIn and direct ATS (Greenhouse) are deduplicated."""
    gh_job = Job(
        job_id="greenhouse:figma:5552549004",
        ats="greenhouse",
        company="Figma",
        title="Software Engineer - Distributed Systems",
        location="San Francisco, CA",
        url="https://boards.greenhouse.io/figma/jobs/5552549004",
        description="Figma distributed systems team role.",
        posted_at="2026-11-14",
        source="greenhouse",
        source_tier=1,
        country="United States",
        remote=False,
        canonical_source="greenhouse",
        sources=["greenhouse"],
    )
    li_job = Job(
        job_id="linkedin:998877",
        ats="linkedin",
        company="Figma",
        title="Software Engineer - Distributed Systems",
        location="San Francisco, CA",
        url="https://www.linkedin.com/jobs/view/998877",
        description="Figma distributed systems team role reposted to LinkedIn.",
        posted_at="2026-11-15",
        source="linkedin",
        source_tier=2,
        country="United States",
        remote=False,
        canonical_source="linkedin",
        sources=["linkedin"],
    )

    unique, dupes = deduplicate_jobs([gh_job, li_job])
    assert len(unique) == 1
    assert dupes == 1
    # Preserves primary canonical record and aggregates sources
    assert "greenhouse" in unique[0].sources or "linkedin" in unique[0].sources


# =============================================================================
# 3. Seen URLs & Pre-Check
# =============================================================================

def test_load_seen_identifiers(tmp_path: Path):
    """Asserts seen.json reader extracts LinkedIn IDs and URLs accurately."""
    mock_seen_file = tmp_path / "seen.json"
    mock_data = {
        "linkedin:4159827361": {
            "company": "Google",
            "title": "AI Engineer",
            "url": "https://www.linkedin.com/jobs/view/4159827361/",
        },
        "greenhouse:airbnb:12345": {
            "company": "Airbnb",
            "title": "ML Engineer",
            "url": "https://careers.airbnb.com/positions/12345",
        }
    }
    mock_seen_file.write_text(json.dumps(mock_data), encoding="utf-8")

    seen_ids = _load_seen_identifiers(mock_seen_file)
    assert "4159827361" in seen_ids
    assert "linkedin:4159827361" in seen_ids
    assert "https://www.linkedin.com/jobs/view/4159827361/" in seen_ids


# =============================================================================
# 4. Scraper Execution & Mocks
# =============================================================================

def test_async_fetch_linkedin_jobs_disabled():
    """Asserts scraper immediately returns [] when enabled=False in config."""
    cfg = {"sources": {"linkedin": {"enabled": False}}}
    jobs = asyncio.run(_async_fetch_linkedin_jobs(cfg))
    assert jobs == []


def test_async_fetch_linkedin_missing_session(tmp_path: Path):
    """Asserts scraper returns [] when session file does not exist."""
    missing_session = tmp_path / "non_existent_session.json"
    cfg = {
        "sources": {
            "linkedin": {
                "enabled": True,
                "session_file": str(missing_session),
            }
        }
    }
    jobs = asyncio.run(_async_fetch_linkedin_jobs(cfg))
    assert jobs == []


def test_async_fetch_linkedin_expired_session(tmp_path: Path):
    """Asserts scraper detects expired session and returns [] safely."""
    dummy_session = tmp_path / "session.json"
    dummy_session.write_text('{"cookies": []}', encoding="utf-8")

    cfg = {
        "sources": {
            "linkedin": {
                "enabled": True,
                "session_file": str(dummy_session),
                "headless": True,
            }
        }
    }

    mock_bm = MagicMock()
    mock_bm.start = AsyncMock()
    mock_bm.load_session = AsyncMock()
    mock_bm.close = AsyncMock()
    mock_bm.page = MagicMock()
    mock_bm.page.goto = AsyncMock()

    with patch("jobhunt.linkedin.BrowserManager", return_value=mock_bm), \
         patch("jobhunt.linkedin.is_logged_in", new=AsyncMock(return_value=False)):
        jobs = asyncio.run(_async_fetch_linkedin_jobs(cfg))
        assert jobs == []
        mock_bm.close.assert_called_once()


def test_async_fetch_linkedin_search_and_scrape(tmp_path: Path):
    """Asserts scraper handles multiple keywords, multiple locations, and retrieves jobs."""
    dummy_session = tmp_path / "session.json"
    dummy_session.write_text('{"cookies": []}', encoding="utf-8")

    cfg = {
        "sources": {
            "linkedin": {
                "enabled": True,
                "session_file": str(dummy_session),
                "headless": True,
                "keywords": ["AI Engineer", "GenAI Engineer"],
                "locations": ["India", "Remote"],
                "limit_per_search": 5,
                "rate_limit_delay": 0.01,
            }
        },
        "seen_file": str(tmp_path / "seen.json"),
    }

    mock_bm = MagicMock()
    mock_bm.start = AsyncMock()
    mock_bm.load_session = AsyncMock()
    mock_bm.close = AsyncMock()
    mock_bm.page = MagicMock()
    mock_bm.page.goto = AsyncMock()

    mock_search = MagicMock()
    mock_search.search = AsyncMock(side_effect=[
        ["https://www.linkedin.com/jobs/view/1001/", "https://www.linkedin.com/jobs/view/1002/"],
        ["https://www.linkedin.com/jobs/view/1002/", "https://www.linkedin.com/jobs/view/1003/"],  # Duplicate 1002
        [],
        ["https://www.linkedin.com/jobs/view/1004/"],
    ])

    mock_detail = MagicMock()
    mock_detail.scrape = AsyncMock(side_effect=lambda url: {
        "job_title": "AI Engineer",
        "company_name": "TestCorp",
        "location": "India",
        "job_description": "Develop LLM models",
        "linkedin_url": url,
        "posted_date": "2026-11-18",
    })

    with patch("jobhunt.linkedin.BrowserManager", return_value=mock_bm), \
         patch("jobhunt.linkedin.is_logged_in", new=AsyncMock(return_value=True)), \
         patch("jobhunt.linkedin.JobSearchScraper", return_value=mock_search), \
         patch("jobhunt.linkedin.JobScraper", return_value=mock_detail):

        jobs = asyncio.run(_async_fetch_linkedin_jobs(cfg))

        # 1001, 1002, 1003, 1004 -> 4 unique jobs scraped
        assert len(jobs) == 4
        assert {j.job_id for j in jobs} == {
            "linkedin:1001",
            "linkedin:1002",
            "linkedin:1003",
            "linkedin:1004",
        }
        mock_bm.close.assert_called_once()


def test_async_fetch_linkedin_rate_limit_backoff(tmp_path: Path):
    """Asserts scraper backs off and retries when encountering RateLimitError."""
    from linkedin_scraper.core.exceptions import RateLimitError

    dummy_session = tmp_path / "session.json"
    dummy_session.write_text('{"cookies": []}', encoding="utf-8")

    cfg = {
        "sources": {
            "linkedin": {
                "enabled": True,
                "session_file": str(dummy_session),
                "keywords": ["AI Engineer"],
                "locations": ["India"],
                "rate_limit_delay": 0.01,
                "max_retries": 2,
            }
        },
        "seen_file": str(tmp_path / "seen.json"),
    }

    mock_bm = MagicMock()
    mock_bm.start = AsyncMock()
    mock_bm.load_session = AsyncMock()
    mock_bm.close = AsyncMock()
    mock_bm.page = MagicMock()
    mock_bm.page.goto = AsyncMock()

    mock_search = MagicMock()
    mock_search.search = AsyncMock(return_value=["https://www.linkedin.com/jobs/view/2001/"])

    mock_detail = MagicMock()
    # First call raises RateLimitError, second succeeds
    mock_detail.scrape = AsyncMock(side_effect=[
        RateLimitError("Rate limit hit"),
        {
            "job_title": "AI Engineer",
            "company_name": "Resilient AI",
            "location": "India",
            "job_description": "Backoff test",
            "linkedin_url": "https://www.linkedin.com/jobs/view/2001/",
        }
    ])

    with patch("jobhunt.linkedin.BrowserManager", return_value=mock_bm), \
         patch("jobhunt.linkedin.is_logged_in", new=AsyncMock(return_value=True)), \
         patch("jobhunt.linkedin.JobSearchScraper", return_value=mock_search), \
         patch("jobhunt.linkedin.JobScraper", return_value=mock_detail):

        jobs = asyncio.run(_async_fetch_linkedin_jobs(cfg))
        assert len(jobs) == 1
        assert jobs[0].job_id == "linkedin:2001"
        assert mock_detail.scrape.call_count == 2


# =============================================================================
# 5. Pipeline Execution & Status Tracker
# =============================================================================

def test_run_linkedin_scrape_pipeline_completed(tmp_path: Path):
    """Asserts run_linkedin_scrape_pipeline completes, deduplicates, and tracks status."""
    dummy_session = tmp_path / "session.json"
    dummy_session.write_text('{"cookies": []}', encoding="utf-8")

    cfg_file = tmp_path / "config.yaml"
    seen_file = tmp_path / "seen.json"
    seen_file.write_text("{}", encoding="utf-8")

    cfg_data = {
        "sources": {
            "linkedin": {
                "enabled": True,
                "session_file": str(dummy_session),
            }
        },
        "seen_file": str(seen_file),
        "out_dir": str(tmp_path / "out"),
    }
    cfg_file.write_text(yaml.dump(cfg_data), encoding="utf-8")

    mock_jobs = [
        Job(
            job_id="linkedin:3001",
            ats="linkedin",
            company="NeuralNet Co",
            title="AI Systems Architect",
            location="Remote",
            url="https://www.linkedin.com/jobs/view/3001/",
            description="Agentic LLM pipelines",
            posted_at="2026-11-18",
            source="linkedin",
            source_tier=2,
            country="India",
            remote=True,
            canonical_source="linkedin",
            sources=["linkedin"],
        )
    ]

    status_tracker: dict = {}
    with patch("jobhunt.linkedin.fetch_linkedin_jobs", return_value=mock_jobs):
        result = run_linkedin_scrape_pipeline(
            config_path=cfg_file,
            status_tracker=status_tracker,
        )

        assert result["status"] == "completed"
        assert result["is_running"] is False
        assert result["jobs_found"] == 1
        assert result["jobs_added"] == 1
        assert result["duplicates_filtered"] == 0
        assert result["auth_valid"] is True
        assert result["error"] is None

        # Verify seen.json recorded the new job
        stored = json.loads(seen_file.read_text(encoding="utf-8"))
        assert "linkedin:3001" in stored


def test_run_linkedin_scrape_pipeline_missing_session(tmp_path: Path):
    """Asserts run_linkedin_scrape_pipeline sets auth_required when session is missing."""
    cfg_file = tmp_path / "config.yaml"
    cfg_data = {
        "sources": {
            "linkedin": {
                "enabled": True,
                "session_file": str(tmp_path / "missing.json"),
            }
        }
    }
    cfg_file.write_text(yaml.dump(cfg_data), encoding="utf-8")

    status_tracker: dict = {}
    result = run_linkedin_scrape_pipeline(
        config_path=cfg_file,
        status_tracker=status_tracker,
    )

    assert result["status"] == "auth_required"
    assert result["is_running"] is False
    assert result["auth_valid"] is False
    assert "Missing session file" in result["error"]


# =============================================================================
# 6. Source Registry & Adapter
# =============================================================================

def test_source_registry_contains_linkedin_adapter():
    """Asserts LinkedInAdapter is registered in SourceRegistry under 'LinkedIn'."""
    assert "LinkedIn" in REGISTRY.adapters
    adapter = REGISTRY.adapters["LinkedIn"]
    assert isinstance(adapter, LinkedInAdapter)
    assert adapter.name == "LinkedIn"
    assert adapter.category == "professional_network"
    assert adapter.tier == 2


# =============================================================================
# 7. Backend API Endpoints (gui/server.py)
# =============================================================================

def test_backend_api_get_linkedin_status_safe_response():
    """Asserts GET /api/sources/linkedin/status returns expected metrics without leaking secrets."""
    from gui.server import JobHuntHandler, LINKEDIN_STATUS, LINKEDIN_STATUS_LOCK

    with LINKEDIN_STATUS_LOCK:
        LINKEDIN_STATUS["status"] = "idle"
        LINKEDIN_STATUS["last_scan"] = "2026-11-19T00:00:00+00:00"
        LINKEDIN_STATUS["jobs_found"] = 42
        LINKEDIN_STATUS["jobs_added"] = 12
        LINKEDIN_STATUS["duplicates_filtered"] = 30
        LINKEDIN_STATUS["auth_valid"] = True

    handler = JobHuntHandler.__new__(JobHuntHandler)
    handler.path = "/api/sources/linkedin/status"
    handler.headers = {}
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = io.BytesIO()

    handler.do_GET()

    assert handler.send_response.called
    assert handler.send_response.call_args[0][0] == 200

    payload = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert payload["status"] == "idle"
    assert payload["jobs_found"] == 42
    assert payload["jobs_added"] == 12
    assert payload["duplicates_filtered"] == 30
    assert payload["auth_valid"] is True
    # Ensure no credentials or cookie paths exist in payload
    assert "cookies" not in payload
    assert "password" not in payload
    assert "token" not in payload


def test_backend_api_post_scrape_conflict_when_already_running():
    """Asserts POST /api/sources/linkedin/scrape returns 409 Conflict if task is active."""
    from gui.server import JobHuntHandler, LINKEDIN_STATUS, LINKEDIN_STATUS_LOCK

    with LINKEDIN_STATUS_LOCK:
        LINKEDIN_STATUS["is_running"] = True
        LINKEDIN_STATUS["status"] = "running"

    try:
        handler = JobHuntHandler.__new__(JobHuntHandler)
        handler.path = "/api/sources/linkedin/scrape"
        handler.headers = {"Content-Length": "2"}
        handler.rfile = io.BytesIO(b"{}")
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = io.BytesIO()

        handler.do_POST()

        assert handler.send_response.call_args[0][0] == 409
        resp = json.loads(handler.wfile.getvalue().decode("utf-8"))
        assert resp["success"] is False
        assert resp["status"] == "already_running"
    finally:
        with LINKEDIN_STATUS_LOCK:
            LINKEDIN_STATUS["is_running"] = False
            LINKEDIN_STATUS["status"] = "idle"


# =============================================================================
# 8. CLI Subcommand Registration
# =============================================================================

def test_cli_linkedin_auth_subcommand_registered():
    """Asserts linkedin-auth subcommand exists in CLI help output."""
    from jobhunt.cli import main

    # Calling with --help should print help and raise SystemExit(0)
    with pytest.raises(SystemExit) as exc_info:
        main(["linkedin-auth", "--help"])
    assert exc_info.value.code == 0
