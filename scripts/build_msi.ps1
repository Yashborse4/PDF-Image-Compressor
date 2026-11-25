# Build Windows MSI Installer using WiX Toolset
# Usage: .\scripts\build_msi.ps1

$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Push-Location $root
try {

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Building DocuTools Windows MSI Package " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Ensure standalone binaries are built
$exePath = Join-Path $root "dist\DocuTools\DocuTools.exe"
if (-not (Test-Path $exePath)) {
    Write-Host "DocuTools binaries not found. Invoking build_docutools.ps1..." -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot "build_docutools.ps1") -SkipZip
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

# 2. Ensure WiX toolset exists
$wixDir = Join-Path $root "tools\wix"
$candle = Join-Path $wixDir "candle.exe"
$light = Join-Path $wixDir "light.exe"
$heat = Join-Path $wixDir "heat.exe"

if (-not (Test-Path $candle)) {
    Write-Host "WiX tools not found in tools\wix. Downloading WiX 3.11 binaries..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path $wixDir | Out-Null
    $wixUrl = "https://github.com/wixtoolset/wix3/releases/download/wix3112rtm/wix311-binaries.zip"
    $wixZip = Join-Path $wixDir "wix.zip"
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $wixUrl -OutFile $wixZip
    Expand-Archive -Path $wixZip -DestinationPath $wixDir -Force
    Remove-Item $wixZip -Force
}

$installerDir = Join-Path $root "installer"
$distInstallerDir = Join-Path $root "dist\installer"
New-Item -ItemType Directory -Force -Path $distInstallerDir | Out-Null

$harvestedWxs = Join-Path $installerDir "DocuToolsFiles.wxs"
$productWxs = Join-Path $installerDir "Product.wxs"
$msiOut = Join-Path $distInstallerDir "DocuTools-v1.0.0-windows-x64.msi"

# 3. Harvest components from dist\DocuTools
Write-Host "Harvesting application binaries..." -ForegroundColor Yellow
$sourceDir = Join-Path $root "dist\DocuTools"
& $heat dir $sourceDir -cg DocuToolsComponents -dr INSTALLFOLDER -scom -sreg -sfrag -srd -ag -var "var.SourceDir" -out $harvestedWxs
if ($LASTEXITCODE -ne 0) {
    Write-Error "heat.exe harvesting failed"
    exit $LASTEXITCODE
}

# 4. Compile WiX sources
Write-Host "Compiling WiX source files (candle.exe)..." -ForegroundColor Yellow
& $candle -nologo -arch x64 "-dSourceDir=$sourceDir" -out "$distInstallerDir\\" $productWxs $harvestedWxs
if ($LASTEXITCODE -ne 0) {
    Write-Error "candle.exe compilation failed"
    exit $LASTEXITCODE
}

# 5. Link MSI package
Write-Host "Linking Windows MSI installer (light.exe)..." -ForegroundColor Yellow
$prodObj = Join-Path $distInstallerDir "Product.wixobj"
$filesObj = Join-Path $distInstallerDir "DocuToolsFiles.wixobj"
& $light -nologo -ext WixUIExtension -out $msiOut $prodObj $filesObj -sval
if ($LASTEXITCODE -ne 0) {
    Write-Error "light.exe linking failed"
    exit $LASTEXITCODE
}

if (Test-Path $msiOut) {
    $sizeMB = [math]::Round((Get-Item $msiOut).Length / 1MB, 2)
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " Successfully built MSI Installer!      " -ForegroundColor Green
    Write-Host " Path: $msiOut ($sizeMB MB)             " -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Error "MSI output was not found at $msiOut"
    exit 1
}
} finally {
    Pop-Location
}
