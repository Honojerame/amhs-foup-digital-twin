from __future__ import annotations

import argparse
import json
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .simulation import FabSimulation, demo_fab

WEB_ROOT = Path(__file__).with_name("web")
MIME_TYPES = {".html": "text/html", ".css": "text/css", ".js": "text/javascript"}


class LiveFab:
    """Thread-safe adapter between deterministic plant time and wall-clock time."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.sim: FabSimulation = demo_fab()
        self.paused = False
        self.speed = 1.0
        self.running = True

    def loop(self) -> None:
        while self.running:
            started = time.monotonic()
            with self.lock:
                if not self.paused:
                    steps = max(1, round(self.speed))
                    for _ in range(steps):
                        self.sim.step()
            elapsed = time.monotonic() - started
            time.sleep(max(0.0, self.sim.dt_s - elapsed))

    def snapshot(self) -> dict[str, object]:
        with self.lock:
            state = self.sim.snapshot()
            state.update({"paused": self.paused, "speed": self.speed})
            return state

    def control(self, action: str, vehicle_id: str = "", speed: float | None = None) -> None:
        with self.lock:
            if action == "pause":
                self.paused = True
            elif action == "resume":
                self.paused = False
            elif action == "reset":
                self.sim = demo_fab()
                self.paused = False
            elif action == "speed" and speed in (1.0, 2.0, 4.0):
                self.speed = speed
            elif action in ("fault", "clear_fault"):
                vehicle = next((v for v in self.sim.vehicles if v.vehicle_id == vehicle_id), None)
                if vehicle is None:
                    raise ValueError("Unknown vehicle")
                if action == "fault":
                    vehicle.emergency_stop("Obstacle photoeye interlock")
                else:
                    vehicle.reset_fault()
            else:
                raise ValueError("Unknown control action")


class DashboardHandler(BaseHTTPRequestHandler):
    live_fab: LiveFab

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/state":
            self._json(self.live_fab.snapshot())
            return
        relative = "index.html" if path == "/" else path.lstrip("/")
        file_path = (WEB_ROOT / relative).resolve()
        if WEB_ROOT.resolve() not in file_path.parents or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", MIME_TYPES.get(file_path.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/control":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            self.live_fab.control(payload.get("action", ""), payload.get("vehicle_id", ""), payload.get("speed"))
            self._json({"ok": True})
        except (ValueError, json.JSONDecodeError) as exc:
            self._json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AMHS real-time digital twin dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    live_fab = LiveFab()
    DashboardHandler.live_fab = live_fab
    thread = threading.Thread(target=live_fab.loop, daemon=True)
    thread.start()
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"AMHS dashboard: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        live_fab.running = False
        server.server_close()


if __name__ == "__main__":
    main()
