# Raspberry Pi kit

One folder per physical display, so a broken Pi can be rebuilt from its own
folder without touching the other one.

```
pi/
  common/      shared by every display (daemon, service unit, setup script)
  display-1/   identity + deploy script for Pi 1  (web route "/")
  display-2/   identity + deploy script for Pi 2  (web route "/display-2")
```

The **only** thing that differs between displays is `display.env`, and in it
the only line that matters is `DISPLAY_ID`. The daemon derives everything else
from that number:

| DISPLAY_ID | feed table        | pi_status row | pi_settings row |
|-----------:|-------------------|--------------:|----------------:|
| 1          | `display_media`   | 1             | 1               |
| 2          | `display_media_2` | 2             | 2               |

## Rebuild a Pi from scratch

1. Flash Raspberry Pi OS (Desktop, 64-bit), user `pi`, enable SSH, join Wi-Fi
   and Tailscale (or note its LAN IP). Enable desktop auto-login.
2. Install the SSH key so deploys are passwordless: copy `common/install_key.sh`
   to the Pi and run it there, or use `ssh-copy-id`.
3. Make sure `~/.ssh/config` on the Mac has a host entry for the Pi
   (`mri-pi` for display 1, `mri-pi-2` for display 2), or pass `PI_HOST=`.
4. From this Mac:

   ```bash
   cd pi/display-2        # or display-1
   ./deploy.sh            # PI_HOST=pi@192.168.1.50 ./deploy.sh to override
   ```

   `deploy.sh` copies `common/*` plus `display.env` (as `.env`) to
   `/home/pi/display_media/` and runs `setup.sh` there, which installs mpv and
   the Python venv, enables the `display-media` systemd user service and starts
   it. Re-run `deploy.sh` any time to push an updated daemon.

5. Audio HAT (WM8960) gain settings: see `../amp_controls.md`.

## Check it's alive

- Web app header shows `LIVE` for that display within ~90 s.
- On the Pi: `systemctl --user status display-media` and
  `tail -f /tmp/display_media.log` (first line prints the display id and table).

## Device notes

- **Pi 2** (installed 2026-09-03): Pi 4 Model B, Debian 13 (trixie), hostname
  `helmetpetB`, labwc/Wayland. `sudo` asks for the `pi` password on this image,
  so `deploy.sh` (which runs `setup.sh` over `ssh -t`) will prompt once. It is
  not on Tailscale yet; `mri-pi-2` in `~/.ssh/config` points at its LAN IP.
  No WM8960 card was detected (only HDMI + headphone jack): if the audio HAT is
  fitted, enable `dtoverlay=wm8960-soundcard` in `/boot/firmware/config.txt`.

## Notes

- Never change `DISPLAY_ID` on a Pi that is already installed; it would start
  playing the other product's feed.
- Pi 1 was installed before this layout existed. If it is ever redeployed with
  `display-1/deploy.sh` it ends up identical to a fresh install; `DISPLAY_ID=1`
  keeps it on the original tables.
