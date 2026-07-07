@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ===== Kiwoom Quant launcher diagnostics =====
echo Current folder: %CD%
echo.
echo [Python launcher]
where py
py -3.11 --version
py -3.11 -c "import sys; print(sys.executable); print(sys.version)"
echo.
echo [Python command]
where python
python --version
python -c "import sys; print(sys.executable); print(sys.version)"
echo.
echo [VENV]
dir ".venv\Scripts\python.exe"
dir ".venv\Scripts\activate.bat"
echo.
echo [Files]
dir requirements.txt
dir .env
dir .env.example
echo.
echo [Repair command used by quant.bat]
echo If .venv is broken, quant.bat deletes and recreates it, then runs .venv\Scripts\python.exe directly.
echo =============================================
pause
