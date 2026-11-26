# Build the standalone bundle and distribution archive with PyInstaller.
# Usage:  .\scripts\package.ps1
$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "build_docutools.ps1") @args
exit $LASTEXITCODE
