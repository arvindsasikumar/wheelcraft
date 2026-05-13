@echo off
REM Downloads the ViGEmBus installer to installer\vendor\ for bundling.
setlocal
cd /d "%~dp0"

if not exist vendor mkdir vendor

if exist vendor\ViGEmBus.exe (
    echo Already present: vendor\ViGEmBus.exe
    exit /b 0
)

echo Downloading ViGEmBus v1.22.0...
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/nefarius/ViGEmBus/releases/download/v1.22.0/ViGEmBus_1.22.0_x64_x86_arm64.exe' -OutFile 'vendor\ViGEmBus.exe'"

if errorlevel 1 (
    echo Download failed.
    exit /b 1
)

echo Done.
