<div align="center">

![vr2xr PC Studio Banner](./banner.jpg)

# vr2xr PC Studio for XREAL One / XREAL One Pro

**180° / 360° Stereoscopic Side-by-Side (SBS) VR Video Player, 1000Hz 3DoF IMU Head-Tracking Bridge & YouTube VR Streamer for Windows / Linux / macOS**

[![Download Standalone EXE](https://img.shields.io/badge/Download-Standalone%20Windows%20.EXE-22c55e?style=for-the-badge&logo=windows)](https://github.com/f1nal-b0ss/vr2xr-pc/releases/latest)
[![GitHub Repo](https://img.shields.io/badge/GitHub-f1nal--b0ss%2Fvr2xr--pc-0ea5e9?style=for-the-badge&logo=github)](https://github.com/f1nal-b0ss/vr2xr-pc)
[![Hardware](https://img.shields.io/badge/Glasses-XREAL%20One%20%2F%20One%20Pro-10b981?style=for-the-badge)](https://github.com/f1nal-b0ss/vr2xr-pc)
[![YouTube VR](https://img.shields.io/badge/YouTube%20VR-yt--dlp%20Proxy-f43f5e?style=for-the-badge)](https://github.com/f1nal-b0ss/vr2xr-pc)
[![License: MIT](https://img.shields.io/badge/License-MIT-6366f1?style=for-the-badge)](./LICENSE)

*Inspired by [Skarian/vr2xr](https://github.com/skarian/vr2xr) and [SamiMitwalli/One-Pro-IMU-Retriever-Demo](https://github.com/SamiMitwalli/One-Pro-IMU-Retriever-Demo).*

</div>

## 📥 Instant Download (No Python Required)

👉 **[Download `vr2xr_PC_Studio.exe` from the Latest GitHub Release](https://github.com/f1nal-b0ss/vr2xr-pc/releases/latest)**

Double-click `vr2xr_PC_Studio.exe` on Windows 10/11 to automatically start the XREAL One Pro 1000Hz 3DoF IMU head-tracking bridge, local YouTube VR180 stream proxy, and native-style VR player window in one click!

## 🖥️ Live App Screenshot

<div align="center">

![vr2xr PC Studio Running App Screenshot](./app_screenshot.jpg)

</div>

## ✨ Key Features

* **🌐 100% True Spherical 3D WebGL Projections**:
  * **VR180 Equirectangular Hemisphere**: Standard 180° stereoscopic dome mapping Left Eye (`u ∈ [0, 0.5]`) and Right Eye (`u ∈ [0.5, 1.0]`).
  * **VR180 Equidistant Fisheye**: True spherical fisheye UV projection for dual-fisheye VR180 cameras.
  * **VR360 Full Sphere**: Complete 360° stereoscopic sphere.
  * **Cinema 3D Dome**: Curved 110° × 70° spherical theater screen.
* **🎯 Internal XREAL One Pro 3DoF Head Tracking**:
  * Connects directly to the XREAL One / One Pro USB-C NCM/RNDIS telemetry stream (`169.254.2.1:52998` & `169.254.1.1:52998`).
  * **Smart Firmware Auto-Alignment**: Automatically scans incoming 134-byte sensor packets (`283600000080` and `273600000080` headers) to lock onto the exact float32 byte offset where the accelerometer matches Earth's gravity vector (`~9.81 m/s²`), ensuring compatibility across all XREAL firmware revisions.
  * **Auto-Connecting WebSocket (`ws://127.0.0.1:8765`)**: The web player automatically connects and reconnects to `xreal_imu_bridge.py` in the background—no manual button clicks required.
  * **Additional Input Fallbacks**: Includes direct browser **USB WebHID**, **OpenTrack UDP relay (`--opentrack-udp 4242`)**, virtual gamepad polling, and **Free-Look Mouse Pointer Lock (`M` key)**.
* **▶️ Built-In YouTube VR180 / 3D Streamer (`http://127.0.0.1:8766`)**:
  * Paste any YouTube VR180 or 3D SBS video link directly into the player and click **Load**.
  * Uses `yt-dlp` to buffer high-resolution H.264/VP9 video (`bv*/b`) and companion audio (`ba*/b`) into `yt_cache/`—working seamlessly **even without `ffmpeg` installed**—and serves them locally with `Access-Control-Allow-Origin: *` and HTTP Byte-Range support.
* **⏱️ Auto-Hiding Fullscreen Progress Bar (3-Second Fade)**:
  * Interactive timeline scrubber, Play/Pause, `-15s`/`+15s` seek buttons, and live pose telemetry overlay in both **Glasses Fullscreen** and the **Pop-Out Glasses Display** window.
  * Automatically appears on mouse movement, click, scroll, or keypress and fades away after **3 seconds** of inactivity (hiding the mouse cursor in fullscreen).
* **🔍 Optical Zoom & Reversed Y-Axis Mouse Look**:
  * Smooth `0.50×` to `3.00×` optical camera zoom via mouse wheel, `+`/`-`/`0` hotkeys, or slider.
  * Reversed vertical mouse drag axis (enabled by default, with a UI toggle in the Touchpad deck) plus continuous edge auto-pan.
* **📦 One-Click Standalone Windows `.EXE` Compiler**:
  * Double-click `Build_Standalone_EXE.bat` to bundle `vr2xr_pc_player.html`, `xreal_imu_bridge.py`, `websockets`, and `yt-dlp` into a single standalone **`vr2xr_PC_Studio.exe`** executable via PyInstaller.

## 🚀 Quick Start

### Option A: Run the Standalone Windows Executable (`vr2xr_PC_Studio.exe`)

1. Download **`vr2xr_PC_Studio.exe`** from the **[Releases page](https://github.com/f1nal-b0ss/vr2xr-pc/releases/latest)**.
2. Plug in your **XREAL One Pro** (or **XREAL One**) glasses via USB-C.
3. Double-click the red **X (Menu)** button on your glasses:
   * Set **Spatial Screen → 3D Mode** (`Half SBS 1920×1080` or `Full SBS 3840×1080`).
   * Set **Follow Mode** (Stabilization Off) so raw IMU telemetry streams over USB-C.
4. Double-click **`vr2xr_PC_Studio.exe`** — it starts the 1000Hz IMU bridge, YouTube VR proxy, and VR player window automatically!

### Option B: Run From Source (`Launch_vr2xr_PC.bat`) or Build `.EXE` (`Build_Standalone_EXE.bat`)

1. Clone or download this repository.
2. Double-click **`Launch_vr2xr_PC.bat`** to run directly with Python, or double-click **`Build_Standalone_EXE.bat`** to compile `vr2xr_PC_Studio.exe` yourself.

## ⌨️ Keyboard & Mouse Controls

| Input / Hotkey | Action |
| :--- | :--- |
| **`Z`** | **Zero View** — Lock current head orientation as neutral forward center |
| **`R`** | **Recalibrate IMU** — Run 250-sample stationary gyroscope bias calibration |
| **`F`** | **Toggle Glasses Fullscreen** (or use **Pop-Out Glasses Display**) |
| **`M`** | **Toggle Free-Look Mouse Mode** (Pointer Lock look-around without holding click) |
| **`Space`** | **Play / Pause** active VR video or procedural test dome |
| **`Mouse Wheel` / `+` / `-`** | **Optical Zoom In / Out** (`0.50×` – `3.00×`) |
| **`0`** | **Reset Optical Zoom** to `1.00×` |
| **`←` / `→`** | **Seek Backward / Forward** `±15 seconds` |
| **`↑` / `↓`** | **Adjust Projection FOV** `±2°` (`50°` – `135°`) |

## 🛠️ Command-Line Options (`xreal_imu_bridge.py`)

```bash
python xreal_imu_bridge.py --help
```

* `--host 169.254.2.1` — XREAL One Pro USB-C NCM IPv4 address (automatically falls back to `169.254.1.1`)
* `--port 52998` — XREAL One Pro TCP IMU port
* `--ws-port 8765` — Local WebSocket telemetry port
* `--http-port 8766` — Local HTTP App & YouTube VR proxy port
* `--opentrack-udp 4242` — Relay 6-double UDP pose packets from OpenTrack
* `--simulate` — Run synthetic 3DoF head motion without glasses connected
* `--no-browser` — Do not auto-launch the browser app window on startup

## 📄 License

Released under the [MIT License](./LICENSE).