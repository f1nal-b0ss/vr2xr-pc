@echo off
cd /d "%~dp0"
title Build Standalone vr2xr_PC_Studio.exe
echo ============================================================================
echo   vr2xr PC Studio - One-Click Standalone Windows .EXE Compiler
echo   Supports XREAL One/Pro/Air, VITURE [0x35CA], Rokid, RayNeo ^& OpenTrack
echo ============================================================================
echo.

REM Clean up any interrupted Git rebase or merge state if present
git rebase --abort 2>nul
git merge --abort 2>nul

echo [1/3] Installing PyInstaller, websockets, yt-dlp, and hidapi...
python -m pip install --upgrade pyinstaller websockets yt-dlp hidapi
if errorlevel 1 python -m pip install --upgrade pyinstaller websockets yt-dlp

echo.
echo [2/3] Compiling vr2xr_pc_player.html + xreal_imu_bridge.py into a single EXE...
python -m PyInstaller --noconfirm --clean --onefile --name "vr2xr_PC_Studio" --add-data "vr2xr_pc_player.html;." --hidden-import websockets --hidden-import yt_dlp --hidden-import hid --collect-all yt_dlp --collect-all websockets xreal_imu_bridge.py

if not exist "dist\vr2xr_PC_Studio.exe" goto :build_error

copy /Y "dist\vr2xr_PC_Studio.exe" "vr2xr_PC_Studio.exe" >nul
echo.
echo ============================================================================
echo   [3/3] SUCCESS! Created standalone executable:
echo         %CD%\vr2xr_PC_Studio.exe
echo         %CD%\dist\vr2xr_PC_Studio.exe
echo.
echo   Double-click vr2xr_PC_Studio.exe anytime to launch the VR player,
echo   XREAL / VITURE / Rokid 3DoF head tracker, and YouTube VR180 proxy!
echo ============================================================================
goto :done

:build_error
echo.
echo [Error] Build did not produce dist\vr2xr_PC_Studio.exe. Check output above.

:done
echo.
pause
