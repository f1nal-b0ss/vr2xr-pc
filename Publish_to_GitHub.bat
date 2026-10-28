@echo off
cd /d "%~dp0"
title Publish vr2xr-pc to GitHub (f1nal-b0ss)
echo ============================================================================
echo   Publishing vr2xr PC Studio to https://github.com/f1nal-b0ss/vr2xr-pc
echo ============================================================================
echo.
REM If a previous git rebase or merge was interrupted, abort it cleanly so no conflict markers remain:
git rebase --abort 2>nul
git merge --abort 2>nul

git init
git branch -M main
git remote remove origin 2>nul
git remote add origin https://github.com/f1nal-b0ss/vr2xr-pc.git
git add vr2xr_pc_player.html xreal_imu_bridge.py Build_Standalone_EXE.bat Launch_vr2xr_PC.bat Publish_to_GitHub.bat README.md banner.jpg app_screenshot.jpg banner.svg LICENSE .gitignore 2>nul
git add .
git commit -m "Update vr2xr PC Studio: 3DoF XREAL One Pro IMU tracking, YouTube VR streamer, standalone EXE builder, 3s fullscreen HUD, and banner"
echo.
echo Pushing cleanly to https://github.com/f1nal-b0ss/vr2xr-pc.git ...
git push -u origin main --force
echo.
echo ============================================================================
echo   Done! Visit: https://github.com/f1nal-b0ss/vr2xr-pc
echo ============================================================================
pause
