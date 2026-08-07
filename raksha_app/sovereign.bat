@echo off
:: SovereignAI Edge CLI launcher for Windows — run from the project root:
::   sovereign list
::   sovereign chat llama3:8b
setlocal
set "ROOT=%~dp0"

:: Prefer the backend venv (used during dev), else the root venv (created by launch.bat)
if exist "%ROOT%backend\.venv\Scripts\python.exe" (
    set "PY=%ROOT%backend\.venv\Scripts\python.exe"
) else (
    set "PY=%ROOT%.venv\Scripts\python.exe"
)

if not exist "%PY%" (
    echo [ERROR] Virtual environment not found. Run launch.bat once to set it up.
    exit /b 1
)

cd /d "%ROOT%backend\app"
"%PY%" -m cli.main %*
exit /b %errorlevel%
