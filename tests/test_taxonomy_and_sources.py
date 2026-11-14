"""Unit and Integration Tests for Role Taxonomy, False-Positive Guardrails,
Canonical Deduplication, and Source Adapters.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobhunt.fetch import Job
from jobhunt.roles import classify_job, extract_experience, ROLE_TAXONOMY
from jobhunt.dedupe import deduplicate_jobs, normalize_url, normalize_title, normalize_location
from jobhunt.prefilter import is_senior_experience, prefilter
from jobhunt.sources import REGISTRY, BaseSourceAdapter


# =============================================================================
# 1. TAXONOMY CLASSIFICATION ACROSS ALL 12 FAMILIES
# =============================================================================

@pytest.mark.parametrize("title,expected_family", [
    ("Senior AI Engineer", "AI_CORE"),
    ("Applied Machine Learning Engineer", "AI_CORE"),
    ("GenAI Engineer", "GENAI_AGENTIC"),
    ("LLM Application Developer", "GENAI_AGENTIC"),
    ("AI Agent Engineer", "GENAI_AGENTIC"),
    ("Forward Deployed Engineer", "DEPLOYMENT"),
    ("AI FDE", "DEPLOYMENT"),
    ("Junior Data Analyst", "DATA"),
    ("Business Intelligence Analyst", "DATA"),
    ("Python Backend Developer", "SOFTWARE"),
    ("Junior Software Engineer", "SOFTWARE"),
    ("MLOps Engineer", "PLATFORM"),
    ("DevOps Engineer", "CLOUD_DEVOPS"),
    ("Site Reliability Engineer", "CLOUD_DEVOPS"),
    ("AI Automation Developer", "AUTOMATION"),
    ("RPA Engineer", "AUTOMATION"),
    ("Cybersecurity Analyst", "SECURITY"),
    ("SDET", "QA_TESTING"),
    ("QA Automation Engineer", "QA_TESTING"),
    ("Technical Solutions Engineer", "PRODUCT_TECH"),
    ("Application Support Engineer", "OTHER_TECH"),
])
def test_taxonomy_classification_covers_all_families(title, expected_family):
    res = classify_job(title)
    assert not res["is_false_positive"]
    assert expected_family in res["role_families"], f"{title} did not match {expected_family}: {res}"
    assert res["role_confidence"] > 0.6


def test_taxonomy_complete_12_families_exist():
    expected = {
        "AI_CORE", "GENAI_AGENTIC", "DEPLOYMENT", "DATA", "SOFTWARE",
        "PLATFORM", "CLOUD_DEVOPS", "AUTOMATION", "SECURITY", "QA_TESTING",
        "PRODUCT_TECH", "OTHER_TECH"
    }
    assert set(ROLE_TAXONOMY.keys()) == expected


# =============================================================================
# 2. FALSE POSITIVE GUARDRAILS
# =============================================================================

@pytest.mark.parametrize("fp_title", [
    "Data Center Engineer",
    "Data Center Technician",
    "Civil Engineer",
    "Mechanical Engineer",
    "Electrical Engineer",
    "Sales Engineer",
    "Hardware Design Engineer",
    "Structural Engineer",
    "Chemical Engineer",
    "Aerospace Engineer",
])
def test_false_positive_guardrails_reject_non_software_engineering(fp_title):
    res = classify_job(fp_title)
    assert res["is_false_positive"] is True
    assert res["role_confidence"] == 0.0
    assert len(res["matched_roles"]) == 0


# =============================================================================
# 3. SENIORITY & EXPERIENCE GATING
# =============================================================================

@pytest.mark.parametrize("exp_str,is_senior", [
    ("0-2 years", False),
    ("1–3 years", False),
    ("2–5 years", False),
    ("fresher", False),
    ("entry level", False),
    ("3+ years", False),
    ("5+ years", True),
    ("5–8 years", True),
    ("7+ years", True),
    ("10+ years", True),
])
def test_senior_experience_gating(exp_str, is_senior):
    assert is_senior_experience(exp_str) == is_senior


def test_extract_experience_patterns():
    assert extract_experience("Requires 2-4 years experience in Python") == "2–4 years"
    assert extract_experience("Looking for a fresher or new grad") == "0–1 years"
    assert extract_experience("Must have 5+ years of experience") == "5+ years"


# =============================================================================
# 4. CANONICAL DEDUPLICATION
# =============================================================================

def test_deduplication_promotes_tier1_canonical_and_merges_sources():
    job_board = Job(
        job_id="remotive:12345",
        ats="remotive",
        source="Remotive",
        source_tier=3,
        company="Databricks",
        title="Software Engineer, Data Systems",
        location="Remote (India)",
        url="https://remotive.com/jobs/12345?utm_source=feed",
        apply_url="https://boards.greenhouse.io/databricks/jobs/999888",
        description="Short board summary"
    )

    direct_ats = Job(
        job_id="greenhouse:databricks:999888",
        ats="greenhouse",
        source="Greenhouse",
        source_tier=1,
        company="Databricks",
        title="Software Engineer, Data Systems",
        location="Bangalore, India",
        url="https://boards.greenhouse.io/databricks/jobs/999888?gh_src=custom",
        apply_url="https://boards.greenhouse.io/databricks/jobs/999888",
        description="Full extensive job description with deep tech stack and qualifications."
    )

    unique, dupes = deduplicate_jobs([job_board, direct_ats])
    assert dupes == 1
    assert len(unique) == 1

    canonical = unique[0]
    # Tier 1 should be preferred as canonical source
    assert canonical.source_tier == 1
    assert canonical.canonical_source in ("Greenhouse", "greenhouse")
    assert "Remotive" in canonical.sources
    assert len(canonical.description) > 30


def test_url_normalization_strips_utm_and_trackers():
    url = "https://boards.greenhouse.io/openai/jobs/123?utm_source=linkedin&ref=tracker&gh_src=feed"
    norm = normalize_url(url)
    assert "utm_source" not in norm
    assert "gh_src" not in norm
    assert "https://boards.greenhouse.io/openai/jobs/123" in norm


# =============================================================================
# 5. SOURCE ADAPTER REGISTRY & HEALTH MONITORING
# =============================================================================

def test_registry_contains_all_major_categories():
    categories = {ad.category for ad in REGISTRY.adapters.values()}
    assert "direct_ats" in categories
    assert "remote" in categories
    assert "startup" in categories
    assert "india_job_board" in categories
    assert "global_job_board" in categories
    assert "fresher" in categories
    assert "ai_specific" in categories


def test_source_health_export_valid_json(tmp_path):
    health_file = tmp_path / "source_health.json"
    exported_path = REGISTRY.export_health(health_file)
    assert exported_path.exists()

    data = json.loads(exported_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 80

    for item in data:
        assert "source" in item
        assert "category" in item
        assert "tier" in item
        assert item["status"] in ("HEALTHY", "DEGRADED", "CONFIG_REQUIRED", "NOT_CONFIGURED")
