@echo off
title Building Charlie-yt Executable
echo ===================================================
echo   Compiling Charlie-yt to Standalone Windows EXE...
echo ===================================================

python -m PyInstaller --noconsole --onefile ^
  --icon=app_icon.ico ^
  --name="Charlie-yt" ^
  --collect-all customtkinter ^
  --collect-all yt_dlp ^
  --collect-all PIL ^
  main.py

echo.
echo ===================================================
echo   Build complete! Output located at: dist\Charlie-yt.exe
echo ===================================================
pause
