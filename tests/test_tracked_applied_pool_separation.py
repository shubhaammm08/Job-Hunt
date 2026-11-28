"""Regression tests for Tracked vs Applied pool separation, external Apply link decoupling,
and idempotent reload persistence across gui/server.py and gui/index.html -> index.html.
"""
from __future__ import annotations

import base64
from http.server import HTTPServer
import json
from pathlib import Path
import re
import socket
import sys
import threading
import urllib.error
import urllib.request

import pytest
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import gui.server as server_mod


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _make_sample_seen() -> dict:
    return {
        "linkedin:100001": {
            "first_seen": "2026-11-28T05:00:00+00:00",
            "company": "Alpha AI",
            "title": "AI Engineer",
            "location": "Remote",
            "url": "https://www.linkedin.com/jobs/view/100001",
            "score": 8.5,
            "reason": "Strong GenAI fit",
            "canonical_source": "linkedin",
            "sources": ["linkedin"],
            "role_families": ["AI_CORE"],
            "matched_roles": ["AI Engineer"],
            "fit_score": 8.5,
            "emailed": True,
            "applied": False,
            "applied_on": None,
        },
        "naukri:200002": {
            "first_seen": "2026-11-28T04:00:00+00:00",
            "company": "Beta Data",
            "title": "Data Analyst",
            "location": "Mumbai",
            "url": "https://www.naukri.com/job-listings-data-analyst-200002",
            "score": 6.5,
            "reason": "Solid analytics fit",
            "canonical_source": "naukri",
            "sources": ["naukri"],
            "role_families": ["DATA"],
            "matched_roles": ["Data Analyst"],
            "fit_score": 6.5,
            "emailed": False,
            "applied": True,
            "applied_on": "2026-11-27T10:00:00+00:00",
        },
        "greenhouse:gamma:300003": {
            "first_seen": "2026-11-27T04:00:00+00:00",
            "company": "Gamma Corp",
            "title": "Python Developer",
            "location": "Bengaluru",
            "url": "https://boards.greenhouse.io/gamma/jobs/300003",
            "score": 5.0,
            "reason": "Backend match",
            "canonical_source": "greenhouse",
            "sources": ["greenhouse"],
            "role_families": ["SOFTWARE"],
            "matched_roles": ["Python Developer"],
            "fit_score": 5.0,
            "emailed": False,
            "applied": False,
            "applied_on": None,
        },
    }


@pytest.fixture()
def isolated_server(tmp_path, monkeypatch):
    """Run JobHuntHandler against an isolated temp ROOT directory."""
    seen_path = tmp_path / "seen.json"
    seen_path.write_text(json.dumps(_make_sample_seen(), indent=2), encoding="utf-8")
    (tmp_path / "profile.json").write_text(
        json.dumps({"name": "Test User", "email": "test@example.com"}),
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "source_health.json").write_text("[]", encoding="utf-8")

    # Inject sample INITIAL_DATA where naukri:200002 is applied AND greenhouse:gamma:300003
    # is stale-marked applied in INITIAL_DATA while seen.json has it unapplied (tests stale INITIAL_DATA).
    template = (ROOT_DIR / "gui" / "index.html").read_text(encoding="utf-8")
    sample_seen = _make_sample_seen()
    stale_jobs = [{"job_id": k, **v} for k, v in sample_seen.items()]
    stale_jobs[2]["applied"] = True  # Intentionally stale in INITIAL_DATA
    initial_payload = {
        "jobs": stale_jobs,
        "stats": {
            "total": 3,
            "unapplied": 1,
            "tracked": 1,
            "applied": 2,
            "emailed": 1,
            "recommended": 2,
            "recommended_unapplied": 1,
            "sources_count": 0,
        },
        "profile": {"name": "Test User", "email": "test@example.com"},
        "source_health": [],
        "digest_html": "",
    }
    injected = f"<script>window.INITIAL_DATA = {json.dumps(initial_payload)};</script>\n</head>"
    (tmp_path / "index.html").write_text(template.replace("</head>", injected, 1), encoding="utf-8")

    monkeypatch.setattr(server_mod, "ROOT", tmp_path)

    port = _get_free_port()
    srv = HTTPServer(("127.0.0.1", port), server_mod.JobHuntHandler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}", tmp_path
    finally:
        srv.shutdown()
        srv.server_close()


def test_static_templates_decouple_external_apply_from_toggle_applied():
    """Clicking external Apply or Auto-Fill & Apply must not call toggleApplied."""
    for html_path in [ROOT_DIR / "gui" / "index.html", ROOT_DIR / "index.html"]:
        content = html_path.read_text(encoding="utf-8")
        m_handle = re.search(r"function handleApplyClick\(.*?\n    \}", content, re.DOTALL)
        assert m_handle, f"handleApplyClick not found in {html_path}"
        assert "toggleApplied" not in m_handle.group(0), (
            f"handleApplyClick must not call toggleApplied in {html_path}"
        )

        m_apply_cur = re.search(r"function applyCurrentJob\(.*?\n    \}", content, re.DOTALL)
        assert m_apply_cur, f"applyCurrentJob not found in {html_path}"
        assert "toggleApplied" not in m_apply_cur.group(0), (
            f"applyCurrentJob must not call toggleApplied in {html_path}"
        )


def test_api_data_no_store_and_unapplied_stats(isolated_server):
    """GET /api/data returns Cache-Control: no-store and accurate unapplied/tracked stats."""
    base_url, _ = isolated_server
    with urllib.request.urlopen(f"{base_url}/api/data") as resp:
        assert resp.headers.get("Cache-Control") == "no-store"
        data = json.loads(resp.read().decode("utf-8"))

    stats = data["stats"]
    assert stats["total"] == 3
    assert stats["unapplied"] == 2
    assert stats["tracked"] == 2
    assert stats["applied"] == 1
    assert stats["recommended"] == 2
    assert stats["recommended_unapplied"] == 1


def test_api_toggle_applied_is_idempotent_and_updates_applied_on(isolated_server):
    """POST /api/toggle-applied accepts explicit applied bool, sets/clears applied_on, and exports CSV."""
    base_url, tmp_path = isolated_server

    def post_toggle(payload: dict) -> dict:
        req = urllib.request.Request(
            f"{base_url}/api/toggle-applied",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # Idempotent false -> false (must NOT flip false to true!)
    res1 = post_toggle({"job_id": "linkedin:100001", "applied": False})
    assert res1 == {"success": True, "job_id": "linkedin:100001", "applied": False}
    seen = json.loads((tmp_path / "seen.json").read_text(encoding="utf-8"))
    assert seen["linkedin:100001"]["applied"] is False
    assert seen["linkedin:100001"]["applied_on"] is None

    # Idempotent true -> true sets applied_on and stays true on repeat
    res2 = post_toggle({"job_id": "linkedin:100001", "applied": True})
    assert res2 == {"success": True, "job_id": "linkedin:100001", "applied": True}
    seen = json.loads((tmp_path / "seen.json").read_text(encoding="utf-8"))
    first_applied_on = seen["linkedin:100001"]["applied_on"]
    assert isinstance(first_applied_on, str) and first_applied_on

    res3 = post_toggle({"job_id": "linkedin:100001", "applied": True})
    assert res3["applied"] is True
    seen = json.loads((tmp_path / "seen.json").read_text(encoding="utf-8"))
    assert seen["linkedin:100001"]["applied_on"] == first_applied_on

    # Explicit false clears applied and applied_on
    res4 = post_toggle({"job_id": "linkedin:100001", "applied": False})
    assert res4["applied"] is False
    seen = json.loads((tmp_path / "seen.json").read_text(encoding="utf-8"))
    assert seen["linkedin:100001"]["applied"] is False
    assert seen["linkedin:100001"]["applied_on"] is None

    # CSV export reflects updated seen.json
    csv_text = (tmp_path / "out" / "tracker.csv").read_text(encoding="utf-8")
    assert "linkedin:100001" in csv_text


def test_local_server_e2e_pool_separation_and_reload_persistence(isolated_server):
    """Verifies initial counts ignore stale INITIAL_DATA, external Apply doesn't mark,
    Mark Applied persists, and unmarking from Applied Hub persists across reload.
    """
    base_url, _ = isolated_server

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Mock Firestore REST so tests never touch live cloud state
        cloud_ids = ["naukri:200002"]

        def handle_firestore(route):
            req = route.request
            if req.method == "PATCH":
                body = json.loads(req.post_data or "{}")
                vals = (
                    body.get("fields", {})
                    .get("applied_ids", {})
                    .get("arrayValue", {})
                    .get("values", [])
                )
                cloud_ids[:] = [v["stringValue"] for v in vals if "stringValue" in v]
                route.fulfill(status=200, content_type="application/json", body=json.dumps({"fields": {}}))
            else:
                doc = {
                    "fields": {
                        "applied_ids": {
                            "arrayValue": {"values": [{"stringValue": jid} for jid in cloud_ids]}
                        },
                        "applied_jobs": {"mapValue": {"fields": {}}},
                    }
                }
                route.fulfill(status=200, content_type="application/json", body=json.dumps(doc))

        page.route("https://firestore.googleapis.com/**", handle_firestore)
        page.goto(f"{base_url}/", wait_until="networkidle")
        page.wait_for_selector(".job-card", timeout=5000)

        # Even though INITIAL_DATA had greenhouse:gamma:300003 marked applied, live /api/data wins (2 unapplied, 1 applied)
        assert page.inner_text("#metric-total").strip() == "2"
        assert page.inner_text("#metric-applied").strip() == "1"
        assert page.inner_text("#metric-recommended").strip() == "1"
        assert page.inner_text("#metric-applied-rate").strip() == "33% applied"
        assert "Showing 2 of 2 opportunities" in page.inner_text("#results-count")
        assert page.query_selector("[id='card-naukri:200002']") is None
        assert page.query_selector("[id='card-greenhouse:gamma:300003']") is not None

        # Clicking external Apply link on linkedin:100001 must NOT mark it applied
        with context.expect_page() as popup_info:
            page.click("[id='card-linkedin:100001'] .btn-apply-link")
        popup_info.value.close()
        page.wait_for_timeout(150)
        assert page.inner_text("#metric-total").strip() == "2"
        assert page.inner_text("#metric-applied").strip() == "1"
        assert page.query_selector("[id='card-linkedin:100001']") is not None

        # Clicking Mark Applied moves linkedin:100001 out of Tracked into Applied
        page.click("[id='card-linkedin:100001'] .btn-applied")
        page.wait_for_timeout(250)
        assert page.inner_text("#metric-total").strip() == "1"
        assert page.inner_text("#metric-applied").strip() == "2"
        assert page.inner_text("#metric-recommended").strip() == "0"
        assert page.inner_text("#metric-applied-rate").strip() == "67% applied"
        assert "Showing 1 of 1 opportunities" in page.inner_text("#results-count")
        assert page.query_selector("[id='card-linkedin:100001']") is None

        # Reload persists (1 Tracked, 2 Applied)
        page.reload(wait_until="networkidle")
        page.wait_for_selector(".job-card", timeout=5000)
        assert page.inner_text("#metric-total").strip() == "1"
        assert page.inner_text("#metric-applied").strip() == "2"
        assert page.query_selector("[id='card-linkedin:100001']") is None

        # Open Applied Hub, remove pre-existing naukri:200002, verify reload persists unmark!
        page.click("button:has-text('Applied Hub')")
        page.wait_for_selector("#modal-applied-tracker.open", timeout=3000)
        remove_btns = page.query_selector_all("#applied-tracker-list button:has-text('Remove')")
        assert len(remove_btns) == 2
        # Unmark both from Applied Hub -> 0 applied, 3 tracked
        for _ in range(2):
            page.click("#applied-tracker-list button:has-text('Remove')")
            page.wait_for_timeout(200)

        assert page.inner_text("#metric-total").strip() == "3"
        assert page.inner_text("#metric-applied").strip() == "0"
        assert page.inner_text("#metric-applied-rate").strip() == "0% applied"

        page.reload(wait_until="networkidle")
        page.wait_for_selector(".job-card", timeout=5000)
        assert page.inner_text("#metric-total").strip() == "3"
        assert page.inner_text("#metric-applied").strip() == "0"
        assert page.query_selector("[id='card-naukri:200002']") is not None
        assert page.query_selector("[id='card-linkedin:100001']") is not None

        browser.close()


def test_api_toggle_applied_rejects_invalid_json_with_400_and_unknown_job_with_404(isolated_server):
    """POST /api/toggle-applied returns 400 on malformed/non-dict/empty JSON and missing job_id, 404 on unknown job_id."""
    base_url, _ = isolated_server

    def post_raw(raw_bytes: bytes) -> tuple[int, dict]:
        req = urllib.request.Request(
            f"{base_url}/api/toggle-applied",
            data=raw_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            raw_body = err.read().decode("utf-8")
            return err.code, json.loads(raw_body) if raw_body else {}

    for bad_payload in [b"{not valid json", b'["linkedin:100001"]', b"123", b""]:
        status, body = post_raw(bad_payload)
        assert status == 400, f"Expected 400 for {bad_payload!r}, got {status}"
        assert body.get("success") is False

    status_missing_id, body_missing_id = post_raw(b'{"applied": true}')
    assert status_missing_id == 400
    assert body_missing_id.get("success") is False

    status_unknown, body_unknown = post_raw(b'{"job_id": "unknown:999999", "applied": true}')
    assert status_unknown == 404
    assert body_unknown.get("success") is False


def test_transient_api_data_failure_does_not_poison_local_storage(isolated_server):
    """Transient /api/data 500 fallback to stale INITIAL_DATA must not write stale applied flags to localStorage."""
    base_url, _ = isolated_server

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        cloud_ids = ["naukri:200002"]

        def handle_firestore(route):
            req = route.request
            if req.method == "PATCH":
                body = json.loads(req.post_data or "{}")
                vals = (
                    body.get("fields", {})
                    .get("applied_ids", {})
                    .get("arrayValue", {})
                    .get("values", [])
                )
                cloud_ids[:] = [v["stringValue"] for v in vals if "stringValue" in v]
                route.fulfill(status=200, content_type="application/json", body=json.dumps({"fields": {}}))
            else:
                doc = {
                    "fields": {
                        "applied_ids": {
                            "arrayValue": {"values": [{"stringValue": jid} for jid in cloud_ids]}
                        },
                        "applied_jobs": {"mapValue": {"fields": {}}},
                    }
                }
                route.fulfill(status=200, content_type="application/json", body=json.dumps(doc))

        fail_api_data = {"active": True}

        def handle_api_data(route):
            if fail_api_data["active"]:
                fail_api_data["active"] = False
                route.fulfill(status=500, content_type="application/json", body='{"error":"restart"}')
            else:
                route.continue_()

        page.route("https://firestore.googleapis.com/**", handle_firestore)
        page.route("**/api/data", handle_api_data)

        # First load: /api/data returns 500 -> falls back to stale INITIAL_DATA (greenhouse:gamma:300003 applied=True)
        page.goto(f"{base_url}/", wait_until="networkidle")
        page.wait_for_selector(".job-card", timeout=5000)

        ls_after_500 = page.evaluate("""() => ({
            appliedJobs: JSON.parse(localStorage.getItem('jobhunt_applied_jobs') || '{}'),
            appliedList: JSON.parse(localStorage.getItem('jobhunt_applied') || '[]'),
        })""")
        assert "greenhouse:gamma:300003" not in ls_after_500["appliedJobs"]
        assert "greenhouse:gamma:300003" not in ls_after_500["appliedList"]

        # Subsequent reload: /api/data recovers (200) -> stale INITIAL_DATA must not resurrect greenhouse:gamma:300003
        page.reload(wait_until="networkidle")
        page.wait_for_selector(".job-card", timeout=5000)
        assert page.inner_text("#metric-total").strip() == "2"
        assert page.inner_text("#metric-applied").strip() == "1"
        assert page.query_selector("[id='card-greenhouse:gamma:300003']") is not None
        assert "greenhouse:gamma:300003" not in cloud_ids

        browser.close()


def test_pull_cloud_sync_missing_applied_at_respects_unmarked_tombstone(isolated_server):
    """pullCloudSync() with missing applied_at in Firestore applied_jobs must not resurrect an unmarked job."""
    base_url, _ = isolated_server

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        cloud_state = {
            "ids": ["naukri:200002"],
            "omit_applied_at": False,
        }

        def handle_firestore(route):
            req = route.request
            if req.method == "PATCH":
                body = json.loads(req.post_data or "{}")
                vals = (
                    body.get("fields", {})
                    .get("applied_ids", {})
                    .get("arrayValue", {})
                    .get("values", [])
                )
                cloud_state["ids"] = [v["stringValue"] for v in vals if "stringValue" in v]
                route.fulfill(status=200, content_type="application/json", body=json.dumps({"fields": {}}))
            else:
                job_fields = {
                    "job_id": {"stringValue": "naukri:200002"},
                    "title": {"stringValue": "Data Analyst"},
                }
                if not cloud_state["omit_applied_at"]:
                    job_fields["applied_at"] = {"stringValue": "2026-11-27T10:00:00.000Z"}
                doc = {
                    "fields": {
                        "applied_ids": {
                            "arrayValue": {"values": [{"stringValue": jid} for jid in cloud_state["ids"]]}
                        },
                        "applied_jobs": {
                            "mapValue": {
                                "fields": (
                                    {"naukri:200002": {"mapValue": {"fields": job_fields}}}
                                    if "naukri:200002" in cloud_state["ids"]
                                    else {}
                                )
                            }
                        },
                    }
                }
                route.fulfill(status=200, content_type="application/json", body=json.dumps(doc))

        page.route("https://firestore.googleapis.com/**", handle_firestore)
        page.goto(f"{base_url}/", wait_until="networkidle")
        page.wait_for_selector(".job-card", timeout=5000)

        # Unmark naukri:200002 via Applied Hub -> sets jobhunt_unmarked_jobs['naukri:200002']
        page.click("button:has-text('Applied Hub')")
        page.wait_for_selector("#modal-applied-tracker.open", timeout=3000)
        page.click("#applied-tracker-list button:has-text('Remove')")
        page.wait_for_timeout(200)
        assert page.inner_text("#metric-total").strip() == "3"
        assert page.inner_text("#metric-applied").strip() == "0"

        # Simulate stale cloud doc still listing naukri:200002 WITHOUT applied_at
        cloud_state["ids"] = ["naukri:200002"]
        cloud_state["omit_applied_at"] = True
        page.evaluate("() => pullCloudSync(true)")
        page.wait_for_timeout(250)

        assert page.inner_text("#metric-total").strip() == "3"
        assert page.inner_text("#metric-applied").strip() == "0"
        tombstones = page.evaluate("() => JSON.parse(localStorage.getItem('jobhunt_unmarked_jobs') || '{}')")
        assert "naukri:200002" in tombstones
        assert "naukri:200002" not in cloud_state["ids"]

        browser.close()


def test_import_applied_sync_code_clears_unmarked_tombstones(isolated_server):
    """importAppliedSyncCode() clears jobhunt_unmarked_jobs for imported IDs so pullCloudSync does not undo import."""
    base_url, _ = isolated_server

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        cloud_state = {
            "ids": ["naukri:200002"],
            "patch_count": 0,
            "applied_at": "2026-11-28T04:30:00.000Z",
        }

        def handle_firestore(route):
            req = route.request
            if req.method == "PATCH":
                cloud_state["patch_count"] += 1
                body = json.loads(req.post_data or "{}")
                vals = (
                    body.get("fields", {})
                    .get("applied_ids", {})
                    .get("arrayValue", {})
                    .get("values", [])
                )
                cloud_state["ids"] = [v["stringValue"] for v in vals if "stringValue" in v]
                route.fulfill(status=200, content_type="application/json", body=json.dumps({"fields": {}}))
            else:
                doc = {
                    "fields": {
                        "applied_ids": {
                            "arrayValue": {"values": [{"stringValue": jid} for jid in cloud_state["ids"]]}
                        },
                        "applied_jobs": {
                            "mapValue": {
                                "fields": (
                                    {
                                        "naukri:200002": {
                                            "mapValue": {
                                                "fields": {
                                                    "job_id": {"stringValue": "naukri:200002"},
                                                    "applied_at": {"stringValue": cloud_state["applied_at"]},
                                                    "title": {"stringValue": "Data Analyst"},
                                                }
                                            }
                                        }
                                    }
                                    if "naukri:200002" in cloud_state["ids"]
                                    else {}
                                )
                            }
                        },
                    }
                }
                route.fulfill(status=200, content_type="application/json", body=json.dumps(doc))

        page.route("https://firestore.googleapis.com/**", handle_firestore)
        page.goto(f"{base_url}/", wait_until="networkidle")
        page.wait_for_selector(".job-card", timeout=5000)

        # Unmark naukri:200002 -> creates jobhunt_unmarked_jobs['naukri:200002']
        page.click("button:has-text('Applied Hub')")
        page.wait_for_selector("#modal-applied-tracker.open", timeout=3000)
        page.click("#applied-tracker-list button:has-text('Remove')")
        page.wait_for_timeout(200)
        assert page.inner_text("#metric-applied").strip() == "0"

        sync_payload = {
            "applied_ids": ["naukri:200002"],
            "applied_jobs": {
                "naukri:200002": {
                    "job_id": "naukri:200002",
                    "applied_at": "2026-11-28T04:30:00.000Z",
                    "title": "Data Analyst",
                }
            },
        }
        sync_code = base64.b64encode(json.dumps(sync_payload).encode("utf-8")).decode("ascii")

        page.evaluate(
            """(code) => {
                window.prompt = () => code;
                importAppliedSyncCode();
            }""",
            sync_code,
        )
        page.wait_for_timeout(250)

        tombstones = page.evaluate("() => JSON.parse(localStorage.getItem('jobhunt_unmarked_jobs') || '{}')")
        assert "naukri:200002" not in tombstones
        assert page.inner_text("#metric-applied").strip() == "1"
        assert page.inner_text("#metric-total").strip() == "2"

        patches_before_pull = cloud_state["patch_count"]
        page.evaluate("() => pullCloudSync(true)")
        page.wait_for_timeout(250)

        assert cloud_state["patch_count"] == patches_before_pull
        assert page.inner_text("#metric-applied").strip() == "1"
        assert page.inner_text("#metric-total").strip() == "2"

        browser.close()
