#!/bin/bash
# Deploy / rebuild DISPLAY 1 from this Mac.
#   ./deploy.sh              -> uses ssh host "mri-pi" (see ~/.ssh/config)
#   PI_HOST=pi@1.2.3.4 ./deploy.sh
# First time on a fresh Pi: run ../common/install_key.sh on the Pi (or
# ssh-copy-id) so this script can log in without a password.
set -euo pipefail
cd "$(dirname "$0")"
PI_HOST="${PI_HOST:-mri-pi}"
COMMON=../common

echo "==> Deploying display 1 to $PI_HOST"
ssh "$PI_HOST" 'mkdir -p ~/display_media'
scp "$COMMON/display_media.py" "$COMMON/requirements.txt" "$COMMON/display-media.service" "$COMMON/setup.sh" "$PI_HOST:~/display_media/"
scp display.env "$PI_HOST:~/display_media/.env"
ssh -t "$PI_HOST" 'bash ~/display_media/setup.sh'
