@echo off
REM Build a standalone wheelmap distribution using PyInstaller.
REM Output: dist\wheelmap\  (folder with wheelmap.exe + bundled deps)
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pyinstaller.exe" (
    echo PyInstaller not found in .venv. Installing...
    .venv\Scripts\python.exe -m pip install pyinstaller || (echo Install failed & exit /b 1)
)

echo Cleaning previous build...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
if exist wheelmap.spec del wheelmap.spec

REM Locate ffi.dll from the base Python install (Anaconda calls it ffi.dll,
REM not libffi-8.dll, and PyInstaller's auto-detection misses it).
for /f "delims=" %%i in ('.venv\Scripts\python.exe -c "import sys, os; p = os.path.join(sys.base_prefix, 'Library', 'bin', 'ffi.dll'); print(p if os.path.exists(p) else '')"') do set FFI_DLL=%%i

set EXTRA=
if defined FFI_DLL (
    echo Found ffi.dll: %FFI_DLL%
    set EXTRA=--add-binary "%FFI_DLL%;."
)

echo Running PyInstaller...
.venv\Scripts\pyinstaller.exe ^
    --name wheelmap ^
    --onedir ^
    --windowed ^
    --add-data "static;static" ^
    --collect-all vgamepad ^
    %EXTRA% ^
    --noconfirm ^
    server.py

if errorlevel 1 (
    echo.
    echo Build FAILED.
    exit /b 1
)

echo.
echo Build OK.
echo Output: %~dp0dist\wheelmap\wheelmap.exe
echo Try it:  dist\wheelmap\wheelmap.exe
