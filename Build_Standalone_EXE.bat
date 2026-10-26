@echo off
cd /d "%~dp0"
title Build Standalone vr2xr_PC_Studio.exe
echo ============================================================================
echo   vr2xr PC Studio - One-Click Standalone Windows .EXE Compiler
echo ============================================================================
echo.

REM Clean up any interrupted Git rebase/merge state if present
git rebase --abort 2>nul
git merge --abort 2>nul

echo [1/3] Installing PyInstaller, websockets, and yt-dlp (for YouTube VR)...
python -m pip install --upgrade pyinstaller websockets yt-dlp
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [Error] Could not install build packages. Ensure Python is in your PATH.
    pause
    exit /b 1
)

echo.
echo [2/3] Compiling vr2xr_pc_player.html + xreal_imu_bridge.py into a single EXE...
python -m PyInstaller --noconfirm --clean --onefile ^
    --name "vr2xr_PC_Studio" ^
    --add-data "vr2xr_pc_player.html;." ^
    --hidden-import websockets ^
    --hidden-import yt_dlp ^
    --collect-all yt_dlp ^
    --collect-all websockets ^
    xreal_imu_bridge.py

if exist "dist\vr2xr_PC_Studio.exe" (
    copy /Y "dist\vr2xr_PC_Studio.exe" "vr2xr_PC_Studio.exe" >nul
    echo.
    echo ============================================================================
    echo   [3/3] SUCCESS! Created standalone executable:
    echo         %CD%\vr2xr_PC_Studio.exe
    echo         %CD%\dist\vr2xr_PC_Studio.exe
    echo.
    echo   Double-click vr2xr_PC_Studio.exe anytime to launch the VR player,
    echo   XREAL One Pro IMU head tracker, and YouTube VR180 stream proxy!
    echo ============================================================================
) else (
    echo.
    echo [Error] Build did not produce dist\vr2xr_PC_Studio.exe. Check output above.
)
echo.
pause
