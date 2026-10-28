@echo off
cd /d "%~dp0"
title Create GitHub Release - vr2xr_PC_Studio.exe
echo ============================================================================
echo   vr2xr PC Studio - GitHub Release Helper
echo   Repo: https://github.com/f1nal-b0ss/vr2xr-pc
echo ============================================================================
echo.

set "EXE_FILE="
if exist "vr2xr_PC_Studio.exe" set "EXE_FILE=vr2xr_PC_Studio.exe"
if "%EXE_FILE%"=="" if exist "dist\vr2xr_PC_Studio.exe" set "EXE_FILE=dist\vr2xr_PC_Studio.exe"

if "%EXE_FILE%"=="" goto :missing_exe

echo Found executable: %CD%\%EXE_FILE%
echo.
set "REL_TAG=v2.1.0"
set /p REL_TAG="Enter new version tag [press Enter for v2.1.0, or type e.g. v2.2.0]: "
if "%REL_TAG%"=="" set "REL_TAG=v2.1.0"

echo.
echo Opening GitHub Release creator for tag %REL_TAG% and highlighting %EXE_FILE% in Explorer...
echo.
echo   1. In the GitHub browser tab that opens:
echo      - Tag version is pre-filled as: %REL_TAG% [must be a new tag not used before]
echo   2. Drag and drop "%EXE_FILE%" from the Explorer window into the binaries box
echo   3. Click "Publish release" at the bottom!
echo.
explorer.exe /select,"%CD%\%EXE_FILE%"
start "" "https://github.com/f1nal-b0ss/vr2xr-pc/releases/new?tag=%REL_TAG%&title=vr2xr+PC+Studio+%REL_TAG%+-+Standalone+Windows+EXE+[XREAL,+VITURE,+Rokid]"
pause
exit /b 0

:missing_exe
echo [!] vr2xr_PC_Studio.exe was not found in this folder or dist\.
echo     Run Build_Standalone_EXE.bat first to compile the EXE!
echo.
pause
exit /b 1
