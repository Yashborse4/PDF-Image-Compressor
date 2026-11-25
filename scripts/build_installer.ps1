# Build the Windows installer (Inno Setup) from the already-built onedir bundle.
# Usage:  .\scripts\build_installer.ps1 [-InnoSetupPath <path to ISCC.exe>]
param(
    [string]$InnoSetupPath
)
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
$iss = Join-Path $root "installer\docutools.iss"
$bundleExe = Join-Path $root "dist\DocuTools\DocuTools.exe"

if (-not (Test-Path $iss)) {
    Write-Error "Installer script not found: $iss"
    exit 1
}
if (-not (Test-Path $bundleExe)) {
    Write-Host "Onedir bundle not found ($bundleExe). Running build_docutools.ps1 first..." -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot "build_docutools.ps1") -SkipZip
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

# --- Version: single source of truth = pyproject.toml [project].version ---
. "$PSScriptRoot\_version.ps1"
$version = Get-AppVersion
Write-Host "Version (from pyproject.toml): $version"

# --- Locate ISCC.exe (the Inno Setup compiler) ---
$iscc = $null
if ($InnoSetupPath) {
    if (Test-Path $InnoSetupPath) {
        $iscc = $InnoSetupPath
    } else {
        Write-Error "ISCC.exe not found at -InnoSetupPath: $InnoSetupPath"
        exit 1
    }
} else {
    $candidates = @(
        (Get-Command iscc.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { $iscc = $c; break }
    }
}
if (-not $iscc) {
    Write-Error "Inno Setup compiler (ISCC.exe) not found. Install it with:  winget install -e --id JRSoftware.InnoSetup   (or pass -InnoSetupPath)."
    exit 1
}
Write-Host "Using ISCC: $iscc"

# --- Compile the installer ---
New-Item -ItemType Directory -Force -Path (Join-Path $root "dist\installer") | Out-Null
& $iscc "/DMyAppVersion=$version" $iss
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$setup = Join-Path $root "dist\installer\DocuTools-Setup-v$version.exe"
if (-not (Test-Path $setup)) {
    Write-Error "ISCC reported success but the setup exe was not found at $setup"
    exit 1
}
$setupMB = [math]::Round((Get-Item $setup).Length / 1MB, 2)
Write-Host "========================================" -ForegroundColor Green
Write-Host " Inno Setup Installer successfully built!" -ForegroundColor Green
Write-Host " Path: $setup ($setupMB MB)             " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
exit 0
