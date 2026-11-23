# DocuTools Automated Build Script (Windows)
param(
    [switch]$BuildInstaller,
    [switch]$SkipZip
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Building DocuTools Standalone Executable" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 0. Check for running instances of DocuTools
$running = @(Get-Process -Name "DocuTools" -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) {
    Write-Warning "DocuTools is running (PID: $($running.Id -join ', ')). Stopping..."
    $running | Stop-Process -Force
    Start-Sleep -Seconds 1
}

# 1. Clean previous build artifacts
if (Test-Path "dist\DocuTools") {
    Write-Host "Cleaning dist\DocuTools..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "dist\DocuTools"
}
if (Test-Path "build") {
    Write-Host "Cleaning build directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "build"
}

# 2. Run PyInstaller with DocuTools.spec
Write-Host "Running PyInstaller (DocuTools.spec)..." -ForegroundColor Yellow
python -m PyInstaller DocuTools.spec --noconfirm --clean

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed!"
    exit 1
}

$exePath = "dist\DocuTools\DocuTools.exe"
if (-not (Test-Path $exePath)) {
    Write-Error "Expected executable not found at $exePath"
    exit 1
}

Write-Host "Standalone build succeeded at $exePath" -ForegroundColor Green

# 3. Create release distribution archive (.zip)
if (-not $SkipZip) {
    Write-Host "Packaging release zip archive..." -ForegroundColor Yellow
    $zipPath = "dist\DocuTools-v1.0.0-windows-x64.zip"
    if (Test-Path $zipPath) {
        Remove-Item -Force $zipPath
    }
    Compress-Archive -Path "dist\DocuTools\*" -DestinationPath $zipPath -Force
    Write-Host "Archive created at $zipPath" -ForegroundColor Green

    # Mirror to packages folder if it exists
    if (Test-Path "packages") {
        Copy-Item -Path $zipPath -Destination "packages\DocuTools-v1.0.0-windows-x64.zip" -Force
        Write-Host "Mirrored archive to packages\DocuTools-v1.0.0-windows-x64.zip" -ForegroundColor Green
    }
}

# 4. Optional Inno Setup compilation
if ($BuildInstaller) {
    $InnoCompiler = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if (Test-Path $InnoCompiler) {
        Write-Host "Compiling Inno Setup Windows Installer..." -ForegroundColor Yellow
        & $InnoCompiler "installer\docutools.iss"
        Write-Host "Installer compiled at dist\installer\" -ForegroundColor Green
    } else {
        Write-Warning "Inno Setup compiler (ISCC.exe) not found at default location. Skipping installer compilation."
    }
}
