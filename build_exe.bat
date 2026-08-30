@echo off
title Building Charlie-yt Executable with C++ Native Engine
echo ===================================================
echo   Compiling C++ Native DLL first...
echo ===================================================

call build_cpp.bat

echo.
echo ===================================================
echo   Compiling Charlie-yt to Standalone Windows EXE...
echo ===================================================

python -m PyInstaller --noconsole --onefile ^
  --icon=app_icon.ico ^
  --name="Charlie-yt" ^
  --add-binary "charlie_core_native.dll;." ^
  --add-binary "native_backend\charlie_core_native.dll;native_backend" ^
  --collect-all customtkinter ^
  --collect-all yt_dlp ^
  --collect-all PIL ^
  main.py

echo.
echo ===================================================
echo   Build complete! Output located at: dist\Charlie-yt.exe
echo ===================================================
pause
