@echo off
cd /d "%~dp0"
title vr2xr PC Studio - XREAL ^& VITURE 3DoF IMU Bridge + YouTube VR Proxy
echo ============================================================================
echo   vr2xr PC Studio - XREAL One/Air ^& VITURE 3DoF Bridge + YouTube VR Proxy
echo ============================================================================
echo.
echo [1/2] Checking Python dependencies [websockets, yt-dlp, hidapi]...
python -m pip install -q --upgrade websockets yt-dlp hidapi 2>nul
if errorlevel 1 python -m pip install -q --upgrade websockets yt-dlp
echo [2/2] Starting vr2xr PC Studio Bridge ^& Player Window...
echo.
python xreal_imu_bridge.py
pause
