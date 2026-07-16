@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Meow My Crop MOD Speed Settings
cd /d "%~dp0"
echo =====================================================
echo Meow My Crop MOD v1.8 - CHANGE GROWTH SPEED
echo Close the game before changing speed.
echo =====================================================
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0Tools\ModManager.ps1" -Mode Speed
set "RC=%ERRORLEVEL%"
echo.
echo Result code: %RC%
echo Log file: "%~dp0mod_manager.log"
echo.
pause
exit /b %RC%
