@echo off
setlocal
echo ======================================================================
echo   Compiling Charlie-yt Native C++ App with DirectX 12 Acceleration...
echo ======================================================================

set VCVARS="C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"

if not exist %VCVARS% (
    echo Error: MSVC BuildTools not found at %VCVARS%
    exit /b 1
)

call %VCVARS% x64

set SDK_INC=webview2_sdk\build\native\include
set SDK_LIB=webview2_sdk\build\native\x64

cl.exe /O2 /Oi /Ot /GL /std:c++17 /EHsc /I"%SDK_INC%" ^
  src\main.cpp src\downloader_bridge.cpp ^
  /Fe:Charlie-yt.exe ^
  /link /LTCG /OPT:REF /OPT:ICF ^
  /LIBPATH:"%SDK_LIB%" WebView2Loader.dll.lib ^
  User32.lib Gdi32.lib Shell32.lib Ole32.lib Shlwapi.lib /SUBSYSTEM:WINDOWS

copy /Y "%SDK_LIB%\WebView2Loader.dll" "WebView2Loader.dll" >nul

echo.
echo ======================================================================
echo   Build SUCCESS: Charlie-yt.exe (249 KB Native C++ App) is ready!
echo ======================================================================
