@echo off
cd /d "%~dp0"
title Create GitHub Release (vr2xr_PC_Studio.exe)
echo ============================================================================
echo   vr2xr PC Studio - GitHub Release Helper (v2.0.0)
echo   Repo: https://github.com/f1nal-b0ss/vr2xr-pc
echo ============================================================================
echo.

set EXE_FILE=
if exist "vr2xr_PC_Studio.exe" set EXE_FILE=vr2xr_PC_Studio.exe
if "%EXE_FILE%"=="" if exist "dist\vr2xr_PC_Studio.exe" set EXE_FILE=dist\vr2xr_PC_Studio.exe

if "%EXE_FILE%"=="" (
    echo [!] vr2xr_PC_Studio.exe was not found in this folder or dist\.
    echo     Run Build_Standalone_EXE.bat first to compile the EXE!
    echo.
    pause
    exit /b 1
)

echo Found executable: %CD%\%EXE_FILE%
echo.

REM Check if GitHub CLI (gh) is installed for automatic 1-command release creation
where gh >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [GitHub CLI Detected] Creating Release v2.0.0 and uploading %EXE_FILE%...
    gh release create v2.0.0 "%EXE_FILE%" --repo f1nal-b0ss/vr2xr-pc --title "vr2xr PC Studio v2.0.0 — Standalone Windows EXE (XREAL One / One Pro)" --notes "### vr2xr PC Studio v2.0.0 (Standalone Windows Executable)\n\n- **Zero-Install Standalone EXE**: Download and double-click `vr2xr_PC_Studio.exe` to start the 1000Hz XREAL One / One Pro 3DoF IMU head-tracking bridge, local YouTube VR180 stream proxy, and 3D SBS WebGL player window.\n- **True Spherical 3D Projections**: VR180 Equirectangular, VR180 Fisheye, VR360 Sphere, and Cinema 3D Dome.\n- **Built-In YouTube VR Streamer**: Paste any YouTube VR180 or 3D SBS link directly into the player (no `ffmpeg` required).\n- **Auto-Hiding 3-Second Fullscreen Progress Bar**, Optical Zoom (`0.50x-3.00x`), and Reversed Vertical Mouse Axis."
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo ============================================================================
        echo   SUCCESS! Release v2.0.0 is live at:
        echo   https://github.com/f1nal-b0ss/vr2xr-pc/releases/tag/v2.0.0
        echo ============================================================================
        pause
        exit /b 0
    )
)

echo Opening GitHub Release creator in your browser and highlighting %EXE_FILE% in Explorer...
echo.
echo   1. In the GitHub browser tab that opens:
echo      - Tag version: v2.0.0
echo      - Release title: vr2xr PC Studio v2.0.0 (Standalone Windows EXE)
echo   2. Drag and drop "%EXE_FILE%" from the Explorer window into "Attach binaries by dropping them here"
echo   3. Click "Publish release" (green button at the bottom)!
echo.
explorer.exe /select,"%CD%\%EXE_FILE%"
start "" "https://github.com/f1nal-b0ss/vr2xr-pc/releases/new?tag=v2.0.0&title=vr2xr+PC+Studio+v2.0.0+%E2%80%94+Standalone+Windows+EXE"
pause
