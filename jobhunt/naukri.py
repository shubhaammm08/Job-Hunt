"""Naukri.com Scraping Engine and Integration for JobHunt.

Provides session management (dual-mode: Playwright interactive auth or manual cookie string),
defensive fetching against Naukri's job search API (https://www.naukri.com/jobapi/v3/search),
extraction based on the Rockposedon/WebScraping schema, normalization into canonical Job dataclass,
and safe CI-skipping to prevent datacenter IP blocks in GitHub Actions.
"""
from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import requests

from .fetch import Job, strip_html
from .roles import classify_job

logger = logging.getLogger("jobhunt.naukri")

NAUKRI_SEARCH_API = "https://www.naukri.com/jobapi/v3/search"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# -----------------------------------------------------------------------------
# Normalization & Extraction Helpers
# -----------------------------------------------------------------------------
def clean_naukri_id(raw_id: str | int | None) -> str:
    """Extract clean alphanumeric job ID."""
    s = str(raw_id or "").strip()
    if not s or s.lower() == "n/a":
        return ""
    # Usually a numeric or alphanumeric string like 061123006487
    m = re.search(r"(\d{8,14})", s)
    if m:
        return m.group(1)
    return re.sub(r"[^\w]", "", s)


def normalize_naukri_job(raw: dict[str, Any]) -> Job:
    """Normalize raw Naukri job data (from API response or Rockposedon scraper) into Job."""
    job_id_raw = raw.get("jobId") or raw.get("Job ID") or raw.get("id") or raw.get("url") or ""
    clean_id = clean_naukri_id(job_id_raw)

    title = str(raw.get("title") or raw.get("Job Title") or "").strip()
    company = str(raw.get("companyName") or raw.get("Company Name") or "Company").strip()

    # Extract location, experience, salary from placeholders if present
    placeholders = raw.get("placeholders", [])
    location = raw.get("Location") or raw.get("location") or ""
    experience = raw.get("Experience") or raw.get("experience") or ""
    salary = raw.get("Salary") or raw.get("salary") or ""

    if isinstance(placeholders, list):
        for placeholder in placeholders:
            if not isinstance(placeholder, dict):
                continue
            p_type = placeholder.get("type", "")
            p_label = placeholder.get("label", "")
            if p_type == "location" and not location:
                location = p_label
            elif p_type == "experience" and not experience:
                experience = p_label
            elif p_type == "salary" and not salary:
                salary = p_label

    location = str(location).strip() or "India"
    experience = str(experience).strip()
    if experience.lower() in ("n/a", "none"):
        experience = ""

    # Clean salary
    salary_str = str(salary).strip()
    if salary_str.lower() in ("n/a", "not disclosed", "none", ""):
        clean_salary = None
    else:
        clean_salary = salary_str

    # Build canonical URL
    static_url = raw.get("staticUrl") or raw.get("jdURL") or raw.get("url") or ""
    if static_url and isinstance(static_url, str):
        if static_url.startswith("http"):
            canonical_url = static_url
        elif static_url.startswith("/"):
            canonical_url = f"https://www.naukri.com{static_url}"
        else:
            canonical_url = f"https://www.naukri.com/{static_url}"
    elif clean_id:
        canonical_url = f"https://www.naukri.com/job-listings-{clean_id}"
    else:
        comp_s = re.sub(r"[^\w]", "", company.lower())
        title_s = re.sub(r"[^\w]", "", title.lower())
        clean_id = f"{comp_s}_{title_s}" if (comp_s or title_s) else str(int(time.time()))
        canonical_url = f"https://www.naukri.com/job-listings-{clean_id}"

    # Job description
    desc_raw = raw.get("jobDescription") or raw.get("Job Description") or raw.get("description") or ""
    description = strip_html(desc_raw)

    # Date parsing
    footer = str(raw.get("footerPlaceholderLabel") or raw.get("Footer Placeholder Label") or "").strip()
    posted_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Tags / skills
    tags = raw.get("tagsAndSkills") or raw.get("Tags and Skills") or []
    if isinstance(tags, str):
        matched_skills = [t.strip() for t in tags.split(",") if t.strip()]
    elif isinstance(tags, list):
        matched_skills = [str(t).strip() for t in tags if str(t).strip()]
    else:
        matched_skills = []

    # Remote detection
    loc_lower = location.lower()
    title_lower = title.lower()
    is_remote = bool(
        "remote" in loc_lower
        or "remote" in title_lower
        or "wfh" in loc_lower
        or "work from home" in loc_lower
        or "anywhere" in loc_lower
    )

    # Classify against JobHunt career taxonomy
    classification = classify_job(title, description)
    role_families = classification.get("role_families", [])
    matched_roles = classification.get("matched_roles", [])
    role_confidence = classification.get("role_confidence", 0.0)
    extra_skills = classification.get("matched_skills", [])
    for s in extra_skills:
        if s not in matched_skills:
            matched_skills.append(s)

    if not experience and classification.get("experience_required"):
        experience = classification.get("experience_required", "")

    return Job(
        job_id=f"naukri:{clean_id}",
        ats="naukri",
        company=company,
        title=title,
        location=location,
        url=canonical_url,
        description=description,
        posted_at=posted_at,
        salary=clean_salary,
        source="naukri",
        source_tier=2,
        country="India",
        remote=is_remote,
        employment_type="Full-time",
        apply_url=canonical_url,
        canonical_source="naukri",
        sources=["naukri"],
        role_families=role_families,
        matched_roles=matched_roles,
        matched_skills=matched_skills,
        role_confidence=role_confidence,
        experience_required=experience,
    )


def extract_naukri_api_response(data: dict[str, Any]) -> list[Job]:
    """Parse JSON response from Naukri search API into list of Job objects."""
    jobs: list[Job] = []
    if not isinstance(data, dict):
        return jobs

    job_details = data.get("jobDetails", [])
    if not isinstance(job_details, list):
        return jobs

    for raw_item in job_details:
        if not isinstance(raw_item, dict):
            continue
        try:
            job = normalize_naukri_job(raw_item)
            if job.title and job.title != "N/A":
                jobs.append(job)
        except Exception as e:
            logger.debug("Failed to normalize Naukri job item: %s", e)

    return jobs


# -----------------------------------------------------------------------------
# Rockposedon/WebScraping dataset import
#
# The upstream scraper writes one plain-text block per job in
# `naukri_jobs_data_lakhs.txt`. Its own live API path is now challenge-blocked,
# but the exported dataset is still a useful source of real Naukri listings.
# These helpers turn that export into the same canonical Job objects produced by
# the API/JSON path, so the rest of the pipeline does not need to care.
# -----------------------------------------------------------------------------
NAUKRI_DATASET_URL = (
    "https://raw.githubusercontent.com/Rockposedon/WebScraping/main/"
    "naukri_jobs_data_lakhs.txt"
)

DATASET_FIELD_LABELS = (
    "Job Title",
    "Company Name",
    "Footer Placeholder Label",
    "Tags and Skills",
    "Experience",
    "Salary",
    "Location",
    "Job Description",
)
_DATASET_FIELD_RE = re.compile(
    r"^(" + "|".join(re.escape(label) for label in DATASET_FIELD_LABELS) + r"):\s*(.*)$"
)


def parse_naukri_dataset(text: str) -> list[dict[str, Any]]:
    """Parse the Rockposedon text export into raw Naukri records.

    Returns at most one record per clean Naukri job ID. The upstream script
    fetches page 1 repeatedly, so the published file contains thousands of
    duplicate blocks; deduplication here keeps the import tractable.
    """
    records: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    current: dict[str, str] = {}
    current_field: str | None = None

    def flush() -> None:
        nonlocal current, current_field
        job_id = clean_naukri_id(current.get("Job ID", ""))
        title = (current.get("Job Title") or "").strip()
        if job_id and title and title.lower() != "n/a":
            raw = {"Job ID": job_id}
            for label in DATASET_FIELD_LABELS:
                raw[label] = (current.get(label) or "").strip()
            existing = by_id.get(job_id)
            if existing is None:
                by_id[job_id] = raw
                records.append(raw)
            elif len(raw.get("Job Description", "")) > len(existing.get("Job Description", "")):
                # Keep the most informative copy when the same ID repeats.
                existing.update(raw)
        current = {}
        current_field = None

    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("Job ID:"):
            if current:
                flush()
            current_field = "Job ID"
            current["Job ID"] = stripped.split(":", 1)[1].strip()
            continue
        if not current:
            continue
        match = _DATASET_FIELD_RE.match(stripped)
        if match:
            current_field = match.group(1)
            current[current_field] = match.group(2).strip()
        elif current_field and stripped:
            current[current_field] += " " + stripped
    if current:
        flush()

    return records


def naukri_dataset_jobs(text: str, limit: int | None = None) -> list[Job]:
    """Normalize the Rockposedon text export into canonical Job objects."""
    jobs: list[Job] = []
    seen_ids: set[str] = set()
    for raw in parse_naukri_dataset(text):
        job = normalize_naukri_job(raw)
        if not job.title or job.job_id in seen_ids:
            continue
        seen_ids.add(job.job_id)
        jobs.append(job)
        if limit and len(jobs) >= limit:
            break
    return jobs


def fetch_naukri_dataset(url: str = NAUKRI_DATASET_URL, timeout: int = 60) -> str:
    """Download the upstream Naukri dataset export as text."""
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": DEFAULT_USER_AGENT})
    resp.raise_for_status()
    return resp.text


def infer_naukri_posted_date(job_id: str) -> str | None:
    """Infer an ISO date from Naukri IDs whose first six digits are DDMMYY."""
    digits = re.sub(r"\D", "", str(job_id or "").split(":")[-1])
    if len(digits) < 6:
        return None
    try:
        return datetime(2000 + int(digits[4:6]), int(digits[2:4]), int(digits[0:2])).date().isoformat()
    except ValueError:
        return None


# -----------------------------------------------------------------------------
# Cookie & Session Management
# -----------------------------------------------------------------------------
def parse_cookie_string(cookie_str: str) -> dict[str, str]:
    """Parse a cookie header string into a dict of key-value pairs."""
    cookies: dict[str, str] = {}
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookies[k.strip()] = v.strip().strip('"').strip("'")
    return cookies


def load_naukri_cookies(session_path: str = "session_naukri.json") -> dict[str, str]:
    """Load cookies from NAUKRI_COOKIE environment variable or session file."""
    # 1. Environment variable has highest precedence
    env_cookie = os.environ.get("NAUKRI_COOKIE", "").strip()
    if env_cookie:
        return parse_cookie_string(env_cookie)

    # 2. Check session file
    p = Path(session_path)
    if not p.exists():
        # Fallback to root or PWP_jobhunt directory if relative
        alt_p = Path("PWP_jobhunt") / session_path
        if alt_p.exists():
            p = alt_p

    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                # Format 1: Playwright storage_state format: {"cookies": [{"name": ..., "value": ...}]}
                if "cookies" in data and isinstance(data["cookies"], list):
                    return {c["name"]: c["value"] for c in data["cookies"] if "name" in c and "value" in c}
                # Format 2: Direct key-value dict: {"_abck": "...", ...}
                return {str(k): str(v) for k, v in data.items()}
            elif isinstance(data, list):
                # Format 3: List of cookie objects
                return {c["name"]: c["value"] for c in data if "name" in c and "value" in c}
        except Exception as e:
            logger.warning("Could not parse Naukri session file '%s': %s", session_path, e)

    return {}


def save_naukri_cookie_session(cookie: str | dict[str, str], session_path: str = "session_naukri.json") -> bool:
    """Save raw cookie string or dictionary into session file."""
    target_path = Path(session_path)
    cookie_dict: dict[str, str] = {}

    if isinstance(cookie, str):
        clean_cookie = cookie.strip().strip('"').strip("'")
        if not clean_cookie:
            print("[-] Error: Cookie string cannot be empty.")
            return False
        cookie_dict = parse_cookie_string(clean_cookie)
    elif isinstance(cookie, dict):
        cookie_dict = cookie

    if not cookie_dict:
        print("[-] Error: No valid cookies found to save.")
        return False

    cookies_list = []
    for k, v in cookie_dict.items():
        cookies_list.append({
            "name": k,
            "value": v,
            "domain": ".naukri.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax",
        })

    session_payload = {
        "cookies": cookies_list,
        "origins": [],
    }

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(session_payload, indent=2), encoding="utf-8")
    print("=" * 60)
    print(f"[+] Successfully saved Naukri session to: {target_path.resolve()}")
    print("=" * 60)
    return True


def run_naukri_auth(session_path: str = "session_naukri.json", timeout: int = 300, cookie: str | None = None) -> bool:
    """Run interactive headful browser to obtain Naukri session or save cookie directly."""
    if cookie:
        return save_naukri_cookie_session(cookie, session_path)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[-] Error: Playwright is not installed. Run 'pip install playwright'.")
        return False

    print("=" * 60)
    print("  JobHunt Interactive Naukri Authentication")
    print("=" * 60)
    print("[*] Opening headful browser window...")
    print(f"[*] Destination session file: {Path(session_path).resolve()}")
    print(f"[*] Waiting up to {timeout} seconds...")
    print("[*] Please log in to Naukri or complete any Cloudflare/Akamai challenge.")
    print("=" * 60)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(user_agent=DEFAULT_USER_AGENT)
            page = context.new_page()
            page.goto("https://www.naukri.com/nlogin/login", timeout=30000, wait_until="domcontentloaded")

            start_time = time.time()
            authenticated = False
            last_count = 0

            while (time.time() - start_time) < timeout:
                cookies = context.cookies()
                cookie_names = {c.get("name") for c in cookies}
                # Check for active session cookie or bot verification tokens
                if len(cookies) > 5 and ("_t_s" in cookie_names or "_abck" in cookie_names or "nauk_at" in cookie_names):
                    if len(cookies) != last_count:
                        last_count = len(cookies)
                        print(f"[*] Collected {len(cookies)} browser cookies...")

                # Detect when user reaches authenticated dashboard or home
                curr_url = page.url
                if any(k in curr_url for k in ("/mnjuser/homepage", "/jobsearch", "/user/dashboard")):
                    authenticated = True
                    print("[+] Detected successful navigation to Naukri user area!")
                    break

                # Also accept if we have bot cookies and user has spent at least 15s or closed login
                if "_abck" in cookie_names and (time.time() - start_time) > 10 and "login" not in curr_url:
                    authenticated = True
                    print("[+] Captured required Akamai session cookies!")
                    break

                time.sleep(1.0)

            final_cookies = context.cookies()
            browser.close()

            if not final_cookies:
                print("[-] No cookies captured.")
                return False

            cookie_dict = {c["name"]: c["value"] for c in final_cookies}
            return save_naukri_cookie_session(cookie_dict, session_path)

    except Exception as e:
        print(f"[-] Interactive authentication error: {e}")
        return False


# -----------------------------------------------------------------------------
# Zero-Login Guest Browser Scraping
# -----------------------------------------------------------------------------
def fetch_naukri_guest_browser(
    keywords: list[str],
    exp_filter: str = "0-2",
    max_pages: int = 1,
    session_file: str = "session_naukri.json"
) -> list[Job]:
    """Fetch jobs directly from Naukri public search pages using a guest browser context (NO LOGIN REQUIRED)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright is not installed. Cannot run guest browser scraper.")
        return []

    all_jobs: list[Job] = []
    seen_ids: set[str] = set()

    # Normalize exp_filter into Naukri query parameters
    exp_params = []
    if exp_filter:
        m = re.match(r"(\d+)\s*[-~]\s*(\d+)", exp_filter)
        if m:
            start_yr, end_yr = int(m.group(1)), int(m.group(2))
            for y in range(start_yr, end_yr + 1):
                exp_params.append(f"experience={y}")
        elif exp_filter.isdigit():
            exp_params.append(f"experience={exp_filter}")
    exp_query = "&".join(exp_params)

    logger.info("Naukri: Starting zero-login guest browser scraping...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(user_agent=DEFAULT_USER_AGENT)
            page = context.new_page()

            for kw in keywords[:5]:
                kw_slug = re.sub(r"[^\w]+", "-", kw.strip().lower()).strip("-") + "-jobs"
                for pg_num in range(1, max_pages + 1):
                    url = f"https://www.naukri.com/{kw_slug}"
                    if pg_num > 1:
                        url += f"-{pg_num}"
                    if exp_query:
                        url += f"?{exp_query}"

                    try:
                        logger.info("Naukri guest fetch: %s", url)
                        page.goto(url, timeout=25000, wait_until="domcontentloaded")
                        time.sleep(2.5)  # wait for dynamic card rendering

                        cards = page.locator(".srp-jobtuple-wrapper")
                        card_count = cards.count()
                        logger.info("Naukri: Found %d cards on page for '%s'", card_count, kw)

                        for idx in range(card_count):
                            card = cards.nth(idx)
                            try:
                                title_loc = card.locator("a.title")
                                if title_loc.count() == 0:
                                    continue
                                title = title_loc.first.inner_text().strip()
                                job_url = title_loc.first.get_attribute("href") or ""
                                if job_url and not job_url.startswith("http"):
                                    job_url = f"https://www.naukri.com{job_url}"

                                comp_loc = card.locator("a.comp-name, .comp-name")
                                comp = comp_loc.first.inner_text().strip() if comp_loc.count() > 0 else "Company"

                                exp_loc = card.locator(".exp-wrap span, .exp")
                                exp = exp_loc.first.inner_text().strip() if exp_loc.count() > 0 else ""

                                loc_loc = card.locator(".loc-wrap span, .loc")
                                loc = loc_loc.first.inner_text().strip() if loc_loc.count() > 0 else "India"

                                sal_loc = card.locator(".sal-wrap span, .sal")
                                sal = sal_loc.first.inner_text().strip() if sal_loc.count() > 0 else ""

                                desc_loc = card.locator(".job-desc, .desc")
                                desc = desc_loc.first.inner_text().strip() if desc_loc.count() > 0 else ""

                                tag_locs = card.locator(".tag-li, .tags-gt li, .tags-gt span")
                                tag_count = tag_locs.count()
                                tags = [tag_locs.nth(i).inner_text().strip() for i in range(tag_count)]

                                clean_id = clean_naukri_id(job_url)

                                raw_dict = {
                                    "jobId": clean_id,
                                    "title": title,
                                    "companyName": comp,
                                    "location": loc,
                                    "experience": exp,
                                    "salary": sal,
                                    "jobDescription": desc,
                                    "tagsAndSkills": tags,
                                    "url": job_url,
                                }
                                job_obj = normalize_naukri_job(raw_dict)
                                if job_obj.job_id not in seen_ids:
                                    seen_ids.add(job_obj.job_id)
                                    all_jobs.append(job_obj)
                            except Exception as card_err:
                                logger.debug("Error parsing single card: %s", card_err)

                    except Exception as pg_err:
                        logger.warning("Error fetching Naukri page '%s': %s", url, pg_err)

                    time.sleep(1.0)

            # Automatically capture and save clearance cookies for next time
            try:
                cookies = context.cookies()
                if cookies and session_file:
                    cookie_dict = {c["name"]: c["value"] for c in cookies}
                    save_naukri_cookie_session(cookie_dict, session_file)
            except Exception:
                pass

            browser.close()

    except Exception as e:
        logger.warning("Naukri guest browser scraping encountered error: %s", e)

    return all_jobs


# -----------------------------------------------------------------------------
# Main Fetch Logic
# -----------------------------------------------------------------------------
def fetch_naukri_jobs(config: dict[str, Any]) -> list[Job]:
    """Fetch jobs from Naukri search API using cookies, falling back seamlessly to guest browser scraping."""
    naukri_cfg = (
        config.get("sources", {}).get("naukri", {})
        if isinstance(config.get("sources"), dict)
        else config.get("naukri", {})
    )

    if not naukri_cfg or not naukri_cfg.get("enabled", True):
        logger.info("Naukri adapter is disabled in configuration.")
        return []

    # CI guardrail: In GitHub Actions, datacenter IPs are blocked by Akamai. Skip unless explicitly enabled.
    is_ci = os.environ.get("GITHUB_ACTIONS") == "true" or os.environ.get("CI") == "true"
    run_in_ci = naukri_cfg.get("run_in_ci", False)
    if is_ci and not run_in_ci:
        logger.info("Naukri: Running in CI (GitHub Actions) - skipping direct scraping to protect runner IP.")
        return []

    # Derive keywords from config
    keywords: list[str] = naukri_cfg.get("keywords", [])
    if not keywords:
        tracks = config.get("target_career_tracks", {})
        for track in tracks.values():
            if isinstance(track, dict):
                t_title = track.get("title", "")
                if t_title:
                    keywords.append(t_title.split("(")[0].strip())
    if not keywords:
        keywords = ["Python Developer", "Data Analyst", "AI Engineer", "Machine Learning"]

    max_pages = naukri_cfg.get("max_pages_per_search", 1)
    limit_per_search = naukri_cfg.get("limit_per_search", 20)
    exp_filter = naukri_cfg.get("experience", "0-2")
    session_file = naukri_cfg.get("session_file", "session_naukri.json")

    cookies = load_naukri_cookies(session_file)

    # If no cookies found or invalid, seamlessly fallback to zero-login guest browser scraping
    if not cookies:
        logger.info("Naukri: No session cookies configured. Using zero-login guest browser scraper.")
        return fetch_naukri_guest_browser(
            keywords=keywords,
            exp_filter=exp_filter,
            max_pages=max_pages,
            session_file=session_file,
        )

    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
    headers = {
        "authority": "www.naukri.com",
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9",
        "appid": "109",
        "clientid": "d3skt0p",
        "content-type": "application/json",
        "systemid": "Naukri",
        "user-agent": DEFAULT_USER_AGENT,
        "cookie": cookie_header,
        "referer": "https://www.naukri.com/",
    }

    all_jobs: list[Job] = []
    seen_ids: set[str] = set()

    for kw in keywords[:5]:  # limit to top 5 queries per run to respect rate limits
        for page in range(1, max_pages + 1):
            params = {
                "noOfResults": str(limit_per_search),
                "urlType": "search_by_keyword",
                "searchType": "adv",
                "keyword": kw,
                "pageNo": str(page),
                "k": kw,
                "src": "jobsearchDesk",
            }
            if exp_filter:
                params["experience"] = exp_filter

            try:
                resp = requests.get(NAUKRI_SEARCH_API, headers=headers, params=params, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    jobs = extract_naukri_api_response(data)
                    new_count = 0
                    for j in jobs:
                        if j.job_id not in seen_ids:
                            seen_ids.add(j.job_id)
                            all_jobs.append(j)
                            new_count += 1
                    logger.info("Naukri: '%s' page %d -> %d jobs (%d new)", kw, page, len(jobs), new_count)
                elif resp.status_code in (403, 406):
                    logger.info(
                        "Naukri API returned HTTP %d (Akamai challenge). Switching to zero-login guest browser mode.",
                        resp.status_code
                    )
                    guest_jobs = fetch_naukri_guest_browser(
                        keywords=keywords,
                        exp_filter=exp_filter,
                        max_pages=max_pages,
                        session_file=session_file,
                    )
                    for gj in guest_jobs:
                        if gj.job_id not in seen_ids:
                            seen_ids.add(gj.job_id)
                            all_jobs.append(gj)
                    return all_jobs
                else:
                    logger.warning("Naukri API returned HTTP %d for query '%s'", resp.status_code, kw)
            except Exception as e:
                logger.warning("Naukri request failed for query '%s': %s", kw, e)

            time.sleep(1.0)  # polite throttle

    return all_jobs

