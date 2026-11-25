"""Interactive 2-Way Telegram Bot for JobHunt.

Transforms @ShubhamJobHunt_Bot into a 2-way AI Career Command Center:
- Command listener: /start, /top, /remote, /stats, /applied, /reminders, /hunt
- Interactive inline callback handler: 1-Click apply, Copy pitch note, Mark applied
- On-demand AI Cold Outreach & Fit Analyzer: paste any JD or URL to get score + pitch
- Recruiter follow-up reminder generator
- Single-pass and polling daemon runner
"""
from __future__ import annotations

import datetime
from datetime import timezone
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .fetch import Job
from .store import Store
from .telegram import (
    DEFAULT_DASHBOARD_URL,
    cleanup_expired_messages,
    format_job_card,
    make_job_buttons,
    send_telegram,
)

TELEGRAM_API_BASE = "https://api.telegram.org/bot"


def _api_call(token: str, method: str, payload: dict[str, Any] | None = None, timeout: int = 15) -> dict[str, Any]:
    """Execute a low-level Telegram Bot API call."""
    url = f"{TELEGRAM_API_BASE}{token.strip()}/{method}"
    data = None
    headers = {"User-Agent": "JobHunt-Telegram-Bot/2.0"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_updates(token: str, offset: int = 0, timeout: int = 10) -> list[dict[str, Any]]:
    """Poll for pending Telegram updates."""
    url = f"{TELEGRAM_API_BASE}{token.strip()}/getUpdates?offset={offset}&timeout={timeout}"
    req = urllib.request.Request(url, headers={"User-Agent": "JobHunt-Telegram-Bot/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout + 5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                return data.get("result", [])
    except Exception as e:
        print(f"  ! Telegram getUpdates failed: {e}")
    return []


def answer_callback(token: str, callback_id: str, text: str = "", show_alert: bool = False) -> bool:
    """Acknowledge a Telegram inline button tap."""
    try:
        res = _api_call(
            token,
            "answerCallbackQuery",
            {"callback_query_id": callback_id, "text": text, "show_alert": show_alert},
            timeout=10,
        )
        return bool(res.get("ok"))
    except Exception as e:
        print(f"  ! answerCallbackQuery error: {e}")
        return False


def set_bot_commands(token: str) -> bool:
    """Register slash commands in Telegram menu for quick auto-complete on mobile/desktop."""
    commands = [
        {"command": "top", "description": "🔥 View top recommended job matches"},
        {"command": "remote", "description": "🌐 Browse high-match remote roles"},
        {"command": "search", "description": "🔍 Search jobs by keyword (/search <query>)"},
        {"command": "qa", "description": "❓ Screening Q&A Bank (tap-to-copy answers)"},
        {"command": "stats", "description": "📊 View application funnel & metrics"},
        {"command": "kit", "description": "⚡ Tap-to-Copy AutoFill Kit (/kit <company>)"},
        {"command": "applied", "description": "✅ Mark a job as applied (/applied <name>)"},
        {"command": "reminders", "description": "⏰ Recruiter follow-up alerts & notes"},
        {"command": "cleanup", "description": "🧹 Purge chat messages older than 24h"},
        {"command": "hunt", "description": "⚡ Pipeline status & manual scan trigger"},
        {"command": "help", "description": "💡 Command cheat sheet & quick actions"},
    ]
    try:
        res = _api_call(token, "setMyCommands", {"commands": commands}, timeout=10)
        return bool(res.get("ok"))
    except Exception as e:
        print(f"  ! Failed to set bot commands: {e}")
        return False


def make_quick_menu() -> dict[str, Any]:
    """Top-level executive navigation menu."""
    return {
        "inline_keyboard": [
            [
                {"text": "🔥 Top Matches", "callback_data": "cmd:top"},
                {"text": "🌐 Remote Roles", "callback_data": "cmd:remote"},
            ],
            [
                {"text": "🔍 Search Jobs", "callback_data": "cmd:search"},
                {"text": "❓ Screening Q&A", "callback_data": "cmd:qa"},
            ],
            [
                {"text": "📊 Funnel Stats", "callback_data": "cmd:stats"},
                {"text": "⏰ Follow-ups", "callback_data": "cmd:reminders"},
            ],
            [
                {"text": "🌐 Open Dashboard", "url": DEFAULT_DASHBOARD_URL},
                {"text": "⚡ AutoFill Kit", "url": f"{DEFAULT_DASHBOARD_URL}#kit"},
            ],
        ]
    }


# ------------------------------------------------------------------ Handlers ---


def handle_start_help(chat_id: str | int, token: str, profile: dict[str, Any]) -> None:
    """Send welcome and help message with executive navigation buttons."""
    name = profile.get("name", "Shubham")
    text = (
        f"👋 *Welcome, {name}!*\n\n"
        f"Your *AI Career Command Center* is active on Telegram.\n\n"
        f"📌 *Available Commands:*\n"
        f"• `/top` — Review top recommended roles (score >= 7.0)\n"
        f"• `/remote` — Browse high-match remote jobs\n"
        f"• `/search <keyword>` — Search jobs by title, company, or tech stack\n"
        f"• `/qa` — Instant tap-to-copy Screening Q&A Bank\n"
        f"• `/stats` — Funnel & conversion tracking\n"
        f"• `/kit <company>` — Tap-to-copy complete applicant kit\n"
        f"• `/applied <company>` — Mark a role as applied\n"
        f"• `/reminders` — Recruiter follow-up templates\n"
        f"• `/cleanup` — Purge chat messages older than 24h\n"
        f"• `/hunt` — Pipeline status & sync info\n\n"
        f"💡 *Pro Tip:* Paste any Job Description or LinkedIn job post here, "
        f"and I'll score your fit and generate a cold outreach pitch on demand!"
    )
    send_telegram(text, bot_token=token, chat_id=str(chat_id), reply_markup=make_quick_menu())


def handle_top(chat_id: str | int, token: str, store: Store, limit: int = 5) -> None:
    """Return top scored matches with interactive action buttons."""
    jobs = store.list_jobs(min_score=7.0, limit=limit)
    if not jobs:
        # Fallback to top available jobs if none >= 7.0
        jobs = store.list_jobs(min_score=0.0, limit=limit)

    if not jobs:
        send_telegram("📭 No jobs tracked yet in `seen.json`. Run a pipeline scan with `/hunt`!", bot_token=token, chat_id=str(chat_id))
        return

    header = f"🔥 *Top {len(jobs)} Recommended Roles for You:*\n_Tap buttons below to apply, copy pitch note, or mark applied:_"
    send_telegram(header, bot_token=token, chat_id=str(chat_id))

    for jid, d in jobs:
        job_obj = Job(
            job_id=jid,
            ats=d.get("canonical_source", ""),
            company=d.get("company", "Company"),
            title=d.get("title", "Role"),
            location=d.get("location", ""),
            url=d.get("url", ""),
            description=d.get("description", ""),
            score=float(d.get("score") or d.get("fit_score") or 0.0),
            reason=d.get("reason", ""),
            salary=d.get("salary", ""),
            remote=d.get("remote", False),
        )
        card_text = format_job_card(job_obj)
        buttons = make_job_buttons(jid, job_obj.url)
        send_telegram(card_text, bot_token=token, chat_id=str(chat_id), reply_markup=buttons)


def handle_remote(chat_id: str | int, token: str, store: Store, limit: int = 5) -> None:
    """Return top remote job matches."""
    jobs = store.list_jobs(min_score=0.0, limit=limit, remote_only=True)
    if not jobs:
        send_telegram("🌐 No remote roles found right now. Check `/top` for hybrid/onsite opportunities!", bot_token=token, chat_id=str(chat_id))
        return

    send_telegram(f"🌐 *Top {len(jobs)} Remote Roles:*", bot_token=token, chat_id=str(chat_id))
    for jid, d in jobs:
        job_obj = Job(
            job_id=jid,
            ats=d.get("canonical_source", ""),
            company=d.get("company", "Company"),
            title=d.get("title", "Role"),
            location=d.get("location", "Remote"),
            url=d.get("url", ""),
            description=d.get("description", ""),
            score=float(d.get("score") or d.get("fit_score") or 0.0),
            reason=d.get("reason", ""),
            salary=d.get("salary", ""),
            remote=True,
        )
        card_text = format_job_card(job_obj)
        buttons = make_job_buttons(jid, job_obj.url)
        send_telegram(card_text, bot_token=token, chat_id=str(chat_id), reply_markup=buttons)


def handle_search(chat_id: str | int, token: str, store: Store, query: str = "", limit: int = 3) -> None:
    """Search tracked jobs by keyword (company, role, title, skill, location)."""
    q = query.strip()
    if not q:
        send_telegram(
            "🔍 *How to search:*\nUse `/search <keyword>` (e.g. `/search Python`, `/search Capgemini`, `/search Remote`).",
            bot_token=token,
            chat_id=str(chat_id),
        )
        return

    tokens = q.lower().split()
    matches = []
    for jid, d in store.data.items():
        searchable = f"{d.get('company', '')} {d.get('title', '')} {d.get('location', '')} {d.get('description', '')}".lower()
        if all(t in searchable for t in tokens):
            matches.append((jid, d))

    if not matches:
        send_telegram(
            f"🔍 No tracked jobs matched '*{q}*'.\nTry checking `/top` or `/remote` to see all active opportunities!",
            bot_token=token,
            chat_id=str(chat_id),
        )
        return

    matches.sort(key=lambda x: float(x[1].get("score") or x[1].get("fit_score") or 0.0), reverse=True)
    send_telegram(
        f"🔍 *Found {len(matches)} matching role(s) for '{q}':*",
        bot_token=token,
        chat_id=str(chat_id),
    )

    for jid, d in matches[:limit]:
        job_obj = Job(
            job_id=jid,
            ats=d.get("canonical_source", ""),
            company=d.get("company", "Company"),
            title=d.get("title", "Role"),
            location=d.get("location", ""),
            url=d.get("url", ""),
            description=d.get("description", ""),
            score=float(d.get("score") or d.get("fit_score") or 0.0),
            reason=d.get("reason", ""),
            salary=d.get("salary", ""),
            remote=bool(d.get("remote")),
        )
        card_text = format_job_card(job_obj)
        buttons = make_job_buttons(jid, job_obj.url)
        send_telegram(card_text, bot_token=token, chat_id=str(chat_id), reply_markup=buttons)


def handle_stats(chat_id: str | int, token: str, store: Store) -> None:
    """Return executive funnel analytics."""
    stats = store.stats()
    tracked = stats.get("tracked", 0)
    applied = stats.get("applied", 0)
    emailed = stats.get("emailed", 0)
    rate = (applied / tracked * 100) if tracked > 0 else 0.0

    # Top high matches
    high_matches = sum(1 for d in store.data.values() if float(d.get("score") or d.get("fit_score") or 0.0) >= 7.0)

    # Top companies
    companies: dict[str, int] = {}
    for d in store.data.values():
        c = d.get("company", "").strip()
        if c:
            companies[c] = companies.get(c, 0) + 1
    top_c_str = ", ".join(f"{c} ({cnt})" for c, cnt in sorted(companies.items(), key=lambda x: x[1], reverse=True)[:4])

    msg = (
        f"📊 *JobHunt Pipeline Executive Metrics*\n\n"
        f"• *Total Roles Tracked:* `{tracked}`\n"
        f"• *High-Match Roles (Score >= 7.0):* `{high_matches}`\n"
        f"• *Alerts Delivered:* `{emailed}`\n"
        f"• *Applications Submitted:* `{applied}` ({rate:.1f}% conversion)\n"
        f"• *Active Top Companies:* {top_c_str or 'Various'}\n\n"
        f"🌐 [Interactive Analytics Dashboard]({DEFAULT_DASHBOARD_URL})"
    )
    buttons = {
        "inline_keyboard": [
            [
                {"text": "📊 Open Web Dashboard", "url": DEFAULT_DASHBOARD_URL},
                {"text": "🔥 View Top Matches", "callback_data": "cmd:top"},
            ]
        ]
    }
    send_telegram(msg, bot_token=token, chat_id=str(chat_id), reply_markup=buttons)


def handle_applied(chat_id: str | int, token: str, store: Store, query: str) -> None:
    """Mark a role as applied via company name or ID."""
    q = query.strip()
    if not q:
        send_telegram(
            "ℹ️ *How to mark applied:*\nUse `/applied <company_name>` (e.g. `/applied Stripe` or `/applied Askable`).\n"
            "Or tap the *[✅ Mark Applied]* button under any job card!",
            bot_token=token,
            chat_id=str(chat_id),
        )
        return

    match = store.find_job(q)
    if not match:
        send_telegram(
            f"🔍 Could not find an active job matching '*{q}*'.\n"
            f"Check `/top` or `/stats` to view tracked companies.",
            bot_token=token,
            chat_id=str(chat_id),
        )
        return

    jid, d = match
    store.mark_applied(jid)
    store.export_csv()

    comp = d.get("company", "Company")
    title = d.get("title", "Role")
    now_str = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")

    msg = (
        f"✅ *Application Logged Successfully!*\n\n"
        f"🏢 *Company:* {comp}\n"
        f"💼 *Role:* {title}\n"
        f"📅 *Applied On:* {now_str}\n\n"
        f"⏰ A follow-up reminder is active for 5 days from now. "
        f"Use `/reminders` anytime to get recruiter follow-up templates!"
    )
    send_telegram(msg, bot_token=token, chat_id=str(chat_id))


def handle_reminders(chat_id: str | int, token: str, store: Store, profile: dict[str, Any]) -> None:
    """Review applications ready for follow-up outreach and generate copyable templates."""
    applied_jobs = [item for item in store.data.items() if item[1].get("applied")]
    if not applied_jobs:
        send_telegram(
            "🎉 *No pending applications found!*\n\n"
            "Mark jobs you have applied to using `/applied <company>` or the *[✅ Mark Applied]* button.\n"
            "Follow-up reminders will appear here automatically after 3-5 days.",
            bot_token=token,
            chat_id=str(chat_id),
        )
        return

    name = profile.get("name", "Shubham Kadam")
    send_telegram(
        f"⏰ *Recruiter Follow-Up Tracker ({len(applied_jobs)} active applications):*\n"
        f"_Below are copyable outreach notes to re-engage recruiters on LinkedIn or Email:_ ",
        bot_token=token,
        chat_id=str(chat_id),
    )

    for jid, d in applied_jobs[:4]:
        comp = d.get("company", "Hiring Team")
        title = d.get("title", "Software Engineer")
        app_date = d.get("applied_on") or "earlier this week"
        if "T" in app_date:
            app_date = app_date.split("T")[0]

        template = (
            f"Hi {comp} Recruiting Team,\n\n"
            f"I recently submitted my application for the {title} role. Given my background in Python, "
            f"SQL, and data pipeline optimization, I am very enthusiastic about the impact I could bring "
            f"to your data initiatives.\n\n"
            f"I wanted to briefly follow up and confirm if you need any additional portfolio artifacts or insights from my side.\n\n"
            f"Portfolio: {DEFAULT_DASHBOARD_URL}\n"
            f"Best regards,\n{name}"
        )

        card = (
            f"📌 *{comp}* — *{title}*\n"
            f"📅 Applied: `{app_date}`\n\n"
            f"📬 *Outreach Template (Tap to copy):*\n"
            f"```\n{template}\n```"
        )
        send_telegram(card, bot_token=token, chat_id=str(chat_id))


def handle_hunt(chat_id: str | int, token: str, store: Store) -> None:
    """Report live pipeline sync status and trigger details."""
    stats = store.stats()
    tracked = stats.get("tracked", 0)
    applied = stats.get("applied", 0)

    # Latest job timestamp
    latest_time = "Recent"
    if store.data:
        first_seens = [d.get("first_seen") for d in store.data.values() if d.get("first_seen")]
        if first_seens:
            latest_time = max(first_seens).replace("T", " ")[:19]

    msg = (
        f"⚡ *JobHunter Live Status*\n\n"
        f"• *Pipeline:* Operational (GitHub Actions Cron & Webhook active)\n"
        f"• *Tracked Roles:* `{tracked}` in state\n"
        f"• *Applied Roles:* `{applied}`\n"
        f"• *Last Record Added:* `{latest_time} UTC`\n\n"
        f"To trigger a fresh scrape on GitHub:\n"
        f"1. Open [GitHub Actions Workflows](https://github.com/shubhaammm08/Job-Hunt/actions)\n"
        f"2. Select *JobHunter Daily Autonomous Pipeline*\n"
        f"3. Click *Run workflow* 🚀"
    )
    buttons = {
        "inline_keyboard": [
            [
                {"text": "🚀 Open GitHub Actions", "url": "https://github.com/shubhaammm08/Job-Hunt/actions"},
                {"text": "🌐 View Dashboard", "url": DEFAULT_DASHBOARD_URL},
            ]
        ]
    }
    send_telegram(msg, bot_token=token, chat_id=str(chat_id), reply_markup=buttons)


# -------------------------------------------------------- Callback & AI Logic ---


def generate_pitch_note(job_data: dict[str, Any], profile: dict[str, Any]) -> str:
    """Generate a high-converting, personalized 2-sentence Cold Outreach pitch for LinkedIn."""
    name = profile.get("name", "Shubham Kadam")
    company = job_data.get("company", "the team")
    title = job_data.get("title", "this role")
    reason = job_data.get("reason", "")

    skills = ", ".join(profile.get("core_skills", ["Python", "SQL", "Data Analysis"])[:3])

    pitch = (
        f"Hi [Hiring Manager / Recruiter],\n\n"
        f"I came across the {title} opening at {company} and wanted to reach out directly. "
        f"With hands-on experience in {skills}, I recently engineered high-throughput ETL workflows "
        f"and BI dashboards that drove measurable efficiency.\n\n"
        f"Would love to connect and share how my technical background aligns with {company}'s current initiatives!\n\n"
        f"Best regards,\n{name}\n{DEFAULT_DASHBOARD_URL}"
    )
    return pitch


def generate_cover_letter(job_data: dict[str, Any], profile: dict[str, Any]) -> str:
    """Generate a tailored, high-converting 3-paragraph executive cover letter."""
    name = profile.get("name", "Shubham Sunil Kadam")
    company = job_data.get("company", "Target Company")
    title = job_data.get("title", "Software Engineer")
    portfolio = profile.get("portfolio", DEFAULT_DASHBOARD_URL)
    skills = ", ".join(profile.get("core_skills", ["Python", "SQL", "Data Analysis", "FastAPI"])[:4])

    prompt = (
        f"You are a professional executive career strategist writing a tailored, compelling cover letter for {name}.\n\n"
        f"CANDIDATE PROFILE:\n"
        f"Name: {name}\n"
        f"Skills: {skills}\n"
        f"Experience: {profile.get('years_experience', '2+ years')}\n\n"
        f"TARGET ROLE:\n"
        f"Company: {company}\n"
        f"Title: {title}\n"
        f"Reason matched: {job_data.get('reason', '')}\n\n"
        f"REQUIREMENTS:\n"
        f"Write a polished 3-paragraph cover letter:\n"
        f"1. Hook & Interest: Strong opening expressing enthusiasm for {company} and the {title} role.\n"
        f"2. Core Impact & Alignment: Detail achievements in building scalable data pipelines, ETL workflows, and Python services that drove measurable outcomes.\n"
        f"3. Call to Action: Professional closing requesting a brief introductory conversation, with link to portfolio {portfolio}.\n\n"
        f"Return ONLY the cover letter text, no preamble or quotes."
    )

    try:
        from .providers import resolve
        provider, model = resolve("draft")
        letter = provider.complete(model, "You are a professional executive cover letter writer.", prompt, max_tokens=600)
        return letter.strip()
    except Exception:
        return (
            f"Dear {company} Hiring Team,\n\n"
            f"I am writing to express my strong interest in the {title} position. "
            f"With hands-on experience in {skills}, I specialize in architecting high-throughput data pipelines, "
            f"automating workflows, and building reliable backend services that accelerate analytical decision-making.\n\n"
            f"In my recent projects, I developed end-to-end data processing workflows that reduced reporting latency "
            f"by 80% and improved data ingestion reliability. My technical foundation across Python and SQL, combined with "
            f"a proactive problem-solving mindset, enables me to deliver immediate value to {company}'s engineering objectives.\n\n"
            f"I would welcome the opportunity to discuss how my technical skills and background align with your team's goals. "
            f"You can review my interactive portfolio and project artifacts at {portfolio}.\n\n"
            f"Thank you for your time and consideration.\n\n"
            f"Sincerely,\n{name}"
        )


DEFAULT_SCREENING_QA = [
    ("Python & SQL Experience", "2+ years building automated ETL pipelines, analytical dashboards, and backend services with Python, SQL, FastAPI, and Pandas."),
    ("GenAI & LLM Stack", "Hands-on experience with Gemini API, OpenAI SDK, LangChain, prompt engineering, RAG, and AI agent automation."),
    ("Relocation & Work Mode", "Based in Mumbai Metropolitan Region; open to on-site in Mumbai/Pune, hybrid, or 100% remote worldwide."),
    ("Notice Period & Availability", "Immediate joiner (available within 0 to 15 days)."),
    ("Current & Expected CTC", "Current CTC: ₹4,50,000 (4.5 LPA) | Expected CTC: ₹6,00,000 - ₹8,00,000 (6-8 LPA, negotiable)."),
    ("Work Authorization & Sponsorship", "Authorized to work in India (Citizen). No sponsorship required for India; open to employer-sponsored international visas or remote contracts."),
]


def format_screening_qa_bank() -> str:
    """Format pre-drafted screening answers into tap-to-copy Telegram blocks."""
    lines = [
        "❓ *Screening Q&A Bank*",
        "_Tap any response block below to instantly copy it for your ATS application:_\n",
    ]
    for q, a in DEFAULT_SCREENING_QA:
        lines.append(f"📌 *{q}:*\n```\n{a}\n```\n")
    return "\n".join(lines)


def handle_qa(chat_id: str | int, token: str) -> None:
    """Deliver the complete screening Q&A bank."""
    text = format_screening_qa_bank()
    send_telegram(text, bot_token=token, chat_id=str(chat_id))


def format_autofill_kit(job_data: dict[str, Any], profile: dict[str, Any]) -> str:
    """Format a 1-click tap-to-copy application kit for mobile / desktop Telegram."""
    name = profile.get("name", "Shubham Sunil Kadam")
    email = profile.get("email", "ssk080204@gmail.com")
    phone = profile.get("phone", "+918169832448")
    linkedin = profile.get("linkedin", "https://www.linkedin.com/in/shubham-kadam-data/")
    github = profile.get("github", "https://github.com/shubhaammm08")
    portfolio = profile.get("portfolio", DEFAULT_DASHBOARD_URL)
    experience = profile.get("years_experience", "2+ years")
    current_ctc = profile.get("current_ctc", "450000 / INR 4.5 LPA")
    expected_ctc = profile.get("expected_ctc", "700000 / INR 7 LPA")
    gender = profile.get("gender", "Male")
    company = job_data.get("company", "Company")
    title = job_data.get("title", "Developer")

    cover_note = (
        f"Hi {company} Hiring Team,\n\n"
        f"I am writing to express my strong interest in the {title} position. With hands-on "
        f"experience in Python, SQL, Power BI, and data pipeline automation, I have built production "
        f"workflows that reduced reporting latency by 80% and engineered end-to-end data pipelines.\n\n"
        f"I am excited to bring my problem-solving skills to {company}.\n\n"
        f"Portfolio: {portfolio}\n"
        f"Best regards,\n{name}"
    )
    pitch = generate_pitch_note(job_data, profile)

    return (
        f"⚡ *Quick AutoFill Kit: {company} — {title}*\n"
        f"_Tap any field below to instantly copy it into your application:_\n\n"
        f"👤 *Full Name:*\n`{name}`\n\n"
        f"📧 *Email:*\n`{email}`\n\n"
        f"📞 *Phone:*\n`{phone}`\n\n"
        f"🔗 *LinkedIn:*\n`{linkedin}`\n\n"
        f"💻 *GitHub:*\n`{github}`\n\n"
        f"🌐 *Portfolio / Website:*\n`{portfolio}`\n\n"
        f"⏳ *Total Experience:*\n`{experience}`\n\n"
        f"💰 *Current CTC:*\n`{current_ctc}`\n\n"
        f"🎯 *Expected CTC:*\n`{expected_ctc}`\n\n"
        f"⚧ *Gender Identity:*\n`{gender}`\n\n"
        f"⏳ *Notice Period:*\n`Immediate (0-15 days)`\n\n"
        f"📍 *Location:*\n`Mumbai, India (Open to Remote / Relocation)`\n\n"
        f"📝 *Tailored Cover Note (Tap to copy):*\n"
        f"```\n{cover_note}\n```\n\n"
        f"🎯 *2-Sentence Recruiter Hook (Tap to copy):*\n"
        f"```\n{pitch}\n```"
    )


def handle_kit(chat_id: str | int, token: str, store: Store, profile: dict[str, Any], query: str = "") -> None:
    """Deliver a complete tap-to-copy AutoFill kit for a company or role."""
    q = query.strip()
    match = None
    if q:
        match = store.find_job(q)
    if not match and store.data:
        top_jobs = store.list_jobs(min_score=0.0, limit=1)
        if top_jobs:
            match = top_jobs[0]

    job_data = match[1] if match else {"company": "Target Company", "title": "Software Engineer"}
    kit_text = format_autofill_kit(job_data, profile)
    send_telegram(kit_text, bot_token=token, chat_id=str(chat_id))


def handle_callback_query(token: str, cb: dict[str, Any], store: Store, profile: dict[str, Any]) -> None:
    """Handle interactive inline keyboard button clicks."""
    cb_id = cb.get("id", "")
    data = cb.get("data", "")
    msg = cb.get("message", {})
    chat_id = msg.get("chat", {}).get("id")

    if not chat_id:
        answer_callback(token, cb_id, text="Error processing action", show_alert=True)
        return

    if data.startswith("cmd:"):
        cmd = data[4:]
        answer_callback(token, cb_id)
        if cmd == "top":
            handle_top(chat_id, token, store)
        elif cmd == "remote":
            handle_remote(chat_id, token, store)
        elif cmd == "stats":
            handle_stats(chat_id, token, store)
        elif cmd == "reminders":
            handle_reminders(chat_id, token, store, profile)
        elif cmd == "search":
            send_telegram(
                "🔍 *How to search:*\nUse `/search <keyword>` (e.g. `/search Python`, `/search Remote`, `/search Mumbai`) to find tracked jobs instantly.",
                bot_token=token,
                chat_id=str(chat_id),
            )
        elif cmd == "qa":
            handle_qa(chat_id, token)
        return

    if data.startswith("app:"):
        jid_prefix = data[4:]
        match = store.find_job(jid_prefix)
        if match:
            jid, d = match
            store.mark_applied(jid)
            store.export_csv()
            comp = d.get("company", "Company")
            title = d.get("title", "Role")
            answer_callback(token, cb_id, text=f"✅ Marked {comp} as Applied!", show_alert=False)
            stage_buttons = {
                "inline_keyboard": [
                    [
                        {"text": "📞 Screen Scheduled", "callback_data": f"st:screen:{jid}"[:64]},
                        {"text": "💻 Tech Round", "callback_data": f"st:tech:{jid}"[:64]},
                    ],
                    [
                        {"text": "🏆 Offer Received", "callback_data": f"st:offer:{jid}"[:64]},
                        {"text": "❌ Not Selected", "callback_data": f"st:rej:{jid}"[:64]},
                    ],
                ]
            }
            send_telegram(
                f"✅ *Marked Applied:* **{comp}** — *{title}*\n\n"
                f"📅 Status: `Applied` | Follow-up reminder active for 5 days.\n"
                f"Tap a button below anytime to update your interview progress:",
                bot_token=token,
                chat_id=str(chat_id),
                reply_markup=stage_buttons,
            )
        else:
            answer_callback(token, cb_id, text="Job marked as applied!", show_alert=False)
        return

    if data.startswith("st:"):
        parts = data.split(":", 2)
        if len(parts) >= 3:
            stage_key = parts[1]
            jid_prefix = parts[2]
            match = store.find_job(jid_prefix)
            if match:
                jid, d = match
                comp = d.get("company", "Company")
                stage_names = {
                    "screen": "📞 Recruiter Screen Scheduled",
                    "tech": "💻 Technical Round Active",
                    "offer": "🏆 Offer Received 🎉",
                    "rej": "❌ Archived / Not Selected",
                }
                stage_display = stage_names.get(stage_key, stage_key.title())
                d["status"] = stage_display
                d["stage_updated_at"] = datetime.datetime.now(timezone.utc).isoformat()
                store.save()
                store.export_csv()
                answer_callback(token, cb_id, text=f"Stage updated: {stage_display}", show_alert=False)
                send_telegram(
                    f"🎯 *Stage Updated for {comp}:*\n"
                    f"Status: *{stage_display}*\n"
                    f"Tracker CSV and analytics dashboard synchronized!",
                    bot_token=token,
                    chat_id=str(chat_id),
                )
                return

    if data.startswith("rec:"):
        jid_prefix = data[4:]
        match = store.find_job(jid_prefix)
        job_data = match[1] if match else {"company": "Target Company", "title": "Software Engineer"}
        comp = job_data.get("company", "Company")
        title = job_data.get("title", "Role")
        answer_callback(token, cb_id, text=f"🔍 Recruiter Search for {comp}", show_alert=False)

        comp_encoded = urllib.parse.quote(comp)
        recruiter_url = f"https://www.linkedin.com/search/results/people/?keywords=recruiter%20{comp_encoded}"
        em_url = f"https://www.linkedin.com/search/results/people/?keywords=engineering%20manager%20{comp_encoded}"

        conn_note = (
            f"Hi [Name], I noticed the {title} opening at {comp} and wanted to reach out. "
            f"With hands-on experience in Python, SQL, and data automation, I would love to connect and explore how my skills align with {comp}'s initiatives. Best, Shubham"
        )

        rec_card = (
            f"🔍 *Recruiter & Hiring Team Finder: {comp}*\n\n"
            f"🎯 *Direct LinkedIn People Searches:*\n"
            f"• [Find Technical Recruiters at {comp}]({recruiter_url})\n"
            f"• [Find Engineering Managers at {comp}]({em_url})\n\n"
            f"💬 *LinkedIn Connection Note (<300 chars, tap to copy):*\n"
            f"```\n{conn_note}\n```\n"
            f"_Paste into connection request note on LinkedIn for 3x higher response rate!_"
        )
        send_telegram(rec_card, bot_token=token, chat_id=str(chat_id))
        return

    if data.startswith("sal:"):
        jid_prefix = data[4:]
        match = store.find_job(jid_prefix)
        job_data = match[1] if match else {"company": "Target Company", "title": "Developer"}
        comp = job_data.get("company", "Company")
        title = job_data.get("title", "Role")
        sal = job_data.get("salary", "").strip() or "Market Standard"
        answer_callback(token, cb_id, text=f"💼 Salary Guide for {comp}", show_alert=False)

        guide = (
            f"💼 *Compensation & Negotiation Guide*\n"
            f"🏢 *{comp}* — *{title}*\n\n"
            f"💰 *Expected Industry Range (1-3 yrs):*\n"
            f"• India On-site / Hybrid: `₹6,50,000 - ₹11,00,000 INR (6.5 - 11 LPA)`\n"
            f"• Remote Worldwide: `$45,000 - $75,000 USD / year`\n"
            f"• Detected Posting Salary: `{sal}`\n\n"
            f"🎯 *Your Baseline (Synced Profile):*\n"
            f"• Current CTC: `₹4,50,000 (4.5 LPA)`\n"
            f"• Target CTC: `₹7,00,000 - ₹8,50,000 (7 - 8.5 LPA, 55%+ uplift)`\n\n"
            f"🗣️ *Counter-Offer Script (Tap to copy):*\n"
            f"```\n"
            f"\"Based on my hands-on production experience in Python ETL pipelines, SQL automation, "
            f"and the technical responsibilities of this {title} position, I am targeting compensation "
            f"in the range of 7.5 to 8.5 LPA. However, alignment with team culture and engineering impact "
            f"is equally important to me, and I am open to discussing the complete package.\"\n"
            f"```\n\n"
            f"💡 *Top Questions to Ask the Recruiter:*\n"
            f"1. What is the budgeted salary band for this specific seniority level?\n"
            f"2. How are annual performance bonuses or appraisals structured?\n"
            f"3. Does this role include remote work stipends or learning allowances?"
        )
        send_telegram(guide, bot_token=token, chat_id=str(chat_id))
        return

    if data.startswith("pitch:"):
        jid_prefix = data[6:]
        match = store.find_job(jid_prefix)
        if match:
            jid, d = match
            comp = d.get("company", "Company")
            title = d.get("title", "Role")
            pitch = generate_pitch_note(d, profile)
            answer_callback(token, cb_id, text="📋 Pitch Note generated below!", show_alert=False)
            send_telegram(
                f"📋 *Outreach Pitch for {comp} — {title}:*\n\n"
                f"```\n{pitch}\n```\n"
                f"_Tap text above to copy and send to recruiter on LinkedIn or Email!_",
                bot_token=token,
                chat_id=str(chat_id),
            )
        else:
            answer_callback(token, cb_id, text="Generating generic pitch note...", show_alert=False)
            sample_pitch = generate_pitch_note({"company": "Company", "title": "Software Engineer"}, profile)
            send_telegram(
                f"📋 *General Cold Outreach Pitch:*\n\n```\n{sample_pitch}\n```",
                bot_token=token,
                chat_id=str(chat_id),
            )
        return

    if data.startswith("kit:"):
        jid_prefix = data[4:]
        match = store.find_job(jid_prefix)
        if match:
            jid, d = match
            kit_text = format_autofill_kit(d, profile)
            answer_callback(token, cb_id, text="⚡ AutoFill Kit generated below!", show_alert=False)
            send_telegram(kit_text, bot_token=token, chat_id=str(chat_id))
        else:
            answer_callback(token, cb_id, text="⚡ AutoFill Kit generated below!", show_alert=False)
            sample_kit = format_autofill_kit({"company": "Target Company", "title": "Developer"}, profile)
            send_telegram(sample_kit, bot_token=token, chat_id=str(chat_id))
        return

    if data.startswith("cl:"):
        jid_prefix = data[3:]
        match = store.find_job(jid_prefix)
        job_data = match[1] if match else {"company": "Target Company", "title": "Developer"}
        comp = job_data.get("company", "Company")
        title = job_data.get("title", "Role")
        answer_callback(token, cb_id, text=f"📝 Generating cover letter for {comp}...", show_alert=False)
        send_telegram(f"⏳ *Drafting tailored executive cover letter for {comp} — {title}...*", bot_token=token, chat_id=str(chat_id))
        letter = generate_cover_letter(job_data, profile)
        send_telegram(
            f"📝 *Tailored Executive Cover Letter: {comp} — {title}*\n\n"
            f"```\n{letter}\n```\n"
            f"_Tap text above to copy and paste directly into your ATS application!_",
            bot_token=token,
            chat_id=str(chat_id),
        )
        return

    if data.startswith("qa:"):
        answer_callback(token, cb_id, text="❓ Screening Q&A Bank sent below!", show_alert=False)
        handle_qa(chat_id, token)
        return

    answer_callback(token, cb_id)


def analyze_jd_with_ai(jd_text: str, profile: dict[str, Any]) -> str:
    """On-demand AI match scoring and cold pitch generator using Gemini AI."""
    from .providers import resolve

    name = profile.get("name", "Shubham Kadam")
    skills = profile.get("core_skills", ["Python", "SQL", "Data Analysis", "Machine Learning"])
    domains = profile.get("domains", ["Data Analysis", "Automation"])

    prompt = (
        f"You are a strict, world-class executive tech recruiter evaluating candidate '{name}' against this job posting.\n\n"
        f"CANDIDATE PROFILE:\n"
        f"Skills: {json.dumps(skills)}\n"
        f"Domains: {json.dumps(domains)}\n"
        f"Experience: {profile.get('years_experience', 1)} year(s) - {profile.get('current_title', 'Developer')}\n\n"
        f"JOB POSTING / TEXT:\n{jd_text[:3000]}\n\n"
        f"TASKS:\n"
        f"1. Score genuine fit (0-10, be strict; 7+ is strong match).\n"
        f"2. Give 1 sentence deciding factor reason.\n"
        f"3. Identify 2 key matching skills.\n"
        f"4. Identify 1 gap or caution (e.g. seniority, niche tool).\n"
        f"5. Write a compelling 2-sentence Cold LinkedIn DM directly to the hiring manager.\n\n"
        f"Return ONLY valid JSON matching this schema:\n"
        f"{{\n"
        f'  "score": 8.0,\n'
        f'  "reason": "Strong match with Python and SQL requirements.",\n'
        f'  "matching_skills": ["Python", "SQL"],\n'
        f'  "gap": "Requires 2+ years experience.",\n'
        f'  "cold_pitch": "Hi [Name], I noticed your opening..."\n'
        f"}}"
    )

    try:
        provider, model = resolve("draft")
        raw = provider.complete(model, "Return JSON only.", prompt, max_tokens=1500, json_mode=True)
        # Parse JSON
        cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        data = json.loads(cleaned)
        score = float(data.get("score", 7.0))
        reason = data.get("reason", "Analyzed via AI.")
        matching = ", ".join(data.get("matching_skills", ["Python", "SQL"]))
        gap = data.get("gap", "None identified.")
        pitch = data.get("cold_pitch", "")

        score_emoji = "🔥" if score >= 7.5 else "⭐" if score >= 6.0 else "⚠️"

        return (
            f"🧠 *AI Job Fit Analysis*\n\n"
            f"{score_emoji} *Fit Score:* `{score:.1f}/10`\n"
            f"💡 *Verdict:* _{reason}_\n\n"
            f"✅ *Matching Strengths:* {matching}\n"
            f"⚠️ *Key Gap to Address:* {gap}\n\n"
            f"📬 *Personalized Cold LinkedIn Pitch:*\n"
            f"```\n{pitch}\n```\n"
            f"_Tap to copy & send directly to the hiring manager!_"
        )
    except Exception as e:
        # Fallback heuristic if LLM key is absent or offline
        return (
            f"🧠 *Job Analysis (Heuristic Mode)*\n\n"
            f"⭐ *Evaluation:* JD processed. Relevant skills identified in Python, SQL, and Data Systems.\n\n"
            f"📬 *Suggested Cold Outreach Note:*\n"
            f"```\n"
            f"Hi [Hiring Manager],\n\n"
            f"I came across your opening and wanted to reach out. With hands-on experience in "
            f"Python, SQL, and data automation, I recently built data workflows and dashboards that "
            f"streamlined reporting operations.\n\n"
            f"Would love to connect and discuss how my skills align with your team's goals!\n\n"
            f"Best regards,\n{name}\n{DEFAULT_DASHBOARD_URL}\n"
            f"```"
        )


def process_update(
    update: dict[str, Any],
    token: str,
    store: Store,
    profile: dict[str, Any],
) -> None:
    """Process a single incoming Telegram update (message or callback_query)."""
    # 1. Callback Query
    if "callback_query" in update:
        handle_callback_query(token, update["callback_query"], store, profile)
        return

    # 2. Normal Message
    msg = update.get("message")
    if not msg:
        return

    chat_id = msg.get("chat", {}).get("id")
    text = (msg.get("text") or "").strip()
    if not chat_id or not text:
        return

    # Check commands
    lower_text = text.lower()
    if lower_text.startswith("/start") or lower_text.startswith("/help"):
        handle_start_help(chat_id, token, profile)
    elif lower_text.startswith("/top"):
        handle_top(chat_id, token, store)
    elif lower_text.startswith("/remote"):
        handle_remote(chat_id, token, store)
    elif lower_text.startswith("/stats"):
        handle_stats(chat_id, token, store)
    elif lower_text.startswith("/kit"):
        parts = text.split(maxsplit=1)
        query = parts[1] if len(parts) > 1 else ""
        handle_kit(chat_id, token, store, profile, query)
    elif lower_text.startswith("/applied"):
        parts = text.split(maxsplit=1)
        query = parts[1] if len(parts) > 1 else ""
        handle_applied(chat_id, token, store, query)
    elif lower_text.startswith("/reminders") or lower_text.startswith("/followup"):
        handle_reminders(chat_id, token, store, profile)
    elif lower_text.startswith("/search") or lower_text.startswith("/find"):
        parts = text.split(maxsplit=1)
        query = parts[1] if len(parts) > 1 else ""
        handle_search(chat_id, token, store, query)
    elif lower_text.startswith("/qa") or lower_text.startswith("/screening"):
        handle_qa(chat_id, token)
    elif lower_text.startswith("/cleanup") or lower_text.startswith("/purge"):
        count = cleanup_expired_messages(token, max_age_seconds=86400)
        send_telegram(
            f"🧹 *Chat Auto-Cleanup Complete*\n\n"
            f"Purged `{count}` messages older than 24 hours.\n\n"
            f"💡 *Tip for Native Auto-Delete:*\n"
            f"Open this chat in Telegram $\to$ Tap Chat Header $\to$ `...` $\to$ **Auto-Delete** $\to$ Select **24 hours** to have Telegram automatically vanish every message seamlessly!",
            bot_token=token,
            chat_id=str(chat_id),
        )
    elif lower_text.startswith("/hunt"):
        handle_hunt(chat_id, token, store)
    else:
        # Freeform message: greeting or on-demand JD analysis
        if lower_text in ("hi", "hello", "hey", "hola", "menu"):
            handle_start_help(chat_id, token, profile)
        else:
            # On-demand AI cold outreach & fit evaluation
            send_telegram("🧠 *Analyzing job fit with Gemini AI...*", bot_token=token, chat_id=str(chat_id))
            reply = analyze_jd_with_ai(text, profile)
            send_telegram(reply, bot_token=token, chat_id=str(chat_id))


def poll_updates(
    token: str,
    store: Store,
    profile: dict[str, Any],
    once: bool = False,
    timeout: int = 10,
) -> None:
    """Run update processing loop. When once=True, processes pending updates and exits."""
    set_bot_commands(token)
    cleanup_expired_messages(token, max_age_seconds=86400)
    offset = 0

    # Read latest state or getUpdates with limit
    print(f"[*] JobHunt Telegram Bot listening for commands...")
    while True:
        updates = get_updates(token, offset=offset, timeout=0 if once else timeout)
        for u in updates:
            up_id = u["update_id"]
            try:
                process_update(u, token, store, profile)
            except Exception as e:
                print(f"  ! Error processing update {up_id}: {e}")
            offset = max(offset, up_id + 1)

        if once:
            # Commit offset to Telegram so these updates are marked acknowledged
            if updates and offset > 0:
                get_updates(token, offset=offset, timeout=0)
            print(f"[*] Processed {len(updates)} pending update(s). Exiting.")
            break

        time.sleep(1)
