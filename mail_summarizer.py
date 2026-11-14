"""Shubham's 4-Hour Email Summarizer & Categorizer.

Connects to Gmail via IMAP, pulls recent unseen emails, categorizes them using
Gemini, filters out promotional noise, and delivers a clean "short and sweet"
HTML briefing of important emails to ssk080204@gmail.com every 4 hours.
"""
from __future__ import annotations

import argparse
import email
from email.header import decode_header
import html
import imaplib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import smtplib
from email.message import EmailMessage
import time
import requests

ROOT = Path(__file__).resolve().parent


def load_env(path: Path | str = ROOT / ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def decode_mime(val: str | None) -> str:
    if not val:
        return ""
    parts = decode_header(val)
    res = []
    for text, enc in parts:
        if isinstance(text, bytes):
            res.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            res.append(str(text))
    return "".join(res).strip()


def extract_body(msg: email.message.Message, max_chars: int = 600) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition"))
            if ct == "text/plain" and "attachment" not in cd:
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="replace")
                    break
        if not body:  # fallback to html snippet if no text/plain
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="replace")
                        break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="replace")

    # Clean whitespace and strip tags crudely
    clean = " ".join(body.split())
    return clean[:max_chars]


def fetch_new_emails(user: str, password: str, state_file: Path,
                     limit: int = 25, force: bool = False) -> tuple[list[dict], int]:
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(user, password)
    mail.select("inbox", readonly=True)

    status, data = mail.search(None, "ALL")
    if status != "OK" or not data[0]:
        mail.logout()
        return [], 0

    all_ids = [int(x) for x in data[0].split()]
    last_seen = 0
    if not force and state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            last_seen = int(state.get("last_seen_id", 0))
        except Exception:
            last_seen = 0

    if last_seen > 0:
        new_ids = [mid for mid in all_ids if mid > last_seen]
    else:
        new_ids = all_ids[-limit:]  # first run: last 20-25 messages

    if not new_ids:
        mail.logout()
        return [], (max(all_ids) if all_ids else 0)

    # cap per run
    eval_ids = new_ids[-limit:]
    fetched = []

    for mid in reversed(eval_ids):
        status, msg_data = mail.fetch(str(mid).encode(), "(RFC822)")
        if status != "OK" or not msg_data:
            continue
        for part in msg_data:
            if isinstance(part, tuple):
                msg = email.message_from_bytes(part[1])
                sender = decode_mime(msg.get("From"))
                subj = decode_mime(msg.get("Subject"))
                date_str = decode_mime(msg.get("Date"))
                
                # skip emails sent by JobHunt itself or self to avoid loops
                if "JobHunt" in subj or (user and user.lower() in sender.lower() and "4-Hour" in subj):
                    continue

                snippet = extract_body(msg)
                fetched.append({
                    "id": mid,
                    "from": sender,
                    "subject": subj,
                    "date": date_str,
                    "snippet": snippet,
                })

    max_seen = max(all_ids) if all_ids else 0
    mail.logout()
    return fetched, max_seen


def analyze_with_gemini(emails: list[dict], api_key: str,
                        model: str = "gemini-flash-lite-latest") -> dict:
    if not emails:
        return {"has_important": False, "headline": "No new emails received.", "categories": [], "noise_summary": ""}

    system_prompt = """You are Shubham Sunil Kadam's executive inbox assistant.
Shubham is a Computer Engineering graduate seeking an entry-level Data Analyst / Junior AI Developer role.

Review the incoming emails and provide a crisp, categorized executive summary.
Strict Rules:
- Emphasize IMPORTANT emails only:
  1. Job Applications & Recruiter Outreach (interview invites, test links, status updates, rejections, offers)
  2. High-fit Job Alerts (Data Analyst, BI, Python, or AI roles in Mumbai, Pune, Bangalore, or Remote)
  3. Action Required & Security Alerts (Google security alerts, deadlines, official notices)
- Filter out marketing spam, promotions, generic newsletters, and sports scores into a brief single-sentence noise note.
- Keep summaries short and sweet (max 1-2 punchy sentences per item).

Return ONLY a JSON object (no markdown fences, no prose outside JSON):
{
  "has_important": bool,
  "headline": str,
  "categories": [
    {
      "title": str,
      "badge_color": str, // #3fb950 (green/important), #7c9cff (blue/info), #d29922 (warning/alert)
      "items": [
        {
          "sender": str,
          "subject": str,
          "summary": str,
          "action_required": str // e.g. "None — Application confirmed" or "Schedule interview" or "Review alert"
        }
      ]
    }
  ],
  "noise_summary": str
}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": api_key}
    payload = {
        "contents": [{"parts": [{"text": f"Here are the latest {len(emails)} emails:\n\n{json.dumps(emails, ensure_ascii=False)}"}]}],
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2, "maxOutputTokens": 2000}
    }

    for attempt in range(1, 4):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=45)
            if r.status_code == 200:
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
            if r.status_code in (429, 503) and attempt < 3:
                time.sleep(2 * attempt)
                continue
        except Exception:
            if attempt < 3:
                time.sleep(2 * attempt)
                continue

    # Fallback if Gemini is unreachable
    return {
        "has_important": True,
        "headline": f"{len(emails)} new email(s) reviewed",
        "categories": [{
            "title": "📬 Recent Inbound",
            "badge_color": "#7c9cff",
            "items": [{"sender": e["from"], "subject": e["subject"], "summary": e["snippet"][:150], "action_required": "Review email"} for e in emails[:5]]
        }],
        "noise_summary": "Automated fallback mode."
    }


def render_html(data: dict, total_scanned: int) -> str:
    now_str = datetime.now().strftime("%d %b %Y · %I:%M %p")
    headline = data.get("headline", "Your 4-Hour Email Summary")
    noise = data.get("noise_summary", "")

    category_html = ""
    for cat in data.get("categories", []):
        items_html = ""
        for item in cat.get("items", []):
            action = item.get("action_required")
            action_tag = f'<div style="margin-top:6px;font-size:12px;color:#d29922;font-weight:600;">⚡ Action: {html.escape(action)}</div>' if action and action.lower() != "none" else ""
            
            items_html += f"""
            <div style="background:#13161c;border:1px solid #262b36;border-radius:8px;padding:12px 14px;margin-bottom:10px;">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div style="font-size:14px;font-weight:700;color:#e6e8ec;">{html.escape(item.get('subject', 'No Subject'))}</div>
              </div>
              <div style="font-size:12px;color:#8b93a3;margin:3px 0 6px 0;">{html.escape(item.get('sender', ''))}</div>
              <p style="margin:0;font-size:13px;line-height:1.5;color:#c9d1d9;">{html.escape(item.get('summary', ''))}</p>
              {action_tag}
            </div>
            """

        badge_color = cat.get("badge_color", "#7c9cff")
        category_html += f"""
        <div style="margin-bottom:20px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
            <span style="background:{badge_color};width:8px;height:8px;border-radius:50%;display:inline-block;"></span>
            <div style="font-size:15px;font-weight:700;color:#e6e8ec;">{html.escape(cat.get('title', 'Category'))}</div>
          </div>
          {items_html}
        </div>
        """

    noise_box = f"""
    <div style="margin-top:16px;padding:12px;background:#0d1017;border:1px solid #262b36;border-radius:8px;font-size:12px;color:#8b93a3;line-height:1.5;">
      🧹 <strong>Low-Priority / Filtered Out:</strong> {html.escape(noise)}
    </div>
    """ if noise else ""

    return f"""<!doctype html>
<html>
<body style="margin:0;padding:20px;background:#0f1115;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="max-width:600px;margin:0 auto;background:#171a21;border:1px solid #262b36;border-radius:12px;padding:22px;">
    
    <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #262b36;padding-bottom:14px;margin-bottom:16px;">
      <div>
        <div style="font-size:20px;font-weight:800;color:#e6e8ec;">Shubham's Email Briefing 📬</div>
        <div style="font-size:12px;color:#8b93a3;margin-top:3px;">{now_str} · Last 4 Hours · {total_scanned} emails reviewed</div>
      </div>
      <span style="background:#238636;color:#ffffff;font-size:11px;font-weight:700;padding:3px 9px;border-radius:999px;">SHORT &amp; SWEET</span>
    </div>

    <div style="background:#1f242d;border-radius:8px;padding:10px 14px;margin-bottom:18px;font-size:14px;color:#7c9cff;font-weight:600;">
      📌 {html.escape(headline)}
    </div>

    {category_html}
    {noise_box}

    <div style="margin-top:20px;padding-top:14px;border-top:1px solid #262b36;text-align:center;font-size:11px;color:#6e7681;">
      Automated 4-hour briefing curated for Shubham Sunil Kadam. Only important updates are surfaced.
    </div>
  </div>
</body>
</html>"""


def send_email(subject: str, html_body: str, host: str = "smtp.gmail.com",
               port: int = 587, user: str = "", password: str = "", to_addr: str = "") -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    msg.set_content("This is an HTML email briefing. Please open in an HTML-capable email client.")
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls()
        s.login(user, password)
        s.send_message(msg)
    print(f"  Briefing delivered to -> {to_addr}")


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser(description="4-Hour Executive Email Summarizer")
    parser.add_argument("--force", action="store_true", help="Process latest emails regardless of seen state")
    args = parser.parse_args()

    user = os.environ.get("GMAIL_EMAIL") or os.environ.get("SMTP_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("SMTP_PASS")
    api_key = os.environ.get("GEMINI_API_KEY")
    to_addr = os.environ.get("MAIL_TO", user)

    if not user or not password or not api_key:
        print("Missing required credentials: GMAIL_EMAIL (or SMTP_USER), GMAIL_APP_PASSWORD (or SMTP_PASS), or GEMINI_API_KEY")
        return 1

    out_dir = ROOT / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    state_file = out_dir / "summary_seen.json"
    log_file = out_dir / "mail_summary.log"

    def log(msg: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    log("Starting 4-hour email summary check...")
    emails, max_id = fetch_new_emails(user, password, state_file, limit=20, force=args.force)

    if not emails:
        log("No new emails received in this window. Skipping email.")
        return 0

    log(f"Fetched {len(emails)} new incoming emails. Analyzing via Gemini...")
    summary = analyze_with_gemini(emails, api_key)

    subject = f"Shubham's 4-Hour Email Briefing 📬 — {datetime.now().strftime('%d %b, %I:%M %p')}"
    html_doc = render_html(summary, len(emails))

    # Save local copy
    (out_dir / "last_briefing.html").write_text(html_doc, encoding="utf-8")

    # Send briefing
    try:
        send_email(subject, html_doc, user=user, password=password, to_addr=to_addr)
        log("Briefing successfully emailed!")
    except Exception as e:
        log(f"Failed to send email: {e}")
        return 1

    # Update state
    state_file.write_text(json.dumps({"last_seen_id": max_id, "updated_at": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
    log(f"State saved. Last processed message ID: {max_id}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
