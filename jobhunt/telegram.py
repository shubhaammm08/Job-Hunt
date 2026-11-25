"""Send daily job digests and instant high-match alerts to Telegram with interactive action buttons.

100% Free forever, officially supported by Telegram Bot API.
Instant delivery with zero queue delays or Meta rate limits.
"""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .fetch import Job

DEFAULT_DASHBOARD_URL = (os.environ.get("DASHBOARD_URL") or "").strip() or "https://shubhaammm08.github.io/Job-Hunt/"
TRACKED_MESSAGES_FILE = Path("out/telegram_messages.json")


def track_sent_message(chat_id: str | int, message_id: int, kind: str = "alert", store_file: Path | str | None = None) -> None:
    """Record sent Telegram message IDs for 24-hour auto-delete lifecycle management."""
    fpath = Path(store_file or TRACKED_MESSAGES_FILE)
    try:
        fpath.parent.mkdir(parents=True, exist_ok=True)
        entries: list[dict[str, Any]] = []
        if fpath.exists():
            try:
                entries = json.loads(fpath.read_text(encoding="utf-8"))
            except Exception:
                entries = []
        entries.append({
            "chat_id": str(chat_id),
            "message_id": int(message_id),
            "sent_at": time.time(),
            "kind": kind,
        })
        fpath.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    except Exception:
        pass


def delete_telegram_message(chat_id: str | int, message_id: int, bot_token: str | None = None) -> bool:
    """Delete a Telegram message via official deleteMessage API."""
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return False
    url = f"https://api.telegram.org/bot{token.strip()}/deleteMessage"
    body = {"chat_id": str(chat_id).strip(), "message_id": int(message_id)}
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "JobHunt-Telegram-Bot/2.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def pin_telegram_message(chat_id: str | int, message_id: int, bot_token: str | None = None, disable_notification: bool = True) -> bool:
    """Pin a message to the top of the Telegram chat."""
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return False
    url = f"https://api.telegram.org/bot{token.strip()}/pinChatMessage"
    body = {
        "chat_id": str(chat_id).strip(),
        "message_id": int(message_id),
        "disable_notification": disable_notification,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "JobHunt-Telegram-Bot/2.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def unpin_telegram_message(chat_id: str | int, message_id: int | None = None, bot_token: str | None = None) -> bool:
    """Unpin a previously pinned message."""
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return False
    method = "unpinChatMessage" if message_id else "unpinAllChatMessages"
    url = f"https://api.telegram.org/bot{token.strip()}/{method}"
    body: dict[str, Any] = {"chat_id": str(chat_id).strip()}
    if message_id:
        body["message_id"] = int(message_id)
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "JobHunt-Telegram-Bot/2.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def cleanup_expired_messages(bot_token: str | None = None, max_age_seconds: int = 86400, store_file: Path | str | None = None) -> int:
    """Delete all tracked Telegram messages older than max_age_seconds (default 24 hours)."""
    fpath = Path(store_file or TRACKED_MESSAGES_FILE)
    if not fpath.exists():
        return 0
    try:
        entries: list[dict[str, Any]] = json.loads(fpath.read_text(encoding="utf-8"))
    except Exception:
        return 0

    now = time.time()
    retained: list[dict[str, Any]] = []
    deleted_count = 0

    for item in entries:
        sent_at = float(item.get("sent_at", 0))
        cid = item.get("chat_id")
        mid = item.get("message_id")
        if (now - sent_at) >= max_age_seconds and cid and mid:
            delete_telegram_message(cid, mid, bot_token=bot_token)
            deleted_count += 1
        else:
            retained.append(item)

    try:
        fpath.write_text(json.dumps(retained, indent=2), encoding="utf-8")
    except Exception:
        pass

    return deleted_count


def extract_tech_tags(text: str) -> list[str]:
    """Extract relevant technology hashtags from job metadata."""
    keywords = [
        "Python", "SQL", "FastAPI", "Pandas", "ETL", "AWS", "GCP", "Azure",
        "Docker", "Power BI", "Tableau", "GenAI", "LLM", "React", "PostgreSQL",
        "Kafka", "Airflow", "Spark", "Machine Learning", "Git",
    ]
    found: list[str] = []
    text_lower = text.lower()
    for kw in keywords:
        pattern = r"\b" + re.escape(kw.lower()) + r"\b"
        if re.search(pattern, text_lower):
            tag = "#" + kw.replace(" ", "")
            if tag not in found:
                found.append(tag)
        if len(found) >= 5:
            break
    return found


def make_job_buttons(job_id: str, apply_url: str) -> dict[str, Any]:
    """Create modern interactive Telegram inline keyboard buttons for a job."""
    cb_applied = f"app:{job_id}"[:64]
    cb_pitch = f"pitch:{job_id}"[:64]
    cb_cl = f"cl:{job_id}"[:64]
    cb_kit = f"kit:{job_id}"[:64]
    cb_qa = f"qa:{job_id}"[:64]
    cb_sal = f"sal:{job_id}"[:64]
    cb_rec = f"rec:{job_id}"[:64]

    keyboard = [
        [
            {"text": "🚀 1-Click Apply", "url": (apply_url or "").strip() or DEFAULT_DASHBOARD_URL},
            {"text": "⚡ AutoFill Kit", "callback_data": cb_kit},
        ],
        [
            {"text": "📋 Pitch Note", "callback_data": cb_pitch},
            {"text": "📝 Cover Letter", "callback_data": cb_cl},
        ],
        [
            {"text": "❓ Screening Q&A", "callback_data": cb_qa},
            {"text": "💼 Salary Guide", "callback_data": cb_sal},
        ],
        [
            {"text": "🔍 Find Recruiters", "callback_data": cb_rec},
            {"text": "✅ Mark Applied", "callback_data": cb_applied},
        ],
    ]
    return {"inline_keyboard": keyboard}


def format_job_card(job: Job) -> str:
    """Format a single job into an executive interactive Telegram card."""
    score = job.score or 0.0
    if score >= 8.5:
        score_pill = f"🔥 *{score:.1f}/10 · TOP MATCH*"
    elif score >= 7.0:
        score_pill = f"⭐ *{score:.1f}/10 · STRONG MATCH*"
    else:
        score_pill = f"🎯 *{score:.1f}/10 · RECOMMENDED*"

    loc = (job.location or "").strip()
    if job.remote or "remote" in loc.lower():
        loc_badge = "🌐 100% Remote"
    elif loc:
        loc_badge = f"📍 {loc}"
    else:
        loc_badge = "📍 Direct ATS"

    lines = [
        f"{score_pill} | {loc_badge}",
        f"🏢 *{job.company}* — *{job.title}*",
    ]

    sal = (job.salary or "").strip()
    if sal:
        lines.append(f"💰 *Compensation:* `{sal}`")

    if job.reason and job.reason.strip():
        reason_clean = re.sub(r"\s+", " ", job.reason).strip()
        if len(reason_clean) > 160:
            reason_clean = reason_clean[:157] + "..."
        lines.append(f"💡 *Why You Match:* _{reason_clean}_")

    tags = extract_tech_tags(f"{job.title} {job.description} {job.reason}")
    if tags:
        lines.append(f"🏷️ {' '.join(tags)}")

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
    kind: str = "alert",
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
        headers={"Content-Type": "application/json", "User-Agent": "JobHunt-Telegram-Bot/2.0"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = 200 <= getattr(resp, "status", 200) < 300
            try:
                raw = resp.read()
                if raw:
                    data = json.loads(raw.decode("utf-8", errors="ignore"))
                    msg_id = data.get("result", {}).get("message_id")
                    if msg_id and cid:
                        track_sent_message(str(cid).strip(), msg_id, kind=kind)
            except Exception:
                pass
            return ok
    except urllib.error.HTTPError as e:
        if e.code == 400 and body.get("parse_mode"):
            # Markdown formatting fallback: retry without markdown to guarantee delivery
            body.pop("parse_mode", None)
            payload2 = json.dumps(body).encode("utf-8")
            req2 = urllib.request.Request(
                url,
                data=payload2,
                headers={"Content-Type": "application/json", "User-Agent": "JobHunt-Telegram-Bot/2.0"},
                method="POST",
            )
            with urllib.request.urlopen(req2, timeout=15) as resp2:
                ok = 200 <= getattr(resp2, "status", 200) < 300
                try:
                    raw = resp2.read()
                    if raw:
                        data = json.loads(raw.decode("utf-8", errors="ignore"))
                        msg_id = data.get("result", {}).get("message_id")
                        if msg_id and cid:
                            track_sent_message(str(cid).strip(), msg_id, kind=kind)
                except Exception:
                    pass
                return ok
        raise


def send_job_card(
    job: Job,
    bot_token: str | None = None,
    chat_id: str | None = None,
) -> bool:
    """Send an individual high-match job card with interactive 1-click action buttons."""
    card_text = format_job_card(job)
    buttons = make_job_buttons(job.job_id, job.apply_url or job.url)
    return send_telegram(card_text, bot_token=bot_token, chat_id=chat_id, reply_markup=buttons, kind="job_card")


def send_telegram_digest(
    jobs: list[Job],
    scanned: int = 0,
    candidates: int = 0,
    stats: dict[str, Any] | None = None,
    cfg: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
    send_interactive_cards: bool = True,
    bot_token: str | None = None,
    chat_id: str | None = None,
) -> bool:
    """Format and send the Telegram digest with 24h auto-delete cleanup, pinning, and interactive cards."""
    cfg = cfg or {}
    profile = profile or {}
    tg_cfg = cfg.get("notifications", {}).get("telegram", {}) if isinstance(cfg.get("notifications"), dict) else {}

    min_score = float(tg_cfg.get("min_score", 6.0))
    max_jobs = int(tg_cfg.get("max_jobs_per_alert", 5))
    candidate_name = profile.get("name", "Shubham")

    # 0. Clean up any expired messages older than 24 hours
    cleanup_expired_messages(bot_token=bot_token, max_age_seconds=86400)

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
                {"text": "📊 Web Dashboard", "url": DEFAULT_DASHBOARD_URL},
                {"text": "⚡ AutoFill Kit", "url": f"{DEFAULT_DASHBOARD_URL}#kit"},
            ],
            [
                {"text": "🔍 Search Jobs", "callback_data": "cmd:search"},
                {"text": "❓ Screening Q&A", "callback_data": "cmd:qa"},
            ],
        ]
    }

    try:
        ok = send_telegram(text, bot_token=bot_token, chat_id=chat_id, reply_markup=quick_menu, kind="briefing")
        if not ok:
            return False

        # Attempt to pin the new daily briefing
        cid = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        if cid and TRACKED_MESSAGES_FILE.exists():
            try:
                tracked = json.loads(TRACKED_MESSAGES_FILE.read_text(encoding="utf-8"))
                briefings = [m for m in tracked if m.get("kind") == "briefing"]
                if briefings:
                    pin_telegram_message(cid, briefings[-1]["message_id"], bot_token=bot_token)
            except Exception:
                pass

        # 2. For top high-match jobs (score >= 7.0), send interactive cards with 1-click buttons
        if send_interactive_cards:
            top_actionable = [j for j in jobs if (j.score or 0.0) >= 7.0]
            top_actionable.sort(key=lambda j: (j.score or 0.0), reverse=True)
            for j in top_actionable[:3]:
                send_job_card(j, bot_token=bot_token, chat_id=chat_id)

        return True
    except Exception as e:
        print(f"  ! Telegram alert skipped or failed: {e}")
        return False
