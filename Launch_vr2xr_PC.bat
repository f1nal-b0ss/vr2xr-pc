@echo off
title vr2xr PC Launcher for XREAL One Pro
cd /d "%~dp0"
echo ============================================================================
echo   vr2xr PC Studio — XREAL One / One Pro 180 SBS VR Launcher
echo ============================================================================
echo.
echo [1/2] Opening vr2xr_pc_player.html in your default browser...
start "" "%~dp0vr2xr_pc_player.html"
echo.
echo [2/2] Checking for Python to start optional XREAL One Pro IMU Head Tracking...
where python >nul 2>nul
if %errorlevel% equ 0 (
    echo Starting XREAL One Pro USB-C IMU Bridge on 169.254.2.1:52998...
    python "%~dp0xreal_imu_bridge.py" --host 169.254.2.1 --port 52998 --kill-existing
) else (
    echo Python not found in PATH — running in standalone browser/touchpad mode.
    pause
)
