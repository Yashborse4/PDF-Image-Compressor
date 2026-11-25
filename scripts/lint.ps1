# Lint + format-check with ruff. Non-zero exit if either fails.
# Usage:  .\scripts\lint.ps1
#
# This MIRRORS the CI gates exactly (.github/workflows/ci.yml):
#   ruff check .   +   ruff format --check .
# Both halves matter: a change can be lint-clean but format-dirty, which is a
# CI failure. Scope is the whole REPO (passed as an absolute path so the result
# never depends on the caller's working directory) — checking only `src tests`
# used to miss scripts/ and conftest, so local could pass while CI failed.
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $py) {
    Write-Error "Python executable not found in .venv or PATH"
    exit 1
}

# Check if ruff module is available
& $py -c "import ruff" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ruff is not installed in Python environment, skipping lint." -ForegroundColor Yellow
    exit 0
}

& $py -m ruff check $root
$check = $LASTEXITCODE

& $py -m ruff format --check $root
$fmt = $LASTEXITCODE

if ($check -ne 0 -or $fmt -ne 0) { exit 1 }
exit 0
