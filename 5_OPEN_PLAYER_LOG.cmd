@echo off
setlocal
set "LOG=%USERPROFILE%\AppData\LocalLow"
for /r "%LOG%" %%F in (Player.log) do (
  findstr /i /c:"MeowMyCrop_Data" "%%F" >nul 2>&1
  if not errorlevel 1 (
    start "" notepad.exe "%%F"
    exit /b 0
  )
)
echo Meow My Crop Player.log was not found under:
echo %LOG%
pause
exit /b 1
