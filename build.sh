#!/usr/bin/env bash
# Builds a single-file executable: dist/phone-dashboard
# Run it on the same kind of computer you want to run it on (a Linux build runs on Linux).
set -e
cd "$(dirname "$0")"

python3 -m venv .build-venv
source .build-venv/bin/activate
pip install --quiet pyinstaller

pyinstaller --onefile --clean --noconfirm \
  --name phone-dashboard \
  --add-data "dashboard:dashboard" \
  --add-data "device_names.json:." \
  app.py

echo
echo "Built: dist/phone-dashboard"
echo "Try:   ./dist/phone-dashboard --self-test"
