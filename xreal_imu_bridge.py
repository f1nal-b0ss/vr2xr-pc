#!/usr/bin/env python3
"""
xreal_imu_bridge.py — Standalone App Host, XREAL One Pro IMU Bridge & YouTube VR Proxy
======================================================================================
Can be run directly with Python OR compiled into a single standalone Windows executable
(`vr2xr_PC_Studio.exe`) using the included `Build_Standalone_EXE.bat` script.

Key Features:
1. Direct XREAL One / One Pro USB-C TCP Stream (`169.254.2.1:52998` & `169.254.1.1:52998`)
   - Supports all firmware packet headers (`283600000080`, `273600000080`, `2836`, `2736`).
   - Smart Auto-Byte-Offset Alignment across firmware versions using Earth gravity vector norm.
   - Fast 250-sample stationary gyroscope bias calibration and 1:1 3DoF integration.
2. Built-In YouTube VR180 / 3D SBS Stream Downloader & Local Range Server (`http://127.0.0.1:8766`)
   - Uses `yt-dlp`'s native downloader (with full signature/n-param decryption and chunked HTTP)
     to fetch the best H.264/VP9 video stream (`bv*/b`) and audio stream (`ba*/b`) into `yt_cache/`
     without requiring `ffmpeg`, avoiding YouTube CDN 403 errors and format-not-available errors.
   - Streams live download progress (`%`) over WebSocket to the player UI and serves the cached
     media with `Access-Control-Allow-Origin: *` and full HTTP Byte-Range seeking.
3. Standalone `.exe` App Launcher (PyInstaller `--onefile` compatible)
   - Serves `vr2xr_pc_player.html` locally on `http://127.0.0.1:8766` and automatically launches
     a native-style Edge/Chrome App window when started.
"""

import argparse
import asyncio
import http.server
import json
import math
import mimetypes
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from typing import Callable, Dict, Optional, Set, Tuple

try:
    import websockets
except ImportError:
    websockets = None


HEADER_V1 = bytes.fromhex("283600000080")
HEADER_V2 = bytes.fromhex("273600000080")
MAGIC_SHORT_1 = bytes.fromhex("2836")
MAGIC_SHORT_2 = bytes.fromhex("2736")

# Cache of resolved YouTube local files for CORS byte-range serving
YT_STREAM_CACHE: Dict[str, dict] = {}
_YT_DLP_UPGRADED = False


def strip_ansi(text: str) -> str:
    """Removes ANSI terminal color escape sequences from error messages."""
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text or "")


def get_resource_path(filename: str) -> str:
    """Returns path to bundled resource (works both in normal Python and PyInstaller --onefile EXE)."""
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(base_dir, filename)
    if os.path.exists(candidate):
        return candidate
    cwd_candidate = os.path.join(os.getcwd(), filename)
    return cwd_candidate if os.path.exists(cwd_candidate) else candidate


def ensure_yt_dlp():
    """Imports yt_dlp, auto-installing or upgrading it via pip when running in normal Python."""
    global _YT_DLP_UPGRADED
    if not getattr(sys, "frozen", False) and not _YT_DLP_UPGRADED:
        _YT_DLP_UPGRADED = True
        try:
            print("\n[YouTube] Ensuring latest 'yt-dlp' is installed...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "--upgrade", "yt-dlp"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
        except Exception:
            pass
    try:
        import yt_dlp  # type: ignore
        return yt_dlp
    except ImportError:
        if getattr(sys, "frozen", False):
            raise RuntimeError("yt-dlp was not bundled in this EXE. Re-run Build_Standalone_EXE.bat.")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "yt-dlp"])
        import yt_dlp  # type: ignore
        return yt_dlp


def _guess_mime(filepath: str, default_mime: str = "video/mp4") -> str:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".webm":
        return "video/webm" if "video" in default_mime else "audio/webm"
    if ext in (".m4a", ".aac"):
        return "audio/mp4"
    if ext == ".mp3":
        return "audio/mpeg"
    if ext == ".ogg" or ext == ".opus":
        return "audio/ogg"
    if ext == ".mp4":
        return "video/mp4"
    guessed, _ = mimetypes.guess_type(filepath)
    return guessed or default_mime


def resolve_youtube_stream(
    youtube_url: str,
    http_port: int,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Downloads the YouTube VR video & audio streams into `yt_cache/` using `yt-dlp`'s native
    downloader (with full signature decryption and chunked range handling) so browser playback
    never hits YouTube 403 Forbidden or 'Requested format is not available' errors.
    Works with or without ffmpeg installed on Windows!
    """
    yt_dlp = ensure_yt_dlp()
    print(f"\n[YouTube] Resolving & caching YouTube VR video: {youtube_url} ...")
    if progress_cb:
        progress_cb("Fetching YouTube VR stream metadata...")

    cache_dir = os.path.join(os.getcwd(), "yt_cache")
    os.makedirs(cache_dir, exist_ok=True)

    last_pct_reported = [-10]

    def ydl_progress_hook(d):
        if d.get("status") == "downloading" and progress_cb:
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            if total > 0:
                pct = int((downloaded * 100) / total)
                if pct - last_pct_reported[0] >= 10:
                    last_pct_reported[0] = pct
                    progress_cb(f"Buffering YouTube VR stream ({pct}%)...")

    # Prefer H.264 (avc1) or VP9 up to 2160p (4K) so HTML5 <video> hardware decoding works in every browser.
    # Notice every fallback branch is a single stream (`bv*` or `b`) so ffmpeg is NOT required!
    video_format_selector = (
        "bv*[height<=2160][vcodec^=avc1][ext=mp4]/"
        "bv*[height<=2160][vcodec^=vp9]/"
        "bv*[height<=2160][vcodec^=vp09]/"
        "bv*[height<=2160][ext=mp4]/"
        "bv*[height<=2160]/"
        "b[ext=mp4]/"
        "bv*/b"
    )

    vid_opts = {
        "quiet": False,
        "no_warnings": True,
        "no_color": True,
        "noplaylist": True,
        "format": video_format_selector,
        "outtmpl": os.path.join(cache_dir, "%(id)s_video.%(ext)s"),
        "progress_hooks": [ydl_progress_hook],
    }

    try:
        with yt_dlp.YoutubeDL(vid_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            if info and info.get("_type") == "playlist" and info.get("entries"):
                info = next(iter(info["entries"]))
            video_file = ydl.prepare_filename(info)
    except Exception as first_err:
        # Ultra-permissive fallback with no format filter constraints
        print(f"[YouTube] Retrying with universal format selector ({strip_ansi(str(first_err))})...")
        fallback_opts = {
            "quiet": False,
            "no_warnings": True,
            "no_color": True,
            "noplaylist": True,
            "format": "bv*/b",
            "outtmpl": os.path.join(cache_dir, "%(id)s_video.%(ext)s"),
            "progress_hooks": [ydl_progress_hook],
        }
        with yt_dlp.YoutubeDL(fallback_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            if info and info.get("_type") == "playlist" and info.get("entries"):
                info = next(iter(info["entries"]))
            video_file = ydl.prepare_filename(info)

    if not info or not os.path.exists(video_file):
        raise RuntimeError("yt-dlp did not produce a local video file.")

    video_id = info.get("id") or str(int(time.time()))
    title = info.get("title") or "YouTube VR Video"
    duration = info.get("duration") or 0
    vid_has_audio = (info.get("acodec") or "none").lower() not in ("none", "")

    audio_file = None
    if not vid_has_audio:
        # Download the companion audio stream separately (no ffmpeg required!)
        if progress_cb:
            progress_cb("Buffering companion audio track...")
        aud_opts = {
            "quiet": True,
            "no_warnings": True,
            "no_color": True,
            "noplaylist": True,
            "format": "ba[ext=m4a]/ba[ext=webm]/ba*/b",
            "outtmpl": os.path.join(cache_dir, "%(id)s_audio.%(ext)s"),
        }
        try:
            with yt_dlp.YoutubeDL(aud_opts) as ydl:
                aud_info = ydl.extract_info(youtube_url, download=True)
                if aud_info and aud_info.get("_type") == "playlist" and aud_info.get("entries"):
                    aud_info = next(iter(aud_info["entries"]))
                candidate_aud = ydl.prepare_filename(aud_info)
                if os.path.exists(candidate_aud):
                    audio_file = candidate_aud
        except Exception as aud_err:
            print(f"[YouTube] Note: Audio track skipped ({strip_ansi(str(aud_err))})")

    YT_STREAM_CACHE[video_id] = {
        "video_file": video_file,
        "video_mime": _guess_mime(video_file, "video/mp4"),
        "audio_file": audio_file,
        "audio_mime": _guess_mime(audio_file, "audio/mp4") if audio_file else None,
        "title": title,
        "duration": duration,
    }

    video_proxy = f"http://127.0.0.1:{http_port}/yt_proxy?id={urllib.parse.quote(video_id)}&track=video&t={int(time.time())}"
    audio_proxy = (
        f"http://127.0.0.1:{http_port}/yt_proxy?id={urllib.parse.quote(video_id)}&track=audio&t={int(time.time())}"
        if audio_file
        else None
    )
    print(f"[YouTube] Ready: '{title}' -> {video_file}")
    return {
        "ok": True,
        "video_id": video_id,
        "title": title,
        "duration": duration,
        "stream_url": video_proxy,
        "audio_url": audio_proxy,
    }


class Vr2xrLocalHttpHandler(http.server.BaseHTTPRequestHandler):
    """Serves vr2xr_pc_player.html and streams cached YouTube VR video/audio files with CORS & Range support."""

    def log_message(self, format_str, *args):
        pass

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Range, Content-Type, Accept")
        self.send_header("Access-Control-Expose-Headers", "Content-Length, Content-Range, Accept-Ranges")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def _serve_local_media_file(self, fpath: str, mime_type: str):
        if not fpath or not os.path.exists(fpath):
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()
            return

        fsize = os.path.getsize(fpath)
        range_hdr = self.headers.get("Range")
        start, end = 0, max(0, fsize - 1)
        status = 200

        if range_hdr and range_hdr.startswith("bytes="):
            status = 206
            parts = range_hdr[6:].split(",")[0].split("-")
            try:
                if parts[0].strip():
                    start = int(parts[0].strip())
                if len(parts) > 1 and parts[1].strip():
                    end = min(fsize - 1, int(parts[1].strip()))
            except ValueError:
                start, end = 0, max(0, fsize - 1)

        length = max(0, end - start + 1) if fsize > 0 else 0
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", mime_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == 206 and fsize > 0:
            self.send_header("Content-Range", f"bytes {start}-{end}/{fsize}")
        self.end_headers()

        try:
            with open(fpath, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/yt_proxy":
            qs = urllib.parse.parse_qs(parsed.query)
            vid = (qs.get("id") or [""])[0]
            track = (qs.get("track") or ["video"])[0]
            entry = YT_STREAM_CACHE.get(vid)
            if not entry:
                self.send_response(404)
                self.send_cors_headers()
                self.end_headers()
                return
            fpath = entry.get("audio_file") if track == "audio" else (entry.get("video_file") or entry.get("local_file"))
            mime = (entry.get("audio_mime") or "audio/mp4") if track == "audio" else (entry.get("video_mime") or "video/mp4")
            if not fpath or not os.path.exists(fpath):
                self.send_response(404)
                self.send_cors_headers()
                self.end_headers()
                return
            fsize = os.path.getsize(fpath)
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", mime)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(fsize))
            self.end_headers()
            return
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        # 1. Serve the standalone VR player UI at / or /vr2xr_pc_player.html
        if path in ("/", "/index.html", "/vr2xr_pc_player.html"):
            html_path = get_resource_path("vr2xr_pc_player.html")
            if not os.path.exists(html_path):
                self.send_response(404)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(b"vr2xr_pc_player.html not found in directory.")
                return
            with open(html_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # 2. Resolve a YouTube URL to local CORS-enabled proxy stream URLs
        if path == "/yt_resolve":
            yt_url = (qs.get("url") or [""])[0].strip()
            if not yt_url:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "Missing url parameter"}).encode("utf-8"))
                return
            try:
                http_port = self.server.server_address[1]
                res = resolve_youtube_stream(yt_url, http_port)
                body = json.dumps(res).encode("utf-8")
                self.send_response(200)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as exc:
                err_body = json.dumps({"ok": False, "error": strip_ansi(str(exc))}).encode("utf-8")
                self.send_response(500)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(err_body)))
                self.end_headers()
                self.wfile.write(err_body)
            return

        # 3. Serve the cached YouTube video or audio file with HTTP Range support & CORS headers
        if path == "/yt_proxy":
            vid = (qs.get("id") or [""])[0]
            track = (qs.get("track") or ["video"])[0]
            entry = YT_STREAM_CACHE.get(vid)
            if not entry:
                self.send_response(404)
                self.send_cors_headers()
                self.end_headers()
                return

            if track == "audio":
                fpath = entry.get("audio_file")
                mime = entry.get("audio_mime") or "audio/mp4"
            else:
                fpath = entry.get("video_file") or entry.get("local_file")
                mime = entry.get("video_mime") or "video/mp4"

            self._serve_local_media_file(fpath, mime)
            return

        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()


def start_local_http_server(host: str, port: int) -> Optional[http.server.ThreadingHTTPServer]:
    """Starts the local HTTP App & YouTube Proxy server on 127.0.0.1:8766 in a daemon thread."""
    try:
        server = http.server.ThreadingHTTPServer((host, port), Vr2xrLocalHttpHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server
    except Exception as exc:
        print(f"[HTTP] Note: Local HTTP server on {host}:{port} could not bind ({exc}).")
        return None


def launch_app_window(url: str):
    """Opens vr2xr PC Studio in a native-looking Edge/Chrome --app window (or default browser)."""
    if sys.platform.startswith("win"):
        edge_paths = [
            shutil.which("msedge"),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        chrome_paths = [
            shutil.which("chrome"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        for browser_bin in edge_paths + chrome_paths:
            if browser_bin and os.path.exists(browser_bin):
                try:
                    subprocess.Popen([browser_bin, f"--app={url}"])
                    return
                except Exception:
                    pass
    webbrowser.open(url)


def is_port_in_use(host: str, port: int) -> bool:
    """Checks if a local TCP port already has an active listener."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


def free_port_on_windows_or_unix(port: int) -> bool:
    """Attempts to terminate an existing process listening on `port`."""
    try:
        if sys.platform.startswith("win"):
            out = subprocess.check_output(
                ["netstat", "-ano", "-p", "TCP"], text=True, stderr=subprocess.DEVNULL
            )
            pids = set()
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[1].endswith(f":{port}") and parts[3].upper() == "LISTENING":
                    pid = int(parts[4])
                    if pid != os.getpid() and pid > 0:
                        pids.add(pid)
            for pid in pids:
                print(f"[Bridge] Stopping previous bridge process (PID {pid}) on port {port}...")
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            time.sleep(0.5)
            return bool(pids)
        else:
            out = subprocess.check_output(["lsof", "-ti", f"tcp:{port}"], text=True, stderr=subprocess.DEVNULL)
            for pid_str in out.splitlines():
                pid = int(pid_str.strip())
                if pid != os.getpid():
                    os.kill(pid, 9)
            time.sleep(0.4)
            return True
    except Exception:
        return False


class XrealOneImuTracker:
    """Gyroscope bias estimator and 3DoF orientation integrator for XREAL One / One Pro."""

    def __init__(self, calib_samples: int = 250, sensitivity: float = 1.0):
        self.calib_samples = calib_samples
        self.sensitivity = sensitivity
        self.detected_offset: Optional[int] = None
        self.packets_parsed = 0
        self.reset_calibration()
        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        self.last_ts: Optional[float] = None
        self.gyro_unit_scale: Optional[float] = None

    def reset_calibration(self):
        self.samples_collected = 0
        self.bias_gx = 0.0
        self.bias_gy = 0.0
        self.bias_gz = 0.0
        self.calibrating = True
        self.gyro_unit_scale = None

    def zero_view(self):
        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0

    def update(self, gx: float, gy: float, gz: float, ax: float, ay: float, az: float, now: float):
        self.packets_parsed += 1

        if self.calibrating:
            self.bias_gx += gx
            self.bias_gy += gy
            self.bias_gz += gz
            self.samples_collected += 1
            if self.samples_collected >= self.calib_samples:
                self.bias_gx /= self.calib_samples
                self.bias_gy /= self.calib_samples
                self.bias_gz /= self.calib_samples
                bias_mag = math.sqrt(self.bias_gx ** 2 + self.bias_gy ** 2 + self.bias_gz ** 2)
                self.gyro_unit_scale = (180.0 / math.pi) if bias_mag < 0.8 else 1.0
                self.calibrating = False
                print(
                    f"\n[IMU] Calibration complete ({self.calib_samples} samples) | "
                    f"ByteOffset={self.detected_offset} | "
                    f"Bias=({self.bias_gx:.5f}, {self.bias_gy:.5f}, {self.bias_gz:.5f})"
                )
            self.last_ts = now
            return

        dt = 0.001 if self.last_ts is None else max(0.0001, min(0.05, now - self.last_ts))
        self.last_ts = now

        cx = gx - self.bias_gx
        cy = gy - self.bias_gy
        cz = gz - self.bias_gz

        unit_scale = self.gyro_unit_scale if self.gyro_unit_scale is not None else (180.0 / math.pi)

        deadzone = 0.0015 if unit_scale > 10.0 else 0.08
        if abs(cx) < deadzone:
            cx = 0.0
        if abs(cy) < deadzone:
            cy = 0.0
        if abs(cz) < deadzone:
            cz = 0.0

        d_pitch = cx * dt * unit_scale * self.sensitivity
        d_yaw = cy * dt * unit_scale * self.sensitivity
        d_roll = cz * dt * unit_scale * self.sensitivity

        self.pitch = max(-89.0, min(89.0, self.pitch + d_pitch))
        self.yaw += d_yaw
        self.roll = max(-89.0, min(89.0, self.roll + d_roll))

        acc_norm = math.sqrt(ax * ax + ay * ay + az * az)
        if 0.5 < acc_norm < 20.0:
            self.roll *= 0.998


def parse_imu_payload(packet: bytes, tracker: XrealOneImuTracker) -> Optional[Tuple[float, float, float, float, float, float]]:
    if len(packet) < 38:
        return None

    if tracker.detected_offset is not None and tracker.detected_offset + 24 <= len(packet):
        try:
            vals = struct.unpack_from("<6f", packet, tracker.detected_offset)
            if all(math.isfinite(v) and abs(v) < 500.0 for v in vals):
                gx, gy, gz, ax, ay, az = vals
                acc_norm = math.sqrt(ax * ax + ay * ay + az * az)
                if 0.4 <= acc_norm <= 25.0:
                    return gx, gy, gz, ax, ay, az
        except struct.error:
            pass

    priority_offsets = [14, 15, 13, 12, 16, 17, 18, 19, 20, 22, 24, 26, 28, 30, 32, 34, 36, 8, 10]
    all_offsets = priority_offsets + [o for o in range(6, len(packet) - 24) if o not in priority_offsets]

    best_offset = None
    best_vals = None
    best_score = 999.0

    for off in all_offsets:
        if off + 24 > len(packet):
            continue
        try:
            vals = struct.unpack_from("<6f", packet, off)
        except struct.error:
            continue
        if not all(math.isfinite(v) for v in vals):
            continue
        gx, gy, gz, ax, ay, az = vals
        if any(abs(g) > 35.0 for g in (gx, gy, gz)):
            continue
        if any(0.0 < abs(v) < 1e-9 for v in vals):
            continue
        acc_norm = math.sqrt(ax * ax + ay * ay + az * az)
        dist_98 = abs(acc_norm - 9.81)
        dist_1g = abs(acc_norm - 1.0) * 9.81
        score = min(dist_98, dist_1g)
        if score < 3.2 and score < best_score:
            best_score = score
            best_offset = off
            best_vals = vals

    if best_vals is not None and best_offset is not None:
        if tracker.detected_offset != best_offset:
            tracker.detected_offset = best_offset
            print(f"\n[IMU] Auto-detected XREAL One Pro payload alignment at byte offset {best_offset}")
        return best_vals

    for fallback_off in (14, 15, 13, 16):
        if fallback_off + 24 <= len(packet):
            try:
                vals = struct.unpack_from("<6f", packet, fallback_off)
                if all(math.isfinite(v) and abs(v) < 100.0 for v in vals):
                    if any(abs(v) > 1e-6 for v in vals[:3]):
                        return vals
            except struct.error:
                pass
    return None


def find_next_packet_header(buf: bytearray, start_pos: int = 0) -> int:
    idx1 = buf.find(HEADER_V1, start_pos)
    idx2 = buf.find(HEADER_V2, start_pos)
    candidates = [i for i in (idx1, idx2) if i != -1]
    if candidates:
        return min(candidates)
    idx3 = buf.find(MAGIC_SHORT_1, start_pos)
    idx4 = buf.find(MAGIC_SHORT_2, start_pos)
    short_candidates = [i for i in (idx3, idx4) if i != -1]
    return min(short_candidates) if short_candidates else -1


async def run_bridge(args):
    if websockets is None:
        raise SystemExit("Error: 'websockets' library not installed. Run: pip install websockets")

    ws_port = args.ws_port
    http_port = args.http_port

    if is_port_in_use(args.ws_host, ws_port):
        if not args.no_kill_existing:
            free_port_on_windows_or_unix(ws_port)
            free_port_on_windows_or_unix(http_port)
        if is_port_in_use(args.ws_host, ws_port):
            print(
                f"\n[Notice] An XREAL IMU Bridge is ALREADY running on ws://{args.ws_host}:{ws_port}!\n"
                f"  -> Opening vr2xr PC Studio...\n"
            )
            if not args.no_browser:
                launch_app_window(f"http://{args.ws_host}:{http_port}/")
            return

    http_srv = start_local_http_server(args.ws_host, http_port)
    if http_srv:
        print(f"[HTTP] App & YouTube VR Stream Proxy listening on http://{args.ws_host}:{http_port}/")

    clients: Set = set()
    tracker = XrealOneImuTracker(calib_samples=250, sensitivity=args.sensitivity)

    async def ws_handler(websocket):
        clients.add(websocket)
        print(f"\n[WS] vr2xr Web Player connected! ({len(clients)} active client)")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    cmd = data.get("cmd")
                    if cmd == "recalibrate":
                        print("\n[IMU] Recalibrating gyroscope stationary bias...")
                        tracker.reset_calibration()
                    elif cmd == "zero_view":
                        print("\n[IMU] Zero View locked to current head orientation.")
                        tracker.zero_view()
                    elif cmd == "resolve_youtube":
                        yt_url = data.get("url", "").strip()
                        if yt_url:
                            loop = asyncio.get_running_loop()

                            def send_progress(msg_txt: str):
                                try:
                                    asyncio.run_coroutine_threadsafe(
                                        websocket.send(
                                            json.dumps({"type": "youtube_progress", "message": msg_txt})
                                        ),
                                        loop,
                                    )
                                except Exception:
                                    pass

                            try:
                                res = await loop.run_in_executor(
                                    None, resolve_youtube_stream, yt_url, http_port, send_progress
                                )
                                await websocket.send(json.dumps({"type": "youtube_resolved", **res}))
                            except Exception as exc:
                                await websocket.send(
                                    json.dumps({
                                        "type": "youtube_resolved",
                                        "ok": False,
                                        "error": strip_ansi(str(exc)),
                                    })
                                )
                except Exception:
                    pass
        finally:
            clients.discard(websocket)
            print(f"\n[WS] vr2xr Web Player disconnected ({len(clients)} active)")

    async def broadcast_pose():
        last_print = 0.0
        while True:
            now = time.monotonic()
            if clients:
                payload = json.dumps({
                    "yaw": round(tracker.yaw, 3),
                    "pitch": round(tracker.pitch, 3),
                    "roll": round(tracker.roll, 3),
                    "calibrating": tracker.calibrating,
                    "packets": tracker.packets_parsed,
                })
                await asyncio.gather(
                    *(c.send(payload) for c in list(clients)),
                    return_exceptions=True,
                )
            if tracker.packets_parsed > 0 and (now - last_print) >= 0.25:
                last_print = now
                status = "CALIBRATING" if tracker.calibrating else "LIVE 3DoF"
                sys.stdout.write(
                    f"\r[IMU {status}] Pkts: {tracker.packets_parsed:6d} | "
                    f"Offset: {str(tracker.detected_offset):>3s} | "
                    f"Yaw: {tracker.yaw:+7.2f}° | Pitch: {tracker.pitch:+7.2f}° | Roll: {tracker.roll:+6.2f}°   "
                )
                sys.stdout.flush()
            await asyncio.sleep(1.0 / 60.0)

    async def tcp_xreal_reader():
        candidate_hosts = [args.host]
        for fallback_ip in ("169.254.2.1", "169.254.1.1"):
            if fallback_ip not in candidate_hosts:
                candidate_hosts.append(fallback_ip)

        host_idx = 0
        while True:
            target_host = candidate_hosts[host_idx % len(candidate_hosts)]
            host_idx += 1
            try:
                print(f"[TCP] Connecting to XREAL One Pro at {target_host}:{args.port}...")
                reader, _ = await asyncio.wait_for(
                    asyncio.open_connection(target_host, args.port), timeout=3.0
                )
                print(
                    f"[TCP] Connected to XREAL One Pro at {target_host}:{args.port}!\n"
                    f"[IMU] Keep glasses still for 0.3 seconds to calibrate gyroscope..."
                )
                buf = bytearray()
                while True:
                    chunk = await reader.read(4096)
                    if not chunk:
                        raise ConnectionError("EOF from glasses TCP stream")
                    buf.extend(chunk)

                    while len(buf) >= 280:
                        start = find_next_packet_header(buf, 0)
                        if start == -1:
                            del buf[:-12]
                            break
                        if start > 0:
                            del buf[:start]
                        if len(buf) < 134:
                            break
                        next_hdr = find_next_packet_header(buf, 6)
                        if next_hdr != -1 and 64 <= next_hdr <= 200:
                            pkt = bytes(buf[:next_hdr])
                            del buf[:next_hdr]
                        else:
                            pkt = bytes(buf[:134])
                            del buf[:134]

                        parsed = parse_imu_payload(pkt, tracker)
                        if parsed:
                            tracker.update(*parsed, time.monotonic())
            except Exception as exc:
                print(f"\n[TCP] Glasses stream unavailable at {target_host}:{args.port} ({exc}). Retrying...")
                await asyncio.sleep(1.5)

    async def udp_opentrack_reader(udp_port: int):
        print(f"[UDP] Listening for OpenTrack UDP pose packets on 127.0.0.1:{udp_port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", udp_port))
        sock.setblocking(False)
        tracker.calibrating = False
        loop = asyncio.get_running_loop()
        while True:
            try:
                data, _ = await loop.sock_recvfrom(sock, 1024)
                if len(data) >= 48:
                    _, _, _, yaw, pitch, roll = struct.unpack("<6d", data[:48])
                    tracker.yaw = yaw
                    tracker.pitch = pitch
                    tracker.roll = roll
                    tracker.packets_parsed += 1
            except Exception:
                await asyncio.sleep(0.005)

    async def simulated_reader():
        print("[SIM] Running simulated 3DoF head movement...")
        tracker.calibrating = False
        t0 = time.monotonic()
        while True:
            t = time.monotonic() - t0
            tracker.yaw = math.sin(t * 0.9) * 35.0
            tracker.pitch = math.cos(t * 1.2) * 15.0
            tracker.roll = math.sin(t * 0.6) * 4.0
            tracker.packets_parsed += 1
            await asyncio.sleep(1.0 / 120.0)

    async def auto_open_ui_if_needed():
        await asyncio.sleep(0.9)
        if not args.no_browser and not clients and http_srv:
            app_url = f"http://{args.ws_host}:{http_port}/"
            print(f"[App] Launching vr2xr PC Studio window ({app_url})...")
            launch_app_window(app_url)

    async with websockets.serve(ws_handler, args.ws_host, ws_port):
        print(f"[WS] vr2xr IMU WebSocket Bridge listening on ws://{args.ws_host}:{ws_port}")
        if args.simulate:
            producer = simulated_reader()
        elif args.opentrack_udp:
            producer = udp_opentrack_reader(args.opentrack_udp)
        else:
            producer = tcp_xreal_reader()
        await asyncio.gather(broadcast_pose(), producer, auto_open_ui_if_needed())


def main():
    parser = argparse.ArgumentParser(description="XREAL One / One Pro IMU Bridge & Standalone App Host for vr2xr PC")
    parser.add_argument("--host", default="169.254.2.1", help="XREAL One Pro link-local IPv4 address (default: 169.254.2.1)")
    parser.add_argument("--port", type=int, default=52998, help="XREAL One Pro IMU TCP stream port (default: 52998)")
    parser.add_argument("--ws-host", default="127.0.0.1", help="Local WebSocket bind address (default: 127.0.0.1)")
    parser.add_argument("--ws-port", type=int, default=8765, help="Local WebSocket port (default: 8765)")
    parser.add_argument("--http-port", type=int, default=8766, help="Local HTTP App & YouTube Proxy port (default: 8766)")
    parser.add_argument("--sensitivity", type=float, default=1.0, help="Angular velocity sensitivity multiplier (default: 1.0)")
    parser.add_argument("--opentrack-udp", type=int, default=0, help="Optional OpenTrack UDP port to relay (e.g., 4242)")
    parser.add_argument("--simulate", action="store_true", help="Stream simulated head movement without glasses connected")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the player window on startup")
    parser.add_argument("--kill-existing", action="store_true", help="Stop any existing bridge using port 8765 (enabled by default)")
    parser.add_argument("--no-kill-existing", action="store_true", help="Do not stop an existing bridge process on port 8765")
    args = parser.parse_args()

    try:
        asyncio.run(run_bridge(args))
    except KeyboardInterrupt:
        print("\n[Bridge] Stopped by user.")


if __name__ == "__main__":
    main()