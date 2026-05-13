# Cut a wheelcraft release.
# Usage: .\release.ps1 -Version 0.1.2
# (or invoke via release.bat which forwards to here)

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Version
)

$ErrorActionPreference = "Stop"
$Tag = "v$Version"

Set-Location (Split-Path -Parent $PSCommandPath)

function Resolve-Tool {
    param([string]$Name, [string[]]$Candidates)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($candidate in $Candidates) {
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}

$Iscc = Resolve-Tool "iscc.exe" @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
if (-not $Iscc) { throw "ISCC.exe not found. Install Inno Setup (winget install JRSoftware.InnoSetup)." }

$Gh = Resolve-Tool "gh.exe" @("$env:ProgramFiles\GitHub CLI\gh.exe")
if (-not $Gh) { throw "gh.exe not found. Install GitHub CLI (winget install GitHub.cli)." }

git diff --quiet
if ($LASTEXITCODE -ne 0) { throw "Uncommitted changes. Commit or stash first." }
git diff --staged --quiet
if ($LASTEXITCODE -ne 0) { throw "Staged changes. Commit them first." }

# Check tag doesn't already exist. git tag -l prints the matching tag name
# (or nothing) and never errors, so it's safer than git rev-parse for this.
$existing = git tag -l $Tag
if ($existing) { throw "Tag $Tag already exists." }

Write-Host ""
Write-Host "=== Releasing wheelcraft $Tag ==="
Write-Host "ISCC: $Iscc"
Write-Host "GH:   $Gh"
Write-Host ""

# Bump version in installer .iss
(Get-Content installer\wheelmap.iss) -replace '#define MyAppVersion ".*"', "#define MyAppVersion `"$Version`"" | Set-Content installer\wheelmap.iss

# Build wheelmap.exe bundle
& cmd.exe /c ".\build.bat"
if ($LASTEXITCODE -ne 0) { throw "Build failed." }

# Fetch ViGEmBus vendor binary if missing
if (-not (Test-Path "installer\vendor\ViGEmBus.exe")) {
    Write-Host "Fetching ViGEmBus vendor binary..."
    & cmd.exe /c ".\installer\fetch_vendor.bat"
    if ($LASTEXITCODE -ne 0) { throw "Vendor fetch failed." }
}

# Compile installer
& $Iscc "installer\wheelmap.iss"
if ($LASTEXITCODE -ne 0) { throw "Installer compile failed." }

# Commit version bump if .iss actually changed
git diff --quiet installer\wheelmap.iss
if ($LASTEXITCODE -ne 0) {
    git add installer\wheelmap.iss
    git commit -m "Bump version to $Version"
    if ($LASTEXITCODE -ne 0) { throw "Version-bump commit failed." }
}

# Tag and push
git tag $Tag
git push origin main
if ($LASTEXITCODE -ne 0) { throw "Push failed." }
git push origin $Tag
if ($LASTEXITCODE -ne 0) { throw "Tag push failed." }

# Generate release notes from commits since the previous tag.
# git describe writes to stderr when no tags exist; isolate in a sub-scope.
$prevTag = $null
& {
    $ErrorActionPreference = "Continue"
    $prev = git describe --tags --abbrev=0 "$Tag^" 2>$null
    if ($LASTEXITCODE -eq 0 -and $prev) { $script:prevTag = $prev.Trim() }
}

if ($prevTag) {
    $log = (git log --pretty=format:"- %s" "$prevTag..$Tag") -join "`n"
    $notes = "Changes since $prevTag`n`n$log"
} else {
    $notes = "Initial release"
}

$notesFile = New-TemporaryFile
$notes | Set-Content -Path $notesFile.FullName -NoNewline

try {
    & $Gh release create $Tag "installer\Output\wheelcraft-setup.exe" --title "wheelcraft $Tag" --notes-file $notesFile.FullName
    if ($LASTEXITCODE -ne 0) { throw "Release create failed." }
} finally {
    Remove-Item $notesFile.FullName -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "SUCCESS: Released wheelcraft $Tag" -ForegroundColor Green
Write-Host "https://github.com/arvindsasikumar/wheelcraft/releases/tag/$Tag"
