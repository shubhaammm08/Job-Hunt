"""jobhunt CLI: profile -> fetch -> prefilter -> screen -> draft -> digest -> mail.

The agent never submits an application. It finds, filters, ranks and drafts.
A human reads the digest, edits the note, and presses submit.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

from typing import Any

import yaml

from . import digest as digest_mod
from . import llm, mailer
from .fetch import fetch_all
from .mock import fetch_all_mock
from .prefilter import prefilter
from .providers import LLMError, resolve
from .store import Store

ROOT = Path(__file__).resolve().parent.parent


def _load_env(path: str = ".env") -> None:
    """Minimal .env reader so there is no python-dotenv dependency."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _cfg(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"config not found: {p}  (run from the project root)")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _load_profile(cfg: dict, allow_sample: bool) -> dict | None:
    path = Path(cfg.get("profile_file", "profile.json"))
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    sample = ROOT / "profile.example.json"
    if allow_sample and sample.exists():
        print(f"  ! {path} missing — using {sample.name} for this dry run.")
        print("    Build the real one: python -m jobhunt profile --resume resume.pdf")
        return json.loads(sample.read_text(encoding="utf-8"))

    print(f"missing {path} — run `python -m jobhunt profile --resume <file>` first")
    return None


# ------------------------------------------------------------------ profile --
def cmd_profile(args) -> int:
    src = Path(args.resume)
    if not src.exists():
        print(f"resume not found: {src}")
        return 1
    is_pdf = src.suffix.lower() == ".pdf"

    try:
        provider, model = resolve("draft")
        print(f"reading {src.name} via {provider.name}/{model} ...")
        profile = llm.build_profile(
            resume_bytes=src.read_bytes() if is_pdf else None,
            resume_text=None if is_pdf else src.read_text(encoding="utf-8", errors="replace"),
            is_pdf=is_pdf, provider=provider, model=model,
        )
    except (LLMError, ValueError) as e:
        print(f"profile extraction failed: {e}")
        return 1

    Path(args.out).write_text(json.dumps(profile, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    print(f"wrote {args.out}\n")
    print(json.dumps(profile, indent=2, ensure_ascii=False)[:900])
    return 0


def _clean_score(val: Any) -> float | None:
    if val is None or isinstance(val, bool):
        return None
    try:
        s = float(val)
        if math.isnan(s) or math.isinf(s):
            return None
        return s
    except (ValueError, TypeError, OverflowError):
        return None


def _get_job_score(j: Any) -> float | None:
    try:
        if isinstance(j, dict):
            return _clean_score(j.get("score"))
        return _clean_score(getattr(j, "score", None))
    except Exception:
        return None


def _parse_threshold(cfg: dict | None) -> float:
    if not isinstance(cfg, dict):
        return 6.0
    raw = cfg.get("score_threshold")
    if raw is None or isinstance(raw, bool):
        return 6.0
    try:
        val = float(raw)
        if math.isnan(val) or math.isinf(val):
            return 6.0
        return val
    except (ValueError, TypeError, OverflowError):
        return 6.0


def select_shortlist(jobs: Any, cfg: dict | None) -> list:
    """Select qualifying opportunities for the digest according to score and max_per_digest config.
    Delivers all fresh opportunities meeting criteria (min 10 when available) without artificial truncation.
    """
    if not jobs or isinstance(jobs, (str, bytes)):
        return []
    try:
        job_iter = iter(jobs)
    except TypeError:
        return []

    if not isinstance(cfg, dict):
        cfg = {}

    threshold = _parse_threshold(cfg)
    qualifying = []
    for j in job_iter:
        score = _get_job_score(j)
        if score is not None and score >= threshold:
            qualifying.append(j)

    qualifying.sort(key=lambda j: _get_job_score(j) or 0.0, reverse=True)

    raw_max = cfg.get("max_per_digest")
    if raw_max is None or isinstance(raw_max, bool):
        return qualifying
    try:
        val = float(str(raw_max).strip())
        if math.isnan(val) or math.isinf(val):
            top_n = 0
        else:
            top_n = int(val)
    except (ValueError, TypeError, OverflowError):
        top_n = 0
    if top_n <= 0:
        return qualifying
    top_n = max(top_n, 10)
    return qualifying[:top_n]


# ---------------------------------------------------------------------- run --
def cmd_run(args) -> int:
    cfg = _cfg(args.config)
    profile = _load_profile(cfg, allow_sample=args.mock)
    if profile is None:
        return 1
    store = Store(cfg.get("seen_file", "seen.json"))
    candidate_name = (profile or {}).get("name", "Shubham")
    filters = cfg.get("filters", {}) or {}

    # ---- 1. fetch
    print("\n[1/5] fetching boards & registered sources")
    if args.mock:
        jobs = fetch_all_mock()
    else:
        companies = _cfg(cfg.get("companies_file", "companies.yaml")).get("companies") or []
        jobs = fetch_all(companies) if companies else []
        from .sources import REGISTRY
        source_jobs = REGISTRY.fetch_all_sources(cfg)
        jobs.extend(source_jobs)
    scanned = len(jobs)
    if not scanned:
        print("no postings fetched — check the slugs in companies.yaml or network connectivity")
        return 1

    # ---- 2. prefilter + dedupe (deterministic, free, no LLM)
    print("\n[2/5] deduplicating & filtering")
    from .dedupe import deduplicate_jobs
    jobs, dupe_count = deduplicate_jobs(jobs)
    if dupe_count > 0:
        print(f"  canonical deduplication: consolidated {dupe_count} duplicate listings across sources")
    jobs = prefilter(jobs, filters)
    passed_filters = len(jobs)
    jobs = store.unseen(jobs)
    print(f"  new since last run: {len(jobs)}")
    candidates = len(jobs)
    if args.limit and args.limit > 0:
        jobs = jobs[:args.limit]
        print(f"  --limit {args.limit} applied")

    if not jobs:
        subject, doc = digest_mod.build([], scanned, 0, store.stats(), name=candidate_name)
        path = digest_mod.write(doc, cfg.get("digest_file", "out/digest.html"))
        print(f"\nnothing new today. preview: {path}")
        return 0

    # ---- 3. screen
    scorer = "keyword" if args.scorer == "keyword" else "llm"
    if scorer == "keyword":
        print(f"\n[3/5] screening {len(jobs)} jobs (keyword stub — DEV ONLY)")
        llm.keyword_screen(jobs, profile)
    else:
        try:
            provider, model = resolve("screen")
        except LLMError as e:
            print(f"\n{e}\nNo key? Run with --scorer keyword for an offline dry run.")
            return 1
        print(f"\n[3/5] screening {len(jobs)} jobs via {provider.name}/{model}")
        llm.screen(jobs, profile,
                   batch_size=int(cfg.get("screen_batch_size", 8)),
                   jd_chars=int(cfg.get("screen_jd_chars", 1400)),
                   provider=provider, model=model)

    # If every batch failed, the digest would be empty and — worse — we would
    # record these jobs as seen and never show them again. Bail instead.
    if scorer == "llm" and not any(j.score is not None for j in jobs):
        print("\n! screening scored nothing: every batch failed.\n"
              "  Not recording these jobs, so the next run retries them.\n"
              "  Check the warnings above (bad key, rate limit, wrong model id).")
        return 1

    threshold = _parse_threshold(cfg)
    shortlist = select_shortlist(jobs, cfg)
    print(f"  {len(shortlist)} scored >= {threshold}")

    # ---- 4. draft
    print(f"\n[4/5] drafting kits for {len(shortlist)}")
    if not shortlist:
        print("  nothing cleared the threshold")
    elif scorer == "keyword" or args.no_draft:
        print("  skipped (keyword scorer / --no-draft)")
    else:
        try:
            provider, model = resolve("draft")
            print(f"  via {provider.name}/{model}")
            llm.draft(shortlist, profile,
                      jd_chars=int(cfg.get("draft_jd_chars", 6000)),
                      provider=provider, model=model)
        except LLMError as e:
            print(f"  ! drafting unavailable: {e}")

    # ---- 5. digest
    print("\n[5/5] digest")
    subject, doc = digest_mod.build(shortlist, scanned, candidates, store.stats(), name=candidate_name)
    path = digest_mod.write(doc, cfg.get("digest_file", "out/digest.html"))
    print(f"  wrote {path}")

    sent = False
    if args.send:
        try:
            mailer.send(subject, doc)
            sent = True
        except Exception as e:  # bad app password, blocked port, offline
            print(f"  ! email failed ({type(e).__name__}: {e}) — digest still on disk")
    else:
        print("  --send not passed, email skipped")

    # WhatsApp digest / high-match dispatch
    wa_sent = False
    send_wa = getattr(args, "whatsapp", False) or (args.send and bool(os.getenv("WHATSAPP_APIKEY")))
    if send_wa:
        try:
            from .whatsapp import send_whatsapp_digest
            wa_sent = send_whatsapp_digest(
                jobs=jobs,
                scanned=scanned,
                candidates=candidates,
                stats=store.stats(),
                cfg=cfg,
                profile=profile,
            )
        except Exception as e:
            print(f"  ! whatsapp delivery error ({type(e).__name__}: {e})")
    elif getattr(args, "whatsapp", False):
        print("  --whatsapp passed but credentials missing in environment")

    # Telegram digest / high-match dispatch
    send_tg = getattr(args, "telegram", False) or (args.send and bool(os.getenv("TELEGRAM_BOT_TOKEN")))
    if send_tg:
        try:
            from .telegram import send_telegram_digest
            send_telegram_digest(
                jobs=jobs,
                scanned=scanned,
                candidates=candidates,
                stats=store.stats(),
                cfg=cfg,
                profile=profile,
            )
        except Exception as e:
            print(f"  ! telegram delivery error ({type(e).__name__}: {e})")

    store.record(jobs, emailed=sent)
    csv_path = store.export_csv(cfg.get("tracker_csv", "out/tracker.csv"))

    # Export source health report
    from .sources import REGISTRY
    health_file = cfg.get("source_health_file", "out/source_health.json")
    health_path = REGISTRY.export_health(health_file)

    print(f"\nfunnel: {scanned} scanned -> {passed_filters} passed filters "
          f"-> {candidates} new -> {len(shortlist)} in digest")
    print(f"subject: {subject}")
    print(f"tracker: {store.stats()}  ({csv_path})")
    print(f"source health: {health_path}")

    # Auto-rebuild dashboard index.html so UI is immediately refreshed
    try:
        build_script = ROOT / "build_mobile_gui.py"
        if build_script.exists():
            import subprocess
            subprocess.run([sys.executable, str(build_script)], cwd=str(ROOT), capture_output=True, text=True, timeout=20)
    except Exception:
        pass

    return 0


# ------------------------------------------------------------------- misc --
def cmd_applied(args) -> int:
    store = Store(_cfg(args.config).get("seen_file", "seen.json"))
    ok = store.mark_applied(args.job_id)
    print("marked applied" if ok else f"unknown job_id: {args.job_id}")
    return 0 if ok else 1


def cmd_stats(args) -> int:
    cfg = _cfg(args.config)
    store = Store(cfg.get("seen_file", "seen.json"))
    print(json.dumps(store.stats(), indent=2))
    print(f"csv: {store.export_csv(cfg.get('tracker_csv', 'out/tracker.csv'))}")
    return 0


def cmd_sources(args) -> int:
    cfg = _cfg(args.config)
    from .sources import REGISTRY
    out_file = getattr(args, "out", None) or cfg.get("source_health_file", "out/source_health.json")
    path = REGISTRY.export_health(out_file)
    print(f"Exported source health report to {path}")
    for name, adapter in REGISTRY.adapters.items():
        print(f"  {name:<32} {adapter.category:<18} Tier {adapter.tier} -> {adapter.health.status}")
    return 0


def cmd_whatsapp(args) -> int:
    cfg = _cfg(args.config)
    profile = _load_profile(cfg, allow_sample=True) or {}
    from .whatsapp import send_whatsapp, clean_phone_number

    phone = os.environ.get("WHATSAPP_PHONE") or os.environ.get("CALLMEBOT_PHONE")
    apikey = os.environ.get("WHATSAPP_APIKEY") or os.environ.get("CALLMEBOT_APIKEY")

    if not phone or not apikey:
        print("\n[WhatsApp Alert Setup - 60 Second Setup (100% Free)]")
        print("1. Open WhatsApp on your phone.")
        print("2. Send this exact message:")
        print("   'I allow callmebot to send me messages'")
        print("   to phone number: +34 623 78 64 49 (CallMeBot active gateway)")
        print("3. CallMeBot will reply in ~5 seconds with your API key:")
        print("   e.g. 'API Activated. Your API Key is: 123456'")
        print("4. Add to your .env file or GitHub Secrets:")
        print("   WHATSAPP_PHONE=+91XXXXXXXXXX")
        print("   WHATSAPP_APIKEY=123456")
        print("\nThen run 'python -m jobhunt whatsapp --test' to verify!")
        return 1

    msg = getattr(args, "message", None)
    if not msg or getattr(args, "test", False):
        name = profile.get("name", "Shubham")
        msg = (
            f"✅ *JobHunt WhatsApp Connected!*\n\n"
            f"Hello {name}, your automated job pipeline is connected to WhatsApp.\n"
            f"You will receive daily curated digests and instant alerts for high-fit roles.\n\n"
            f"🌐 Executive Dashboard:\nhttps://shubhaammm08.github.io/Job-Hunt/"
        )

    try:
        send_whatsapp(msg)
        print("WhatsApp alert successfully sent!")
        return 0
    except Exception as e:
        print(f"Failed to send WhatsApp message: {e}")
        return 1


def cmd_telegram(args) -> int:
    cfg = _cfg(args.config)
    profile = _load_profile(cfg, allow_sample=True) or {}
    from .telegram import send_telegram

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("\n[Telegram Phone Alert Setup - 30 Second Instant Setup (100% Free)]")
        print("1. Open Telegram on your phone or PC.")
        print("2. Search for '@BotFather' and click Start.")
        print("3. Send '/newbot', give your bot a name (e.g. 'ShubhamJobHuntBot').")
        print("4. Copy the HTTP API token provided by BotFather.")
        print("5. Search for your new bot in Telegram, click Start.")
        print("6. To get your chat_id, visit: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates")
        print("   (Look for 'id': 123456789 under 'chat')")
        print("7. Add to your .env or GitHub Secrets:")
        print("   TELEGRAM_BOT_TOKEN=your-bot-token")
        print("   TELEGRAM_CHAT_ID=your-chat-id")
        print("\nThen run 'python -m jobhunt telegram --test' to verify!")
        return 1

    msg = getattr(args, "message", None)
    if not msg or getattr(args, "test", False):
        name = profile.get("name", "Shubham")
        msg = (
            f"✅ *JobHunt Telegram Connected!*\n\n"
            f"Hello {name}, your automated pipeline is connected to Telegram.\n"
            f"Instant alerts and daily morning digests will arrive here.\n\n"
            f"🌐 [Executive Dashboard](https://shubhaammm08.github.io/Job-Hunt/)"
        )

    try:
        send_telegram(msg)
        print("Telegram alert successfully sent!")
        return 0
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
        return 1


def cmd_bot(args) -> int:
    cfg = _cfg(args.config)
    profile = _load_profile(cfg, allow_sample=True) or {}
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Missing TELEGRAM_BOT_TOKEN in environment or .env")
        return 1

    store = Store(cfg.get("seen_file", "seen.json"))
    from .telegram_bot import poll_updates

    poll_updates(token=token, store=store, profile=profile, once=args.once)
    return 0


def cmd_linkedin_auth(args) -> int:
    """Run interactive headful LinkedIn login to save browser session."""
    from .linkedin import run_linkedin_auth
    session_path = getattr(args, "session", "session.json")
    timeout = getattr(args, "timeout", 600)
    email = getattr(args, "email", None)
    password = getattr(args, "password", None)
    cookie = getattr(args, "cookie", None)
    success = run_linkedin_auth(
        session_path=session_path,
        timeout=timeout,
        email=email,
        password=password,
        cookie=cookie,
    )
    return 0 if success else 1


def cmd_naukri_auth(args) -> int:
    """Run interactive or cookie-based Naukri session save."""
    from .naukri import run_naukri_auth
    session_path = getattr(args, "session", "session_naukri.json")
    timeout = getattr(args, "timeout", 300)
    cookie = getattr(args, "cookie", None)
    success = run_naukri_auth(
        session_path=session_path,
        timeout=timeout,
        cookie=cookie,
    )
    return 0 if success else 1


def cmd_naukri_import(args) -> int:
    """Import Naukri jobs from the Rockposedon dataset or a focused live scan."""
    from .dedupe import deduplicate_jobs
    from .llm import keyword_screen
    from .naukri import (
        fetch_naukri_dataset,
        fetch_naukri_jobs,
        infer_naukri_posted_date,
        naukri_dataset_jobs,
    )

    cfg = _cfg(args.config)
    if args.live:
        jobs = fetch_naukri_jobs(cfg)
        historical = False
        label = "live Naukri scan"
    else:
        if args.file:
            text = Path(args.file).read_text(encoding="utf-8", errors="replace")
        else:
            text = fetch_naukri_dataset(args.url)
        jobs = naukri_dataset_jobs(text, limit=args.limit)
        historical = True
        label = "Rockposedon Naukri dataset"

    jobs, dupes = deduplicate_jobs(jobs)
    store = Store(args.seen or cfg.get("seen_file", "seen.json"))
    new_jobs = store.unseen(jobs)
    print(f"\n{label}: {len(jobs)} jobs ({dupes} duplicates merged)")
    print(f"  new since last run: {len(new_jobs)}")
    if args.dry_run:
        print("  dry run - nothing recorded")
        return 0
    if not new_jobs:
        return 0

    if not args.no_score:
        profile = _load_profile(cfg, allow_sample=True) or {}
        keyword_screen(new_jobs, profile)
        for job in new_jobs:
            if job.reason and job.reason.startswith("[keyword stub]"):
                job.reason = job.reason.replace("[keyword stub]", "[Naukri import]", 1)

    store.record(new_jobs, emailed=False)
    if historical:
        # The upstream export is from 2023. Preserve the listing age so these
        # jobs do not masquerade as a fresh scan in the dashboard.
        for job in new_jobs:
            posted = infer_naukri_posted_date(job.job_id)
            if posted:
                store.data[job.job_id]["first_seen"] = f"{posted}T00:00:00+00:00"
        store.save()
    print(f"  recorded {len(new_jobs)} Naukri jobs in {store.path}")
    return 0


def main(argv=None) -> int:
    from .naukri import NAUKRI_DATASET_URL

    _load_env()
    p = argparse.ArgumentParser(
        prog="jobhunt",
        description="Personal job-search agent. Finds and drafts; never submits.")
    p.add_argument("--config", default="config.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("profile", help="turn a resume into profile.json")
    sp.add_argument("--resume", required=True, help="path to a .pdf, .txt or .md resume")
    sp.add_argument("--out", default="profile.json")
    sp.set_defaults(func=cmd_profile)

    sr = sub.add_parser("run", help="run the daily pipeline")
    sr.add_argument("--mock", action="store_true", help="bundled fixtures, no network")
    sr.add_argument("--scorer", choices=["llm", "keyword", "claude"], default="llm",
                    help="keyword = offline stub, needs no API key ('claude' is an "
                         "alias for 'llm', kept for older docs)")
    sr.add_argument("--no-draft", action="store_true", help="skip the expensive stage")
    sr.add_argument("--send", action="store_true", help="actually email the digest")
    sr.add_argument("--whatsapp", action="store_true", help="send digest/high-match alerts to WhatsApp")
    sr.add_argument("--telegram", action="store_true", help="send digest/high-match alerts to Telegram")
    sr.add_argument("--limit", type=int, help="cap jobs sent to the LLM (cost guard)")
    sr.set_defaults(func=cmd_run)

    sa = sub.add_parser("applied", help="mark a job_id as applied")
    sa.add_argument("job_id")
    sa.set_defaults(func=cmd_applied)

    ss = sub.add_parser("stats", help="tracker summary + CSV export")
    ss.set_defaults(func=cmd_stats)

    ssrc = sub.add_parser("sources", help="inspect source registry and health report")
    ssrc.add_argument("--out", default="out/source_health.json")
    ssrc.set_defaults(func=cmd_sources)

    swa = sub.add_parser("whatsapp", help="test or send WhatsApp alert")
    swa.add_argument("--test", action="store_true", help="send a test WhatsApp alert")
    swa.add_argument("--message", help="custom message text to send")
    swa.set_defaults(func=cmd_whatsapp)

    stg = sub.add_parser("telegram", help="test or send Telegram alert")
    stg.add_argument("--test", action="store_true", help="send a test Telegram alert")
    stg.add_argument("--message", help="custom message text to send")
    stg.set_defaults(func=cmd_telegram)

    sbot = sub.add_parser("bot", help="run interactive Telegram Bot listener")
    sbot.add_argument("--once", action="store_true", help="process pending messages once and exit")
    sbot.add_argument("--poll", action="store_true", help="continuous long-polling daemon (default)")
    sbot.set_defaults(func=cmd_bot)

    sauth = sub.add_parser("linkedin-auth", help="interactive LinkedIn login to save browser session")
    sauth.add_argument("--session", default="session.json", help="path to session file (default: session.json)")
    sauth.add_argument("--timeout", type=int, default=600, help="login timeout in seconds (default: 600)")
    sauth.add_argument("--email", "--username", dest="email", help="LinkedIn login email / username")
    sauth.add_argument("--password", help="LinkedIn login password")
    sauth.add_argument("--cookie", "--li-at", dest="cookie", help="direct li_at cookie value (bypasses Cloudflare)")
    sauth.set_defaults(func=cmd_linkedin_auth)

    snaukri = sub.add_parser("naukri-auth", help="interactive Naukri login or cookie save to session file")
    snaukri.add_argument("--session", default="session_naukri.json", help="path to session file (default: session_naukri.json)")
    snaukri.add_argument("--timeout", type=int, default=300, help="login timeout in seconds (default: 300)")
    snaukri.add_argument("--cookie", help="direct Naukri cookie header string")
    snaukri.set_defaults(func=cmd_naukri_auth)

    simp = sub.add_parser(
        "naukri-import",
        help="import Naukri jobs from the Rockposedon dataset or a live scan",
    )
    simp.add_argument("--file", help="local Rockposedon dataset .txt (default: download)")
    simp.add_argument("--url", default=NAUKRI_DATASET_URL, help="dataset URL")
    simp.add_argument("--live", action="store_true", help="run a focused live guest-browser scan instead")
    simp.add_argument("--limit", type=int, help="cap imported jobs for a quick trial")
    simp.add_argument("--seen", help="override seen.json path")
    simp.add_argument("--dry-run", action="store_true", help="preview without writing")
    simp.add_argument("--no-score", action="store_true", help="skip offline keyword scoring")
    simp.set_defaults(func=cmd_naukri_import)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
