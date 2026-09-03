#!/bin/bash
# Runs ON the Pi. Installs system deps, the Python venv, the daemon and its
# systemd user service. Idempotent: safe to re-run to update the daemon.
#
# Expects the following to already be in ~/display_media (deploy.sh copies them):
#   display_media.py  requirements.txt  display-media.service  .env
set -euo pipefail

APP_DIR="$HOME/display_media"
cd "$APP_DIR"

echo "==> Checking .env"
[ -f .env ] || { echo "ERROR: $APP_DIR/.env missing (copy from pi/display-N/display.env)"; exit 1; }
grep -q '^DISPLAY_ID=' .env || { echo "ERROR: .env has no DISPLAY_ID"; exit 1; }
echo "    DISPLAY_ID=$(grep '^DISPLAY_ID=' .env | cut -d= -f2)"

echo "==> System packages"
sudo apt-get update -qq
sudo apt-get install -y -qq mpv python3-venv python3-pip wireplumber

echo "==> Python venv"
[ -d venv ] || python3 -m venv venv
./venv/bin/pip install --quiet --upgrade pip
./venv/bin/pip install --quiet -r requirements.txt

echo "==> Cache dir"
mkdir -p "$APP_DIR/cache"

echo "==> systemd user service"
mkdir -p "$HOME/.config/systemd/user"
cp display-media.service "$HOME/.config/systemd/user/display-media.service"
# Start the user manager at boot even before anyone logs in.
sudo loginctl enable-linger "$USER"
systemctl --user daemon-reload
systemctl --user enable display-media.service
systemctl --user restart display-media.service

echo "==> Done. Status:"
systemctl --user --no-pager status display-media.service | head -5
echo "Logs: journalctl --user -u display-media -f   or   tail -f /tmp/display_media.log"
