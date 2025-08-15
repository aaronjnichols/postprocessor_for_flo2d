@echo off
REM Build script for FLO-2D Postprocessor installer
REM This script builds both the executable and the Windows installer

echo ==========================================================
echo FLO-2D Postprocessor - Complete Build Process
echo ==========================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo Error: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

echo Step 1: Building executable...
echo.
cd /d "%~dp0\.."
python tools\build_exe.py
if %errorlevel% neq 0 (
    echo Error: Executable build failed
    pause
    exit /b 1
)

echo.
echo Step 2: Checking for Inno Setup...

REM Check if Inno Setup is installed
set "INNO_PATH="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "INNO_PATH=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set "INNO_PATH=%ProgramFiles%\Inno Setup 6\ISCC.exe"
) else (
    echo.
    echo Inno Setup not found. Please install Inno Setup 6 from:
    echo https://jrsoftware.org/isdl.php
    echo.
    echo After installation, you can manually build the installer by:
    echo 1. Opening installer.iss in Inno Setup
    echo 2. Clicking "Build" -^> "Compile"
    echo.
    echo Press any key to continue without building installer...
    pause >nul
    goto :end
)

echo Found Inno Setup: %INNO_PATH%
echo Building installer...

"%INNO_PATH%" installer.iss
if %errorlevel% neq 0 (
    echo Error: Installer build failed
    pause
    exit /b 1
)

:end
echo.
echo ==========================================================
echo BUILD COMPLETE!
echo ==========================================================
echo.
echo Files created:
echo - dist\FLO2D-Postprocessor.exe (standalone executable)
if exist "installer_output\FLO2D-Postprocessor-Setup.exe" (
    echo - installer_output\FLO2D-Postprocessor-Setup.exe (installer)
)
echo.
echo Next steps:
echo 1. Test the executable on different Windows versions
echo 2. Test the installer on a clean system
echo 3. Upload to GitHub releases or distribution platform
echo.
pause