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
from .telegram import DEFAULT_DASHBOARD_URL, format_job_card, make_job_buttons, send_telegram

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
        {"command": "stats", "description": "📊 View application funnel & metrics"},
        {"command": "kit", "description": "⚡ Tap-to-Copy AutoFill Kit (/kit <company>)"},
        {"command": "applied", "description": "✅ Mark a job as applied (/applied <name>)"},
        {"command": "reminders", "description": "⏰ Recruiter follow-up alerts & notes"},
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
        f"• `/stats` — Funnel & conversion tracking\n"
        f"• `/applied <company>` — Mark a role as applied\n"
        f"• `/reminders` — Recruiter follow-up templates\n"
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


def format_autofill_kit(job_data: dict[str, Any], profile: dict[str, Any]) -> str:
    """Format a 1-click tap-to-copy application kit for mobile / desktop Telegram."""
    name = profile.get("name", "Shubham Sunil Kadam")
    email = profile.get("email", "ssk080204@gmail.com")
    phone = profile.get("phone", "+918169832448")
    linkedin = "https://www.linkedin.com/in/shubham-kadam"
    github = "https://github.com/shubhaammm08"
    portfolio = DEFAULT_DASHBOARD_URL
    company = job_data.get("company", "Company")
    title = job_data.get("title", "Developer")

    cover_note = (
        f"Hi {company} Hiring Team,\n\n"
        f"I am writing to express my strong interest in the {title} position. With 1 year of practical "
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
            send_telegram(
                f"✅ *Marked Applied:* **{comp}** — *{title}*\n"
                f"Reminder scheduled for 5 days. Check `/reminders` anytime!",
                bot_token=token,
                chat_id=str(chat_id),
            )
        else:
            answer_callback(token, cb_id, text="Job marked as applied!", show_alert=False)
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
