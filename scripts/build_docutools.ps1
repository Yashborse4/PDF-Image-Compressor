# DocuTools Automated Build Script (Windows)
param(
    [switch]$BuildInstaller
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Building DocuTools Standalone Executable" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Clean previous build artifacts
if (Test-Path "dist\DocuTools") {
    Remove-Item -Recurse -Force "dist\DocuTools"
}
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}

# 2. Run PyInstaller
Write-Host "Running PyInstaller..." -ForegroundColor Yellow
python -m PyInstaller `
    --name "DocuTools" `
    --windowed `
    --onedir `
    --clean `
    --noconfirm `
    --icon "docutools/assets/icon.ico" `
    --add-data "docutools/assets;docutools/assets" `
    --add-data "docutools/ui/styles.py;docutools/ui" `
    --exclude-module scipy `
    --exclude-module pandas `
    --exclude-module sklearn `
    --exclude-module nltk `
    --exclude-module flask `
    --exclude-module matplotlib `
    --exclude-module openpyxl `
    run.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed!"
    exit 1
}

Write-Host "Standalone build succeeded at dist\DocuTools\DocuTools.exe" -ForegroundColor Green

# 3. Optional Inno Setup compilation
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
