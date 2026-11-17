"""Send daily job digests and instant high-match alerts to Telegram.

100% Free forever, officially supported by Telegram Bot API.
Instant 1-second delivery with zero queue delays or Meta rate limits.
"""
from __future__ import annotations

import datetime
import os
import re
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .fetch import Job

DEFAULT_DASHBOARD_URL = "https://shubhaammm08.github.io/Job-Hunt/"


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
) -> bool:
    """Deliver a message via official Telegram Bot API."""
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    cid = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not cid:
        raise RuntimeError(
            "Missing Telegram credentials: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env "
            "(or GitHub Secrets). To get them in 30s: message @BotFather on Telegram, send /newbot."
        )

    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id": str(cid).strip(),
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": "false",
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"User-Agent": "JobHunt-Telegram-Bot/1.0"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        return 200 <= resp.status < 300


def send_telegram_digest(
    jobs: list[Job],
    scanned: int = 0,
    candidates: int = 0,
    stats: dict[str, Any] | None = None,
    cfg: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
) -> bool:
    """Format and send the Telegram digest based on configuration."""
    cfg = cfg or {}
    profile = profile or {}
    tg_cfg = cfg.get("notifications", {}).get("telegram", {}) if isinstance(cfg.get("notifications"), dict) else {}

    min_score = float(tg_cfg.get("min_score", 6.0))
    max_jobs = int(tg_cfg.get("max_jobs_per_alert", 5))
    candidate_name = profile.get("name", "Shubham")

    text = format_telegram_alert(
        jobs=jobs,
        scanned=scanned,
        candidates=candidates,
        stats=stats,
        name=candidate_name,
        max_jobs=max_jobs,
        min_score=min_score,
    )

    try:
        return send_telegram(text)
    except Exception as e:
        print(f"  ! Telegram alert skipped or failed: {e}")
        return False
