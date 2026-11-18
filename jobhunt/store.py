"""seen.json doubles as the dedupe index AND the application tracker."""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .fetch import Job


class Store:
    def __init__(self, path: str | Path = "seen.json"):
        self.path = Path(path)
        self.data: dict[str, dict] = {}
        if self.path.exists():
            try:
                try:
                    content = self.path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = self.path.read_text(encoding="cp1252", errors="replace")
                self.data = json.loads(content)
            except json.JSONDecodeError:
                print(f"  ! {self.path} corrupt, starting fresh")
                self.data = {}

    def unseen(self, jobs: list[Job]) -> list[Job]:
        return [j for j in jobs if j.job_id not in self.data]

    def record(self, jobs: list[Job], emailed: bool) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for j in jobs:
            self.data.setdefault(j.job_id, {
                "first_seen": now,
                "company": j.company,
                "title": j.title,
                "location": j.location,
                "url": j.url,
                "score": j.score,
                "reason": j.reason,
                "canonical_source": j.canonical_source or j.source or j.ats,
                "sources": j.sources or [j.source or j.ats],
                "role_families": j.role_families,
                "matched_roles": j.matched_roles,
                "fit_score": j.fit_score or j.score,
                "emailed": emailed,
                "applied": False,
                "applied_on": None,
            })
        self.save()

    def mark_applied(self, job_id: str) -> bool:
        # Support full job_id or prefix (since Telegram callbacks are capped at 64 chars)
        target_id = job_id
        if target_id not in self.data:
            matches = [k for k in self.data if k.startswith(job_id) or job_id in k]
            if matches:
                target_id = matches[0]
            else:
                return False

        self.data[target_id]["applied"] = True
        self.data[target_id]["applied_on"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.save()
        return True

    def find_job(self, query: str) -> tuple[str, dict] | None:
        """Find a job by ID, prefix, company name, or title substring."""
        q = (query or "").strip().lower()
        if not q:
            return None

        # 1. Exact job_id match
        if query in self.data:
            return query, self.data[query]

        # 2. Prefix job_id match
        for jid, d in self.data.items():
            if jid.lower().startswith(q):
                return jid, d

        # 3. Exact company match
        for jid, d in self.data.items():
            if d.get("company", "").strip().lower() == q:
                return jid, d

        # 4. Substring company match
        for jid, d in self.data.items():
            if q in d.get("company", "").strip().lower():
                return jid, d

        # 5. Substring title match
        for jid, d in self.data.items():
            if q in d.get("title", "").strip().lower():
                return jid, d

        return None

    def list_jobs(
        self,
        applied: bool | None = None,
        min_score: float = 0.0,
        limit: int = 10,
        remote_only: bool = False,
    ) -> list[tuple[str, dict]]:
        """List jobs filtered and sorted by score descending."""
        candidates = []
        for jid, d in self.data.items():
            if applied is not None and bool(d.get("applied")) != applied:
                continue
            score = float(d.get("score") or d.get("fit_score") or 0.0)
            if score < min_score:
                continue
            if remote_only:
                loc = (d.get("location") or "").lower()
                is_rem = d.get("remote") or "remote" in loc or "anywhere" in loc
                if not is_rem:
                    continue
            candidates.append((jid, d))

        candidates.sort(
            key=lambda item: (
                float(item[1].get("score") or item[1].get("fit_score") or 0.0),
                item[1].get("first_seen") or "",
            ),
            reverse=True,
        )
        return candidates[:limit]

    def pending_reminders(self, min_days: int = 5) -> list[tuple[str, dict]]:
        """Return applied jobs ready for a follow-up outreach."""
        now = datetime.now(timezone.utc)
        results = []
        for jid, d in self.data.items():
            if not d.get("applied"):
                continue
            app_on = d.get("applied_on")
            if not app_on:
                # If marked applied without date, consider eligible
                results.append((jid, d))
                continue
            try:
                dt = datetime.fromisoformat(app_on)
                if (now - dt).total_seconds() >= min_days * 86400:
                    results.append((jid, d))
            except (ValueError, TypeError):
                results.append((jid, d))
        return results

    def stats(self) -> dict:
        return {
            "tracked": len(self.data),
            "emailed": sum(1 for v in self.data.values() if v.get("emailed")),
            "applied": sum(1 for v in self.data.values() if v.get("applied")),
        }

    def export_csv(self, path: str | Path = "out/tracker.csv") -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        cols = ["first_seen", "company", "title", "location", "canonical_source",
                "sources", "role_families", "score", "reason", "applied", "applied_on", "url"]
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["job_id"] + cols, extrasaction="ignore")
            w.writeheader()
            for jid, row in sorted(self.data.items(),
                                   key=lambda kv: kv[1].get("first_seen", ""), reverse=True):
                w.writerow({"job_id": jid, **row})
        return path

    def save(self) -> None:
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp.{os.getpid()}")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, self.path)
