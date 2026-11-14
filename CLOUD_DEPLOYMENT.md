# Cloud Deployment & Operations Guide

**Project**: Shubham's JobHunt — Cloud Migration to GitHub Actions  
**Target Repository**: `https://github.com/perryvegehan/PWP_jobhunt`  
**Execution Environment**: GitHub Actions (`ubuntu-latest`)  
**State Architecture**: Zero-cost persistent orphan branches (`state/jobhunter` and `state/inbox`)  
**Date**: 2026-11-14  

---

## 1. Overview

This document provides step-by-step instructions for deploying Shubham's JobHunt and Inbox Assistant engines to GitHub Actions. Following this guide ensures that:
- Job discovery runs autonomously every day at **9:00 AM IST** (03:30 UTC).
- Executive email briefings run autonomously **every 4 hours** (02:17, 06:17, 10:17, 14:17, 18:17, 22:17 IST).
- Candidate deduplication history and application tracking are permanently maintained without data loss.
- Total cloud costs remain **₹0.00 / month**.
- Local Windows batch scripts (`run_daily.bat`, `run_test.bat`, etc.) remain fully functional.

---

## 2. Prerequisites & Credentials

Before enabling GitHub Actions, ensure you have the following credentials ready:
1. **GitHub Repository Admin Access**: Required to configure Secrets and Actions permissions.
2. **Google AI Studio Gemini API Key**:
   - Obtain from [Google AI Studio](https://aistudio.google.com/app/apikey).
   - Free tier: 1,500 requests/day, 15 RPM, ₹0 cost.
3. **Gmail Account & App Password**:
   - Email: `ssk080204@gmail.com`.
   - 16-character Google Account App Password (generate at [Google Account Security → 2-Step Verification → App Passwords](https://myaccount.google.com/apppasswords)).
   - Used for IMAP inbox reading and SMTP email delivery.
4. **Candidate Profile (`profile.json`)**:
   - The JSON string representation of Shubham's profile (name, title, target roles, skills, locations, work authorization).

---

## 3. Step-by-Step Deployment Procedure

### Step 1: Configure GitHub Repository Secrets & Variables

Navigate to your GitHub repository: **Settings → Secrets and variables → Actions**.

#### A. Required Repository Secrets (**Repository secrets** tab):
Click **New repository secret** for each item:

| Secret Name | Value | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | `AIzaSy...` | API Key for Gemini screening and email summarization |
| `GMAIL_APP_PASSWORD` | `xxxx xxxx xxxx xxxx` | 16-character Google App Password (spaces optional) |
| `GMAIL_EMAIL` | `ssk080204@gmail.com` | Shubham's Gmail address |
| `PROFILE_JSON` | `{"name": "Shubham Kadam", ...}` | Content of your local `profile.json` |

*(Note: The workflows also support legacy aliases `SMTP_USER` and `SMTP_PASS` interchangeably).*

#### B. Optional Secrets:
| Secret Name | Value | Default if Omitted |
|---|---|---|
| `MAIL_TO` | Recipient email | Defaults to `GMAIL_EMAIL` (`ssk080204@gmail.com`) |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Optional backup LLM provider |

#### C. Repository Variables (**Variables** tab):
Click **New repository variable** (optional tuning):
- `LLM_PROVIDER`: `gemini`
- `SCREEN_MODEL`: `gemini-2.5-flash-lite`
- `DRAFT_MODEL`: `gemini-2.5-flash`
- `SMTP_HOST`: `smtp.gmail.com`
- `SMTP_PORT`: `587`

---

### Step 2: Configure Workflow Permissions

1. In repository settings, navigate to **Actions → General**.
2. Scroll to **Workflow permissions**:
   - Select: **Read and write permissions** (Required to commit persistent state to `state/*` branches).
   - Check: **Allow GitHub Actions to create and approve pull requests** (Optional).
3. Click **Save**.

---

### Step 3: Seed Persistent State Branches (Pre-Migration One-Time Step)

To preserve Shubham's existing 48 tracked jobs and current email inbox watermark, execute the following commands in your local Git terminal before running the cloud workflows:

```bash
cd C:\Users\admin\Desktop\Hunt\PWP_jobhunt

# 1. Seed state/jobhunter branch with current seen.json & tracker.csv
git checkout --orphan state/jobhunter
git rm -rf .
# Ensure seen.json and out/tracker.csv are staged
git add -f seen.json
cp out/tracker.csv tracker.csv 2>/dev/null || true
git add tracker.csv 2>/dev/null || true
git commit -m "feat(state): initial seed for JobHunter (48 seen jobs, tracker.csv)"
git push -u origin state/jobhunter

# 2. Seed state/inbox branch with current summary_seen.json
git checkout --orphan state/inbox
git rm -rf .
cp out/summary_seen.json summary_seen.json 2>/dev/null || echo '{"last_seen_id": 26782}' > summary_seen.json
git add summary_seen.json
git commit -m "feat(state): initial seed for Inbox Assistant (last_seen_id: 26782)"
git push -u origin state/inbox

# 3. Return to your working branch
git checkout main
```

---

### Step 4: Deploy Workflow & Adaptation Files

Commit and push the target workflow files and UTF-8 encoding fix to `main`:
1. `.github/workflows/jobhunter.yml` (replacing legacy `daily.yml`)
2. `.github/workflows/inbox_assistant.yml`
3. `.github/workflows/ci.yml` (optional PR test quality gate)
4. `jobhunt/store.py` (UTF-8 encoding hardening patch)
5. `.gitignore` (hardened rules ignoring state files on `main`)

```bash
git add .github/workflows/jobhunter.yml .github/workflows/inbox_assistant.yml .github/workflows/ci.yml
git add jobhunt/store.py .gitignore
git commit -m "feat(cloud): deploy autonomous GitHub Actions pipelines and UTF-8 store hardening"
git push origin main
```

---

### Step 5: Staging Dry-Run & Verification (Manual Trigger)

Before relying on scheduled autonomous execution, verify both workflows using manual `workflow_dispatch`:

#### Test 1: JobHunter Dry-Run Staging
1. In GitHub, go to the **Actions** tab.
2. Select **JobHunter Daily Autonomous Pipeline** from the left sidebar.
3. Click **Run workflow**:
   - Check: `dry_run: true` (skips email delivery).
   - Set `limit: 5` (screens top 5 candidates).
   - Click **Run workflow**.
4. **Verification**:
   - Run should complete in ~45 seconds with green checkmark.
   - Click on the completed run:
     * Check **Artifacts**: Download `jobhunter-artifacts-<run>` to inspect `out/digest.html` and `out/tracker.csv`.
     * Check **Job Summary**: Confirm "Execution Summary" reflects processed postings.
     * Check `state/jobhunter` branch: Confirm no email was sent and state integrity was preserved.

#### Test 2: Inbox Assistant Staging
1. Select **Inbox Assistant 4-Hour Autonomous Briefing** from the sidebar.
2. Click **Run workflow** (default parameters).
3. **Verification**:
   - Run completes in ~20-30 seconds.
   - Check **Job Summary**: Confirms last processed email ID.
   - Check `state/inbox` branch: Confirms `summary_seen.json` updated cleanly.
   - Check Shubham's Gmail inbox: Verify receipt of the formatted executive briefing email.

#### Test 3: Full Production Run
1. Trigger **JobHunter Daily Autonomous Pipeline** with `dry_run: false`.
2. Verify receipt of the daily job search digest email in Shubham's inbox.
3. Verify `state/jobhunter` branch has an automated commit: `"Auto-update jobhunter state [run #...]"` authored by `github-actions[bot]`.

---

## 4. Operational Monitoring & Maintenance

### 4.1 Viewing Application Tracker Online
Because `tracker.csv` is committed to the root of the orphan branch `state/jobhunter`, you can view and search your job application history directly in GitHub's web interface:
- Navigate to: `https://github.com/perryvegehan/PWP_jobhunt/blob/state/jobhunter/tracker.csv`.
- GitHub renders the CSV as an interactive, searchable, paginated table.

### 4.2 Checking Monthly Free-Tier Usage
- Navigate to: **GitHub Settings → Billing and plans → Plans and usage**.
- Under **Actions**, monitor your consumed minutes (expected ~230 / 2,000 minutes).

### 4.3 Google App Password Renewal
- If Google invalidates your App Password or you change your Google Account password:
  1. Generate a fresh 16-character App Password at [Google Account Security](https://myaccount.google.com/apppasswords).
  2. Update the `GMAIL_APP_PASSWORD` secret in GitHub Settings. No codebase changes are required.

---

## 5. Rollback to Local Windows Execution

If cloud execution needs to be suspended at any time:
1. **Disable Cloud Workflows**:
   - Go to **Actions** tab $\rightarrow$ Select workflow $\rightarrow$ Click `...` $\rightarrow$ **Disable workflow**.
2. **Sync Latest State to Local Machine**:
   ```bash
   git fetch origin state/jobhunter
   git checkout origin/state/jobhunter -- seen.json out/tracker.csv
   git fetch origin state/inbox
   git checkout origin/state/inbox -- summary_seen.json
   mv summary_seen.json out/summary_seen.json
   ```
3. **Resume Local Execution**:
   - Double-click `run_daily.bat` or `run_mail_summary.bat` as usual. Local batch scripts remain 100% operational.
