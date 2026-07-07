@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Kiwoom Quant one-click launcher - self-healing Windows CMD version
REM Safe rule: never depend on activate.bat. Always run .venv\Scripts\python.exe directly.

cd /d "%~dp0"

echo [0/5] Working folder: %CD%

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 (
    py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3,11) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3.11"
)

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo [ERROR] Python was not found. Install Python 3.11.9 64-bit and check "Add python.exe to PATH".
    pause
    exit /b 1
)

echo [1/5] Checking virtual environment...
if exist ".venv" (
    if not exist ".venv\Scripts\python.exe" (
        echo [WARN] Broken .venv detected. Recreating it...
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo [2/5] Creating virtual environment...
    %PYTHON_CMD% -m venv ".venv"
    if errorlevel 1 goto FAIL
) else (
    echo [2/5] Virtual environment already exists.
)

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv\Scripts\python.exe was not created.
    goto FAIL
)

if not exist ".env" (
    echo [INFO] .env not found. Creating from .env.example...
    copy /y ".env.example" ".env" >nul
)

echo [3/5] Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto FAIL

echo [4/5] Installing requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto FAIL

echo [5/5] Starting Quant server...
start "" "http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
exit /b 0

:FAIL
echo.
echo [ERROR] Launcher failed. The launcher already tried to repair .venv and .env.
echo        1^) Check Python 3.11 installation.
echo        2^) Check that this folder path has no permission restrictions.
echo        3^) Run quant_debug.bat and share the output if it still fails.
pause
exit /b 1
