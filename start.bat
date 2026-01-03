@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title AirForce API Auto Register System

:: ==========================================
:: AirForce API Auto Register - Smart Launcher
:: Features:
::   - Auto detect/download embedded Python
::   - Auto create virtual environment
::   - Real-time dependency installation logs
::   - Fast mode with marker file
:: ==========================================

cd /d "%~dp0"

:: Configuration
set "APP_NAME=AirForce API Auto Register"
set "PYTHON_VERSION=3.11.9"
set "PYTHON_DIR=%~dp0python"
set "VENV_DIR=%~dp0venv"
set "MARKER_FILE=%~dp0.env_ready"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"

:: Display header
echo.
echo ==========================================
echo    %APP_NAME% - Smart Launcher
echo ==========================================
echo.

:: Fast check - if marker file exists, skip full check
if exist "%MARKER_FILE%" (
    echo [*] Fast mode: Environment validated previously
    echo.
    goto :run_app
)

echo [*] First run or environment check needed...
echo.

:: ==========================================
:: Step 1: Check Python availability
:: ==========================================
echo [1/4] Checking Python environment...

set "PYTHON_EXE="
set "USE_EMBEDDED=0"

:: Priority 1: Check embedded Python
if exist "%PYTHON_DIR%\python.exe" (
    set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
    set "USE_EMBEDDED=1"
    echo      [+] Found embedded Python
    goto :python_found
)

:: Priority 2: Check system Python
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "SYSTEM_PY_VER=%%v"
    echo      [+] System Python found: !SYSTEM_PY_VER!
    
    :: Check version >= 3.8
    for /f "tokens=1,2 delims=." %%a in ("!SYSTEM_PY_VER!") do (
        if %%a geq 3 if %%b geq 8 (
            set "PYTHON_EXE=python"
            echo      [+] Version OK, using system Python
            goto :python_found
        )
    )
    echo      [-] Version too low, need Python 3.8+
)

:: No suitable Python found, download embedded version
echo      [-] No suitable Python found, downloading embedded Python...
goto :download_python

:python_found
echo      [OK] Python ready
echo.
goto :check_venv

:: ==========================================
:: Step 2: Download embedded Python
:: ==========================================
:download_python
echo.
echo [*] Downloading Python %PYTHON_VERSION% embedded...
echo     URL: %PYTHON_URL%
echo.

:: Create python directory
if not exist "%PYTHON_DIR%" mkdir "%PYTHON_DIR%"

:: Download using PowerShell (with progress)
set "PYTHON_ZIP=%PYTHON_DIR%\python.zip"
echo     Downloading...
powershell -Command "& {$ProgressPreference = 'Continue'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP%' -UseBasicParsing}"

if not exist "%PYTHON_ZIP%" (
    echo.
    echo [ERROR] Failed to download Python. Please check network connection.
    echo         You can manually install Python 3.8+ and try again.
    pause
    exit /b 1
)

:: Extract
echo     Extracting...
powershell -Command "& {Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force}"
del "%PYTHON_ZIP%" 2>nul

:: Enable pip support - modify python311._pth
set "PTH_FILE=%PYTHON_DIR%\python311._pth"
if exist "%PTH_FILE%" (
    echo python311.zip> "%PTH_FILE%"
    echo .>> "%PTH_FILE%"
    echo Lib\site-packages>> "%PTH_FILE%"
    echo import site>> "%PTH_FILE%"
)

:: Download and install pip
echo.
echo [*] Installing pip...
set "GET_PIP=%PYTHON_DIR%\get-pip.py"
powershell -Command "& {$ProgressPreference = 'Continue'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%GET_PIP_URL%' -OutFile '%GET_PIP%' -UseBasicParsing}"

"%PYTHON_DIR%\python.exe" "%GET_PIP%"
del "%GET_PIP%" 2>nul

set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "USE_EMBEDDED=1"
echo      [OK] Embedded Python installed
echo.

:: ==========================================
:: Step 3: Check/Create virtual environment
:: ==========================================
:check_venv
echo [2/4] Checking virtual environment...

:: For embedded Python, skip venv (use embedded directly with local packages)
if "%USE_EMBEDDED%"=="1" (
    echo      [+] Using embedded Python, skipping venv
    set "PIP_EXE=%PYTHON_DIR%\Scripts\pip.exe"
    if not exist "!PIP_EXE!" set "PIP_EXE=%PYTHON_DIR%\python.exe -m pip"
    echo.
    goto :check_deps
)

:: Check if venv exists
if exist "%VENV_DIR%\Scripts\python.exe" (
    echo      [OK] Virtual environment exists
    set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
    set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"
    echo.
    goto :check_deps
)

:: Create virtual environment
echo      [+] Creating virtual environment...
python -m venv "%VENV_DIR%"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)

set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"
echo      [OK] Virtual environment created
echo.

:: ==========================================
:: Step 4: Check/Install dependencies
:: ==========================================
:check_deps
echo [3/4] Checking dependencies...

:: Quick check - try importing required modules
"%PYTHON_EXE%" -c "import PyQt6; import httpx; import matplotlib" 2>nul
if %errorlevel% equ 0 (
    echo      [OK] All dependencies installed
    echo.
    goto :create_marker
)

:: Install missing dependencies (with FULL output for visibility)
echo.
echo      [-] Missing dependencies, installing now...
echo      ============================================
echo.

if "%USE_EMBEDDED%"=="1" (
    echo [pip] Installing PyQt6...
    "%PYTHON_EXE%" -m pip install PyQt6 --no-warn-script-location
    echo.
    echo [pip] Installing httpx...
    "%PYTHON_EXE%" -m pip install httpx --no-warn-script-location
    echo.
    echo [pip] Installing matplotlib...
    "%PYTHON_EXE%" -m pip install matplotlib --no-warn-script-location
) else (
    echo [pip] Installing from requirements.txt...
    echo.
    "%PIP_EXE%" install -r requirements.txt
)

echo.
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install some dependencies
    echo         Please check network connection and try again.
    pause
    exit /b 1
)
echo      ============================================
echo      [OK] Dependencies installed successfully!
echo.

:: ==========================================
:: Step 5: Create marker file
:: ==========================================
:create_marker
echo [4/4] Finalizing setup...

:: Create marker file with timestamp
echo Environment validated on %date% %time%> "%MARKER_FILE%"
echo Python: %PYTHON_EXE%>> "%MARKER_FILE%"
echo      [OK] Environment ready
echo.

:: ==========================================
:: Run application
:: ==========================================
:run_app
echo ==========================================
echo    Starting application...
echo ==========================================
echo.

:: Determine Python executable
if exist "%VENV_DIR%\Scripts\python.exe" (
    set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
) else if exist "%PYTHON_DIR%\python.exe" (
    set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
) else (
    set "PYTHON_EXE=python"
)

:: Run the application
"%PYTHON_EXE%" main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with error code %errorlevel%
    echo.
    :: Remove marker file so next run will recheck
    del "%MARKER_FILE%" 2>nul
    pause
)

endlocal
