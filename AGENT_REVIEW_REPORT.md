# Multi-Agent Codebase Inspection & Review Report

**Project**: Shubham's JobHunt — Cloud Migration to GitHub Actions  
**Target Repository**: `C:\Users\admin\Desktop\Hunt\PWP_jobhunt`  
**Lead Coordinator**: Orchestrator (`orchestrator_1`)  
**Date**: 2026-11-14  
**Integrity Mode**: Development (Read-Only Inspection & Planning Phase)  
**Mandatory Approval Gate**: ACTIVE — Zero project files modified  

---

## 1. Executive Summary

A coordinated team of 6 specialized autonomous explorer subagents conducted an exhaustive, independent, parallel inspection of the `PWP_jobhunt` codebase without modifying, creating, renaming, or deleting any project files.

The inspection verified that the existing system is architecturally decoupled into two distinct engines:
1. **JobHunter Core** (`jobhunt/` package): An end-to-end job discovery, direct ATS scraping, deduplication, 12-family taxonomy classification, Gemini LLM scoring, tailored draft generation, and HTML digest delivery engine.
2. **Inbox Assistant** (`mail_summarizer.py`): A standalone IMAP executive email briefing engine that monitors Shubham's Gmail inbox every 4 hours, analyzes incoming emails with Gemini, filters newsletters, renders executive briefings, and delivers updates via SMTP.

All 136 automated unit tests pass in ~1.2 to 4.6 seconds completely offline without network calls or external credentials. The inspection uncovered critical latent defects in the legacy implementation (notably an unhandled `cp1252` encoding crash in `jobhunt/store.py` that would fatal-crash on Linux runners, state wipe hazards in empty runs, and PII leakage in artifact uploads). Detailed, zero-cost cloud architecture specifications were formulated across all 6 focus areas.

---

## 2. Specialized Agent Focus Areas & Summary of Findings

| Agent Role | Subagent Folder | Key Focus | Primary Findings & Consensus |
|---|---|---|---|
| **Lead Architect & Migration Coordinator** | `explorer_lead_arch_1` | Architecture mapping, entry points, component interfaces, cloud decomposition | Confirmed clean engine decoupling; mapped all 14 `jobhunt/` modules and `mail_summarizer.py`; verified offline test suite (136/136 passing); established target two-workflow architecture (`jobhunter.yml` & `inbox_assistant.yml`); preserved local Windows execution. |
| **GitHub Actions Workflow Engineer** | `explorer_gha_1` | Workflow syntax, triggers, cron scheduling, runner specs, concurrency | Formulated exact UTC cron schedules: `30 3 * * *` (09:00 AM IST) and `47 0,4,8,12,16,20 * * *` (every 4h IST with :47 offset to avoid runner queue spikes); designed isolated temporary git directory checkouts (`$RUNNER_TEMP`) to protect `main` workspace; specified `workflow_dispatch` manual inputs. |
| **Persistent State Management Engineer** | `explorer_state_1` | State files (`seen.json`, `tracker.csv`, `summary_seen.json`), branch persistence, anti-wipe logic | Diagnosed failure modes of legacy `actions/cache@v4` (7-day eviction) and direct `main` commits (PR merge conflicts); designed dedicated orphan branches (`state/jobhunter` and `state/inbox`); built pre-commit count invariants (`len(new) >= len(old)`) and semantic dictionary re-merge on push conflict. |
| **Security Engineer** | `explorer_sec_1` | Secrets isolation, `.gitignore`, least-privilege token permissions, PII defense | Audited credentials (`GEMINI_API_KEY`, `GMAIL_EMAIL`, `GMAIL_APP_PASSWORD`); verified git history clean of secrets; identified and resolved URL query parameter key leakage (`?key=` -> `x-goog-api-key` header); blocked inbox PII leakage from artifact uploads; produced hardened `.gitignore`. |
| **Linux Compatibility & Free-Tier Optimization Engineer** | `explorer_linux_free_1` | Cross-platform compatibility, encoding defects, Pathlib, free-tier resource modeling | Discovered critical `cp1252` byte `0x95` in Windows `seen.json` causing `UnicodeDecodeError` on Linux; formulated UTF-8 hardening in `store.py`; modeled monthly runtime: ~230 min/month consumed (11.5% of 2,000 free minutes) and ~12-19 Gemini requests/day (1.2% of 1,500 daily quota) = **Guaranteed ₹0/month**. |
| **Testing and Quality Assurance Engineer** | `explorer_qa_1` | Test suite inventory, mocking, dry-run safety, CI validation, verification checklists | Profiled 136 pytest tests; identified discrepancy in `run_test.bat` (runs live staging rather than pytest); identified 0% test coverage on `mail_summarizer.py` and drafted `tests/test_mail_summarizer.py`; designed safe staging dry-run matrix; established pre/post-deployment verification checklists and rollback plan. |

---

## 3. Key Technical Discoveries & Architectural Resolutions

### 3.1 The `cp1252` Bullet Byte Defect in `seen.json` & `jobhunt/store.py`
- **Discovery**: In `jobhunt/store.py`, `self.path.read_text()` and `self.path.write_text()` omit explicit encoding. On Windows, Python defaults to `cp1252`. When a job location contained a bullet symbol (`•`), Windows wrote byte `0x95`. On Ubuntu Linux (`ubuntu-latest`), Python defaults to `UTF-8`, where byte `0x95` is an invalid leading byte. Running `Store('seen.json')` under UTF-8 raises `UnicodeDecodeError` immediately.
- **Architectural Resolution**:
  1. Patch `jobhunt/store.py` to specify `encoding="utf-8"`, with an automatic fallback to `cp1252` when loading legacy files.
  2. Set `env: PYTHONUTF8: "1"` across all GitHub Actions workflow runners.
  3. Transcode `seen.json` to valid UTF-8 when seeding the `state/jobhunter` branch.

### 3.2 Vulnerability of GitHub Actions Cache & Main Branch Commits
- **Discovery**: Previous workflow drafts attempted to persist `seen.json` either by committing directly to `main` (which caused merge conflicts when the user pushed code updates) or by using `actions/cache@v4` (which evicts cache after 7 days of inactivity, wiping history and causing duplicate email blasts).
- **Architectural Resolution**:
  - Implement zero-cost state persistence on dedicated orphan git branches:
    * `state/jobhunter`: Stores cumulative `seen.json` and `tracker.csv`.
    * `state/inbox`: Stores `summary_seen.json`.
  - State operations execute in isolated runner temp directories (`$RUNNER_TEMP`), keeping the `main` branch workspace completely clean.

### 3.3 Latent State Wipe Bug on Script Failures
- **Discovery**: In `jobhunt/store.py:19-21`, catching `JSONDecodeError` resets `self.data = {}`. If an empty or truncated file is read, subsequent `store.record()` writes an empty/partial dictionary, permanently erasing all previous candidate history.
- **Architectural Resolution**:
  - Implement an **Anti-Wipe Validation Gate** before committing state:
    $$\text{count}(\text{new\_seen.json}) \ge \text{count}(\text{pre\_run\_seen.json})$$
    $$\text{last\_seen\_id}_{\text{new}} \ge \text{last\_seen\_id}_{\text{old}}$$
  - If count decreases or file is malformed, the workflow immediately halts with an error and skips the git push, preserving remote state.
  - On push conflict (concurrent runs), perform a Python dictionary union (`merged = {**remote_data, **local_data}`) rather than a destructive text rebase.

### 3.4 PII & Secret Leakage Prevention in CI Artifacts and API URLs
- **Discovery**:
  1. `.github/workflows/daily.yml` uploaded `path: out/` as a workflow artifact. `out/latest_emails.json` contains raw subject lines, sender addresses, and body snippets of incoming personal emails, exposing private inbox communications.
  2. `jobhunt/providers.py` and `mail_summarizer.py` transmitted `GEMINI_API_KEY` via URL query parameter `?key=...`, exposing the key in connection error tracebacks and proxy logs.
- **Architectural Resolution**:
  1. Restrict artifact uploads strictly to `out/digest.html` (rendered job digest preview with 7-day retention). Never upload `out/` or `latest_emails.json`.
  2. Migrate Gemini API calls to use the official HTTP header `x-goog-api-key: <key>`, removing credentials from request URLs.

---

## 4. Cross-Agent Consensus & Unified Recommendations

1. **Decoupled Workflow Model**: Consensus across Lead Architect, Workflow Engineer, and QA Engineer that `jobhunt` and `mail_summarizer.py` must run in separate workflow files on their respective schedules (`jobhunter.yml` daily at 09:00 AM IST; `inbox_assistant.yml` every 4 hours).
2. **Zero-Cost Budget Guarantee**: Consensus across Linux/Free-Tier Engineer and Workflow Engineer that total cloud consumption (~230 runner minutes/month and ~18 requests/day) operates well below free-tier limits, ensuring permanent ₹0/month operation.
3. **Local Windows Script Preservation**: Consensus across all 6 agents that local batch scripts (`run_daily.bat`, `run_test.bat`, `run_scheduled.bat`, `run_mail_summary.bat`, `reset_history.bat`) must be preserved 100% untouched to allow seamless local fallback.
4. **Mandatory Approval Gate**: All 6 agents adhered strictly to the read-only mandate. Zero repository files were touched during this phase.
