"""Tests for digest opportunity delivery without artificial truncation.

Verifies:
  1. Default config (config.yaml) delivers all qualifying opportunities without capping at 5.
  2. select_shortlist delivers all fresh qualifying opportunities (>= 10 when available).
  3. Fresh qualifying opportunities are no longer truncated at 5.
  4. Score threshold defaults to 6.0.
  5. Digest HTML rendering accommodates all opportunities without truncation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobhunt.cli import select_shortlist, _cfg
from jobhunt.fetch import Job
from jobhunt import digest as digest_mod

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def make_scored_job(job_id: str, score: float | None, title: str = "AI Engineer") -> Job:
    return Job(
        job_id=job_id,
        ats="greenhouse",
        company="Acme Corp",
        title=title,
        location="Bengaluru, India",
        url=f"https://example.com/jobs/{job_id}",
        description="Python, SQL, Machine Learning",
        score=score,
        reason="Good fit"
    )


def test_config_defaults_accommodate_all_qualifying():
    """config.yaml must default score_threshold to 6.0 and max_per_digest to 0 (uncapped)."""
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    assert cfg.get("score_threshold") == 6.0, "score_threshold in config.yaml must be 6.0"
    assert cfg.get("max_per_digest") == 0, (
        "max_per_digest in config.yaml must be 0 to deliver all qualifying fresh opportunities"
    )
    assert cfg.get("max_per_digest") != 5, "max_per_digest must no longer be artificially capped at 5"


def test_select_shortlist_delivers_all_when_more_than_10_qualify():
    """When 15 jobs qualify, all 15 should be delivered (at least 10, no artificial truncation)."""
    cfg = {"score_threshold": 6.0, "max_per_digest": 0}
    jobs = [make_scored_job(f"job_{i}", 6.0 + (i * 0.2)) for i in range(15)]
    shortlist = select_shortlist(jobs, cfg)

    assert len(shortlist) == 15
    assert len(shortlist) >= 10
    # verify sorted descending by score
    scores = [j.score for j in shortlist]
    assert scores == sorted(scores, reverse=True)


def test_select_shortlist_delivers_all_qualifying_when_fewer_than_10_qualify():
    """When only 7 jobs qualify, exactly those 7 should be delivered without error."""
    cfg = {"score_threshold": 6.0, "max_per_digest": 0}
    qualifying = [make_scored_job(f"good_{i}", 6.5 + i * 0.1) for i in range(7)]
    disqualified = [make_scored_job(f"bad_{i}", 5.5 - i * 0.1) for i in range(5)]
    all_jobs = qualifying + disqualified

    shortlist = select_shortlist(all_jobs, cfg)
    assert len(shortlist) == 7
    assert all(j.score >= 6.0 for j in shortlist)


def test_select_shortlist_not_truncated_at_5():
    """Verify 8 qualifying jobs are not capped at 5."""
    cfg = {"score_threshold": 6.0, "max_per_digest": 0}
    jobs = [make_scored_job(f"job_{i}", 8.0) for i in range(8)]
    shortlist = select_shortlist(jobs, cfg)
    assert len(shortlist) == 8, "Expected 8 opportunities, but got truncated!"


def test_select_shortlist_legacy_cap_5_overridden_to_minimum_10():
    """If an old config with max_per_digest: 5 is supplied, ensure at least 10 opportunities when available."""
    legacy_cfg = {"score_threshold": 6.0, "max_per_digest": 5}
    jobs = [make_scored_job(f"job_{i}", 7.0 + i * 0.1) for i in range(14)]
    shortlist = select_shortlist(jobs, legacy_cfg)
    assert len(shortlist) >= 10, f"Expected at least 10 opportunities, got {len(shortlist)}"
    assert len(shortlist) == 10


def test_select_shortlist_default_score_threshold_is_6():
    """When score_threshold is omitted, default to 6.0."""
    cfg = {"max_per_digest": 0}
    j1 = make_scored_job("j1", 6.0)
    j2 = make_scored_job("j2", 5.9)
    shortlist = select_shortlist([j1, j2], cfg)
    assert len(shortlist) == 1
    assert shortlist[0].job_id == "j1"


def test_select_shortlist_empty_and_edge_cases():
    """Edge cases: empty list, all below threshold, None scores, invalid max_per_digest string."""
    cfg = {"score_threshold": 6.0}
    assert select_shortlist([], cfg) == []

    none_scored = [make_scored_job("none_1", None), make_scored_job("low_1", 3.0)]
    assert select_shortlist(none_scored, cfg) == []

    # invalid string max_per_digest safely treated as uncapped
    cfg_invalid = {"score_threshold": 6.0, "max_per_digest": "invalid"}
    jobs = [make_scored_job(f"j_{i}", 8.0) for i in range(12)]
    assert len(select_shortlist(jobs, cfg_invalid)) == 12


def test_digest_build_renders_all_qualifying_opportunities():
    """digest_mod.build should render all provided opportunities into the HTML document."""
    jobs = [make_scored_job(f"job_{i}", 8.0 + (i * 0.1), title=f"Role {i}") for i in range(12)]
    subject, html_doc = digest_mod.build(jobs, scanned=100, candidates=20, stats={"tracked": 50, "applied": 10}, name="Shubham Sunil Kadam")

    assert "12 curated jobs for you" in subject
    assert "<strong>12</strong> recommended" in html_doc
    for i in range(12):
        assert f"Role {i}" in html_doc


def test_cmd_run_integration_with_select_shortlist(tmp_path, monkeypatch):
    """End-to-end integration test of cmd_run verifying shortlist delivers all qualifying fresh jobs."""
    import json
    from jobhunt.cli import main

    test_seen = tmp_path / "seen.json"
    test_seen.write_text("{}", encoding="utf-8")
    test_digest = tmp_path / "digest.html"

    # Copy config and override paths
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    cfg["seen_file"] = str(test_seen)
    cfg["digest_file"] = str(test_digest)
    cfg["tracker_csv"] = str(tmp_path / "tracker.csv")
    cfg["source_health_file"] = str(tmp_path / "source_health.json")
    cfg["score_threshold"] = 0.0  # let keyword screened jobs qualify
    cfg["max_per_digest"] = 0     # all qualifying

    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump(cfg), encoding="utf-8")

    argv = ["--config", str(cfg_file), "run", "--mock", "--scorer", "keyword", "--no-draft"]
    ret = main(argv)
    assert ret == 0
    assert test_digest.exists()
    content = test_digest.read_text(encoding="utf-8")
    assert "<strong>5</strong> recommended" in content
    assert "Job Digest" in content


def test_select_shortlist_exact_boundary_scores():
    """Score boundary test: exact score 6.0 is included, 5.999 is excluded."""
    cfg = {"score_threshold": 6.0, "max_per_digest": 0}
    j_exact = make_scored_job("exact", 6.0)
    j_below = make_scored_job("below", 5.999)
    j_above = make_scored_job("above", 6.001)

    shortlist = select_shortlist([j_below, j_exact, j_above], cfg)
    ids = [j.job_id for j in shortlist]
    assert "exact" in ids
    assert "above" in ids
    assert "below" not in ids
    assert len(shortlist) == 2


def test_select_shortlist_exact_10_and_11_counts():
    """Verify exact 10 and 11 qualifying jobs are delivered in full without truncation."""
    cfg = {"score_threshold": 6.0, "max_per_digest": 0}
    jobs_10 = [make_scored_job(f"j10_{i}", 7.0) for i in range(10)]
    assert len(select_shortlist(jobs_10, cfg)) == 10

    jobs_11 = [make_scored_job(f"j11_{i}", 7.0) for i in range(11)]
    assert len(select_shortlist(jobs_11, cfg)) == 11


def test_select_shortlist_explicit_positive_and_negative_limits():
    """Explicit positive limit > 10 is respected; negative limit treated as uncapped."""
    jobs_20 = [make_scored_job(f"j_{i}", 7.0 + i * 0.1) for i in range(20)]

    cfg_15 = {"score_threshold": 6.0, "max_per_digest": 15}
    assert len(select_shortlist(jobs_20, cfg_15)) == 15

    cfg_neg = {"score_threshold": 6.0, "max_per_digest": -1}
    assert len(select_shortlist(jobs_20, cfg_neg)) == 20


def test_select_shortlist_none_and_invalid_score_threshold_defaults_to_6():
    """score_threshold: None, 'invalid', or boolean must safely fall back to 6.0."""
    j_qualifying = make_scored_job("j_qual", 6.5)
    j_subpar = make_scored_job("j_sub", 5.5)

    # score_threshold: None
    shortlist_none = select_shortlist([j_qualifying, j_subpar], {"score_threshold": None})
    assert len(shortlist_none) == 1
    assert shortlist_none[0].job_id == "j_qual"

    # score_threshold: "invalid"
    shortlist_str = select_shortlist([j_qualifying, j_subpar], {"score_threshold": "invalid"})
    assert len(shortlist_str) == 1
    assert shortlist_str[0].job_id == "j_qual"

    # score_threshold: True
    shortlist_bool = select_shortlist([j_qualifying, j_subpar], {"score_threshold": True})
    assert len(shortlist_bool) == 1
    assert shortlist_bool[0].job_id == "j_qual"


def test_select_shortlist_unscored_jobs_never_qualify_even_at_threshold_zero():
    """Unscored jobs (score is None, e.g. failed screening) must never be shortlisted."""
    j_unscored = make_scored_job("unscored", None)
    j_zero = make_scored_job("zero", 0.0)
    j_positive = make_scored_job("positive", 1.0)

    shortlist = select_shortlist([j_unscored, j_zero, j_positive], {"score_threshold": 0.0, "max_per_digest": 0})
    ids = [j.job_id for j in shortlist]
    assert "unscored" not in ids, "Unscored job must not qualify even when score_threshold is 0.0"
    assert "zero" in ids
    assert "positive" in ids
    assert len(shortlist) == 2


def test_select_shortlist_handles_string_scores_and_dict_jobs():
    """Robustness against string scores and dict-structured jobs."""
    j_str_score = make_scored_job("str_scored", "8.5")  # string score
    j_dict = {"job_id": "dict_job", "score": 9.0, "title": "AI Engineer"}

    shortlist = select_shortlist([j_str_score, j_dict], {"score_threshold": 6.0, "max_per_digest": 0})
    assert len(shortlist) == 2
    # Dict job with score 9.0 should come first, then str_scored with 8.5
    assert shortlist[0]["job_id"] == "dict_job"
    assert shortlist[1].job_id == "str_scored"


def test_select_shortlist_boolean_max_per_digest_treated_as_uncapped():
    """max_per_digest boolean values (True/False) should not artificially truncate to 10."""
    jobs = [make_scored_job(f"j_{i}", 7.0 + i * 0.1) for i in range(15)]

    # True should be treated as uncapped, not int(1) -> 10
    shortlist_true = select_shortlist(jobs, {"score_threshold": 6.0, "max_per_digest": True})
    assert len(shortlist_true) == 15

    # False should be treated as uncapped
    shortlist_false = select_shortlist(jobs, {"score_threshold": 6.0, "max_per_digest": False})
    assert len(shortlist_false) == 15


def test_select_shortlist_string_float_limit_parsed_properly():
    """max_per_digest string representation of floats or ints."""
    jobs = [make_scored_job(f"j_{i}", 7.0 + i * 0.1) for i in range(25)]

    shortlist_str_float = select_shortlist(jobs, {"score_threshold": 6.0, "max_per_digest": "15.0"})
    assert len(shortlist_str_float) == 15

    shortlist_float = select_shortlist(jobs, {"score_threshold": 6.0, "max_per_digest": 15.0})
    assert len(shortlist_float) == 15


def test_cmd_run_delivers_more_than_10_qualifying_opportunities_end_to_end(tmp_path, monkeypatch):
    """End-to-end integration test of cmd_run verifying >= 10 qualifying jobs are delivered in digest HTML."""
    from jobhunt.cli import main
    import jobhunt.cli as cli_mod

    test_seen = tmp_path / "seen.json"
    test_seen.write_text("{}", encoding="utf-8")
    test_digest = tmp_path / "digest.html"

    # Create 15 qualifying jobs with distinct companies and urls to avoid deduplication
    mock_15_jobs = [
        Job(
            job_id=f"mock_job_{i}",
            ats="greenhouse",
            company=f"Enterprise {i}",
            title=f"AI Engineer Level {i}",
            location="Bengaluru, India",
            url=f"https://enterprise{i}.com/jobs/{i}",
            description="Python, Machine Learning, Data Analytics",
            score=None,
        )
        for i in range(15)
    ]

    # Monkeypatch fetch_all_mock to return these 15 jobs
    monkeypatch.setattr(cli_mod, "fetch_all_mock", lambda: list(mock_15_jobs))
    # Monkeypatch prefilter to keep all 15 jobs
    monkeypatch.setattr(cli_mod, "prefilter", lambda jobs, filters: jobs)

    # Monkeypatch keyword_screen to score all 15 above threshold
    def mock_keyword_screen(jobs, profile, **_):
        for idx, j in enumerate(jobs):
            j.score = 7.0 + (idx * 0.1)
            j.fit_score = j.score
            j.reason = f"Excellent fit for role {idx}"
        return jobs

    monkeypatch.setattr(cli_mod.llm, "keyword_screen", mock_keyword_screen)

    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    cfg["seen_file"] = str(test_seen)
    cfg["digest_file"] = str(test_digest)
    cfg["tracker_csv"] = str(tmp_path / "tracker.csv")
    cfg["source_health_file"] = str(tmp_path / "source_health.json")
    cfg["score_threshold"] = 6.0
    cfg["max_per_digest"] = 0  # uncapped: deliver all qualifying fresh opportunities (minimum 10 when available)

    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump(cfg), encoding="utf-8")

    argv = ["--config", str(cfg_file), "run", "--mock", "--scorer", "keyword", "--no-draft"]
    ret = main(argv)
    assert ret == 0
    assert test_digest.exists()
    content = test_digest.read_text(encoding="utf-8")

    # Confirm subject and body reflect all 15 opportunities (at least 10, no truncation)
    assert "<strong>15</strong> recommended" in content
    for i in range(15):
        assert f"AI Engineer Level {i}" in content


def test_select_shortlist_none_jobs_and_none_cfg_safe():
    """select_shortlist must safely handle jobs=None, cfg=None, or both."""
    assert select_shortlist(None, {}) == []
    assert select_shortlist([], None) == []
    assert select_shortlist(None, None) == []

    # Valid jobs with cfg=None should use defaults (threshold 6.0, uncapped)
    jobs = [make_scored_job("j1", 7.0), make_scored_job("j2", 5.0)]
    shortlist = select_shortlist(jobs, None)
    assert len(shortlist) == 1
    assert shortlist[0].job_id == "j1"


def test_select_shortlist_inf_and_nan_max_per_digest_treated_as_uncapped():
    """max_per_digest as inf, -inf, or nan must not crash with OverflowError and must be treated as uncapped."""
    jobs = [make_scored_job(f"j_{i}", 7.0 + i * 0.1) for i in range(15)]

    # string 'inf' and float('inf')
    shortlist_str_inf = select_shortlist(jobs, {"score_threshold": 6.0, "max_per_digest": "inf"})
    assert len(shortlist_str_inf) == 15

    shortlist_float_inf = select_shortlist(jobs, {"score_threshold": 6.0, "max_per_digest": float("inf")})
    assert len(shortlist_float_inf) == 15

    # string '-inf'
    shortlist_neg_inf = select_shortlist(jobs, {"score_threshold": 6.0, "max_per_digest": "-inf"})
    assert len(shortlist_neg_inf) == 15

    # string 'nan' and float('nan')
    shortlist_str_nan = select_shortlist(jobs, {"score_threshold": 6.0, "max_per_digest": "nan"})
    assert len(shortlist_str_nan) == 15

    shortlist_float_nan = select_shortlist(jobs, {"score_threshold": 6.0, "max_per_digest": float("nan")})
    assert len(shortlist_float_nan) == 15


def test_select_shortlist_nan_and_inf_threshold_defaults_to_6():
    """score_threshold as nan or inf must safely default to 6.0."""
    j_qual = make_scored_job("qual", 7.0)
    j_subpar = make_scored_job("sub", 5.5)

    shortlist_nan = select_shortlist([j_qual, j_subpar], {"score_threshold": "nan"})
    assert len(shortlist_nan) == 1
    assert shortlist_nan[0].job_id == "qual"

    shortlist_inf = select_shortlist([j_qual, j_subpar], {"score_threshold": "inf"})
    assert len(shortlist_inf) == 1
    assert shortlist_inf[0].job_id == "qual"


def test_select_shortlist_rejects_nan_and_inf_job_scores():
    """Job scores with nan or inf must be rejected and never qualify."""
    j_nan = make_scored_job("nan_job", float("nan"))
    j_inf = make_scored_job("inf_job", float("inf"))
    j_valid = make_scored_job("valid_job", 8.0)

    shortlist = select_shortlist([j_nan, j_inf, j_valid], {"score_threshold": 6.0})
    assert len(shortlist) == 1
    assert shortlist[0].job_id == "valid_job"


def test_select_shortlist_sort_stability_with_duplicate_scores():
    """Jobs with identical scores must preserve their original encounter order (stable sort)."""
    jobs = [
        make_scored_job(f"first_seen_{i}", 8.5)
        for i in range(12)
    ]
    shortlist = select_shortlist(jobs, {"score_threshold": 6.0, "max_per_digest": 0})
    assert len(shortlist) == 12
    # Verify relative encounter order is preserved
    for i in range(12):
        assert shortlist[i].job_id == f"first_seen_{i}"


def test_select_shortlist_non_iterable_jobs_safely_returns_empty():
    """Non-iterable jobs (e.g. numbers, booleans, strings, bytes) must safely return empty list."""
    assert select_shortlist(42, {}) == []
    assert select_shortlist(True, {}) == []
    assert select_shortlist(False, {}) == []
    assert select_shortlist(3.14, {}) == []
    assert select_shortlist("some string", {}) == []
    assert select_shortlist(b"raw bytes", {}) == []


def test_select_shortlist_handles_broken_attributes_gracefully():
    """Jobs with broken properties or attributes raising exceptions are ignored without crashing."""
    class BrokenJob:
        @property
        def score(self):
            raise RuntimeError("Corrupted score property")

    valid_job = make_scored_job("valid", 8.0)
    shortlist = select_shortlist([BrokenJob(), valid_job], {"score_threshold": 6.0})
    assert len(shortlist) == 1
    assert shortlist[0].job_id == "valid"


def test_select_shortlist_supports_iterators_and_generators():
    """select_shortlist should successfully process generator and iterator streams of jobs."""
    def job_gen():
        for i in range(12):
            yield make_scored_job(f"gen_{i}", 7.0 + (i * 0.1))

    shortlist = select_shortlist(job_gen(), {"score_threshold": 6.0, "max_per_digest": 0})
    assert len(shortlist) == 12
    assert shortlist[0].job_id == "gen_11"





