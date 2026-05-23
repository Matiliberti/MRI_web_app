#!/usr/bin/env python3
"""
Raspberry Pi fullscreen media display daemon.
Connects to Supabase, fetches the latest row from display_media,
downloads and plays it via mpv, then polls for changes.
Assets flagged cache_locally are stored in CACHE_DIR and survive reboots.
Falls back to the most recent cached file when Supabase is unreachable.
"""
import os
import sys
import time
import json
import socket
import signal
import shutil
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
CACHE_DIR = Path(os.getenv("CACHE_DIR", "/home/pi/display_media/cache"))

_VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ts"}


def _ext(url: str) -> str:
    return Path(url.split("?")[0]).suffix.lower()


def _is_video(url: str) -> bool:
    return _ext(url) in _VIDEO_EXTS


def _cached_path(media_id: str, url: str) -> Path:
    suffix = _ext(url) or ".bin"
    return CACHE_DIR / f"{media_id}{suffix}"


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
        .select("id, file_url, created_at, cache_locally")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def _download(url: str, timeout=(15, None)) -> str:
    """Download url to a temp file. timeout=(connect, read); None = no limit."""
    suffix = _ext(url) or ".bin"
    fd, path = tempfile.mkstemp(suffix=suffix, dir="/tmp")
    os.close(fd)
    log.info("Downloading %s -> %s", url, path)
    with requests.get(url, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
    return path


def _download_to_cache(media_id: str, url: str) -> Path:
    """Download to persistent CACHE_DIR. No-op if already cached."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dest = _cached_path(media_id, url)
    if dest.exists():
        return dest
    tmp = _download(url, timeout=(15, None))  # no read timeout for large files
    shutil.move(tmp, dest)
    log.info("Cached %s -> %s", media_id, dest)
    return dest


def _find_fallback() -> Optional[str]:
    """Return the most recently modified file in CACHE_DIR, or None."""
    if not CACHE_DIR.exists():
        return None
    files = sorted(CACHE_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    return str(files[0]) if files else None


class Player:
    """Keeps a single mpv process alive and hot-swaps files via the IPC socket
    so transitions don't expose the desktop."""

    SOCKET_PATH = "/tmp/mpv-display.sock"

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._current_file: Optional[str] = None
        self._current_is_temp: bool = True

    def _alive(self) -> bool:
        if not os.path.exists(self.SOCKET_PATH):
            return False
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            sock.connect(self.SOCKET_PATH)
            sock.close()
            return True
        except (OSError, socket.timeout):
            return False

    def play(self, url: str, local_path: Optional[str] = None) -> None:
        """Play media. Uses local_path if provided and exists, else downloads url."""
        if local_path and Path(local_path).exists():
            file_path = local_path
            is_temp = False
        else:
            file_path = _download(url)
            is_temp = True

        old_file = self._current_file
        old_is_temp = self._current_is_temp

        if self._alive():
            try:
                self._send({"command": ["loadfile", file_path, "replace"]})
                self._send({"command": ["set_property", "pause", False]})
                self._current_file = file_path
                self._current_is_temp = is_temp
                if old_is_temp and old_file and old_file != file_path:
                    try:
                        os.unlink(old_file)
                    except OSError:
                        pass
                return
            except Exception as exc:
                log.warning("IPC swap failed (%s); restarting mpv", exc)
                self._stop()

        self._launch(file_path)
        self._current_file = file_path
        self._current_is_temp = is_temp
        if old_is_temp and old_file and old_file != file_path:
            try:
                os.unlink(old_file)
            except OSError:
                pass

    def _launch(self, path: str) -> None:
        try:
            os.unlink(self.SOCKET_PATH)
        except OSError:
            pass
        cmd = [
            "setsid", "-f",
            "mpv", path,
            "--fullscreen",
            "--no-terminal",
            "--no-osd-bar",
            "--no-input-default-bindings",
            "--gpu-api=opengl",
            "--keep-open=always",
            "--idle=yes",
            "--image-display-duration=inf",
            "--loop-file=inf",
            "--loop=inf",
            f"--input-ipc-server={self.SOCKET_PATH}",
        ]
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

    def _stop(self) -> None:
        if self._alive():
            try:
                self._send({"command": ["quit"]})
            except Exception:
                pass
            time.sleep(0.5)
        subprocess.run(["pkill", "-x", "mpv"], stderr=subprocess.DEVNULL)
        self._proc = None
        try:
            os.unlink(self.SOCKET_PATH)
        except OSError:
            pass

    def cleanup(self) -> None:
        self._stop()
        if self._current_file and self._current_is_temp:
            try:
                os.unlink(self._current_file)
            except OSError:
                pass


def main() -> None:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    player = Player()
    current_id: Optional[str] = None
    backoff = POLL_INTERVAL
    fallback_played = False

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
                    # Still on current item — ensure it gets cached if newly flagged
                    if row.get("cache_locally"):
                        cached = _cached_path(row["id"], row["file_url"])
                        if not cached.exists():
                            try:
                                _download_to_cache(row["id"], row["file_url"])
                            except Exception as exc:
                                log.warning("Background cache failed: %s", exc)
                    break

                # New item — ensure cached if flagged before playing
                if row.get("cache_locally"):
                    try:
                        _download_to_cache(row["id"], row["file_url"])
                    except Exception as exc:
                        log.warning("Cache download failed for %s: %s", row["id"], exc)

                cached = _cached_path(row["id"], row["file_url"])
                local = str(cached) if cached.exists() else None

                try:
                    player.play(row["file_url"], local_path=local)
                except requests.exceptions.HTTPError as exc:
                    code = exc.response.status_code if exc.response is not None else 0
                    if 400 <= code < 500:
                        log.warning("Skipping missing file (HTTP %d): %s", code, row["file_url"])
                        continue
                    raise

                current_id = row["id"]
                fallback_played = False
                log.info("Now playing: %s (cached=%s)", row["id"], local is not None)
                break

            backoff = POLL_INTERVAL

        except Exception as exc:
            log.warning("Fetch error (%s); retrying in %ds.", exc, backoff)

            # On first failure with nothing playing, fall back to local cache
            if current_id is None and not fallback_played:
                fallback = _find_fallback()
                if fallback:
                    log.info("Playing cached fallback: %s", fallback)
                    try:
                        player.play("", local_path=fallback)
                        fallback_played = True
                    except Exception as fe:
                        log.warning("Fallback playback failed: %s", fe)

            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
