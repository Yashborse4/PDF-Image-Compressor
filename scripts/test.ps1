# Run the test suite. Extra args are passed through to pytest.
# Usage:  .\scripts\test.ps1  [pytest args...]
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
& $py -m pytest @args
exit $LASTEXITCODE
