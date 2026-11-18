"""Lightweight, zero-dependency local web server for Shubham's JobHunt GUI.
Serves modern responsive dashboard and provides REST APIs for live tracking and actions.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser

ROOT = Path(__file__).resolve().parent.parent
GUI_DIR = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8080


def load_json_safe(path: Path) -> dict | list:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        try:
            return json.loads(path.read_text(encoding="cp1252", errors="replace"))
        except Exception:
            return {}


def _launch_external_browser(url: str, browser: str = "edge") -> bool:
    """Launch a URL in a separate browser software (Edge, Brave, Chrome)."""
    browser = (browser or "edge").lower()
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    brave_paths = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expanduser("~") + r"\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe",
    ]
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]

    target_exe = None
    if browser in ("edge", "msedge"):
        for p in edge_paths:
            if os.path.exists(p):
                target_exe = p
                break
    elif browser == "brave":
        for p in brave_paths:
            if os.path.exists(p):
                target_exe = p
                break
    elif browser == "chrome":
        for p in chrome_paths:
            if os.path.exists(p):
                target_exe = p
                break

    if target_exe:
        try:
            # Auto-Tile Window Splitter: Snap to the right half of the screen
            cmd = [target_exe, "--new-window"]
            try:
                import ctypes
                user32 = ctypes.windll.user32
                sw = user32.GetSystemMetrics(0)
                sh = user32.GetSystemMetrics(1)
                half_w = sw // 2
                cmd.extend([f"--window-position={half_w},0", f"--window-size={half_w},{sh}"])
            except Exception:
                pass
            cmd.append(url)
            subprocess.Popen(cmd)
            return True
        except Exception as e:
            print("Browser launch error:", e)

    # Windows native protocol fallback for Edge
    if browser in ("edge", "msedge"):
        try:
            webbrowser.open(f"microsoft-edge:{url}")
            return True
        except Exception:
            pass

    webbrowser.open(url)
    return True


class JobHuntHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(GUI_DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("", "/"):
            self.path = "/index.html"
            return super().do_GET()

        if path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()

            seen_data = load_json_safe(ROOT / "seen.json")
            if not isinstance(seen_data, dict):
                seen_data = {}

            profile_data = load_json_safe(ROOT / "profile.json")
            health_data = load_json_safe(ROOT / "out" / "source_health.json")
            if not isinstance(health_data, list):
                health_data = []

            # Format jobs list
            jobs_list = []
            for jid, row in seen_data.items():
                if isinstance(row, dict):
                    jobs_list.append({"job_id": jid, **row})

            # Sort descending by score then date
            jobs_list.sort(key=lambda j: (j.get("score") or 0.0, j.get("first_seen") or ""), reverse=True)

            applied_count = sum(1 for j in jobs_list if j.get("applied"))
            payload = {
                "jobs": jobs_list,
                "stats": {
                    "total": len(jobs_list),
                    "applied": applied_count,
                    "emailed": sum(1 for j in jobs_list if j.get("emailed")),
                    "recommended": sum(1 for j in jobs_list if (j.get("score") or 0.0) >= 6.0),
                    "sources_count": len(health_data),
                },
                "profile": profile_data,
                "source_health": health_data,
            }
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/digest":
            digest_file = ROOT / "out" / "digest.html"
            content = digest_file.read_text(encoding="utf-8") if digest_file.exists() else "<h3>No digest generated yet today.</h3>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8", errors="replace")
        try:
            req_data = json.loads(body) if body else {}
        except Exception:
            req_data = {}

        if path == "/api/toggle-applied":
            job_id = req_data.get("job_id")
            seen_file = ROOT / "seen.json"
            seen_data = load_json_safe(seen_file)
            if isinstance(seen_data, dict) and job_id in seen_data:
                curr = seen_data[job_id].get("applied", False)
                seen_data[job_id]["applied"] = not curr
                seen_file.write_text(json.dumps(seen_data, indent=2, ensure_ascii=False), encoding="utf-8")

                # Also update tracker.csv
                try:
                    from jobhunt.store import Store
                    Store(seen_file).export_csv(ROOT / "out" / "tracker.csv")
                except Exception:
                    pass

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "applied": not curr}).encode("utf-8"))
                return

            self.send_response(404)
            self.end_headers()
            return

        if path == "/api/run-local":
            action = req_data.get("action", "test")
            cmd = []
            py_exe = sys.executable
            if action == "test":
                cmd = [py_exe, "-m", "jobhunt", "run", "--limit", "10"]
            elif action == "full":
                cmd = [py_exe, "-m", "jobhunt", "run", "--send"]
            elif action == "inbox":
                cmd = [py_exe, "mail_summarizer.py", "--force"]

            def _bg_run():
                try:
                    subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
                except Exception as e:
                    print("Background action error:", e)

            if cmd:
                threading.Thread(target=_bg_run, daemon=True).start()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "started": action}).encode("utf-8"))
                return

        if path == "/api/launch-browser":
            target_url = req_data.get("url")
            target_browser = req_data.get("browser", "edge")
            if target_url:
                _launch_external_browser(target_url, target_browser)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "browser": target_browser}).encode("utf-8"))
                return

        self.send_response(400)
        self.end_headers()


def start_server(port: int = PORT, open_browser: bool = True):
    server = HTTPServer((HOST, port), JobHuntHandler)
    url = f"http://{HOST}:{port}"
    print(f"\n==================================================")
    print(f"  Shubham's JobHunt GUI Dashboard")
    print(f"  Running at: {url}")
    print(f"  Press Ctrl+C to stop.")
    print(f"==================================================\n")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server...")
        server.server_close()


if __name__ == "__main__":
    p = PORT
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        p = int(sys.argv[1])
    start_server(port=p, open_browser=True)
