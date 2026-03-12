@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "TARGET=%SCRIPT_DIR%UpdateYarnCyclePlanner.py"

if not exist "%TARGET%" (
  echo ERROR: Cannot find UpdateYarnCyclePlanner.py in %SCRIPT_DIR%
  goto :error_pause
)

where py >nul 2>&1
if %errorlevel%==0 (
  py -3.11-32 -c "import struct,sys; sys.exit(0 if struct.calcsize('P')*8==32 else 1)" >nul 2>&1
  if %errorlevel%==0 (
    echo Running with Python Launcher profile: 3.11-32
    py -3.11-32 "%TARGET%"
    if errorlevel 1 goto :error_pause
    exit /b 0
  )
)

if exist "C:\Python311-32\python.exe" (
  "C:\Python311-32\python.exe" -c "import struct,sys; sys.exit(0 if struct.calcsize('P')*8==32 else 1)" >nul 2>&1
  if %errorlevel%==0 (
    echo Running with C:\Python311-32\python.exe
    "C:\Python311-32\python.exe" "%TARGET%"
    if errorlevel 1 goto :error_pause
    exit /b 0
  )
)

echo ERROR: No 32-bit Python interpreter found.
echo Install 32-bit Python and run this launcher again.
echo Example: py -3.11-32 "%TARGET%"
goto :error_pause

:error_pause
echo.
echo Process failed with exit code %errorlevel%.
pause
exit /b 1
