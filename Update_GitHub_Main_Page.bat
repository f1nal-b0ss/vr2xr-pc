@echo off
cd /d "%~dp0"
title Update GitHub Main Page (f1nal-b0ss/vr2xr-pc)
echo ============================================================================
echo   vr2xr PC Studio - Update GitHub Main Page ^& Repository Contents
echo   Target: https://github.com/f1nal-b0ss/vr2xr-pc
echo ============================================================================
echo.

REM Clean up any interrupted Git rebase or merge state
git rebase --abort 2>nul
git merge --abort 2>nul

REM Ensure git is initialized and on the main branch
git init
git branch -M main
git remote remove origin 2>nul
git remote add origin https://github.com/f1nal-b0ss/vr2xr-pc.git

REM Untrack any accidentally staged .exe or cache files so the repo stays clean
git rm --cached *.exe 2>nul
git rm -r --cached yt_cache build dist 2>nul

REM Stage all main-page and source files
git add README.md banner.jpg banner.svg vr2xr_pc_player.html xreal_imu_bridge.py Build_Standalone_EXE.bat Launch_vr2xr_PC.bat Publish_to_GitHub.bat Update_GitHub_Main_Page.bat Create_GitHub_Release.bat LICENSE .gitignore 2>nul
git add .

set /p COMMIT_MSG="Enter short update description (or press Enter for default): "
if "%COMMIT_MSG%"=="" set COMMIT_MSG=Update main page README, banner, and vr2xr PC Studio files

git commit -m "%COMMIT_MSG%"
echo.
echo Pushing updated main page and files to https://github.com/f1nal-b0ss/vr2xr-pc ...
git push -u origin main --force

echo.
echo ============================================================================
echo   SUCCESS! Your GitHub main page is now live at:
echo   https://github.com/f1nal-b0ss/vr2xr-pc
echo ============================================================================
echo.
pause
