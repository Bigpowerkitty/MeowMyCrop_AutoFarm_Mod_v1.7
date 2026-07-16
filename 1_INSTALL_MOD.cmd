@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Meow My Crop MOD Installer
cd /d "%~dp0"
echo =====================================================
echo Meow My Crop MOD v1.8 - INSTALL
echo Adds saved 100 limits, full can shortage analysis, and F5/F6/F7/F8 controls.
echo =====================================================
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0Tools\ModManager.ps1" -Mode Install
set "RC=%ERRORLEVEL%"
echo.
echo Result code: %RC%
echo Log file: "%~dp0mod_manager.log"
echo.
pause
exit /b %RC%
