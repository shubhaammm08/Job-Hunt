# Comprehensive Architecture & Migration Report: Shubham's JobHunt to GitHub Actions

**Project**: Shubham Sunil Kadam's JobHunt & Executive Inbox Assistant  
**Target Repository**: `C:\Users\admin\Desktop\Hunt\PWP_jobhunt`  
**Lead Coordinator**: Orchestrator (`orchestrator_1`)  
**Contributing Specialists**:
- Lead Architect & Migration Coordinator (`explorer_lead_arch_1`)
- GitHub Actions Workflow Engineer (`explorer_gha_1`)
- Persistent State Management Engineer (`explorer_state_1`)
- Security Engineer (`explorer_sec_1`)
- Linux Compatibility & Free-Tier Optimization Engineer (`explorer_linux_free_1`)
- Testing & Quality Assurance Engineer (`explorer_qa_1`)  
**Date**: 2026-11-14  
**Integrity Mode**: Development (Read-Only Inspection & Planning Phase)  
**Mandatory Approval Gate**: ACTIVE — Zero project files modified  

---

## 1. Executive Summary

Shubham's JobHunt is an automated career discovery and email intelligence platform consisting of two autonomous subsystems:
1. **JobHunter Core Engine**: Scrapes direct ATS APIs (Greenhouse, Lever, Ashby) and company career boards, applies canonical deduplication, filters against a 12-family role taxonomy, scores candidates against Shubham's resume profile using Google Gemini LLM, generates tailored application draft kits (fit summaries, custom resume bullets, cover notes, and interview questions), and delivers a formatted daily HTML digest via Gmail SMTP.
2. **Executive Inbox Assistant**: Connects to Shubham's Gmail inbox via IMAP4_SSL every 4 hours, extracts and decodes incoming message payloads, classifies and summarizes urgent recruiter outreach and opportunities using Google Gemini LLM, filters out newsletters and promotional noise, renders an executive HTML briefing, and emails it to Shubham.

Currently, the system is designed to execute locally on a Windows host using Windows batch scripts (`run_daily.bat`, `run_mail_summary.bat`, `run_scheduled.bat`) and local Windows Task Scheduler.

This report establishes the complete architecture and verification methodology for migrating both engines from local Windows execution to autonomous, 100% free-tier GitHub Actions cloud workflows, eliminating the need to keep a local Windows machine running while preserving local execution intact.

---

## 2. Before vs. After Architectural Comparison

| Dimension | Current Local Windows Execution | Target GitHub Actions Cloud Execution |
|---|---|---|
| **Host Environment** | Personal Windows 10/11 workstation (`win32`, `cp1252` locale) | GitHub Actions Hosted Runners (`ubuntu-latest`, Ubuntu 22.04 LTS, UTF-8) |
| **Execution Trigger** | Windows Task Scheduler & manual batch script clicks (`run_daily.bat`) | Automated GitHub Actions cron schedules (`schedule:`) + manual UI dispatch (`workflow_dispatch:`) |
| **JobHunter Cadence** | Daily local scheduled task | Autonomous daily schedule at **09:00 AM IST** (`cron: "30 3 * * *"`, 03:30 UTC) |
| **Inbox Assistant Cadence**| 4-hour local batch loop (`run_mail_summary.bat`) | Autonomous 4-hour schedule at **02:17, 06:17, 10:17, 14:17, 18:17, 22:17 IST** (`cron: "47 0,4,8,12,16,20 * * *"`) |
| **State Persistence** | Local disk files (`seen.json`, `out/tracker.csv`, `out/summary_seen.json`) | Dedicated orphan Git branches (`state/jobhunter` and `state/inbox`) with anti-wipe gates |
| **State Eviction Risk** | In legacy CI: `actions/cache@v4` evicted after 7 days, losing history | **Zero eviction risk**: Git branch history is permanent, versioned, and free |
| **Secret Management** | Local `.env` file stored in project folder on disk | Encrypted GitHub Repository Secrets (`GEMINI_API_KEY`, `GMAIL_EMAIL`, `GMAIL_APP_PASSWORD`, `PROFILE_JSON`) |
| **Gemini API Transport** | API key passed in HTTP URL query parameter (`?key=...`) | Hardened HTTP request header (`x-goog-api-key: <key>`), eliminating URL leak risk |
| **Artifact Retention** | Local `out/` directory on workstation hard drive | GitHub Actions Artifacts with 7-day retention restricted strictly to `out/digest.html` (protecting raw email PII) |
| **Cross-Platform Safety** | Subject to `cp1252` encoding crashes on non-Windows hosts | Enforced `PYTHONUTF8: "1"` environment and UTF-8 encoding fallback in `jobhunt/store.py` |
| **Application Tracking** | Local CSV file `out/tracker.csv` viewable only on workstation | `tracker.csv` committed to `state/jobhunter`, viewable as a live interactive spreadsheet in GitHub UI |
| **Monthly Operating Cost**| ₹0.00 (personal PC electricity / uptime cost) | **₹0.00 / month** (~230 runner mins vs 2,000 free; ~18 Gemini calls/day vs 1,500 free) |
| **Local Script Usability** | Batch scripts functional | **100% Preserved**: All `.bat` scripts remain untouched for local fallback |

---

## 3. Detailed Component Decomposition & Technical Analysis

### 3.1 JobHunter Engine (`jobhunt/` package)
- **`cli.py` (305 lines)**: Main entry point providing `run`, `init`, `screen`, and `stats` commands. Coordinates discovery, deduplication, screening, drafting, digest rendering, email delivery, and state saving.
- **`sources.py` (815 lines)**: Direct pollers for Greenhouse (`boards-api.greenhouse.io`), Lever (`api.lever.co`), and Ashby (`api.ashbyhq.com`), as well as curated startup boards. Includes canonical URL normalization, rate limit backoffs, and health reporting.
- **`dedupe.py` (105 lines)**: Canonical deduplication engine grouping identical job postings across multiple job aggregators, promoting Tier 1 direct ATS postings over third-party feeds.
- **`roles.py` (165 lines)**: 12-family role taxonomy (`AI_CORE`, `GENAI_AGENTIC`, `DEPLOYMENT`, `DATA`, `SOFTWARE`, `PLATFORM`, `CLOUD_DEVOPS`, `AUTOMATION`, `SECURITY`, `QA_TESTING`, `PRODUCT_TECH`, `OTHER_TECH`) with false-positive guardrails.
- **`prefilter.py` (85 lines)**: High-speed regex title matching, location filtering, and freshness gating (30 days maximum).
- **`llm.py` (260 lines)**: Candidate screening and application draft generation. Batches candidate descriptions into groups of 8 to optimize token usage and latency.
- **`providers.py` (310 lines)**: Multi-provider abstraction supporting Google Gemini (default), Anthropic Claude, and Groq, with exponential backoff on HTTP 429/503.
- **`digest.py` (130 lines)**: Jinja2-free, pure Python responsive HTML digest generator with inline CSS.
- **`mailer.py` (28 lines)**: SMTP STARTTLS client connecting to `smtp.gmail.com:587`.
- **`store.py` (77 lines)**: Deduplication storage (`seen.json`) and reverse-chronological CSV application tracker (`out/tracker.csv`).

### 3.2 Inbox Assistant Engine (`mail_summarizer.py`)
- Standalone 356-line script executing every 4 hours:
  1. Connects to `imap.gmail.com:993` via `imaplib.IMAP4_SSL`.
  2. Retrieves unread/new messages since `last_seen_id` stored in `out/summary_seen.json`.
  3. Decodes RFC 2047 MIME headers and extracts plain-text / HTML message bodies.
  4. Filters out self-generated JobHunt digests to prevent feedback loops.
  5. Serializes all incoming emails into a single prompt for Google Gemini (`gemini-flash-lite-latest`).
  6. Categorizes messages into actionable items (recruiter interviews, assessments, urgent alerts) and summarizes noise (newsletters, marketing).
  7. Renders an executive HTML briefing card.
  8. Delivers the briefing to Shubham via Gmail SMTP.
  9. Updates `last_seen_id` in `out/summary_seen.json`.

---

## 4. Critical Defect Discoveries & Resolutions

During multi-agent inspection, the team identified 5 critical defects in the existing codebase that would have caused silent failures or security compromises upon cloud migration:

### Defect 1: The `cp1252` Bullet Symbol Crash in `seen.json`
- **Root Cause**: `jobhunt/store.py` lines 18 and 76 read and write `seen.json` without `encoding="utf-8"`. On Windows, Python defaults to `cp1252`. When a job location contained a bullet symbol (`•`), it was written as byte `0x95`.
- **Failure in CI**: On Ubuntu Linux runners, Python defaults to UTF-8. Under UTF-8, byte `0x95` causes an immediate `UnicodeDecodeError`. Because `store.py` only catches `json.JSONDecodeError`, the workflow crashed immediately with an unhandled exception.
- **Resolution**:
  1. Patch `store.py` to use explicit `encoding="utf-8"`, with an automatic fallback to `cp1252` if legacy bytes are encountered.
  2. Set `env: PYTHONUTF8: "1"` in all GitHub Actions workflow runners.
  3. Transcode `seen.json` during state branch seeding.

### Defect 2: 7-Day Inactivity Eviction in `actions/cache@v4`
- **Root Cause**: Legacy workflow `.github/workflows/daily.yml` used GitHub Actions cache for `seen.json`.
- **Failure in CI**: GitHub Actions cache is evicted after 7 days of inactivity. If Shubham paused his job hunt over a vacation or weekend, the cache was purged. The next run treated all historical postings as new, re-screening hundreds of expired jobs and spamming Shubham's inbox.
- **Resolution**: Abandon Actions cache. Store state on permanent, dedicated orphan Git branches (`state/jobhunter` and `state/inbox`).

### Defect 3: Silent Data Wipes on Truncated State Files
- **Root Cause**: In `jobhunt/store.py:19-21`, when `JSONDecodeError` is caught, the store resets `self.data = {}`. If an empty file was committed or created during an interrupted network run, all 48 historical jobs were wiped on the next save.
- **Resolution**:
  1. Implement an **Anti-Wipe Validation Gate** in the workflow: verify `len(new_seen) >= len(old_seen)` and `last_seen_id_new >= last_seen_id_old` before committing.
  2. Implement an atomic write pattern in `store.py` (`.tmp` file + `os.replace`).
  3. Implement semantic dictionary re-merging on push conflicts (`merged = {**remote_data, **local_data}`).

### Defect 4: Personal Inbox PII Leakage via Artifacts
- **Root Cause**: Legacy `daily.yml` uploaded `path: out/` as a workflow artifact. `out/latest_emails.json` contains raw email snippets and sender addresses from Shubham's personal Gmail inbox.
- **Resolution**: Never upload `out/` or `latest_emails.json`. Restrict `jobhunter.yml` artifacts strictly to `out/digest.html` (job preview), and deliver inbox briefings exclusively via authenticated SMTP.

### Defect 5: API Key Exposure in URL Query Strings
- **Root Cause**: Both `jobhunt/providers.py` and `mail_summarizer.py` appended `?key={api_key}` to the Gemini API endpoint URL, risking exposure in network connection error traces.
- **Resolution**: Switch to the official HTTP header `x-goog-api-key: <key>`, keeping credentials out of request URLs.

---

## 5. Free-Tier Resource & Budget Compliance

A rigorous mathematical usage audit confirms that cloud execution is **100% free (₹0.00 / month)**:

1. **GitHub Actions Runner Minutes**:
   - `jobhunter.yml`: 30 runs/month $\times$ 1 min = 30 minutes.
   - `inbox_assistant.yml`: 180 runs/month $\times$ 1 min = 180 minutes.
   - Buffer / manual dispatch: 20 minutes.
   - Total Monthly Consumption: **~230 minutes/month** (**11.5% of the 2,000 monthly free minutes**).
   - Unused Safety Margin: **1,770 minutes (88.5%)**.

2. **Google Gemini API Free Tier**:
   - Quota: 1,500 requests/day, 15 RPM, 1,000,000 TPM.
   - JobHunter Daily Calls: ~10-12 calls/day.
   - Inbox Assistant Daily Calls: 6 calls/day.
   - Total Daily Requests: **~18 requests/day** (**1.2% of the daily quota**).
   - Peak RPM: ~5 RPM (under 15 RPM ceiling; protected by 1.0s pacing).
   - Financial Cost: **₹0.00 / month**.

---

## 6. Local Windows Script Preservation

A core mandate of the migration is zero disruption to Shubham's existing local Windows setup. The following batch scripts remain 100% untouched and functional:
- `run_daily.bat`: Manual local execution with browser digest launch.
- `run_scheduled.bat`: Local background run with scheduler logging.
- `run_mail_summary.bat`: Local 4-hour email summarizer run.
- `run_test.bat`: Local dry-run screening (cap 10).
- `reset_history.bat`: Local deduplication history reset.

The cloud workflows invoke the underlying Python CLI commands directly (`python -m jobhunt run --send` and `python mail_summarizer.py`), completely bypassing the batch scripts on Linux runners while preserving them for local execution.

---

## 7. Approval Gate Deliverables Inventory

The complete migration planning phase has produced the following deliverable documents in `.agents/teamwork/orchestrator_1/`:
1. `MIGRATION_PLAN.md`: Master migration blueprint, proposed code diffs, risk matrix, 4-tier verification protocol, and rollback procedures.
2. `CLOUD_DEPLOYMENT.md`: Step-by-step operations guide covering GitHub Secrets, one-time branch seeding, manual dispatch testing, and monitoring.
3. `CLOUD_COST_ESTIMATE.md`: Detailed mathematical breakdown proving ₹0/month budget across GitHub Actions and Gemini API free tiers.
4. `MIGRATION_REPORT.md`: Comprehensive before-and-after architecture comparison and technical defect audit (this document).
5. `AGENT_REVIEW_REPORT.md`: Synthesis of the 6 specialized subagent inspection reports, consensus findings, and recommendations.

**Approval Gate Status**: In strict adherence to operational directives, **NO project files in `PWP_jobhunt` have been created, modified, deleted, renamed, or overwritten**. Execution halts cleanly at this mandatory approval gate pending explicit user sign-off.
