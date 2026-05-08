#!/bin/bash
# Installs Claude's public key on the Pi for passwordless SSH/scp.
set -e
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cat > ~/.ssh/authorized_keys << 'KEY_EOF'
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDt4JTt+OwRZ0Sy3DiTINc5vJQrsnBibhgqq5aGLeATj claude-mri
KEY_EOF
chmod 600 ~/.ssh/authorized_keys
echo "Installed. Size: $(wc -c < ~/.ssh/authorized_keys) bytes (expected 92)."
