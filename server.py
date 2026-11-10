#!/usr/bin/env python3
"""
server.py - serves the phone dashboard on your own computer.

    python3 server.py              # then open http://127.0.0.1:8000
    python3 server.py -s SERIAL    # pick a phone if several are connected
    python3 server.py --port 9000

It listens on 127.0.0.1 only, so nobody else on the Wi-Fi can reach it.
It uses phone_stats.py (same folder) to read the phone, and it is read-only.
"""
import argparse
import json
import threading
import time
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import phone_stats

DASHBOARD_DIR = Path(__file__).parent / "dashboard"
CACHE_SECONDS = 1.0   # reading the phone takes a moment, so reuse the result for a second

_cache = {"time": 0.0, "data": None, "error": None}
_lock = threading.Lock()


def get_stats(serial):
    """Return (data, error). Talks to the phone at most once per CACHE_SECONDS."""
    with _lock:
        if time.time() - _cache["time"] > CACHE_SECONDS:
            try:
                _cache["data"] = phone_stats.read_phone(serial)
                _cache["error"] = None
            except Exception as error:   # phone unplugged, adb missing, odd output...
                _cache["data"] = None
                _cache["error"] = str(error)
            _cache["time"] = time.time()
        return _cache["data"], _cache["error"]


class Handler(SimpleHTTPRequestHandler):
    serial = None   # set in main()

    def do_GET(self):
        if self.path.split("?")[0] == "/api/stats":
            data, error = get_stats(self.serial)
            body = json.dumps(data if data else {"error": error}).encode("utf-8")
            self.send_response(200 if data else 503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()   # everything else: files from the dashboard/ folder

    def log_message(self, format, *args):
        pass   # keep the terminal quiet


def make_server(serial=None, port=8000):
    """Create the dashboard server (does not start it)."""
    Handler.serial = serial
    handler = partial(Handler, directory=str(DASHBOARD_DIR))
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


def run(serial=None, port=8000, open_browser=False):
    """Start the dashboard and keep serving until Ctrl+C. Used by server.py and adb_connect_map.py."""
    server = make_server(serial, port)
    url = f"http://127.0.0.1:{port}"
    print(f"Dashboard running at {url}  (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description="Phone dashboard server")
    parser.add_argument("-s", "--serial", help="device serial from `adb devices`")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    run(args.serial, args.port)


if __name__ == "__main__":
    main()
