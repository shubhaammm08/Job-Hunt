"""Send the digest over SMTP. Gmail: use an App Password, not your login."""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def send(subject: str, html_body: str) -> None:
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.environ.get("GMAIL_EMAIL") or os.environ.get("SMTP_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("SMTP_PASS")
    if not user or not password:
        raise RuntimeError("Missing SMTP credentials: set GMAIL_EMAIL/SMTP_USER and GMAIL_APP_PASSWORD/SMTP_PASS")
    to_addr = os.getenv("MAIL_TO", user)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    msg.set_content("This digest is HTML. Open it in an HTML-capable client.")
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls()
        s.login(user, password)
        s.send_message(msg)
    print(f"  mailed -> {to_addr}")
