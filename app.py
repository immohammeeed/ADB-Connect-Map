#!/usr/bin/env python3
"""
app.py - one-step launcher for the Phone Dashboard.

Starts the dashboard and opens it in your browser. This is the file that gets packaged
into a single executable (see build.sh).

    python3 app.py                # or ./phone-dashboard after building
    python3 app.py -s SERIAL      # pick a phone if several are connected
    python3 app.py --no-browser   # do not open the browser automatically
    python3 app.py --self-test    # check that the bundled files and tools are found
"""
import argparse
import shutil

import phone_stats
import server


def main():
    parser = argparse.ArgumentParser(description="Phone Dashboard")
    parser.add_argument("-s", "--serial", help="device serial from `adb devices`")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser")
    parser.add_argument("--self-test", action="store_true", help="check bundled files and tools, then exit")
    args = parser.parse_args()

    if args.self_test:
        dashboard_ok = (server.DASHBOARD_DIR / "index.html").exists()
        print(f"dashboard files: {'OK' if dashboard_ok else 'MISSING'}")
        print(f"device names:    {len(phone_stats.load_name_table())} entries")
        print(f"adb:             {shutil.which('adb') or 'NOT FOUND (install Android platform tools)'}")
        print(f"scrcpy:          {shutil.which('scrcpy') or 'not found (optional, only for screen mirroring)'}")
        return

    if shutil.which("adb") is None:
        print("Note: adb was not found. The dashboard will open, but it needs adb to read your phone.")

    server.run(serial=args.serial, port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
