# DocuTools Automated Build Script (Windows)
param(
    [switch]$BuildInstaller,
    [switch]$BuildMsi,
    [switch]$SkipZip
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Building DocuTools Standalone Executable" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 0. Check for running instances of DocuTools
$running = @(Get-Process -Name "DocuTools", "DocuTools-Portable" -ErrorAction SilentlyContinue)
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
if (Test-Path "dist\DocuTools-Portable.exe") {
    Remove-Item -Force "dist\DocuTools-Portable.exe"
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

Write-Host "Standalone onedir build succeeded at $exePath" -ForegroundColor Green

$portableExe = "dist\DocuTools-Portable.exe"
if (Test-Path $portableExe) {
    $portableMB = [math]::Round((Get-Item $portableExe).Length / 1MB, 2)
    Write-Host "Portable single-file executable built at $portableExe ($portableMB MB)" -ForegroundColor Green
}

# 3. Create release distribution archive (.zip)
if (-not $SkipZip) {
    Write-Host "Packaging release zip archive..." -ForegroundColor Yellow
    $zipPath = "dist\DocuTools-v1.0.0-windows-x64.zip"
    if (Test-Path $zipPath) {
        Remove-Item -Force $zipPath
    }
    # Enclose dist\DocuTools folder as root to prevent incomplete partial extractions
    Compress-Archive -Path "dist\DocuTools" -DestinationPath $zipPath -Force
    Write-Host "Archive created at $zipPath" -ForegroundColor Green

    # Mirror to packages folder if it exists
    if (Test-Path "packages") {
        Copy-Item -Path $zipPath -Destination "packages\DocuTools-v1.0.0-windows-x64.zip" -Force
        Write-Host "Mirrored archive to packages\DocuTools-v1.0.0-windows-x64.zip" -ForegroundColor Green
    }
}

# 4. Inno Setup compilation (Windows EXE Installer & Uninstaller)
if ($BuildInstaller) {
    $innoCandidates = @(
        (Get-Command iscc.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    ) | Where-Object { $_ -and (Test-Path $_) }

    $innoCompiler = $innoCandidates | Select-Object -First 1

    if ($innoCompiler) {
        Write-Host "Compiling Inno Setup Windows Installer ($innoCompiler)..." -ForegroundColor Yellow
        New-Item -ItemType Directory -Force -Path "dist\installer" | Out-Null
        & $innoCompiler "installer\docutools.iss"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Inno Setup Installer compiled at dist\installer\" -ForegroundColor Green
        } else {
            Write-Error "Inno Setup compilation failed!"
        }
    } else {
        Write-Warning "Inno Setup compiler (ISCC.exe) not found. Skipping EXE installer compilation."
    }
}

# 5. WiX MSI compilation (Windows MSI Package)
if ($BuildMsi -or $BuildInstaller) {
    $msiScript = "scripts\build_msi.ps1"
    if (Test-Path $msiScript) {
        Write-Host "Compiling WiX Windows MSI Installer..." -ForegroundColor Yellow
        & (Join-Path $PSScriptRoot "build_msi.ps1")
        if ($LASTEXITCODE -eq 0) {
            Write-Host "MSI Installer compiled at dist\installer\" -ForegroundColor Green
        } else {
            Write-Error "WiX MSI compilation failed!"
        }
    }
}
