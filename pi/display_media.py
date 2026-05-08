#!/usr/bin/env python3
"""
Raspberry Pi fullscreen media display daemon.
Connects to Supabase, fetches the latest row from display_media,
downloads and plays it via mpv, then polls for changes.
"""
import os
import sys
import time
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


def _fetch_latest(supabase: Client) -> Optional[dict]:
    result = (
        supabase.table("display_media")
        .select("id, file_url, created_at")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


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
    """Manages a single mpv subprocess, replacing it on each media change."""

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._current_file: Optional[str] = None

    def play(self, url: str) -> None:
        local_path = _download(url)
        self._stop()

        if _is_video(url):
            extra = ["--loop-file=inf"]
        else:
            extra = ["--image-display-duration=inf", "--loop=inf"]

        cmd = ["mpv", local_path, "--fullscreen", "--no-terminal", "--no-osd-bar"] + extra
        log.info("Launching mpv: %s", " ".join(cmd))
        self._proc = subprocess.Popen(cmd)

        # Remove previous temp file now that the new one is open
        if self._current_file:
            try:
                os.unlink(self._current_file)
            except OSError:
                pass
        self._current_file = local_path

    def _stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
        self._proc = None

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
            media = _fetch_latest(supabase)
            if media and media["id"] != current_id:
                log.info("New media: %s", media["id"])
                player.play(media["file_url"])
                current_id = media["id"]
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
