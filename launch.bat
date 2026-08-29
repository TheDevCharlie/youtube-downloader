@echo off
title YouTube Downloader Pro
cd /d "%~dp0"
echo Starting YouTube Downloader...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred. Press any key to exit.
    pause >nul
)
