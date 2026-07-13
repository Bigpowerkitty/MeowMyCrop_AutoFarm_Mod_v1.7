@echo off
setlocal
if exist "%~dp0mod_manager.log" (
  start "" notepad.exe "%~dp0mod_manager.log"
) else (
  echo No installer log exists yet.
  pause
)
