@echo off
setlocal
echo ======================================================================
echo   Building Charlie-yt Native Setup Installer (Charlie-yt-Setup.exe)...
echo ======================================================================

set ISCC="C:\Users\HP\AppData\Local\Programs\Inno Setup 6\ISCC.exe"

if not exist %ISCC% (
    set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)

if not exist %ISCC% (
    echo Error: Inno Setup compiler ISCC.exe not found!
    exit /b 1
)

:: 1. Compile the native app first
call build_native_app.bat

:: 2. Compile the Windows Setup installer
%ISCC% installer.iss

if %ERRORLEVEL% == 0 (
    echo.
    echo ======================================================================
    echo   Installer Build SUCCESS!
    echo   Output: installer_dist\Charlie-yt-Setup.exe
    echo ======================================================================
) else (
    echo.
    echo Installer build failed with error %ERRORLEVEL%
)
