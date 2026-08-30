@echo off
title Building Universal Media Downloader Executable
echo ===================================================
echo   Compiling Universal Media Downloader to EXE...
echo ===================================================

python -m PyInstaller --noconsole --onefile ^
  --icon=app_icon.ico ^
  --name="UniversalMediaDownloader" ^
  --collect-all customtkinter ^
  --collect-all yt_dlp ^
  --collect-all PIL ^
  main.py

echo.
echo ===================================================
echo   Build complete! Output located at: dist\UniversalMediaDownloader.exe
echo ===================================================
pause
