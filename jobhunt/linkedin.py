"""LinkedIn Scraper Engine and Integration for JobHunt.

Powered by Playwright and linkedin-scraper (v3+). Provides session management,
defensive crawling with exponential backoff and jitter, seen-URL pre-filtering,
synchronous execution bridge, interactive headful authentication CLI, and
background pipeline execution for GUI/API servers.
"""
from __future__ import annotations

import asyncio
import contextlib
import html
import json
import logging
import math
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .fetch import Job, strip_html

logger = logging.getLogger("jobhunt.linkedin")

# Safely import linkedin_scraper and playwright components
try:
    from linkedin_scraper.core.browser import BrowserManager
    from linkedin_scraper.scrapers.job_search import JobSearchScraper
    from linkedin_scraper.scrapers.job import JobScraper
    from linkedin_scraper.core.auth import is_logged_in, wait_for_manual_login
    from linkedin_scraper.core.exceptions import (
        AuthenticationError,
        RateLimitError,
        LinkedInScraperException,
        ScrapingError,
        NetworkError,
    )
except ImportError:
    BrowserManager = None  # type: ignore
    JobSearchScraper = None  # type: ignore
    JobScraper = None  # type: ignore
    is_logged_in = None  # type: ignore
    wait_for_manual_login = None  # type: ignore
    AuthenticationError = Exception  # type: ignore
    RateLimitError = Exception  # type: ignore
    LinkedInScraperException = Exception  # type: ignore
    ScrapingError = Exception  # type: ignore
    NetworkError = Exception  # type: ignore


# -----------------------------------------------------------------------------
# Normalization & ID Extraction Helpers
# -----------------------------------------------------------------------------
def extract_linkedin_job_id(raw_url_or_id: str | None) -> str:
    """Extract clean numeric LinkedIn job ID from URL or string."""
    s = str(raw_url_or_id or "").strip()
    if s.isdigit():
        return s
    m = re.search(r"/view/(?:[^/]+-)?(\d+)", s)
    if m:
        return m.group(1)
    m = re.search(r"currentJobId=(\d+)", s)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d{9,12})\b", s)
    if m:
        return m.group(1)
    cleaned = re.sub(r"[^\w]", "", s)
    return cleaned[-16:] if len(cleaned) > 16 else cleaned


def normalize_linkedin_job(raw: dict[str, Any] | Any) -> Job:
    """Normalize raw LinkedIn scraped data into canonical JobHunt Job dataclass."""
    if isinstance(raw, dict):
        raw_dict = dict(raw)
    elif hasattr(raw, "model_dump"):
        raw_dict = raw.model_dump()
    elif hasattr(raw, "to_dict"):
        raw_dict = raw.to_dict()
    elif hasattr(raw, "__dict__"):
        raw_dict = dict(vars(raw))
    else:
        raw_dict = {}

    # Bridge linkedin_scraper model field names to standard raw keys
    if "linkedin_url" in raw_dict:
        if not raw_dict.get("url"):
            raw_dict["url"] = raw_dict["linkedin_url"]
        if not raw_dict.get("job_id"):
            clean_lid = extract_linkedin_job_id(raw_dict["linkedin_url"])
            if clean_lid:
                raw_dict["job_id"] = clean_lid
    if "job_title" in raw_dict and not raw_dict.get("title"):
        raw_dict["title"] = raw_dict["job_title"]
    if "company_name" in raw_dict and not raw_dict.get("company"):
        raw_dict["company"] = raw_dict["company_name"]
    if "job_description" in raw_dict and not raw_dict.get("description"):
        raw_dict["description"] = raw_dict["job_description"]

    try:
        from .fetch import normalize_linkedin_job as _fetch_normalize
        return _fetch_normalize(raw_dict)
    except (ImportError, AttributeError):
        pass

    return _internal_normalize_linkedin_job(raw_dict)


def _internal_normalize_linkedin_job(raw: dict[str, Any] | Any) -> Job:
    """Fallback normalization converting dict or Pydantic/dataclass models to Job."""
    if isinstance(raw, dict):
        raw_dict = raw
    elif hasattr(raw, "model_dump"):
        raw_dict = raw.model_dump()
    elif hasattr(raw, "to_dict"):
        raw_dict = raw.to_dict()
    elif hasattr(raw, "__dict__"):
        raw_dict = vars(raw)
    else:
        raw_dict = {}

    url = (
        raw_dict.get("linkedin_url")
        or raw_dict.get("url")
        or raw_dict.get("job_url")
        or ""
    )
    raw_id = (
        raw_dict.get("job_id")
        or raw_dict.get("id")
        or raw_dict.get("urn")
        or extract_linkedin_job_id(url)
    )
    clean_id = extract_linkedin_job_id(str(raw_id))
    if not clean_id:
        comp_s = re.sub(r"[^\w]", "", str(raw_dict.get("company", "")).lower())
        title_s = re.sub(r"[^\w]", "", str(raw_dict.get("job_title") or raw_dict.get("title", "")).lower())
        clean_id = f"{comp_s}_{title_s}" if (comp_s or title_s) else str(random.randint(100000000, 999999999))

    canonical_url = url or f"https://www.linkedin.com/jobs/view/{clean_id}"
    apply_url = raw_dict.get("apply_url") or raw_dict.get("external_url") or canonical_url

    title = str(raw_dict.get("job_title") or raw_dict.get("title") or "").strip()
    company = str(raw_dict.get("company") or raw_dict.get("company_name") or "Company").strip()
    location = str(raw_dict.get("location") or raw_dict.get("place") or "India").strip()
    desc_raw = raw_dict.get("job_description") or raw_dict.get("description") or ""
    description = strip_html(desc_raw)

    raw_date = raw_dict.get("posted_date") or raw_dict.get("posted_at") or raw_dict.get("date_posted")
    if raw_date and isinstance(raw_date, str) and re.match(r"^\d{4}-\d{2}-\d{2}", raw_date):
        posted_at = raw_date[:10]
    else:
        posted_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    salary = raw_dict.get("salary") or raw_dict.get("compensation") or None
    wp = str(raw_dict.get("workplace_type") or "").lower()
    is_remote = bool(
        raw_dict.get("remote")
        or "remote" in wp
        or "remote" in location.lower()
        or "wfh" in location.lower()
    )

    role_families = []
    matched_roles = []
    matched_skills = []
    role_confidence = 0.0
    experience_required = ""
    try:
        from .roles import classify_job
        classification = classify_job(title, description)
        matched_roles = classification.get("matched_roles", [])
        role_families = classification.get("role_families", [])
        matched_skills = classification.get("matched_skills", [])
        role_confidence = classification.get("role_confidence", 0.0)
        experience_required = classification.get("experience_required", "")
    except Exception:
        pass

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
        country="India",
        remote=is_remote,
        employment_type=str(raw_dict.get("employment_type") or "Full-time"),
        apply_url=apply_url,
        canonical_source="linkedin",
        sources=["linkedin"],
        role_families=role_families,
        matched_roles=matched_roles,
        matched_skills=matched_skills,
        role_confidence=role_confidence,
        experience_required=experience_required,
    )


# -----------------------------------------------------------------------------
# Async Execution Bridge Helper
# -----------------------------------------------------------------------------
def _run_async(coro: Any) -> Any:
    """Run an async coroutine synchronously, safely handling running loops."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


# -----------------------------------------------------------------------------
# Seen URLs & Pre-Check
# -----------------------------------------------------------------------------
def _load_seen_identifiers(seen_file: str | Path = "seen.json") -> set[str]:
    """Extract seen job IDs and URLs from seen.json for pre-scrape skipping."""
    seen: set[str] = set()
    path = Path(seen_file)
    if not path.exists():
        return seen

    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        if isinstance(data, dict):
            for k, v in data.items():
                seen.add(str(k))
                if str(k).startswith("linkedin:"):
                    clean = str(k).split("linkedin:", 1)[1]
                    seen.add(clean)
                if isinstance(v, dict):
                    u = v.get("url") or ""
                    if u:
                        seen.add(str(u))
                        clean = extract_linkedin_job_id(u)
                        if clean:
                            seen.add(clean)
                            seen.add(f"linkedin:{clean}")
    except Exception as e:
        logger.debug("Could not inspect seen file '%s': %s", seen_file, e)
    return seen


# -----------------------------------------------------------------------------
# DOM & Page Detail Fallback Extractor
# -----------------------------------------------------------------------------
async def _extract_details_from_page(page: Any, url: str) -> dict[str, Any]:
    """Defensive fallback extractor directly inspecting page DOM and title."""
    title = ""
    company = ""
    location = "India"
    description = ""
    workplace_type = "On-site"
    employment_type = "Full-time"

    try:
        page_title = await page.title()
        if "|" in page_title:
            parts = [p.strip() for p in page_title.split("|")]
            if len(parts) >= 3 and parts[-1].lower() == "linkedin":
                title = parts[0]
                company = parts[1]
            elif len(parts) >= 2:
                title = parts[0]
                company = parts[1]
    except Exception:
        pass

    try:
        if not title:
            for sel in [
                ".job-details-jobs-unified-top-card__job-title",
                ".jobs-unified-top-card__job-title",
                ".top-card-layout__title",
                "h1",
            ]:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    t = (await loc.first.inner_text()).strip()
                    if t:
                        title = t
                        break

        if not company:
            for sel in [
                ".job-details-jobs-unified-top-card__company-name",
                ".jobs-unified-top-card__company-name",
                "a[href*='/company/']",
            ]:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    c = (await loc.first.inner_text()).strip()
                    if c and len(c) > 1 and not c.lower().startswith("logo"):
                        company = c
                        break

        main_loc = page.locator("main")
        if await main_loc.count() > 0:
            main_txt = await main_loc.first.inner_text()
            if "About the job" in main_txt:
                desc_part = main_txt.split("About the job", 1)[1]
                for end_marker in [
                    "About the company",
                    "Set alert for similar jobs",
                    "More jobs",
                    "People you can reach out to",
                ]:
                    if end_marker in desc_part:
                        desc_part = desc_part.split(end_marker, 1)[0]
                description = desc_part.strip()

            lines = [line.strip() for line in main_txt.split("\n") if line.strip()]
            for l in lines[1:10]:
                if "·" in l or "India" in l or "Remote" in l or "Hybrid" in l:
                    location = l.split("·")[0].strip()
                    break

            main_lower = main_txt.lower()
            if "remote" in main_lower:
                workplace_type = "Remote"
            elif "hybrid" in main_lower:
                workplace_type = "Hybrid"
            else:
                workplace_type = "On-site"
        else:
            for sel in [".jobs-description__content", "#job-details", "article"]:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    description = (await loc.first.inner_text()).strip()
                    if description:
                        break
    except Exception as e:
        logger.debug("Fallback page extraction warning for %s: %s", url, e)

    return {
        "url": url,
        "job_title": title,
        "title": title,
        "company": company,
        "company_name": company,
        "location": location,
        "job_description": description,
        "description": description,
        "workplace_type": workplace_type,
        "employment_type": employment_type,
    }


# -----------------------------------------------------------------------------
# Async Scraper Engine
# -----------------------------------------------------------------------------
async def _async_fetch_linkedin_jobs(config: dict[str, Any]) -> list[Job]:
    """Execute asynchronous LinkedIn job search and scraping workflow."""
    if BrowserManager is None or JobSearchScraper is None or JobScraper is None:
        logger.warning("linkedin_scraper / Playwright dependencies not available. Returning empty job list.")
        return []

    # Extract LinkedIn configuration block
    li_cfg: dict[str, Any] = {}
    if "sources" in config and isinstance(config["sources"], dict) and "linkedin" in config["sources"]:
        li_cfg = config["sources"]["linkedin"]
    elif "linkedin" in config and isinstance(config["linkedin"], dict):
        li_cfg = config["linkedin"]
    elif isinstance(config, dict):
        li_cfg = config

    if not li_cfg.get("enabled", True):
        logger.info("LinkedIn source adapter disabled in configuration.")
        return []

    session_file = str(li_cfg.get("session_file") or "session.json")
    headless = bool(li_cfg.get("headless", True))
    rate_limit_delay = float(li_cfg.get("rate_limit_delay", 2.0))
    limit_per_search = int(li_cfg.get("limit_per_search", 15))
    max_retries = int(li_cfg.get("max_retries", 3))
    backoff_factor = float(li_cfg.get("backoff_factor", 2.0))

    keywords = li_cfg.get("keywords") or [
        "AI Engineer",
        "GenAI Engineer",
        "LLM Engineer",
        "RAG Engineer",
        "Data Analyst",
        "Machine Learning Engineer",
    ]
    if isinstance(keywords, str):
        keywords = [keywords]

    locations = li_cfg.get("locations") or ["India", "Remote"]
    if isinstance(locations, str):
        locations = [locations]

    seen_file = config.get("seen_file", "seen.json") if isinstance(config, dict) else "seen.json"
    seen_identifiers = _load_seen_identifiers(seen_file)

    # 1. Session verification pre-check
    session_path = Path(session_file)
    if not session_path.exists():
        logger.warning(
            "LinkedIn session file '%s' not found. "
            "Please run 'python -m jobhunt linkedin-auth' to authenticate.",
            session_file
        )
        return []

    # 2. Launch browser & load session
    bm = BrowserManager(headless=headless)
    try:
        await bm.start()
    except Exception as e:
        logger.error("Failed to start browser for LinkedIn scraping: %s", e)
        return []

    scraped_jobs: list[Job] = []
    try:
        # Load session state
        try:
            await bm.load_session(str(session_path))
        except Exception as e:
            logger.warning("Failed to load session from '%s': %s", session_file, e)
            return []

        # 3. Check authentication status
        authenticated = False
        try:
            if bm.page:
                try:
                    await bm.page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=15000)
                except Exception as e:
                    logger.debug("Navigation to feed timed out or error: %s", e)
            if is_logged_in is not None:
                authenticated = await is_logged_in(bm.page)
            else:
                authenticated = True
        except Exception as e:
            logger.debug("Authentication check threw exception: %s", e)
            authenticated = False

        if not authenticated:
            logger.warning(
                "LinkedIn session in '%s' is expired or invalid. "
                "Run 'python -m jobhunt linkedin-auth' to re-authenticate.",
                session_file
            )
            return []

        logger.info("LinkedIn session validated successfully.")

        # 4. Search and collect job posting URLs
        search_scraper = JobSearchScraper(bm.page)
        collected_urls: list[str] = []

        for kw in keywords:
            for loc in locations:
                logger.info("Searching LinkedIn jobs: keyword='%s', location='%s' (limit=%d)", kw, loc, limit_per_search)
                try:
                    urls = await search_scraper.search(
                        keywords=kw,
                        location=loc,
                        limit=limit_per_search
                    )
                    for u in urls:
                        if u and u not in collected_urls:
                            collected_urls.append(u)
                except Exception as e:
                    logger.warning("Search failed for '%s' in '%s': %s", kw, loc, e)

                # Randomized jitter delay between searches
                jitter = random.uniform(0.5, 1.5)
                await asyncio.sleep(max(0.2, rate_limit_delay + jitter))

        # 5. Detail scraping with defensive seen pre-check & exponential backoff
        job_scraper = JobScraper(bm.page)

        for url in collected_urls:
            clean_id = extract_linkedin_job_id(url)
            if clean_id in seen_identifiers or f"linkedin:{clean_id}" in seen_identifiers or url in seen_identifiers:
                logger.debug("Skipping already seen LinkedIn posting: %s", url)
                continue

            # Defensive scraping with backoff on rate limiting
            scraped_result = None
            for attempt in range(1, max_retries + 1):
                try:
                    scraped_result = await job_scraper.scrape(url)
                    break
                except RateLimitError as rle:
                    wait_time = (backoff_factor ** attempt) * rate_limit_delay + random.uniform(1.0, 3.0)
                    logger.warning(
                        "Rate limit encountered on %s (attempt %d/%d). Backing off for %.1fs: %s",
                        url, attempt, max_retries, wait_time, rle
                    )
                    await asyncio.sleep(wait_time)
                except Exception as se:
                    logger.debug("Scrape failed for %s on attempt %d: %s", url, attempt, se)
                    if attempt == max_retries:
                        logger.warning("Failed to scrape job %s after %d attempts: %s", url, max_retries, se)
                    await asyncio.sleep(1.0)

            # Convert scraped_result or run defensive fallback extractor
            job_dict: dict[str, Any] = {}
            if scraped_result is not None:
                if hasattr(scraped_result, "to_dict"):
                    job_dict = scraped_result.to_dict()
                elif hasattr(scraped_result, "__dict__"):
                    job_dict = vars(scraped_result).copy()
                elif isinstance(scraped_result, dict):
                    job_dict = dict(scraped_result)

            if not job_dict.get("job_title") or not job_dict.get("job_description"):
                try:
                    page_details = await _extract_details_from_page(bm.page, url)
                    if not job_dict.get("job_title") and page_details.get("title"):
                        job_dict["job_title"] = page_details["title"]
                    if not job_dict.get("company") and page_details.get("company"):
                        job_dict["company"] = page_details["company"]
                    if not job_dict.get("location") and page_details.get("location"):
                        job_dict["location"] = page_details["location"]
                    if not job_dict.get("job_description") and page_details.get("description"):
                        job_dict["job_description"] = page_details["description"]
                    if page_details.get("workplace_type"):
                        job_dict["workplace_type"] = page_details["workplace_type"]
                except Exception as pe:
                    logger.debug("Page details fallback extraction failed for %s: %s", url, pe)

            if job_dict.get("job_title") or job_dict.get("title"):
                job_obj = normalize_linkedin_job(job_dict)
                scraped_jobs.append(job_obj)
                seen_identifiers.add(clean_id)
                seen_identifiers.add(f"linkedin:{clean_id}")
                seen_identifiers.add(url)

            # Randomized jitter delay between detail scrapes
            jitter = random.uniform(0.5, 1.5)
            await asyncio.sleep(max(0.2, rate_limit_delay + jitter))

        logger.info("LinkedIn scraping completed. Total jobs retrieved: %d", len(scraped_jobs))
        return scraped_jobs

    finally:
        try:
            await bm.close()
        except Exception as e:
            logger.debug("Error while closing Playwright browser: %s", e)


# -----------------------------------------------------------------------------
# Zero-Login Public Guest Scraper
# -----------------------------------------------------------------------------
def fetch_linkedin_guest_jobs(config: dict[str, Any]) -> list[Job]:
    """Fetch LinkedIn jobs via public guest search endpoint without requiring any credentials or login."""
    import requests
    import urllib.parse
    import time

    li_cfg = config.get("sources", {}).get("linkedin", {}) if isinstance(config.get("sources"), dict) else config.get("linkedin", config)
    if not isinstance(li_cfg, dict):
        li_cfg = {}

    keywords = li_cfg.get("keywords") or [
        "Python Developer", "Data Analyst", "AI Engineer", "Machine Learning"
    ]
    if isinstance(keywords, str):
        keywords = [keywords]

    locations = li_cfg.get("locations") or ["India", "Remote"]
    if isinstance(locations, str):
        locations = [locations]

    limit_per_search = int(li_cfg.get("limit_per_search", 10))
    rate_limit_delay = float(li_cfg.get("rate_limit_delay", 1.5))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    seen_ids: set[str] = set()
    jobs: list[Job] = []

    for kw in keywords:
        for loc in locations:
            params = {
                "keywords": kw,
                "location": loc,
                "start": 0,
            }
            if loc.lower() == "remote":
                params["f_WT"] = "2"

            qs = urllib.parse.urlencode(params)
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?{qs}"
            try:
                r = requests.get(url, headers=headers, timeout=12)
                if r.status_code != 200:
                    logger.debug("LinkedIn guest search for '%s' in '%s' returned HTTP %d", kw, loc, r.status_code)
                    continue

                cards = re.findall(r'<div[^>]+base-search-card[^>]+>.*?</li>', r.text, re.DOTALL)
                for c in cards[:limit_per_search]:
                    jid_m = re.search(r'data-entity-urn="urn:li:jobPosting:(\d+)"', c)
                    if not jid_m:
                        continue
                    clean_id = jid_m.group(1)
                    if clean_id in seen_ids:
                        continue
                    seen_ids.add(clean_id)

                    t_m = re.search(r'base-search-card__title"[^>]*>\s*(.*?)\s*</h3>', c, re.DOTALL)
                    comp_m = re.search(r'base-search-card__subtitle"[^>]*>.*?<a[^>]*>\s*(.*?)\s*</a>', c, re.DOTALL)
                    if not comp_m:
                        comp_m = re.search(r'base-search-card__subtitle"[^>]*>\s*(.*?)\s*</h4>', c, re.DOTALL)
                    loc_m = re.search(r'job-search-card__location"[^>]*>\s*(.*?)\s*</span>', c, re.DOTALL)
                    dt_m = re.search(r'datetime="([^"]+)"', c)

                    title = html.unescape(t_m.group(1).strip()) if t_m else ""
                    company = html.unescape(comp_m.group(1).strip()) if comp_m else ""
                    location_str = html.unescape(loc_m.group(1).strip()) if loc_m else loc
                    date_val = dt_m.group(1) if dt_m else datetime.now(timezone.utc).isoformat()

                    if not title or not company:
                        continue

                    job_url = f"https://www.linkedin.com/jobs/view/{clean_id}"
                    job_obj = Job(
                        job_id=f"linkedin:{clean_id}",
                        title=title,
                        company=company,
                        location=location_str,
                        url=job_url,
                        apply_url=job_url,
                        ats="linkedin",
                        source="linkedin",
                        source_tier=2,
                        country="India" if "india" in location_str.lower() else "",
                        remote="remote" in location_str.lower() or loc.lower() == "remote",
                        description=f"{title} at {company} in {location_str}. View and apply on LinkedIn: {job_url}",
                        posted_at=date_val,
                    )
                    jobs.append(job_obj)

            except Exception as e:
                logger.debug("LinkedIn guest search error for '%s' in '%s': %s", kw, loc, e)

            time.sleep(rate_limit_delay)

    logger.info("LinkedIn guest scraper collected %d jobs.", len(jobs))
    return jobs


# -----------------------------------------------------------------------------
# Synchronous Entry Point
# -----------------------------------------------------------------------------
def fetch_linkedin_jobs(config: dict[str, Any]) -> list[Job]:
    """Synchronous entry point to fetch LinkedIn jobs using Playwright & linkedin-scraper.

    Handles event loops cleanly whether called from main thread or background ThreadPoolExecutor.
    Falls back seamlessly to Zero-Login Guest scraper if session is invalid or missing.
    """
    li_cfg = config.get("sources", {}).get("linkedin", {}) if isinstance(config.get("sources"), dict) else config.get("linkedin", config)
    if isinstance(li_cfg, dict) and not li_cfg.get("enabled", True):
        logger.info("LinkedIn scraper disabled in config.")
        return []

    session_file = li_cfg.get("session_file", "session.json") if isinstance(li_cfg, dict) else "session.json"
    session_path = Path(session_file)
    guest_mode = li_cfg.get("guest_mode", False) if isinstance(li_cfg, dict) else False

    # If guest_mode or session file does not exist, use fast Zero-Login guest search directly
    if guest_mode or not session_path.exists():
        logger.info("Running Zero-Login LinkedIn Guest Job Search...")
        return fetch_linkedin_guest_jobs(config)

    # Try authenticated scraper if session file is present
    try:
        jobs = _run_async(_async_fetch_linkedin_jobs(config))
        if jobs:
            return jobs
    except Exception as e:
        logger.warning("LinkedIn authenticated scraper error: %s", e)

    # Fallback to Zero-Login Guest scraper
    logger.info("Falling back to Zero-Login LinkedIn Guest Job Search...")
    return fetch_linkedin_guest_jobs(config)


# -----------------------------------------------------------------------------
# Headful Authentication CLI Handler
# -----------------------------------------------------------------------------
async def _async_run_linkedin_auth(
    session_path: str = "session.json",
    timeout: int = 600,
    email: str | None = None,
    password: str | None = None,
) -> bool:
    """Open headful Playwright browser for interactive LinkedIn login and save session state."""
    if BrowserManager is None:
        print("[-] Error: linkedin_scraper or Playwright not installed in environment.")
        return False

    target_path = Path(session_path)
    print("=" * 60)
    print("  JobHunt Interactive LinkedIn Authentication")
    print("=" * 60)
    print(f"[*] Opening headful browser window...")
    print(f"[*] Destination session file: {target_path.resolve()}")
    print(f"[*] Waiting up to {timeout} seconds for authentication...")
    print(f"[*] Please log in, complete any verification code / CAPTCHA in the window.")

    bm = BrowserManager(headless=False)
    try:
        await bm.start()
        page = bm.page
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

        # Auto-fill credentials if provided
        if email and password:
            try:
                await page.wait_for_selector("#username", timeout=8000)
                await page.fill("#username", email)
                await page.fill("#password", password)
                print(f"[*] Pre-populated login credentials for: {email}")
                submit_btn = page.locator('button[type="submit"]')
                if await submit_btn.count() > 0:
                    await submit_btn.click()
                    print("[*] Clicked Sign In button automatically.")
            except Exception as fe:
                logger.debug("Auto-fill exception (user can enter manually): %s", fe)

        # Monitor login completion via both li_at session cookie and DOM/URL
        start_time = asyncio.get_event_loop().time()
        authenticated = False
        last_url = ""

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            curr_url = page.url
            if curr_url != last_url:
                last_url = curr_url
                print(f"[*] Current page: {curr_url}")

            # 1. Gold standard: check for active li_at cookie
            try:
                cookies = await bm.context.cookies()
                li_at_cookie = next((c for c in cookies if c.get("name") == "li_at" and c.get("value")), None)
                if li_at_cookie:
                    authenticated = True
                    print("[+] Detected active LinkedIn session cookie (li_at)!")
                    break
            except Exception:
                pass

            # 2. Check is_logged_in helper
            try:
                if is_logged_in is not None and await is_logged_in(page):
                    authenticated = True
                    print("[+] Detected authenticated navigation!")
                    break
            except Exception:
                pass

            # 3. Check for feed or profile URL
            if any(p in curr_url for p in ("/feed", "/mynetwork", "/in/")):
                if not any(b in curr_url for b in ("/login", "/authwall", "/checkpoint", "/challenge", "/uas/")):
                    authenticated = True
                    print("[+] Reached authenticated LinkedIn page!")
                    break

            await asyncio.sleep(1.0)

        if not authenticated:
            print("=" * 60)
            print("[-] Authentication timed out. Please try again.")
            print("=" * 60)
            return False

        # Allow cookies & storage state to settle
        await asyncio.sleep(2.0)

        # Save session storage state
        await bm.save_session(str(target_path))
        print("=" * 60)
        print(f"[+] Authentication successful! Session saved to: {target_path.resolve()}")
        print("=" * 60)
        return True
    except Exception as e:
        logger.error("LinkedIn authentication failed: %s", e)
        print("=" * 60)
        print(f"[-] Authentication failed: {e}")
        print("=" * 60)
        return False
    finally:
        try:
            await bm.close()
        except Exception:
            pass


def save_linkedin_cookie_session(cookie: str, session_path: str = "session.json") -> bool:
    """Save raw li_at session cookie directly into Playwright storage_state format."""
    target_path = Path(session_path)
    clean_cookie = cookie.strip().strip('"').strip("'")
    if not clean_cookie:
        print("[-] Error: Cookie value cannot be empty.")
        return False

    session_payload = {
        "cookies": [
            {
                "name": "li_at",
                "value": clean_cookie,
                "domain": ".www.linkedin.com",
                "path": "/",
                "expires": -1,
                "httpOnly": True,
                "secure": True,
                "sameSite": "None",
            },
            {
                "name": "li_at",
                "value": clean_cookie,
                "domain": ".linkedin.com",
                "path": "/",
                "expires": -1,
                "httpOnly": True,
                "secure": True,
                "sameSite": "None",
            },
        ],
        "origins": [],
    }

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(session_payload, indent=2), encoding="utf-8")
    print("=" * 60)
    print(f"[+] Successfully saved LinkedIn session to: {target_path.resolve()}")
    print("=" * 60)
    return True


def run_linkedin_auth(
    session_path: str = "session.json",
    timeout: int = 600,
    email: str | None = None,
    password: str | None = None,
    cookie: str | None = None,
) -> bool:
    """Open Playwright browser in headful mode or save cookie directly into authenticated session."""
    if cookie:
        return save_linkedin_cookie_session(cookie, session_path)
    return bool(_run_async(_async_run_linkedin_auth(session_path, timeout, email, password)))


# -----------------------------------------------------------------------------
# Background Pipeline Helper for GUI / API Server
# -----------------------------------------------------------------------------
def run_linkedin_scrape_pipeline(
    config_path: str | Path = "config.yaml",
    params: dict[str, Any] | None = None,
    status_tracker: dict[str, Any] | None = None,
    lock: Any = None,
) -> dict[str, Any]:
    """Execute LinkedIn scrape pipeline in background thread.

    Thread-safely updates status_tracker under lock and syncs Store/health.
    """
    if lock is None:
        lock_ctx = contextlib.nullcontext()
    else:
        lock_ctx = lock

    if status_tracker is None:
        status_tracker = {}

    import yaml
    from .store import Store
    from .sources import REGISTRY

    cfg_p = Path(config_path)
    cfg: dict[str, Any] = {}
    if cfg_p.exists():
        try:
            cfg = yaml.safe_load(cfg_p.read_text(encoding="utf-8")) or {}
        except Exception as e:
            logger.warning("Could not read config from %s: %s", config_path, e)

    sources_cfg = cfg.setdefault("sources", {})
    if not isinstance(sources_cfg, dict):
        sources_cfg = {}
        cfg["sources"] = sources_cfg
    li_cfg = sources_cfg.setdefault("linkedin", {})
    if not isinstance(li_cfg, dict):
        li_cfg = {}
        sources_cfg["linkedin"] = li_cfg

    if params and isinstance(params, dict):
        for k, v in params.items():
            if v is not None:
                li_cfg[k] = v

    now_iso = datetime.now(timezone.utc).isoformat()
    with lock_ctx:
        status_tracker["status"] = "running"
        status_tracker["is_running"] = True
        status_tracker["started_at"] = now_iso
        status_tracker["finished_at"] = None
        status_tracker["error"] = None
        status_tracker["jobs_found"] = 0
        status_tracker["jobs_added"] = 0
        status_tracker["duplicates_filtered"] = 0
        status_tracker["auth_valid"] = True

    try:
        session_file = str(li_cfg.get("session_file") or "session.json")
        if not Path(session_file).exists():
            finish_time = datetime.now(timezone.utc).isoformat()
            msg = f"Missing session file '{session_file}'. Run 'python -m jobhunt linkedin-auth' to log in."
            with lock_ctx:
                status_tracker["status"] = "auth_required"
                status_tracker["is_running"] = False
                status_tracker["auth_valid"] = False
                status_tracker["error"] = msg
                status_tracker["finished_at"] = finish_time
                status_tracker["last_scan"] = finish_time
            return dict(status_tracker)

        jobs = fetch_linkedin_jobs(cfg)
        jobs_found = len(jobs)

        from .dedupe import deduplicate_jobs
        unique_jobs, internal_dupes = deduplicate_jobs(jobs)

        # Intelligent classification & scoring on all scraped jobs
        from .roles import classify_job
        from .llm import keyword_screen

        root_dir = Path(__file__).resolve().parent.parent
        profile_path = root_dir / "profile.json"
        if not profile_path.exists():
            profile_path = root_dir / "profile.example.json"
        profile_data = {}
        if profile_path.exists():
            try:
                profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        for j in unique_jobs:
            if not getattr(j, "role_families", None):
                c = classify_job(j.title, j.description)
                j.matched_roles = c.get("matched_roles", [])
                j.role_families = c.get("role_families", [])
                j.matched_skills = c.get("matched_skills", [])
                j.role_confidence = c.get("role_confidence", 0.0)
                j.experience_required = c.get("experience_required", "")

        if profile_data:
            try:
                keyword_screen(unique_jobs, profile_data)
            except Exception as se:
                logger.debug("Keyword screen scoring error: %s", se)

        seen_file = cfg.get("seen_file", "seen.json")
        store = Store(seen_file)
        unseen_jobs = store.unseen(unique_jobs)
        jobs_added = len(unseen_jobs)
        duplicates_filtered = jobs_found - jobs_added

        if unique_jobs:
            store.record(unique_jobs, emailed=False)
            try:
                out_tracker = Path(cfg.get("out_dir", "out")) / "tracker.csv"
                store.export_csv(out_tracker)
            except Exception as e:
                logger.debug("Failed to export tracker CSV: %s", e)

            # Auto-rebuild mobile GUI to keep index.html and INITIAL_DATA in sync
            try:
                import subprocess, sys
                build_script = root_dir / "build_mobile_gui.py"
                if build_script.exists():
                    subprocess.run([sys.executable, str(build_script)], cwd=str(root_dir), check=False)
            except Exception as be:
                logger.debug("Failed to rebuild mobile gui: %s", be)

        # Update registry health if LinkedIn adapter is registered
        if "LinkedIn" in REGISTRY.adapters:
            ad = REGISTRY.adapters["LinkedIn"]
            ad.health.jobs_found = jobs_found
            ad.health.new_jobs = jobs_added
            ad.health.duplicates_removed = duplicates_filtered
            ad.health.last_scan = datetime.now(timezone.utc).isoformat()
            ad.health.status = "HEALTHY"
            try:
                REGISTRY.export_health(Path(cfg.get("out_dir", "out")) / "source_health.json")
            except Exception:
                pass

        finish_time = datetime.now(timezone.utc).isoformat()
        with lock_ctx:
            status_tracker["status"] = "completed"
            status_tracker["is_running"] = False
            status_tracker["jobs_found"] = jobs_found
            status_tracker["jobs_added"] = jobs_added
            status_tracker["duplicates_filtered"] = duplicates_filtered
            status_tracker["last_scan"] = finish_time
            status_tracker["finished_at"] = finish_time
            status_tracker["error"] = None
            status_tracker["auth_valid"] = True

        # Persist status to out/linkedin_status.json
        try:
            out_status = Path(cfg.get("out_dir", "out")) / "linkedin_status.json"
            out_status.parent.mkdir(parents=True, exist_ok=True)
            with lock_ctx:
                snap = dict(status_tracker)
            out_status.write_text(json.dumps(snap, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug("Failed to persist linkedin_status.json: %s", e)

        return dict(status_tracker)

    except Exception as e:
        logger.error("Error running LinkedIn scrape pipeline: %s", e, exc_info=True)
        finish_time = datetime.now(timezone.utc).isoformat()
        with lock_ctx:
            status_tracker["status"] = "error"
            status_tracker["is_running"] = False
            status_tracker["error"] = str(e)
            status_tracker["finished_at"] = finish_time
        return dict(status_tracker)
