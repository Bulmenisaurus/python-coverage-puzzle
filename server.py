#!/usr/bin/env python3
"""Local UI for trying Python snippets against listobject.c coverage."""

import json
import os
import signal
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
CPYTHON = Path(os.environ.get("CPYTHON", ROOT.parent / "cpython"))
SOURCE = CPYTHON / "Objects" / "listobject.c"
BASELINE = ROOT / "baseline_coverage.json"
HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8000"))
TIMEOUT = 60
MAX_CODE = 1_000_000

RUN_LOCK = threading.Lock()

STATIC = {
    "/": "index.html",
    "/index.html": "index.html",
    "/app.js": "app.js",
    "/style.css": "style.css",
}
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


def load_baseline():
    if not SOURCE.is_file():
        return None, f"listobject.c missing at {SOURCE}. Set CPYTHON to the coverage build."
    if not BASELINE.is_file():
        return None, "baseline_coverage.json missing. Run ./baselines.py."
    try:
        data = json.loads(BASELINE.read_text(encoding="utf-8"))
        source = SOURCE.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if "targets" not in data or "hit" not in data:
        return None, "baseline_coverage.json is missing targets or hit. Run ./baselines.py."
    return {"source": source, "targets": data["targets"], "hit": data["hit"]}, None


def interesting_split(targets, baseline_hit, run_hit):
    baseline = set(baseline_hit)
    hit = set(run_hit)
    covered = [n for n in targets if n not in baseline and n in hit]
    uncovered = [n for n in targets if n not in baseline and n not in hit]
    return covered, uncovered


def stats(covered, uncovered):
    total = len(covered) + len(uncovered)
    percent = 100.0 * len(covered) / total if total else 0.0
    return {
        "interesting": total,
        "covered": len(covered),
        "uncovered": len(uncovered),
        "coverage": round(percent, 1),
    }


def kill_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        return


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/puzzle":
            self.serve_puzzle()
            return
        name = STATIC.get(path)
        if name is None:
            self.send_error(404)
            return
        self.serve_static(name)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path != "/api/run":
            self.send_error(404)
            return
        self.serve_run()

    def serve_static(self, name):
        file = WEB / name
        if not file.is_file():
            self.send_error(404)
            return
        body = file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", TYPES.get(file.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_puzzle(self):
        data, error = load_baseline()
        if error:
            self.send_json(500, {"error": error})
            return
        covered, uncovered = interesting_split(data["targets"], data["hit"], ())
        self.send_json(200, {
            "source": data["source"],
            "targets": data["targets"],
            "baseline_hit": data["hit"],
            "covered": covered,
            "uncovered": uncovered,
            "stats": stats(covered, uncovered),
        })

    def serve_run(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "bad Content-Length"})
            return
        if length < 0 or length > MAX_CODE:
            self.send_json(413, {"error": "script is too large"})
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.send_json(400, {"error": "expected JSON"})
            return
        code = payload.get("code")
        if not isinstance(code, str):
            self.send_json(400, {"error": "code must be a string"})
            return

        if not RUN_LOCK.acquire(blocking=False):
            self.send_json(409, {"error": "a run is already in progress"})
            return
        try:
            self.run_code(code)
        finally:
            RUN_LOCK.release()

    def run_code(self, code):
        baseline, error = load_baseline()
        if error:
            self.send_json(500, {"error": error})
            return

        script = tempfile.NamedTemporaryFile(
            prefix="puzzle-", suffix=".py", delete=False, mode="w", encoding="utf-8"
        )
        report = tempfile.NamedTemporaryFile(prefix="puzzle-", suffix=".json", delete=False)
        script_path = script.name
        report_path = report.name
        script.write(code)
        script.close()
        report.close()

        proc = subprocess.Popen(
            [str(ROOT / "coverage.sh"), script_path, report_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=ROOT,
            start_new_session=True,
        )
        timed_out = False
        try:
            stdout, stderr = proc.communicate(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_group(proc)
            stdout, stderr = proc.communicate()

        try:
            if timed_out:
                self.send_json(408, {
                    "error": f"timed out after {TIMEOUT}s",
                    "stdout": stdout.decode("utf-8", "replace"),
                    "stderr": stderr.decode("utf-8", "replace"),
                })
                return

            if proc.returncode != 0 or not Path(report_path).is_file() or Path(report_path).stat().st_size == 0:
                self.send_json(500, {
                    "error": "coverage run failed",
                    "stdout": stdout.decode("utf-8", "replace"),
                    "stderr": stderr.decode("utf-8", "replace"),
                })
                return

            try:
                data = json.loads(Path(report_path).read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.send_json(500, {
                    "error": "coverage report was not valid JSON",
                    "stdout": stdout.decode("utf-8", "replace"),
                    "stderr": stderr.decode("utf-8", "replace"),
                })
                return

            if data.get("targets") != baseline["targets"]:
                self.send_json(409, {
                    "error": "this run's targets differ from baseline_coverage.json. Run ./baselines.py.",
                    "stdout": stdout.decode("utf-8", "replace"),
                    "stderr": stderr.decode("utf-8", "replace"),
                })
                return

            covered, uncovered = interesting_split(
                baseline["targets"], baseline["hit"], data.get("hit", [])
            )
            self.send_json(200, {
                "stdout": stdout.decode("utf-8", "replace"),
                "stderr": stderr.decode("utf-8", "replace"),
                "hit": data.get("hit", []),
                "covered": covered,
                "uncovered": uncovered,
                "stats": stats(covered, uncovered),
            })
        finally:
            Path(script_path).unlink(missing_ok=True)
            Path(report_path).unlink(missing_ok=True)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
