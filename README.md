# ADB Connect Map: Live Phone Dashboard

A fork of [crosenblum/ADB-Connect-Map](https://github.com/crosenblum/ADB-Connect-Map) (MIT license).
The original scans Android devices over ADB and opens them in scrcpy. This fork adds a **live web dashboard** for your phone and makes **wireless debugging** work properly.

## What this fork adds

- **Live dashboard** in your browser: battery (level, temperature, voltage, health), storage and RAM, refreshed every 2 seconds.
- **Material 3 Expressive inspired design:** wavy progress indicators, spring motion, shapes that morph on hover, and a palette generated from any seed color. This is a re-creation in plain HTML, CSS and JavaScript, not Google's official component library.
- **Wireless support:** phones connected over Wi-Fi (any port) are detected, and a guided pairing step helps you connect one.
- **Friendly phone names:** `SM-G991B` is shown as `Galaxy S21 5G`.
- **"No phone connected" screen** with hints that match the problem (unauthorized, adb missing, offline, several devices).
- **Dashboard option in the original menu**, next to scrcpy.

### Fixes to the original

- Wireless devices (`IP:port`) were skipped, and Wi-Fi detection assumed port 5555.
- Devices that had been unplugged were still listed as connected from old saved data.
- adb's `* daemon started` lines were treated as devices.
- Choosing `0` to exit first selected the last device.
- scrcpy output was hidden, so a crash looked like a normal exit. Errors are now shown.
- The needless `adb usb` call before scrcpy was removed.
- Text typed during wireless setup is validated before it reaches a shell command.

## Requirements

- Python 3.8 or newer (no extra packages)
- `adb` (Android platform tools)
- `scrcpy` (optional, only for the screen mirror)
- An Android phone with USB debugging, or Wireless debugging (Android 11 or newer)

Developed and tested on Linux. It should work on macOS and Windows too, but that is untested.

## Quick start

```
git clone https://github.com/immohammeeed/ADB-Connect-Map.git
cd ADB-Connect-Map
python3 adb_connect_map.py
```

Pick your phone, then choose **1. Live dashboard**. Your browser opens at `http://127.0.0.1:8000`. Press Ctrl+C to stop.

You can also run the parts directly:

```
python3 server.py                 # dashboard only (add -s SERIAL to pick a phone)
python3 phone_stats.py            # print battery, storage and RAM in the terminal
python3 phone_stats.py --json     # the same data as JSON
python3 adb_connect_map.py --action dashboard
```

## Single executable

You can package the dashboard into one file that needs no Python installed:

```
./build.sh
./dist/phone-dashboard --self-test    # checks the bundled files, adb and scrcpy
./dist/phone-dashboard                # starts the dashboard and opens your browser
```

The executable still needs `adb` on the computer (and `scrcpy` if you want screen mirroring). It is built with PyInstaller, so build it on the kind of system you want to run it on: a Linux build runs on Linux. If port 8000 is busy, it uses the next free port.

## Connecting wirelessly

1. On the phone: Settings, Developer options, **Wireless debugging** (turn it on). The phone and computer must be on the same Wi-Fi network.
2. Run `python3 adb_connect_map.py`. If no phone is found it offers a guided setup.
3. First time only: tap **Pair device with pairing code** on the phone and enter the address and 6-digit code when asked.
4. Enter the IP address and port shown on the main Wireless debugging screen.

Android chooses a new port each time Wireless debugging is switched on, so reconnect with the new port after toggling it.

## Friendly device names

A small table of Samsung Galaxy models is included in `device_names.json`. To cover almost every phone, run this once (needs internet):

```
python3 update_device_names.py
```

It downloads Google's public list of supported Android devices and merges it into `device_names.json`. Entries you add by hand are kept.

## Privacy and safety

- The dashboard listens on `127.0.0.1` only, so other devices on your network cannot reach it.
- The dashboard only reads data: `dumpsys battery`, `df`, `/proc/meminfo` and `getprop`. It changes nothing on the phone.
- scrcpy mirrors your real screen, including notifications. Turn on Do Not Disturb before showing it to an audience.
- Turn Wireless debugging off when you are not using it.
- `device_map.json` stores serial numbers and IP addresses, so it is excluded from git.

## Project layout

| File | Purpose |
| --- | --- |
| `adb_connect_map.py` | Original program, modified: device menu, wireless support, dashboard and scrcpy options |
| `phone_stats.py` | Reads battery, storage, RAM and the phone's name over ADB |
| `server.py` | Local web server that serves the dashboard and `/api/stats` |
| `dashboard/` | The web page (`index.html`, `style.css`, `app.js`) |
| `device_names.json` | Model code to marketing name table |
| `update_device_names.py` | Builds the full name table from Google's device list |

## Credits and license

Original project by [crosenblum](https://github.com/crosenblum/ADB-Connect-Map), released under the MIT license. See [LICENSE](LICENSE), which is kept unchanged.
The dashboard design is inspired by Google's Material 3 Expressive. This project is not affiliated with Google.
