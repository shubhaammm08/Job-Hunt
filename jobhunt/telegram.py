"""Send daily job digests and instant high-match alerts to Telegram with interactive action buttons.

100% Free forever, officially supported by Telegram Bot API.
Instant delivery with zero queue delays or Meta rate limits.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .fetch import Job

DEFAULT_DASHBOARD_URL = "https://shubhaammm08.github.io/Job-Hunt/"


def make_job_buttons(job_id: str, apply_url: str) -> dict[str, Any]:
    """Create interactive Telegram inline keyboard buttons for a job."""
    cb_applied = f"app:{job_id}"[:64]
    cb_pitch = f"pitch:{job_id}"[:64]
    cb_kit = f"kit:{job_id}"[:64]

    keyboard = [
        [
            {"text": "🚀 1-Click Apply", "url": apply_url or DEFAULT_DASHBOARD_URL},
            {"text": "⚡ AutoFill Kit", "callback_data": cb_kit},
        ],
        [
            {"text": "📋 Pitch Note", "callback_data": cb_pitch},
            {"text": "✅ Mark Applied", "callback_data": cb_applied},
        ],
        [
            {"text": "🌐 Dashboard", "url": DEFAULT_DASHBOARD_URL},
        ],
    ]
    return {"inline_keyboard": keyboard}


def format_job_card(job: Job) -> str:
    """Format a single job into an executive interactive Telegram card."""
    score = job.score or 0.0
    score_icon = "🔥" if score >= 8.0 else "⭐"
    loc = (job.location or "").strip()
    loc_badge = "🌐 Remote" if (job.remote or "remote" in loc.lower()) else (f"📍 {loc}" if loc else "📍 Direct ATS")

    lines = [
        f"{score_icon} *{job.company}* — *{job.title}*",
        f"🎯 Fit Score: *{score:.1f}/10* | {loc_badge}",
    ]
    if job.salary and job.salary.strip():
        lines.append(f"💰 {job.salary.strip()}")
    if job.reason and job.reason.strip():
        reason_clean = re.sub(r"\s+", " ", job.reason).strip()
        lines.append(f"💡 _{reason_clean[:140]}..._" if len(reason_clean) > 140 else f"💡 _{reason_clean}_")

    apply_link = (job.apply_url or job.url or "").strip()
    if apply_link:
        lines.append(f"🔗 [Direct Application Link]({apply_link})")
    return "\n".join(lines)


def format_telegram_alert(
    jobs: list[Job],
    scanned: int = 0,
    candidates: int = 0,
    stats: dict[str, Any] | None = None,
    name: str = "Shubham",
    max_jobs: int = 5,
    min_score: float = 6.0,
    dashboard_url: str = DEFAULT_DASHBOARD_URL,
) -> str:
    """Format job recommendations into an executive Telegram message with Markdown styling."""
    today = datetime.datetime.now().strftime("%d %b %Y")

    scored_jobs = [j for j in jobs if (j.score or 0.0) >= min_score]
    scored_jobs.sort(key=lambda j: (j.score or 0.0), reverse=True)

    lines: list[str] = []

    if scored_jobs:
        high_match_count = sum(1 for j in scored_jobs if (j.score or 0.0) >= 8.0)
        badge = "🔥 *HIGH MATCH ALERT*" if high_match_count > 0 else "🎯 *JOB RECOMMENDATIONS*"

        lines.append(f"{badge} — {name}'s JobHunt")
        lines.append(f"📅 {today}")
        lines.append(f"📊 Scanned: {scanned:,} | Filtered: {candidates:,} | Matched: {len(scored_jobs)}")
        lines.append("")

        top_slice = scored_jobs[:max_jobs]
        for idx, job in enumerate(top_slice, 1):
            score = job.score or 0.0
            score_icon = "🔥" if score >= 8.0 else "⭐"

            loc = (job.location or "").strip()
            if job.remote or "remote" in loc.lower():
                loc_badge = "🌐 Remote"
            elif loc:
                loc_badge = f"📍 {loc}"
            else:
                loc_badge = "📍 Direct ATS"

            lines.append(f"{idx}. {score_icon} *{job.company}* — *{job.title}*")
            lines.append(f"   🎯 Fit Score: *{score:.1f}/10* | {loc_badge}")

            if job.salary and job.salary.strip():
                lines.append(f"   💰 {job.salary.strip()}")

            if job.reason and job.reason.strip():
                clean_reason = re.sub(r"\s+", " ", job.reason).strip()
                if len(clean_reason) > 140:
                    clean_reason = clean_reason[:137] + "..."
                lines.append(f"   💡 _{clean_reason}_")

            apply_link = (job.apply_url or job.url or "").strip()
            if apply_link:
                lines.append(f"   🔗 [1-Click Apply Link]({apply_link})")
            lines.append("")

        remaining = len(scored_jobs) - len(top_slice)
        if remaining > 0:
            lines.append(f"➕ _...and {remaining} more matching opportunities on your dashboard._")
            lines.append("")

        lines.append(f"⚡ [Executive Dashboard & AutoFill Kit]({dashboard_url})")
    else:
        lines.append(f"ℹ️ *JobHunt Daily Update* — {name}")
        lines.append(f"📅 {today}")
        lines.append(f"📊 Scanned {scanned:,} listings across active feeds.")
        lines.append(f"No new postings cleared score >= {min_score} today.")
        lines.append("Boards are quiet or no new roles met criteria.")
        lines.append("")
        lines.append(f"🌐 [Review Pipeline on Dashboard]({dashboard_url})")

    return "\n".join(lines)


def send_telegram(
    message: str,
    bot_token: str | None = None,
    chat_id: str | None = None,
    reply_markup: dict[str, Any] | None = None,
) -> bool:
    """Deliver a message via official Telegram Bot API with optional inline keyboard buttons."""
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    cid = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not cid:
        raise RuntimeError(
            "Missing Telegram credentials: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env "
            "(or GitHub Secrets). To get them in 30s: message @BotFather on Telegram, send /newbot."
        )

    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    body: dict[str, Any] = {
        "chat_id": str(cid).strip(),
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }
    if reply_markup:
        body["reply_markup"] = reply_markup

    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "JobHunt-Telegram-Bot/1.0"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        if e.code == 400 and body.get("parse_mode"):
            # Markdown formatting fallback: retry without markdown to guarantee delivery
            body.pop("parse_mode", None)
            payload2 = json.dumps(body).encode("utf-8")
            req2 = urllib.request.Request(
                url,
                data=payload2,
                headers={"Content-Type": "application/json", "User-Agent": "JobHunt-Telegram-Bot/1.0"},
                method="POST",
            )
            with urllib.request.urlopen(req2, timeout=15) as resp2:
                return 200 <= resp2.status < 300
        raise


def send_job_card(
    job: Job,
    bot_token: str | None = None,
    chat_id: str | None = None,
) -> bool:
    """Send an individual high-match job card with interactive 1-click action buttons."""
    card_text = format_job_card(job)
    buttons = make_job_buttons(job.job_id, job.apply_url or job.url)
    return send_telegram(card_text, bot_token=bot_token, chat_id=chat_id, reply_markup=buttons)


def send_telegram_digest(
    jobs: list[Job],
    scanned: int = 0,
    candidates: int = 0,
    stats: dict[str, Any] | None = None,
    cfg: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
    send_interactive_cards: bool = True,
) -> bool:
    """Format and send the Telegram digest based on configuration, with optional interactive cards."""
    cfg = cfg or {}
    profile = profile or {}
    tg_cfg = cfg.get("notifications", {}).get("telegram", {}) if isinstance(cfg.get("notifications"), dict) else {}

    min_score = float(tg_cfg.get("min_score", 6.0))
    max_jobs = int(tg_cfg.get("max_jobs_per_alert", 5))
    candidate_name = profile.get("name", "Shubham")

    # 1. Send the primary executive digest summary
    text = format_telegram_alert(
        jobs=jobs,
        scanned=scanned,
        candidates=candidates,
        stats=stats,
        name=candidate_name,
        max_jobs=max_jobs,
        min_score=min_score,
    )

    quick_menu = {
        "inline_keyboard": [
            [
                {"text": "📊 View Dashboard", "url": DEFAULT_DASHBOARD_URL},
                {"text": "⚡ AutoFill Kit", "url": f"{DEFAULT_DASHBOARD_URL}#kit"},
            ]
        ]
    }

    try:
        ok = send_telegram(text, reply_markup=quick_menu)
        if not ok:
            return False

        # 2. For top high-match jobs (score >= 7.0), send interactive cards with 1-click buttons
        if send_interactive_cards:
            top_actionable = [j for j in jobs if (j.score or 0.0) >= 7.0]
            top_actionable.sort(key=lambda j: (j.score or 0.0), reverse=True)
            for j in top_actionable[:3]:
                send_job_card(j)

        return True
    except Exception as e:
        print(f"  ! Telegram alert skipped or failed: {e}")
        return False
