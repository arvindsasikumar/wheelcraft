@echo off
REM Cut a wheelcraft release. Wraps release.ps1.
REM Usage: release.bat <version>     Example: release.bat 0.1.2
if "%~1"=="" (
    echo Usage: release.bat ^<version^>
    echo Example: release.bat 0.1.2
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0release.ps1" -Version %1
