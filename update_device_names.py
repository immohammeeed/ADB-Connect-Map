#!/usr/bin/env python3
"""
update_device_names.py - builds device_names.json (model code -> marketing name)
from Google's public list of supported Android devices.

Run it once (needs internet):   python3 update_device_names.py
Names already in device_names.json are kept, so you can add or fix entries by hand.
"""
import csv
import io
import json
import urllib.request
from pathlib import Path

URL = "https://storage.googleapis.com/play_public/supported_devices.csv"
OUT = Path(__file__).with_name("device_names.json")


def build_table(csv_text):
    """Columns we need: 'Marketing Name' and 'Model'. First name found for a model wins."""
    table = {}
    for row in csv.DictReader(io.StringIO(csv_text)):
        model = (row.get("Model") or "").replace("\\", "").strip()
        name = (row.get("Marketing Name") or "").replace("\\", "").strip()
        if model and name and name != model and model not in table:
            table[model] = name
    return table


def main():
    print("Downloading Google's device list...")
    with urllib.request.urlopen(URL, timeout=30) as response:
        raw = response.read()
    table = build_table(raw.decode("utf-16"))   # Google's file is UTF-16

    try:
        existing = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        existing = {}
    merged = {**table, **existing}              # your own entries win

    OUT.write_text(json.dumps(merged, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(f"Saved {len(merged)} device names to {OUT.name}")


if __name__ == "__main__":
    main()
