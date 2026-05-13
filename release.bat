@echo off
REM Cut a wheelcraft release.
REM
REM Usage:   release.bat <version>
REM Example: release.bat 0.1.1
REM
REM Steps:
REM   1. Verify working tree is clean
REM   2. Bump version in installer\wheelmap.iss
REM   3. Build wheelmap.exe (build.bat)
REM   4. Compile wheelcraft-setup.exe (ISCC)
REM   5. Commit version bump, tag v<version>, push
REM   6. Create GitHub release with installer attached
setlocal enabledelayedexpansion
cd /d "%~dp0"

if "%~1"=="" (
    echo Usage: release.bat ^<version^>
    echo Example: release.bat 0.1.1
    exit /b 1
)
set VERSION=%~1
set TAG=v%VERSION%

REM --- locate ISCC.exe ---
set ISCC=
where iscc.exe >nul 2>&1 && set ISCC=iscc.exe
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    echo ERROR: ISCC.exe not found. Install Inno Setup 6 (winget install JRSoftware.InnoSetup).
    exit /b 1
)

REM --- locate gh.exe ---
set GH=
where gh.exe >nul 2>&1 && set GH=gh.exe
if not defined GH if exist "%ProgramFiles%\GitHub CLI\gh.exe" set "GH=%ProgramFiles%\GitHub CLI\gh.exe"
if not defined GH (
    echo ERROR: gh.exe not found. Install GitHub CLI (winget install GitHub.cli).
    exit /b 1
)

REM --- check working tree is clean ---
git diff --quiet
if errorlevel 1 (echo ERROR: uncommitted changes in working tree. Commit or stash first. & exit /b 1)
git diff --staged --quiet
if errorlevel 1 (echo ERROR: staged changes present. Commit them first. & exit /b 1)

REM --- check tag doesn't already exist ---
git rev-parse %TAG% >nul 2>&1
if not errorlevel 1 (echo ERROR: tag %TAG% already exists. & exit /b 1)

echo.
echo === Releasing wheelcraft %TAG% ===
echo ISCC: %ISCC%
echo GH:   %GH%
echo.

REM --- bump version in installer .iss ---
powershell -NoProfile -Command "(Get-Content installer\wheelmap.iss) -replace '#define MyAppVersion \".*\"', '#define MyAppVersion \"%VERSION%\"' | Set-Content installer\wheelmap.iss -NoNewline:$false"
if errorlevel 1 (echo Version bump failed & exit /b 1)

REM --- build wheelmap.exe ---
call build.bat
if errorlevel 1 (echo Build failed & exit /b 1)

REM --- ensure ViGEmBus vendor binary is present ---
if not exist installer\vendor\ViGEmBus.exe (
    echo Fetching ViGEmBus vendor binary...
    call installer\fetch_vendor.bat
    if errorlevel 1 (echo Vendor fetch failed & exit /b 1)
)

REM --- compile installer ---
"%ISCC%" installer\wheelmap.iss
if errorlevel 1 (echo Installer compile failed & exit /b 1)

REM --- commit version bump if .iss actually changed ---
git diff --quiet installer\wheelmap.iss
if errorlevel 1 (
    git add installer\wheelmap.iss
    git commit -m "Bump version to %VERSION%"
)

REM --- tag and push ---
git tag %TAG%
git push origin main
if errorlevel 1 (echo Push failed & exit /b 1)
git push origin %TAG%
if errorlevel 1 (echo Tag push failed & exit /b 1)

REM --- generate release notes from commits since previous tag ---
set PREV_TAG=
for /f "delims=" %%t in ('git describe --tags --abbrev^=0 %TAG%^^ 2^>nul') do set PREV_TAG=%%t

if defined PREV_TAG (
    echo Changes since %PREV_TAG%:> .release-notes.tmp
    echo.>> .release-notes.tmp
    git log --pretty=format:"- %%s" %PREV_TAG%..%TAG% >> .release-notes.tmp
) else (
    echo Initial release > .release-notes.tmp
)

REM --- create GitHub release ---
"%GH%" release create %TAG% installer\Output\wheelcraft-setup.exe --title "wheelcraft %TAG%" --notes-file .release-notes.tmp
if errorlevel 1 (echo Release create failed & exit /b 1)

del .release-notes.tmp >nul 2>&1

echo.
echo SUCCESS: Released wheelcraft %TAG%
echo https://github.com/arvindsasikumar/wheelcraft/releases/tag/%TAG%
