"""Unit tests for the 2-way interactive Telegram Bot."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from jobhunt.store import Store
from jobhunt.telegram_bot import (
    DEFAULT_SCREENING_QA,
    answer_callback,
    analyze_jd_with_ai,
    format_autofill_kit,
    format_screening_qa_bank,
    generate_pitch_note,
    get_updates,
    handle_applied,
    handle_callback_query,
    handle_hunt,
    handle_qa,
    handle_reminders,
    handle_remote,
    handle_search,
    handle_start_help,
    handle_stats,
    handle_top,
    process_update,
    poll_updates,
    set_bot_commands,
)


@pytest.fixture
def mock_store(tmp_path):
    store_file = tmp_path / "test_seen.json"
    data = {
        "greenhouse:stripe:101": {
            "first_seen": "2026-11-17T10:00:00+00:00",
            "company": "Stripe",
            "title": "Software Engineer, Intern",
            "location": "Bengaluru, India",
            "url": "https://stripe.com/jobs/101",
            "score": 8.5,
            "reason": "Strong match with Python and data requirements.",
            "remote": False,
            "applied": False,
            "applied_on": None,
        },
        "remoteok:dataco:202": {
            "first_seen": "2026-11-17T11:00:00+00:00",
            "company": "DataCo",
            "title": "Junior Data Analyst",
            "location": "Remote",
            "url": "https://dataco.com/jobs/202",
            "score": 7.5,
            "reason": "Direct overlap with SQL and Power BI.",
            "remote": True,
            "applied": False,
            "applied_on": None,
        },
        "ashby:oldcorp:303": {
            "first_seen": "2026-11-10T09:00:00+00:00",
            "company": "OldCorp",
            "title": "Data Engineer",
            "location": "Remote",
            "url": "https://oldcorp.com/jobs/303",
            "score": 8.0,
            "reason": "Applied last week.",
            "remote": True,
            "applied": True,
            "applied_on": "2026-11-10T10:00:00+00:00",
        },
    }
    store_file.write_text(json.dumps(data), encoding="utf-8")
    return Store(store_file)


@pytest.fixture
def sample_profile():
    return {
        "name": "Shubham Sunil Kadam",
        "current_title": "Junior AI Developer",
        "years_experience": 1,
        "core_skills": ["Python", "SQL", "Power BI", "Machine Learning"],
        "domains": ["Data Analysis", "ETL Pipelines"],
    }


def test_set_bot_commands():
    fake_resp = MagicMock()
    fake_resp.read.return_value = json.dumps({"ok": True, "result": True}).encode("utf-8")
    fake_resp.__enter__.return_value = fake_resp

    with patch("urllib.request.urlopen", return_value=fake_resp) as mock_url:
        ok = set_bot_commands("test_token")
        assert ok is True
        mock_url.assert_called_once()


def test_get_updates():
    mock_payload = {
        "ok": True,
        "result": [
            {"update_id": 1, "message": {"text": "/top", "chat": {"id": 12345}}},
        ],
    }
    fake_resp = MagicMock()
    fake_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    fake_resp.__enter__.return_value = fake_resp

    with patch("urllib.request.urlopen", return_value=fake_resp):
        updates = get_updates("test_token")
        assert len(updates) == 1
        assert updates[0]["update_id"] == 1


def test_answer_callback():
    fake_resp = MagicMock()
    fake_resp.read.return_value = json.dumps({"ok": True}).encode("utf-8")
    fake_resp.__enter__.return_value = fake_resp

    with patch("urllib.request.urlopen", return_value=fake_resp):
        ok = answer_callback("test_token", "cb_123", "Alert text")
        assert ok is True


def test_handle_start_help(sample_profile):
    with patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        handle_start_help(12345, "token", sample_profile)
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert "Welcome, Shubham" in args[0]
        assert "/top" in args[0]
        assert "reply_markup" in kwargs


def test_handle_top(mock_store):
    with patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        handle_top(12345, "token", mock_store)
        # Should send header + 2 high-match cards
        assert mock_send.call_count >= 2


def test_handle_remote(mock_store):
    with patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        handle_remote(12345, "token", mock_store)
        assert mock_send.call_count >= 2
        # Card should be DataCo or OldCorp
        sent_texts = [call[0][0] for call in mock_send.call_args_list]
        assert any("DataCo" in t or "OldCorp" in t for t in sent_texts)


def test_handle_stats(mock_store):
    with patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        handle_stats(12345, "token", mock_store)
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "Total Roles Tracked" in text
        assert "High-Match Roles" in text


def test_handle_applied(mock_store):
    with patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        # Search by company name
        handle_applied(12345, "token", mock_store, "Stripe")
        assert mock_send.call_count == 1
        text = mock_send.call_args[0][0]
        assert "Application Logged Successfully" in text
        assert "Stripe" in text

        # Verify Store state updated
        assert mock_store.data["greenhouse:stripe:101"]["applied"] is True
        assert mock_store.data["greenhouse:stripe:101"]["applied_on"] is not None


def test_handle_reminders(mock_store, sample_profile):
    with patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        handle_reminders(12345, "token", mock_store, sample_profile)
        assert mock_send.call_count >= 2
        sent_texts = [call[0][0] for call in mock_send.call_args_list]
        assert any("OldCorp" in t for t in sent_texts)
        assert any("Outreach Template" in t for t in sent_texts)


def test_handle_hunt(mock_store):
    with patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        handle_hunt(12345, "token", mock_store)
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "JobHunter Live Status" in text
        assert "GitHub Actions" in text


def test_callback_query_mark_applied(mock_store, sample_profile):
    cb = {
        "id": "cb_001",
        "data": "app:greenhouse:stripe:101",
        "message": {"chat": {"id": 12345}},
    }
    with patch("jobhunt.telegram_bot.answer_callback") as mock_ans, patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        handle_callback_query("token", cb, mock_store, sample_profile)
        mock_ans.assert_called_once()
        assert mock_store.data["greenhouse:stripe:101"]["applied"] is True
        mock_send.assert_called_once()
        assert "Marked Applied" in mock_send.call_args[0][0]


def test_callback_query_pitch_note(mock_store, sample_profile):
    cb = {
        "id": "cb_002",
        "data": "pitch:remoteok:dataco:202",
        "message": {"chat": {"id": 12345}},
    }
    with patch("jobhunt.telegram_bot.answer_callback") as mock_ans, patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        handle_callback_query("token", cb, mock_store, sample_profile)
        mock_ans.assert_called_once()
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "Outreach Pitch" in text
        assert "DataCo" in text


def test_callback_query_autofill_kit(mock_store, sample_profile):
    cb = {
        "id": "cb_003",
        "data": "kit:greenhouse:stripe:101",
        "message": {"chat": {"id": 12345}},
    }
    with patch("jobhunt.telegram_bot.answer_callback") as mock_ans, patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        handle_callback_query("token", cb, mock_store, sample_profile)
        mock_ans.assert_called_once()
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "Quick AutoFill Kit" in text
        assert "Stripe" in text
        assert "ssk080204@gmail.com" in text


def test_generate_pitch_note(sample_profile):
    job_data = {"company": "Figma", "title": "Data Analyst"}
    pitch = generate_pitch_note(job_data, sample_profile)
    assert "Figma" in pitch
    assert "Data Analyst" in pitch
    assert "Shubham" in pitch
    assert "Python" in pitch


def test_analyze_jd_with_ai(sample_profile):
    sample_jd = "Looking for a Python Developer with SQL experience in building data pipelines."
    # With fallback or mock
    res = analyze_jd_with_ai(sample_jd, sample_profile)
    assert "AI Job Fit Analysis" in res or "Job Analysis" in res
    assert "Outreach" in res or "Pitch" in res


def test_process_update_command(mock_store, sample_profile):
    update = {
        "update_id": 99,
        "message": {
            "text": "/stats",
            "chat": {"id": 12345},
        },
    }
    with patch("jobhunt.telegram_bot.handle_stats") as mock_hs:
        process_update(update, "token", mock_store, sample_profile)
        mock_hs.assert_called_once_with(12345, "token", mock_store)


def test_poll_updates_once(mock_store, sample_profile):
    mock_updates = [
        {"update_id": 101, "message": {"text": "/top", "chat": {"id": 12345}}},
    ]
    with patch("jobhunt.telegram_bot.get_updates", return_value=mock_updates), \
         patch("jobhunt.telegram_bot.set_bot_commands"), \
         patch("jobhunt.telegram_bot.process_update") as mock_proc:
        poll_updates("token", mock_store, sample_profile, once=True)
        mock_proc.assert_called_once()


def test_handle_search_with_matches(mock_store):
    with patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        handle_search(12345, "token", mock_store, "Data")
        assert mock_send.call_count >= 2
        sent_texts = [call[0][0] for call in mock_send.call_args_list]
        assert any("Found" in t and "matching role" in t for t in sent_texts)


def test_handle_search_empty_and_no_match(mock_store):
    with patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        # Empty query
        handle_search(12345, "token", mock_store, "")
        assert mock_send.call_count == 1
        assert "How to search" in mock_send.call_args[0][0]

    with patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        # Non-matching query
        handle_search(12345, "token", mock_store, "NonExistentCompanyOrSkill999")
        assert mock_send.call_count == 1
        assert "No tracked jobs matched" in mock_send.call_args[0][0]


def test_handle_qa():
    with patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        handle_qa(12345, "token")
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "Screening Q&A Bank" in text
        assert "Python & SQL Experience" in text
        assert "GenAI & LLM Stack" in text
        assert "Notice Period" in text


def test_format_screening_qa_bank():
    text = format_screening_qa_bank()
    assert "Screening Q&A Bank" in text
    for q, a in DEFAULT_SCREENING_QA:
        assert q in text
        assert a in text


def test_format_autofill_kit_synced_fields(sample_profile):
    job_data = {"company": "Acme", "title": "Data Engineer"}
    kit = format_autofill_kit(job_data, sample_profile)
    assert "https://www.linkedin.com/in/shubham-kadam-data/" in kit
    assert "Shubham Sunil Kadam" in kit
    assert "ssk080204@gmail.com" in kit
    assert "Current CTC" in kit
    assert "Expected CTC" in kit
    assert "Gender Identity" in kit


def test_callback_query_screening_qa(mock_store, sample_profile):
    cb = {
        "id": "cb_004",
        "data": "qa:greenhouse:stripe:101",
        "message": {"chat": {"id": 12345}},
    }
    with patch("jobhunt.telegram_bot.answer_callback") as mock_ans, patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        handle_callback_query("token", cb, mock_store, sample_profile)
        mock_ans.assert_called_once()
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "Screening Q&A Bank" in text


def test_callback_query_cmd_search_and_qa(mock_store, sample_profile):
    cb_search = {
        "id": "cb_005",
        "data": "cmd:search",
        "message": {"chat": {"id": 12345}},
    }
    with patch("jobhunt.telegram_bot.answer_callback") as mock_ans, patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        handle_callback_query("token", cb_search, mock_store, sample_profile)
        mock_ans.assert_called_once()
        mock_send.assert_called_once()
        assert "How to search" in mock_send.call_args[0][0]

    cb_qa = {
        "id": "cb_006",
        "data": "cmd:qa",
        "message": {"chat": {"id": 12345}},
    }
    with patch("jobhunt.telegram_bot.answer_callback") as mock_ans, patch("jobhunt.telegram_bot.send_telegram") as mock_send:
        handle_callback_query("token", cb_qa, mock_store, sample_profile)
        mock_ans.assert_called_once()
        mock_send.assert_called_once()
        assert "Screening Q&A Bank" in mock_send.call_args[0][0]


def test_process_update_search_and_qa(mock_store, sample_profile):
    update_search = {
        "update_id": 102,
        "message": {
            "text": "/search Python",
            "chat": {"id": 12345},
        },
    }
    with patch("jobhunt.telegram_bot.handle_search") as mock_hs:
        process_update(update_search, "token", mock_store, sample_profile)
        mock_hs.assert_called_once_with(12345, "token", mock_store, "Python")

    update_qa = {
        "update_id": 103,
        "message": {
            "text": "/qa",
            "chat": {"id": 12345},
        },
    }
    with patch("jobhunt.telegram_bot.handle_qa") as mock_hq:
        process_update(update_qa, "token", mock_store, sample_profile)
        mock_hq.assert_called_once_with(12345, "token")
