@echo off
title Building Charlie-yt C++ Native Backend (charlie_core_native.dll)
echo ======================================================================
echo   Compiling Charlie-yt C++ Native Engine with MSVC x64 Optimizations...
echo ======================================================================

set VCVARS="C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"

if not exist %VCVARS% (
    echo Error: MSVC BuildTools not found at %VCVARS%
    exit /b 1
)

call %VCVARS% x64

cd /d "%~dp0native_backend"

cl.exe /O2 /Oi /Ot /GL /std:c++17 /EHsc /LD charlie_engine.cpp /Fe:charlie_core_native.dll /link /LTCG /OPT:REF /OPT:ICF

if %ERRORLEVEL% equ 0 (
    echo.
    echo ======================================================================
    echo   Build SUCCESS: native_backend\charlie_core_native.dll ready!
    echo ======================================================================
    copy /Y charlie_core_native.dll ..\charlie_core_native.dll
) else (
    echo.
    echo Build failed with error code %ERRORLEVEL%
)

cd /d "%~dp0"
