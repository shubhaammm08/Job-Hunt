"""Unit and integration tests for WhatsApp Bot alert dispatcher (CallMeBot & Twilio)."""
from __future__ import annotations

import io
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from jobhunt.fetch import Job
from jobhunt.whatsapp import (
    clean_phone_number,
    format_whatsapp_alert,
    send_callmebot,
    send_twilio_whatsapp,
    send_whatsapp,
    send_whatsapp_digest,
)


def _sample_jobs() -> list[Job]:
    return [
        Job(
            job_id="greenhouse:stripe:123",
            ats="greenhouse",
            company="Stripe",
            title="Software Engineer, Intern",
            location="Bengaluru, India",
            url="https://stripe.com/jobs/123",
            description="Software engineering intern in Bangalore.",
            score=8.5,
            reason="Excellent overlap with Python, databases, and junior developer qualifications.",
            salary="INR 12-15 LPA",
            remote=False,
        ),
        Job(
            job_id="remoteok:global:456",
            ats="remoteok",
            company="DataCorp",
            title="Junior Data Analyst",
            location="Remote",
            url="https://remoteok.com/jobs/456",
            description="Entry level data analyst with SQL and PowerBI.",
            score=7.2,
            reason="Direct alignment with candidate SQL and PowerBI projects.",
            remote=True,
        ),
        Job(
            job_id="ashby:openai:789",
            ats="ashby",
            company="AI Innovations",
            title="AI Application Developer",
            location="Remote",
            url="https://jobs.ashbyhq.com/innovations/789",
            description="Junior AI application developer.",
            score=5.5,  # Below default min_score 6.0
            reason="Good candidate, but requires 3 years experience.",
            remote=True,
        ),
    ]


# ---------------------------------------------------------------------- Tests --

def test_clean_phone_number():
    assert clean_phone_number("+91 98765-43210") == "+919876543210"
    assert clean_phone_number("919876543210") == "919876543210"
    assert clean_phone_number("+1 (555) 234-5678") == "+15552345678"
    assert clean_phone_number("") == ""
    assert clean_phone_number("   ") == ""


def test_format_whatsapp_alert_with_high_match():
    jobs = _sample_jobs()
    text = format_whatsapp_alert(
        jobs=jobs,
        scanned=1500,
        candidates=12,
        name="Shubham",
        max_jobs=5,
        min_score=6.0,
    )

    assert "HIGH MATCH ALERT" in text
    assert "Shubham's JobHunt" in text
    assert "Stripe" in text
    assert "Software Engineer, Intern" in text
    assert "Fit Score: *8.5/10*" in text
    assert "DataCorp" in text
    assert "Junior Data Analyst" in text
    assert "Fit Score: *7.2/10*" in text
    # 5.5 should be excluded because min_score is 6.0
    assert "AI Innovations" not in text
    assert "https://shubhaammm08.github.io/Job-Hunt/" in text


def test_format_whatsapp_alert_quiet_day():
    jobs = _sample_jobs()
    # If min_score is 9.0, no jobs match
    text = format_whatsapp_alert(
        jobs=jobs,
        scanned=5000,
        candidates=0,
        name="Shubham",
        min_score=9.0,
    )

    assert "JobHunt Daily Update" in text
    assert "No new postings cleared score >= 9.0" in text
    assert "Scanned 5,000 listings" in text
    assert "https://shubhaammm08.github.io/Job-Hunt/" in text


def test_format_whatsapp_alert_max_jobs_truncation():
    jobs = _sample_jobs()
    text = format_whatsapp_alert(
        jobs=jobs,
        scanned=1000,
        candidates=5,
        name="Shubham",
        max_jobs=1,  # Only 1 shown
        min_score=6.0,
    )

    assert "Stripe" in text
    assert "DataCorp" not in text
    assert "more matching opportunities" in text


def test_send_callmebot_success():
    fake_resp = MagicMock()
    fake_resp.read.return_value = b"Message queued to +919876543210 (Success)"
    fake_resp.__enter__.return_value = fake_resp

    with patch("urllib.request.urlopen", return_value=fake_resp) as mock_urlopen:
        ok = send_callmebot(
            phone="+919876543210",
            apikey="123456",
            text="Test alert message",
        )
        assert ok is True
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert "api.callmebot.com" in req.full_url
        assert "phone=%2B919876543210" in req.full_url or "phone=%2B919876543210" in req.full_url
        assert "apikey=123456" in req.full_url


def test_send_callmebot_error_response():
    fake_resp = MagicMock()
    fake_resp.read.return_value = b"Error: Invalid apikey or phone number"
    fake_resp.__enter__.return_value = fake_resp

    with patch("urllib.request.urlopen", return_value=fake_resp):
        with pytest.raises(RuntimeError, match="CallMeBot API error"):
            send_callmebot("+919876543210", "bad_key", "Test")


def test_send_twilio_whatsapp():
    fake_resp = MagicMock()
    fake_resp.status = 201
    fake_resp.__enter__.return_value = fake_resp

    with patch("urllib.request.urlopen", return_value=fake_resp) as mock_urlopen:
        ok = send_twilio_whatsapp(
            account_sid="AC1234567890",
            auth_token="auth_secret",
            to_phone="+919876543210",
            from_phone="+14155238886",
            text="Twilio WhatsApp Alert",
        )
        assert ok is True
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert "api.twilio.com" in req.full_url
        assert req.method == "POST"


def test_send_whatsapp_missing_credentials(monkeypatch):
    monkeypatch.delenv("WHATSAPP_PHONE", raising=False)
    monkeypatch.delenv("CALLMEBOT_PHONE", raising=False)
    monkeypatch.delenv("WHATSAPP_APIKEY", raising=False)
    monkeypatch.delenv("CALLMEBOT_APIKEY", raising=False)
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("WHATSAPP_WEBHOOK_URL", raising=False)

    with pytest.raises(RuntimeError, match="Missing WhatsApp credentials"):
        send_whatsapp("Test message")


def test_send_whatsapp_callmebot_flow(monkeypatch):
    monkeypatch.setenv("WHATSAPP_PHONE", "+919876543210")
    monkeypatch.setenv("WHATSAPP_APIKEY", "654321")
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)

    fake_resp = MagicMock()
    fake_resp.read.return_value = b"Message sent (Success)"
    fake_resp.__enter__.return_value = fake_resp

    with patch("urllib.request.urlopen", return_value=fake_resp):
        ok = send_whatsapp("Hello from JobHunt")
        assert ok is True


def test_send_whatsapp_digest_safe_execution(monkeypatch):
    monkeypatch.setenv("WHATSAPP_PHONE", "+919876543210")
    monkeypatch.setenv("WHATSAPP_APIKEY", "123456")

    fake_resp = MagicMock()
    fake_resp.read.return_value = b"Success"
    fake_resp.__enter__.return_value = fake_resp

    cfg = {
        "notifications": {
            "whatsapp": {
                "enabled": True,
                "min_score": 7.0,
                "max_jobs_per_alert": 3,
            }
        }
    }
    profile = {"name": "Shubham Kadam"}

    with patch("urllib.request.urlopen", return_value=fake_resp):
        ok = send_whatsapp_digest(_sample_jobs(), scanned=200, candidates=5, cfg=cfg, profile=profile)
        assert ok is True
