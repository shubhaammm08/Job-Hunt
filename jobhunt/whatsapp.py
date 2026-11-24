"""Send daily job digests and instant high-match alerts to WhatsApp via CallMeBot or Twilio.

Zero cost, zero server infrastructure needed.
Supports CallMeBot (100% free personal WhatsApp bot) and Twilio WhatsApp Sandbox.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .fetch import Job


DEFAULT_DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "https://shubhaammm08.github.io/Job-Hunt/")


def clean_phone_number(phone: str) -> str:
    """Normalize phone number to international digits (e.g. +91 98765-43210 -> +919876543210 or 919876543210)."""
    if not phone:
        return ""
    phone = phone.strip()
    has_plus = phone.startswith("+")
    digits = re.sub(r"[^\d]", "", phone)
    if not digits:
        return ""
    return f"+{digits}" if has_plus else digits


def format_whatsapp_alert(
    jobs: list[Job],
    scanned: int = 0,
    candidates: int = 0,
    stats: dict[str, Any] | None = None,
    name: str = "Shubham",
    max_jobs: int = 5,
    min_score: float = 6.0,
    dashboard_url: str = DEFAULT_DASHBOARD_URL,
) -> str:
    """Format job recommendations into an executive WhatsApp message with markdown styling."""
    today = datetime.datetime.now().strftime("%d %b %Y")
    
    # Filter and sort jobs by score
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
            
            # Location / Remote tag
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
                # Clean and truncate reason to 140 chars for clean readability
                clean_reason = re.sub(r"\s+", " ", job.reason).strip()
                if len(clean_reason) > 140:
                    clean_reason = clean_reason[:137] + "..."
                lines.append(f"   💡 _{clean_reason}_")

            apply_link = (job.apply_url or job.url or "").strip()
            if apply_link:
                lines.append(f"   🔗 1-Click Apply: {apply_link}")
            lines.append("")

        remaining = len(scored_jobs) - len(top_slice)
        if remaining > 0:
            lines.append(f"➕ _...and {remaining} more matching opportunities on your dashboard._")
            lines.append("")

        lines.append("⚡ *Auto-Fill Kit & Tracker:*")
        lines.append(dashboard_url)
    else:
        # Quiet day message
        lines.append(f"ℹ️ *JobHunt Daily Update* — {name}")
        lines.append(f"📅 {today}")
        lines.append(f"📊 Scanned {scanned:,} listings across active feeds.")
        lines.append(f"No new postings cleared score >= {min_score} today.")
        lines.append("Boards are quiet or no new roles met criteria.")
        lines.append("")
        lines.append("🌐 *Review Pipeline on Dashboard:*")
        lines.append(dashboard_url)

    return "\n".join(lines)


def send_callmebot(phone: str, apikey: str, text: str) -> bool:
    """Deliver a message via CallMeBot free WhatsApp API."""
    clean_phone = clean_phone_number(phone)
    if not clean_phone or not apikey:
        raise ValueError("CallMeBot requires both phone and apikey")

    # CallMeBot accepts phone number with or without leading +
    encoded_phone = urllib.parse.quote(clean_phone)
    encoded_text = urllib.parse.quote_plus(text)
    encoded_key = urllib.parse.quote(apikey.strip())

    url = f"https://api.callmebot.com/whatsapp.php?phone={encoded_phone}&text={encoded_text}&apikey={encoded_key}"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "JobHunt-WhatsApp-Bot/1.0 (+https://github.com/shubhaammm08/Job-Hunt)"},
        method="GET",
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8", errors="ignore")
        # CallMeBot returns HTTP 200 with text indicating success or error
        if "error" in body.lower() and "success" not in body.lower():
            raise RuntimeError(f"CallMeBot API error: {body.strip()}")
        return True


def send_twilio_whatsapp(
    account_sid: str,
    auth_token: str,
    to_phone: str,
    from_phone: str,
    text: str,
) -> bool:
    """Deliver a message via Twilio WhatsApp API."""
    to_num = clean_phone_number(to_phone)
    if not to_num.startswith("+"):
        to_num = f"+{to_num}"
    
    from_num = clean_phone_number(from_phone)
    if not from_num.startswith("+"):
        from_num = f"+{from_num}"

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    data = urllib.parse.urlencode({
        "To": f"whatsapp:{to_num}",
        "From": f"whatsapp:{from_num}",
        "Body": text,
    }).encode("utf-8")

    import base64
    auth_header = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("ascii")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "JobHunt-Twilio/1.0",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        return 200 <= resp.status < 300


def send_webhook(webhook_url: str, text: str) -> bool:
    """Send alert to a custom webhook URL (Slack/Discord/Telegram bridge/Make/Zapier)."""
    payload = json.dumps({"text": text, "message": text, "content": text}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "JobHunt-Webhook/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return 200 <= resp.status < 300


def send_whatsapp(
    message: str,
    phone: str | None = None,
    apikey: str | None = None,
    provider: str | None = None,
) -> bool:
    """Send a WhatsApp message using configured credentials.
    
    Tries providers in priority:
    1. CallMeBot free API (WHATSAPP_PHONE + WHATSAPP_APIKEY)
    2. Twilio WhatsApp (TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN)
    3. Custom Webhook (WHATSAPP_WEBHOOK_URL)
    """
    phone = phone or os.environ.get("WHATSAPP_PHONE") or os.environ.get("CALLMEBOT_PHONE")
    apikey = apikey or os.environ.get("WHATSAPP_APIKEY") or os.environ.get("CALLMEBOT_APIKEY")
    webhook_url = os.environ.get("WHATSAPP_WEBHOOK_URL")

    # Twilio env vars
    twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
    twilio_from = os.environ.get("TWILIO_WHATSAPP_FROM", "+14155238886")
    twilio_to = os.environ.get("TWILIO_WHATSAPP_TO") or phone

    provider = (provider or os.environ.get("WHATSAPP_PROVIDER") or "").lower()

    if (provider == "twilio" or (twilio_sid and twilio_token)) and provider != "callmebot":
        if twilio_sid and twilio_token and twilio_to:
            try:
                ok = send_twilio_whatsapp(twilio_sid, twilio_token, twilio_to, twilio_from, message)
                print(f"  whatsapp (twilio) -> {clean_phone_number(twilio_to)}")
                return ok
            except Exception as e:
                print(f"  ! twilio whatsapp failed: {e}")

    if webhook_url and (provider == "webhook" or not (phone and apikey)):
        try:
            ok = send_webhook(webhook_url, message)
            print(f"  whatsapp (webhook) -> {webhook_url[:35]}...")
            return ok
        except Exception as e:
            print(f"  ! webhook delivery failed: {e}")

    if phone and apikey:
        try:
            ok = send_callmebot(phone, apikey, message)
            masked_phone = clean_phone_number(phone)
            if len(masked_phone) > 6:
                masked_phone = masked_phone[:4] + "***" + masked_phone[-3:]
            print(f"  whatsapp (callmebot) -> {masked_phone} (delivered)")
            return ok
        except Exception as e:
            print(f"  ! callmebot whatsapp failed: {e}")
            raise

    raise RuntimeError(
        "Missing WhatsApp credentials: set WHATSAPP_PHONE and WHATSAPP_APIKEY in .env "
        "(or GitHub Secrets). To get your free CallMeBot key in 10s: "
        "send 'I allow callmebot to send me messages' to +34 623 78 64 49 on WhatsApp."
    )


def send_whatsapp_digest(
    jobs: list[Job],
    scanned: int = 0,
    candidates: int = 0,
    stats: dict[str, Any] | None = None,
    cfg: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
) -> bool:
    """Format and send the WhatsApp digest based on configuration."""
    cfg = cfg or {}
    profile = profile or {}
    wa_cfg = cfg.get("notifications", {}).get("whatsapp", {}) if isinstance(cfg.get("notifications"), dict) else {}
    
    min_score = float(wa_cfg.get("min_score", 6.0))
    max_jobs = int(wa_cfg.get("max_jobs_per_alert", 5))
    candidate_name = profile.get("name", "Shubham")

    text = format_whatsapp_alert(
        jobs=jobs,
        scanned=scanned,
        candidates=candidates,
        stats=stats,
        name=candidate_name,
        max_jobs=max_jobs,
        min_score=min_score,
    )

    try:
        return send_whatsapp(text)
    except Exception as e:
        print(f"  ! WhatsApp alert skipped or failed: {e}")
        return False
