@echo off
setlocal
if "%~1"=="" (
  set "SQLITE_PATH=%~dp0chat.db"
) else (
  set "SQLITE_PATH=%~1"
)
echo Using SQLite DB: %SQLITE_PATH%
set "PYEXE=%~dp0venv\Scripts\python.exe"
if not exist "%PYEXE%" (
  echo Creating Python venv...
  python -m venv "%~dp0venv"
)
"%PYEXE%" -m pip install --upgrade pip
"%PYEXE%" -m pip install tornado bcrypt cffi emoji requests

:: Start the application
echo Starting DaiP Chat Room...
"%PYEXE%" app.py

:: Keep window open if application exits unexpectedly
pause
