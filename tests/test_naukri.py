"""Unit and integration tests for Naukri.com scraper and adapter."""
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jobhunt.fetch import Job
from jobhunt.naukri import (
    clean_naukri_id,
    normalize_naukri_job,
    extract_naukri_api_response,
    parse_cookie_string,
    load_naukri_cookies,
    save_naukri_cookie_session,
    fetch_naukri_jobs,
    parse_naukri_dataset,
    naukri_dataset_jobs,
    infer_naukri_posted_date,
)
from jobhunt.sources import SourceRegistry, NaukriAdapter


MOCK_NAUKRI_JOB_RAW = {
    "jobId": "061123006487",
    "title": "Junior Python Developer",
    "companyName": "TechCorp India",
    "footerPlaceholderLabel": "1 Day Ago",
    "tagsAndSkills": "Python, Django, FastAPI, SQL, REST APIs",
    "placeholders": [
        {"type": "experience", "label": "0-2 Yrs"},
        {"type": "salary", "label": "6-8 Lacs PA"},
        {"type": "location", "label": "Bangalore/ Bengaluru, Karnataka (Remote)"}
    ],
    "jobDescription": "<p>Looking for a talented <b>Junior Python Developer</b> skilled in FastAPI and PostgreSQL.</p>",
    "staticUrl": "job-listings-junior-python-developer-techcorp-061123006487"
}


def test_clean_naukri_id():
    assert clean_naukri_id("061123006487") == "061123006487"
    assert clean_naukri_id("job_061123006487_item") == "061123006487"
    assert clean_naukri_id("N/A") == ""
    assert clean_naukri_id("") == ""


def test_normalize_naukri_job_full():
    job = normalize_naukri_job(MOCK_NAUKRI_JOB_RAW)

    assert isinstance(job, Job)
    assert job.job_id == "naukri:061123006487"
    assert job.ats == "naukri"
    assert job.company == "TechCorp India"
    assert job.title == "Junior Python Developer"
    assert "Bangalore" in job.location
    assert job.remote is True
    assert job.salary == "6-8 Lacs PA"
    assert job.experience_required == "0-2 Yrs"
    assert job.country == "India"
    assert job.source == "naukri"
    assert job.source_tier == 2
    assert "FastAPI" in job.description
    assert "<p>" not in job.description  # HTML stripped
    assert "https://www.naukri.com/job-listings-junior-python-developer-techcorp-061123006487" in job.url
    assert any("Python" in s for s in job.matched_skills)


def test_normalize_naukri_job_minimal():
    raw = {
        "Job ID": "12345678",
        "Job Title": "Data Analyst Intern",
        "Company Name": "Analytics Co",
        "Location": "Mumbai",
        "Experience": "Fresher",
        "Salary": "Not disclosed",
        "Job Description": "Analyzing data with SQL and Power BI",
        "Tags and Skills": "SQL, Power BI, Excel"
    }
    job = normalize_naukri_job(raw)

    assert job.job_id == "naukri:12345678"
    assert job.company == "Analytics Co"
    assert job.title == "Data Analyst Intern"
    assert job.location == "Mumbai"
    assert job.salary is None  # 'Not disclosed' filtered to None
    assert job.url == "https://www.naukri.com/job-listings-12345678"


def test_extract_naukri_api_response():
    data = {
        "jobDetails": [
            MOCK_NAUKRI_JOB_RAW,
            {
                "jobId": "9988776655",
                "title": "Machine Learning Engineer",
                "companyName": "AI Labs",
                "placeholders": [
                    {"type": "location", "label": "Pune"},
                    {"type": "experience", "label": "1-3 Yrs"}
                ],
                "jobDescription": "Build LLM and PyTorch models."
            }
        ]
    }
    jobs = extract_naukri_api_response(data)
    assert len(jobs) == 2
    assert jobs[0].job_id == "naukri:061123006487"
    assert jobs[1].job_id == "naukri:9988776655"
    assert jobs[1].company == "AI Labs"


def test_extract_naukri_api_response_malformed():
    assert extract_naukri_api_response({}) == []
    assert extract_naukri_api_response({"jobDetails": None}) == []
    assert extract_naukri_api_response({"jobDetails": "not_a_list"}) == []


def test_cookie_parsing_and_session(tmp_path):
    cookie_str = "_abck=12345XYZ; bm_sz=67890ABC; nauk_at=secret_token"
    parsed = parse_cookie_string(cookie_str)
    assert parsed["_abck"] == "12345XYZ"
    assert parsed["bm_sz"] == "67890ABC"
    assert parsed["nauk_at"] == "secret_token"

    session_file = tmp_path / "session_naukri.json"
    ok = save_naukri_cookie_session(cookie_str, str(session_file))
    assert ok is True
    assert session_file.exists()

    loaded = load_naukri_cookies(str(session_file))
    assert loaded["_abck"] == "12345XYZ"
    assert loaded["nauk_at"] == "secret_token"


def test_naukri_adapter_in_registry():
    registry = SourceRegistry()
    assert "Naukri" in registry.adapters
    adapter = registry.adapters["Naukri"]
    assert isinstance(adapter, NaukriAdapter)
    assert adapter.category == "india_job_board"
    assert adapter.tier == 2


def test_naukri_ci_skip(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    adapter = NaukriAdapter()
    config = {
        "sources": {
            "naukri": {
                "enabled": True,
                "run_in_ci": False
            }
        }
    }
    jobs = adapter.fetch(config)
    assert jobs == []
    assert adapter.health.status == "NOT_CONFIGURED"
    assert any("Skipped in CI" in err for err in adapter.health.errors)


def test_naukri_missing_cookies_falls_back_to_guest(monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("NAUKRI_COOKIE", raising=False)
    non_existent = tmp_path / "does_not_exist.json"

    adapter = NaukriAdapter()
    config = {
        "sources": {
            "naukri": {
                "enabled": True,
                "run_in_ci": True,
                "session_file": str(non_existent)
            }
        }
    }
    with patch("jobhunt.naukri.fetch_naukri_guest_browser", return_value=[normalize_naukri_job(MOCK_NAUKRI_JOB_RAW)]):
        jobs = adapter.fetch(config)
        assert len(jobs) == 1
        assert jobs[0].job_id == "naukri:061123006487"
        assert adapter.health.status == "HEALTHY"


def test_fetch_naukri_jobs_mock_api(monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    session_file = tmp_path / "session_naukri.json"
    save_naukri_cookie_session("_abck=test; nauk_at=test", str(session_file))

    config = {
        "sources": {
            "naukri": {
                "enabled": True,
                "run_in_ci": True,
                "session_file": str(session_file),
                "keywords": ["Python Developer"],
                "max_pages_per_search": 1,
                "limit_per_search": 10
            }
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "jobDetails": [MOCK_NAUKRI_JOB_RAW]
    }

    with patch("requests.get", return_value=mock_resp):
        jobs = fetch_naukri_jobs(config)
        assert len(jobs) == 1
        assert jobs[0].job_id == "naukri:061123006487"
        assert jobs[0].title == "Junior Python Developer"


DATASET_SAMPLE = """Job ID: 061123006487
Job Title: Databricks Developer :: Full Time :: Work from Office
Company Name: AXIS DIRECT
Footer Placeholder Label: 1 Day Ago
Tags and Skills: Pyspark,Azure Databricks,Data Bricks
Experience: 7-9 Yrs
Salary: Not disclosed
Location: Bangalore/ Bengaluru, Karnataka(Shivaji Nagar)
Job Description: Looking for a <b>Databricks</b> developer with Pyspark.

Job ID: 021123500486
Job Title: Google Workspace Developer
Company Name: Tracxn
Footer Placeholder Label: 1 Day Ago
Tags and Skills: JavaScript,Google Workspace
Experience: 1-3 Yrs
Salary: 6-8 Lacs PA
Location: Bangalore/Bengaluru
Job Description: Build Google Workspace add-ons.

"""


def test_parse_naukri_dataset_maps_fields_and_dedupes():
    records = parse_naukri_dataset(DATASET_SAMPLE + DATASET_SAMPLE)
    assert len(records) == 2
    assert records[0]["Job ID"] == "061123006487"
    assert records[0]["Tags and Skills"].startswith("Pyspark")
    assert records[1]["Company Name"] == "Tracxn"


def test_naukri_dataset_jobs_normalize_to_canonical_jobs():
    jobs = naukri_dataset_jobs(DATASET_SAMPLE)
    assert len(jobs) == 2
    first = jobs[0]
    assert first.job_id == "naukri:061123006487"
    assert first.source == "naukri"
    assert "<b>" not in first.description
    assert "Databricks" in first.description
    assert first.salary is None
    assert first.experience_required == "7-9 Yrs"


def test_infer_naukri_posted_date():
    assert infer_naukri_posted_date("naukri:061123006487") == "2023-11-06"
    assert infer_naukri_posted_date("naukri:250823010280") == "2023-08-25"
    assert infer_naukri_posted_date("naukri:061126009576") == "2026-11-06"
    assert infer_naukri_posted_date("not-a-naukri-id") is None


def test_cli_naukri_import_dataset_records_historical_jobs(tmp_path):
    from jobhunt.cli import main as cli_main

    dataset = tmp_path / "naukri.txt"
    dataset.write_text(DATASET_SAMPLE, encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.write_text("seen_file: seen.json\n", encoding="utf-8")
    seen = tmp_path / "seen.json"
    base = ["--config", str(config), "naukri-import", "--file", str(dataset),
            "--seen", str(seen), "--no-score"]

    assert cli_main(base + ["--dry-run"]) == 0
    assert not seen.exists()

    assert cli_main(base) == 0
    data = json.loads(seen.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data["naukri:061123006487"]["first_seen"].startswith("2023-11-06")

    assert cli_main(base) == 0
    assert len(json.loads(seen.read_text(encoding="utf-8"))) == 2

