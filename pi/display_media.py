#!/usr/bin/env python3
"""
Raspberry Pi fullscreen media display daemon.
Connects to Supabase, fetches the latest row from display_media,
downloads and plays it via mpv, then polls for changes.
"""
import os
import sys
import time
import json
import socket
import signal
import subprocess
import tempfile
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/display_media.log"),
    ],
)
log = logging.getLogger(__name__)

SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_KEY: str = os.environ["SUPABASE_KEY"]
POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", "5"))

_VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ts"}


def _ext(url: str) -> str:
    return Path(url.split("?")[0]).suffix.lower()


def _is_video(url: str) -> bool:
    return _ext(url) in _VIDEO_EXTS


def _update_heartbeat(supabase: Client) -> None:
    """Upsert pi_status.last_seen so the web app knows the Pi is alive."""
    try:
        supabase.table("pi_status").upsert({
            "id": 1,
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as exc:
        log.debug("Heartbeat upsert failed: %s", exc)


def _fetch_recent(supabase: Client, limit: int = 10) -> list:
    result = (
        supabase.table("display_media")
        .select("id, file_url, created_at")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def _download(url: str) -> str:
    suffix = _ext(url) or ".bin"
    fd, path = tempfile.mkstemp(suffix=suffix, dir="/tmp")
    os.close(fd)
    log.info("Downloading %s -> %s", url, path)
    with requests.get(url, stream=True, timeout=30) as resp:
        resp.raise_for_status()
        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
    return path


class Player:
    """Keeps a single mpv process alive and hot-swaps files via the IPC socket
    so transitions don't expose the desktop."""

    SOCKET_PATH = "/tmp/mpv-display.sock"

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._current_file: Optional[str] = None

    def _alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def play(self, url: str) -> None:
        local_path = _download(url)
        old_file = self._current_file

        if self._alive():
            try:
                self._send({"command": ["loadfile", local_path, "replace"]})
                self._set_loop_for(url)
                self._current_file = local_path
                if old_file and old_file != local_path:
                    try:
                        os.unlink(old_file)
                    except OSError:
                        pass
                return
            except Exception as exc:
                log.warning("IPC swap failed (%s); restarting mpv", exc)
                self._stop()

        self._launch(local_path, url)
        self._current_file = local_path
        if old_file and old_file != local_path:
            try:
                os.unlink(old_file)
            except OSError:
                pass

    def _launch(self, path: str, url: str) -> None:
        try:
            os.unlink(self.SOCKET_PATH)
        except OSError:
            pass
        cmd = [
            "mpv", path,
            "--fullscreen",
            "--no-terminal",
            "--no-osd-bar",
            "--no-input-default-bindings",
            "--background=#000000",
            "--keep-open=always",
            "--idle=yes",
            "--image-display-duration=inf",
            f"--input-ipc-server={self.SOCKET_PATH}",
        ]
        if _is_video(url):
            cmd.append("--loop-file=inf")
        else:
            cmd.append("--loop=inf")
        # Make sure mpv finds the local display when launched from SSH/systemd.
        # Set Wayland and X11 env vars so it works on either compositor.
        env = os.environ.copy()
        env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        env.setdefault("WAYLAND_DISPLAY", "wayland-0")
        env.setdefault("DISPLAY", ":0")
        if "XAUTHORITY" not in env:
            xauth = os.path.expanduser("~/.Xauthority")
            if os.path.exists(xauth):
                env["XAUTHORITY"] = xauth
        log.info("Launching mpv: %s", " ".join(cmd))
        self._proc = subprocess.Popen(cmd, env=env)
        # Wait briefly for the socket to appear so subsequent IPC calls succeed
        for _ in range(20):
            if os.path.exists(self.SOCKET_PATH):
                return
            time.sleep(0.1)

    def _send(self, command: dict) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        try:
            sock.connect(self.SOCKET_PATH)
            sock.sendall((json.dumps(command) + "\n").encode("utf-8"))
        finally:
            sock.close()

    def _set_loop_for(self, url: str) -> None:
        if _is_video(url):
            self._send({"command": ["set_property", "loop-file", "inf"]})
            self._send({"command": ["set_property", "loop", "no"]})
        else:
            self._send({"command": ["set_property", "loop-file", "no"]})
            self._send({"command": ["set_property", "loop", "inf"]})

    def _stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
        self._proc = None
        try:
            os.unlink(self.SOCKET_PATH)
        except OSError:
            pass

    def cleanup(self) -> None:
        self._stop()
        if self._current_file:
            try:
                os.unlink(self._current_file)
            except OSError:
                pass


def main() -> None:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    player = Player()
    current_id: Optional[str] = None
    backoff = POLL_INTERVAL

    def _shutdown(sig, _frame):
        log.info("Signal %d received, shutting down.", sig)
        player.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    log.info("Started. Polling every %ds.", POLL_INTERVAL)

    while True:
        try:
            _update_heartbeat(supabase)
            rows = _fetch_recent(supabase)

            for row in rows:
                if row["id"] == current_id:
                    break  # already playing the best available file
                try:
                    player.play(row["file_url"])
                except requests.exceptions.HTTPError as exc:
                    code = exc.response.status_code if exc.response is not None else 0
                    if 400 <= code < 500:
                        log.warning("Skipping missing file (HTTP %d): %s", code, row["file_url"])
                        continue
                    raise
                current_id = row["id"]
                log.info("Now playing: %s", row["id"])
                break

            backoff = POLL_INTERVAL  # reset on success
        except requests.exceptions.RequestException as exc:
            log.warning("Network error (%s); retrying in %ds.", exc, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue
        except Exception as exc:
            log.error("Unexpected error: %s", exc, exc_info=True)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
