"""Unit tests for Telegram Bot alert dispatcher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from jobhunt.fetch import Job
from jobhunt.telegram import (
    format_telegram_alert,
    send_telegram,
    send_telegram_digest,
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
            reason="Excellent overlap with Python and junior developer qualifications.",
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
    ]


def test_format_telegram_alert():
    jobs = _sample_jobs()
    text = format_telegram_alert(jobs, scanned=1000, candidates=5, name="Shubham")
    assert "HIGH MATCH ALERT" in text
    assert "Stripe" in text
    assert "Software Engineer, Intern" in text
    assert "Fit Score: *8.5/10*" in text
    assert "DataCorp" in text
    assert "[1-Click Apply Link]" in text


def test_send_telegram_success():
    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.__enter__.return_value = fake_resp

    with patch("urllib.request.urlopen", return_value=fake_resp) as mock_urlopen:
        ok = send_telegram("Hello Telegram", bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", chat_id="987654321")
        assert ok is True
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert "api.telegram.org" in req.full_url
        assert "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11" in req.full_url


def test_send_telegram_missing_credentials(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(RuntimeError, match="Missing Telegram credentials"):
        send_telegram("Hello")
