"""Canonical Deduplication Layer for Shubham's JobHunt.

Consolidates duplicate listings across Direct ATS, Job Boards, Startup boards,
and Aggregators into a single canonical Job entry with full source provenance.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs, urlunparse
from typing import Sequence

from .fetch import Job

# Tracking query parameters to strip when computing canonical URLs
STRIP_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "source", "gh_src", "lever-source", "ashby_jid", "tracking",
    "trk", "from", "shared", "midToken", "midSig", "midtoken", "midsig",
    # LinkedIn-specific tracking parameters
    "refid", "trackingid", "position", "pagenum", "originalsubdomain",
    "currentjobid", "ebp", "recommendedflavor", "refsource"
}


def normalize_url(url: str | None) -> str:
    """Normalize apply or career URL for deduplication."""
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        qs = parse_qs(parsed.query)
        clean_qs = {k: v for k, v in qs.items() if k.lower() not in STRIP_PARAMS}
        # reassemble query
        sorted_query = "&".join(f"{k}={v[0]}" for k, v in sorted(clean_qs.items()) if v)
        path = parsed.path.rstrip("/")
        clean = urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", sorted_query, ""))
        return clean
    except Exception:
        return url.strip().rstrip("/").lower()


def normalize_title(title: str) -> str:
    """Strip level numbers, punctuation and location tags from title."""
    t = (title or "").lower()
    t = re.sub(r"[\(\[\{].*?[\)\]\}]", "", t)  # strip parentheticals e.g. (Go), [Remote]
    t = re.sub(r"\b(i{1,3}|[123]|iv|v)\b", "", t)  # strip Roman/Arabic levels
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split())


def normalize_location(location: str) -> str:
    loc = (location or "").lower()
    loc = re.sub(r"[^\w\s]", " ", loc)
    # Map common aliases
    if any(k in loc for k in ("mumbai", "powai", "thane", "navi mumbai", "andheri", "kandivali")):
        return "mumbai"
    if any(k in loc for k in ("bangalore", "bengaluru")):
        return "bangalore"
    if any(k in loc for k in ("pune", "hinjewadi")):
        return "pune"
    if any(k in loc for k in ("hyderabad", "secunderabad", "hitec")):
        return "hyderabad"
    if any(k in loc for k in ("delhi", "gurgaon", "gurugram", "noida")):
        return "delhi_ncr"
    if any(k in loc for k in ("remote", "anywhere", "wfh")):
        return "remote"
    return " ".join(loc.split())


def deduplicate_jobs(jobs: Sequence[Job]) -> tuple[list[Job], int]:
    """Merge duplicate postings across platforms using multi-stage matching.
    
    Returns:
        (canonical_jobs, duplicate_count)
    """
    by_key: dict[str, Job] = {}
    dupe_count = 0

    for j in jobs:
        # Determine candidate keys
        keys = []
        if j.job_id:
            keys.append(f"id:{j.job_id}")

        norm_url = normalize_url(j.apply_url or j.url)
        if norm_url:
            keys.append(f"url:{norm_url}")

        comp = re.sub(r"[^\w]", "", (j.company or "").lower())
        norm_t = normalize_title(j.title)
        norm_l = normalize_location(j.location)
        if comp and norm_t:
            keys.append(f"comp_title:{comp}:{norm_t}:{norm_l}")

        # Check for existing match
        matched_existing: Job | None = None
        for k in keys:
            if k in by_key:
                matched_existing = by_key[k]
                break

        if matched_existing is not None:
            dupe_count += 1
            # Merge sources list
            src = j.source or j.ats
            if src and src not in matched_existing.sources:
                matched_existing.sources.append(src)

            # Compare source tiers (Tier 1 is highest priority)
            if (j.source_tier or 4) < (matched_existing.source_tier or 4):
                # Promote j as the canonical metadata holder
                matched_existing.canonical_source = j.canonical_source or j.source or j.ats
                matched_existing.source_tier = j.source_tier
                if j.url:
                    matched_existing.url = j.url
                if j.apply_url:
                    matched_existing.apply_url = j.apply_url

            # Retain longer description if available
            if len(j.description or "") > len(matched_existing.description or ""):
                matched_existing.description = j.description
        else:
            # First time seeing this job
            if not j.canonical_source:
                j.canonical_source = j.source or j.ats
            if j.canonical_source and j.canonical_source not in j.sources:
                j.sources.append(j.canonical_source)
            for k in keys:
                by_key[k] = j

    # Collect unique Job instances preserving order
    unique_jobs: list[Job] = []
    seen_instances = set()
    for j in by_key.values():
        if id(j) not in seen_instances:
            seen_instances.add(id(j))
            unique_jobs.append(j)

    return unique_jobs, dupe_count
