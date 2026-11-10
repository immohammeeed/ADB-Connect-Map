#!/usr/bin/env python3
"""
phone_stats.py - read battery, storage and RAM from an Android phone over ADB.

Read-only: it only runs commands that READ information from the phone.

Usage:
    python3 phone_stats.py              # pretty text
    python3 phone_stats.py --json       # JSON (this is what the dashboard will use)
    python3 phone_stats.py -s SERIAL    # pick a phone if several are connected
                                        # (SERIAL is what `adb devices` shows, e.g. 192.168.1.5:41005)
"""
import argparse
import json
import subprocess

# Meaning of the numbers Android uses in `dumpsys battery`
BATTERY_STATUS = {1: "unknown", 2: "charging", 3: "discharging", 4: "not charging", 5: "full"}
BATTERY_HEALTH = {1: "unknown", 2: "good", 3: "overheat", 4: "dead",
                  5: "over voltage", 6: "failure", 7: "cold"}


def adb(args, serial=None):
    """Run one adb command and return its text output."""
    cmd = ["adb"] + (["-s", serial] if serial else []) + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "adb command failed")
    return result.stdout


def parse_battery(text):
    """Turn the output of `dumpsys battery` into a clean dictionary."""
    raw = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            raw[key.strip()] = value.strip()

    if raw.get("AC powered") == "true":
        power = "AC charger"
    elif raw.get("USB powered") == "true":
        power = "USB"
    elif raw.get("Wireless powered") == "true":
        power = "wireless charger"
    else:
        power = "on battery"

    return {
        "level_percent": round(int(raw["level"]) * 100 / int(raw["scale"])),
        "temperature_c": int(raw["temperature"]) / 10,   # Android reports tenths of a degree
        "voltage_v": int(raw["voltage"]) / 1000,         # Android reports millivolts
        "status": BATTERY_STATUS.get(int(raw["status"]), "unknown"),
        "health": BATTERY_HEALTH.get(int(raw["health"]), "unknown"),
        "power_source": power,
    }


def parse_storage(text):
    """Turn the output of `df /data` (sizes in 1K blocks) into gigabytes."""
    lines = [l for l in text.splitlines() if l.strip()]
    parts = lines[-1].split()   # last line holds the numbers
    total_kb, used_kb, free_kb = int(parts[1]), int(parts[2]), int(parts[3])
    gb = 1024 * 1024            # 1K blocks -> GB
    return {
        "total_gb": round(total_kb / gb, 1),
        "used_gb": round(used_kb / gb, 1),
        "free_gb": round(free_kb / gb, 1),
        "used_percent": round(used_kb * 100 / total_kb),
    }


def parse_memory(text):
    """Turn /proc/meminfo into RAM numbers.
    We use MemAvailable, not MemFree: Android keeps 'free' RAM busy as cache,
    so MemFree always looks almost empty even when plenty is available."""
    info = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            info[key.strip()] = int(value.split()[0])   # value is in kB
    total, available = info["MemTotal"], info["MemAvailable"]
    gb = 1024 * 1024
    return {
        "total_gb": round(total / gb, 2),
        "available_gb": round(available / gb, 2),
        "used_gb": round((total - available) / gb, 2),
        "used_percent": round((total - available) * 100 / total),
    }


def read_phone(serial=None):
    """Ask the phone for everything and return one dictionary."""
    return {
        "model": adb(["shell", "getprop", "ro.product.model"], serial).strip(),
        "battery": parse_battery(adb(["shell", "dumpsys", "battery"], serial)),
        "storage": parse_storage(adb(["shell", "df", "/data"], serial)),
        "memory": parse_memory(adb(["shell", "cat", "/proc/meminfo"], serial)),
    }


def main():
    parser = argparse.ArgumentParser(description="Read phone stats over ADB (read-only).")
    parser.add_argument("-s", "--serial", help="device serial from `adb devices`")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = parser.parse_args()

    try:
        data = read_phone(args.serial)
    except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError) as error:
        raise SystemExit(f"Could not read the phone: {error}")

    if args.json:
        print(json.dumps(data, indent=2))
        return

    b, s, m = data["battery"], data["storage"], data["memory"]
    print(f"Phone:    {data['model']}")
    print(f"Battery:  {b['level_percent']}% ({b['status']}, {b['power_source']}), "
          f"{b['temperature_c']} C, {b['voltage_v']} V, health {b['health']}")
    print(f"Storage:  {s['used_gb']} / {s['total_gb']} GB used ({s['used_percent']}%)")
    print(f"RAM:      {m['used_gb']} / {m['total_gb']} GB used ({m['used_percent']}%)")


if __name__ == "__main__":
    main()
