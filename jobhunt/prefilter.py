"""Intelligent Deterministic Filter for Shubham's JobHunt.

Applies role taxonomy classification, false-positive guardrails, seniority gating,
location normalization (Mumbai, Pune, Bangalore, Hyderabad, Delhi NCR, Remote),
and posting freshness BEFORE any LLM evaluation.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from .fetch import Job
from .roles import classify_job

REMOTE_HINTS = (
    "remote", "anywhere", "work from home", "wfh", "distributed"
)

SENIOR_HARD_EXCLUDES = re.compile(
    r"\b(director|vp|vice\s+president|head\s+of|chief|cto|cio|ciso|general\s+manager)\b",
    re.I
)


def is_senior_experience(exp_str: str) -> bool:
    """Check if experience requirement indicates a 5+ year senior position."""
    if not exp_str:
        return False
    m_range = re.search(r"(\d+)\s*[-–to]+\s*(\d+)", exp_str)
    if m_range:
        return int(m_range.group(1)) >= 5
    m_single = re.search(r"(\d+)\+?\s*(?:years?|yrs?)", exp_str, re.I)
    if m_single:
        return int(m_single.group(1)) >= 5
    return False


def _any_match(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    v = value.replace("Z", "+00:00")
    for fmt in (None, "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.fromisoformat(v) if fmt is None else datetime.strptime(v, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def is_location_match(job_location: str, job_title: str, locs: list[str], allow_remote: bool) -> tuple[bool, bool]:
    """Check location criteria with Part 21 hub awareness."""
    loc_hay = f"{job_location or ''}".lower()
    is_remote = any(h in loc_hay for h in REMOTE_HINTS)

    if not locs:
        return True, is_remote

    if is_remote:
        if allow_remote:
            return True, True
        # If allow_remote is False, remote role only passes if it explicitly contains an allowed location
        for loc in locs:
            if re.search(rf"\b{re.escape(loc.strip())}\b", loc_hay):
                return True, True
        return False, True

    # Check against configured location targets
    for loc in locs:
        l_clean = loc.lower().strip()
        if re.search(rf"\b{re.escape(l_clean)}\b", loc_hay):
            return True, False

    return False, False


def prefilter(jobs: list[Job], cfg: dict[str, Any]) -> list[Job]:
    # Empty cfg means keep everything (for tests)
    if not cfg:
        return list(jobs)

    inc = cfg.get("include_titles")
    exc = cfg.get("exclude_titles") or []
    locs = [l.lower() for l in (cfg.get("locations") or [])]
    allow_remote = bool(cfg.get("allow_remote", True))
    max_age = cfg.get("max_age_days")
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age) if max_age else None

    kept: list[Job] = []
    stats = {"title": 0, "location": 0, "age": 0}

    for j in jobs:
        # 1. Intelligent Role Classification Layer (Part 2)
        classification = classify_job(j.title, j.description)
        j.matched_roles = classification["matched_roles"]
        j.role_families = classification["role_families"]
        j.role_confidence = classification["role_confidence"]
        j.matched_skills = classification["matched_skills"]
        if classification.get("experience_required"):
            j.experience_required = classification["experience_required"]

        # 2. Guardrails: Filter out non-software false positives (e.g. civil/mechanical/data center)
        if classification.get("is_false_positive"):
            stats["title"] += 1
            continue

        # 3. Role Matching
        if inc:
            role_matched = _any_match(inc, j.title)
            if not role_matched:
                stats["title"] += 1
                continue

        # 4. Seniority Gating (Part 20)
        if exc and _any_match(exc, j.title):
            stats["title"] += 1
            continue

        if SENIOR_HARD_EXCLUDES.search(j.title):
            stats["title"] += 1
            continue

        if j.experience_required and is_senior_experience(j.experience_required):
            stats["title"] += 1
            continue

        # 5. Location Filtering (Part 21)
        loc_ok, is_rem = is_location_match(j.location, j.title, locs, allow_remote)
        if is_rem:
            j.remote = True
        if not loc_ok:
            stats["location"] += 1
            continue

        # 6. Freshness Filter
        if cutoff:
            posted = _parse_date(j.posted_at)
            if posted and posted < cutoff:
                stats["age"] += 1
                continue

        kept.append(j)

    print(f"  prefilter: {len(jobs)} -> {len(kept)} "
          f"(dropped title={stats['title']} location={stats['location']} stale={stats['age']})")
    return kept
