"""Fetch jobs from public ATS APIs. No auth, no scraping, no ToS risk."""
from __future__ import annotations

import html
import re
import time
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Iterable

import requests

UA = {"User-Agent": "jobhunt/1.0 (personal job search agent)"}
TIMEOUT = 20

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")
_NL = re.compile(r"\n{3,}")


def strip_html(raw: str | None) -> str:
    if not raw:
        return ""
    text = html.unescape(raw)
    text = re.sub(r"<\s*(br|/p|/div|/li|/h[1-6])\s*/?>", "\n", text, flags=re.I)
    text = _TAG.sub(" ", text)
    text = html.unescape(text)
    text = _WS.sub(" ", text)
    text = _NL.sub("\n\n", text)
    return text.strip()


@dataclass
class Job:
    job_id: str          # stable global id for dedupe: "<ats>:<slug>:<id>"
    ats: str
    company: str
    title: str
    location: str
    url: str
    description: str
    posted_at: str | None = None
    salary: str | None = None
    # filled in later by the pipeline
    score: float | None = None
    reason: str | None = None
    draft: dict[str, Any] = field(default_factory=dict)

    # Normalized fields (Part 13)
    source: str = ""
    source_tier: int = 1
    country: str = ""
    remote: bool = False
    employment_type: str = ""
    experience_required: str = ""
    updated_at: str | None = None
    apply_url: str = ""
    role_families: list[str] = field(default_factory=list)
    matched_roles: list[str] = field(default_factory=list)
    matched_skills: list[str] = field(default_factory=list)
    role_confidence: float = 0.0
    fit_score: float = 0.0
    sources: list[str] = field(default_factory=list)
    canonical_source: str = ""

    def __post_init__(self) -> None:
        if not self.source:
            self.source = self.ats
        if not self.canonical_source:
            self.canonical_source = self.source
        if self.source and not self.sources:
            self.sources = [self.source]
        elif self.source and self.source not in self.sources:
            self.sources.append(self.source)
        if not self.apply_url:
            self.apply_url = self.url
        if self.score is not None and self.fit_score == 0.0:
            self.fit_score = self.score
        elif self.fit_score != 0.0 and self.score is None:
            self.score = self.fit_score

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------
# Adapters. Each takes the raw JSON body and returns list[Job].
# Keeping parse separate from HTTP is what makes offline testing possible.
# --------------------------------------------------------------------------

def parse_greenhouse(slug: str, company: str, body: Any) -> list[Job]:
    out = []
    for j in (body or {}).get("jobs", []):
        loc = (j.get("location") or {}).get("name") or ""
        out.append(Job(
            job_id=f"greenhouse:{slug}:{j.get('id')}",
            ats="greenhouse",
            company=company,
            title=(j.get("title") or "").strip(),
            location=loc.strip(),
            url=j.get("absolute_url") or "",
            description=strip_html(j.get("content")),
            posted_at=j.get("updated_at") or j.get("first_published"),
        ))
    return out


def parse_lever(slug: str, company: str, body: Any) -> list[Job]:
    out = []
    for j in (body or []):
        cats = j.get("categories") or {}
        # Lever splits the JD across descriptionPlain + a `lists` array.
        chunks = [j.get("descriptionPlain") or strip_html(j.get("description"))]
        for lst in (j.get("lists") or []):
            chunks.append(str(lst.get("text") or ""))
            chunks.append(strip_html(lst.get("content")))
        chunks.append(j.get("additionalPlain") or strip_html(j.get("additional")))
        ts = j.get("createdAt")
        posted = None
        if isinstance(ts, (int, float)):
            posted = time.strftime("%Y-%m-%d", time.gmtime(ts / 1000))
        out.append(Job(
            job_id=f"lever:{slug}:{j.get('id')}",
            ats="lever",
            company=company,
            title=(j.get("text") or "").strip(),
            location=(cats.get("location") or "").strip(),
            url=j.get("hostedUrl") or j.get("applyUrl") or "",
            description="\n\n".join(c for c in chunks if c).strip(),
            posted_at=posted,
            salary=cats.get("commitment"),
        ))
    return out


def parse_ashby(slug: str, company: str, body: Any) -> list[Job]:
    out = []
    for j in (body or {}).get("jobs", []):
        if j.get("isListed") is False:
            continue
        comp = j.get("compensation") or {}
        salary = None
        summary = comp.get("compensationTierSummary") or comp.get("summaryComponents")
        if isinstance(summary, str):
            salary = summary
        out.append(Job(
            job_id=f"ashby:{slug}:{j.get('id')}",
            ats="ashby",
            company=company,
            title=(j.get("title") or "").strip(),
            location=(j.get("location") or "").strip(),
            url=j.get("jobUrl") or j.get("applyUrl") or "",
            description=(j.get("descriptionPlain") or strip_html(j.get("descriptionHtml")) or "").strip(),
            posted_at=j.get("publishedAt"),
            salary=salary,
        ))
    return out


def extract_linkedin_job_id(raw_url_or_id: str | int | None) -> str:
    """Extract clean numeric LinkedIn job ID from URL or string."""
    s = str(raw_url_or_id or "").strip()
    if not s:
        return ""
    if s.isdigit():
        return s

    # Match /jobs/view/123456 or /jobs/view/title-slug-123456
    m = re.search(r"/jobs/view/(?:[a-zA-Z0-9\-_]+-)?(\d+)", s)
    if m:
        return m.group(1)

    # Match /view/123456 or /view/title-slug-123456
    m = re.search(r"/view/(?:[a-zA-Z0-9\-_]+-)?(\d+)", s)
    if m:
        return m.group(1)

    # Match query parameter currentJobId=123456 (case-insensitive)
    m = re.search(r"[?&]currentJobId=(\d+)", s, flags=re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"\bcurrentJobId=(\d+)", s, flags=re.IGNORECASE)
    if m:
        return m.group(1)

    # Match LinkedIn URN format: urn:li:jobPosting:123456 or urn:li:fs_normalized_jobPosting:123456
    m = re.search(r"jobPosting:(\d+)", s, flags=re.IGNORECASE)
    if m:
        return m.group(1)

    # Match standalone 8 to 12 digit number
    m = re.search(r"\b(\d{8,12})\b", s)
    if m:
        return m.group(1)

    # Fallback to sanitized alphanumeric token
    cleaned = re.sub(r"[^\w]", "", s)
    return cleaned[-16:] if len(cleaned) > 16 else cleaned


def normalize_linkedin_job(raw: dict[str, Any]) -> Job:
    """Map raw scraped LinkedIn job data into canonical Job."""
    raw_id = (
        raw.get("job_id")
        or raw.get("id")
        or raw.get("urn")
        or raw.get("url")
        or raw.get("job_url")
        or raw.get("link")
        or ""
    )
    clean_id = extract_linkedin_job_id(raw_id)
    if not clean_id:
        comp_clean = re.sub(r"[^\w]", "", str(raw.get("company", "") or raw.get("company_name", "")).lower())
        title_clean = re.sub(r"[^\w]", "", str(raw.get("title", "") or raw.get("job_title", "")).lower())
        clean_id = f"{comp_clean}_{title_clean}" if (comp_clean or title_clean) else "unknown"

    canonical_url = f"https://www.linkedin.com/jobs/view/{clean_id}"

    ext_url = (
        raw.get("apply_url")
        or raw.get("external_url")
        or raw.get("external_apply_url")
        or raw.get("company_apply_url")
        or ""
    )
    ext_url_str = str(ext_url).strip()
    if ext_url_str and not ext_url_str.startswith("https://www.linkedin.com/jobs/view/"):
        apply_url = ext_url_str
    else:
        apply_url = canonical_url

    title = str(raw.get("title") or raw.get("job_title") or "").strip()
    company = str(raw.get("company") or raw.get("company_name") or raw.get("hiring_company") or "Company").strip()
    location = str(raw.get("location") or raw.get("place") or raw.get("city") or "India").strip()
    if not location:
        location = "India"

    description = strip_html(raw.get("description") or raw.get("job_description") or raw.get("content") or "")

    raw_date = (
        raw.get("posted_at")
        or raw.get("posted_date")
        or raw.get("date_posted")
        or raw.get("post_date")
        or raw.get("listed_at")
    )
    posted_at = None
    if raw_date:
        if isinstance(raw_date, (int, float)):
            ts = raw_date / 1000 if raw_date > 1e11 else raw_date
            posted_at = time.strftime("%Y-%m-%d", time.gmtime(ts))
        elif isinstance(raw_date, str):
            raw_date_str = raw_date.strip()
            m_date = re.match(r"^(\d{4}-\d{2}-\d{2})", raw_date_str)
            if m_date:
                posted_at = m_date.group(1)
            else:
                posted_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not posted_at:
        posted_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    salary = raw.get("salary") or raw.get("compensation") or None
    if salary:
        salary = str(salary).strip() or None

    # Country inference
    country = "India"
    loc_lower = location.lower()
    if any(k in loc_lower for k in ("singapore",)):
        country = "Singapore"
    elif any(k in loc_lower for k in ("united states", "usa", "us ", " san francisco", "new york", "seattle")):
        country = "United States"
    elif any(k in loc_lower for k in ("united kingdom", "uk", "london")):
        country = "United Kingdom"
    elif any(k in loc_lower for k in ("germany", "berlin", "munich")):
        country = "Germany"
    elif any(k in loc_lower for k in ("canada", "toronto", "vancouver")):
        country = "Canada"
    elif "remote" in loc_lower and not any(k in loc_lower for k in ("india", "bangalore", "mumbai", "pune", "hyderabad", "delhi", "noida", "gurgaon", "chennai")):
        country = "Remote"

    # Remote detection
    wp = str(raw.get("workplace_type") or raw.get("workplace") or "").lower()
    title_lower = title.lower()
    is_remote = bool(
        raw.get("remote") is True
        or "remote" in wp
        or "remote" in title_lower
        or "remote" in loc_lower
        or "wfh" in loc_lower
        or "work from home" in loc_lower
        or "anywhere" in loc_lower
    )

    employment_type = str(raw.get("employment_type") or raw.get("job_type") or "Full-time").strip()
    if not employment_type:
        employment_type = "Full-time"

    return Job(
        job_id=f"linkedin:{clean_id}",
        ats="linkedin",
        company=company,
        title=title,
        location=location,
        url=canonical_url,
        description=description,
        posted_at=posted_at,
        salary=salary,
        source="linkedin",
        source_tier=2,
        country=country,
        remote=is_remote,
        employment_type=employment_type,
        apply_url=apply_url,
        canonical_source="linkedin",
        sources=["linkedin"],
    )


ENDPOINTS = {
    "greenhouse": ("https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true", parse_greenhouse),
    "lever":      ("https://api.lever.co/v0/postings/{slug}?mode=json", parse_lever),
    "ashby":      ("https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true", parse_ashby),
}


def fetch_board(ats: str, slug: str, company: str | None = None,
                session: requests.Session | None = None) -> list[Job]:
    """Hit one company's public board. Returns [] on any failure (never raises)."""
    ats_norm = (ats or "").lower().strip()
    if ats_norm not in ENDPOINTS:
        # Check if handled by source registry (SmartRecruiters, Workable, Personio, Breezy, etc.)
        try:
            from .sources import REGISTRY
            cfg_lookup = {"companies": [{"name": company or slug, "slug": slug, "ats": ats_norm}]}
            for name, adapter in REGISTRY.adapters.items():
                clean_name = name.lower().replace(" ", "").replace("_", "")
                clean_ats = ats_norm.replace(" ", "").replace("_", "")
                if clean_name == clean_ats or clean_ats in clean_name:
                    return adapter.fetch(cfg_lookup)
        except Exception as e:
            print(f"  ! {ats}/{slug} adapter lookup failed: {e}")
        print(f"  ! unsupported ATS in companies.yaml: {ats} (slug: {slug})")
        return []

    url_tpl, parser = ENDPOINTS[ats_norm]
    sess = session or requests
    try:
        r = sess.get(url_tpl.format(slug=slug), headers=UA, timeout=TIMEOUT)
        if r.status_code != 200:
            print(f"  ! {ats}/{slug} -> HTTP {r.status_code}")
            return []
        return parser(slug, company or slug, r.json())
    except Exception as e:  # dead slug, rate limit, network blip
        print(f"  ! {ats}/{slug} -> {type(e).__name__}: {e}")
        return []


def fetch_all(companies: Iterable[dict], max_workers: int = 8,
              sleep: float = 0.0) -> list[Job]:
    """Fetch boards concurrently with ThreadPoolExecutor for 5-10x speedup."""
    companies_list = list(companies)
    jobs: list[Job] = []

    def _fetch_one(c: dict) -> tuple[dict, list[Job]]:
        try:
            got = fetch_board(c.get("ats", ""), c.get("slug", ""), c.get("name"))
            return c, got
        except Exception as e:
            print(f"  ! error fetching {c.get('name') or c.get('slug')}: {e}")
            return c, []

    workers = min(max_workers, max(1, len(companies_list)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_fetch_one, c) for c in companies_list]
        for f in as_completed(futures):
            try:
                c, got = f.result()
                if got:
                    print(f"  {c.get('name') or c['slug']:<28} {len(got):>4} jobs  ({c['ats']})")
                jobs.extend(got)
            except Exception as e:
                print(f"  ! worker thread failed: {e}")

    return jobs
