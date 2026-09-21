@echo off
title DeepSeek Chat Exporter
setlocal enabledelayedexpansion

echo ========================================
echo   DeepSeek Chat Exporter
echo ========================================
echo.

set "PYTHON="

python --version >nul 2>&1
if not errorlevel 1 (
    python -m pip --version >nul 2>&1
    if not errorlevel 1 set "PYTHON=python"
)

if not defined PYTHON (
    py --version >nul 2>&1
    if not errorlevel 1 (
        py -m pip --version >nul 2>&1
        if not errorlevel 1 set "PYTHON=py"
    )
)

if not defined PYTHON (
    for /f "delims=" %%P in ('dir /b /s "%LOCALAPPDATA%\Microsoft\WindowsApps\python3*.exe" 2^>nul') do (
        if not defined PYTHON (
            "%%P" -m pip --version >nul 2>&1
            if not errorlevel 1 set "PYTHON=%%P"
        )
    )
)

if not defined PYTHON (
    for %%D in (
        "%LOCALAPPDATA%\Programs\Python"
        "C:\Python313"
        "C:\Python312"
        "C:\Python311"
        "C:\Python310"
        "D:\Python313"
        "D:\Python312"
        "D:\Python311"
    ) do (
        if not defined PYTHON (
            for /f "delims=" %%P in ('dir /b /s "%%~D\python.exe" 2^>nul') do (
                if not defined PYTHON (
                    "%%P" -m pip --version >nul 2>&1
                    if not errorlevel 1 set "PYTHON=%%P"
                )
            )
        )
    )
)

if not defined PYTHON (
    echo [!] Python with pip not found.
    echo     Opening download page...
    echo     Please install Python and CHECK "Add Python to PATH".
    echo.
    pause
    start "" "https://www.python.org/downloads/"
    exit /b
)

echo [1/4] Python found:
"%PYTHON%" --version
echo.

echo [2/4] Checking packages...
"%PYTHON%" -c "import selenium, webdriver_manager" >nul 2>&1
if errorlevel 1 (
    echo     Installing selenium and webdriver-manager...
    "%PYTHON%" -m pip install selenium webdriver-manager
    if errorlevel 1 (
        echo [!] Install failed. Please run manually:
        echo     "%PYTHON%" -m pip install selenium webdriver-manager
        pause
        exit /b
    )
)
echo     Packages OK.
echo.

echo [3/4] Starting Edge debug port...
start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\edge_debug" "https://chat.deepseek.com/"

echo     Waiting for Edge...
timeout /t 6 /nobreak >nul
echo.

echo [4/4] Running export script...
"%PYTHON%" "%~dp0export_chat.py"

echo.
echo Done. Press any key to close.
pause >nul