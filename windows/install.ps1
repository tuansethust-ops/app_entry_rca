param(
    [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $Python = "py"
    & py -3 -c "import sys; assert sys.version_info >= (3,10), sys.version" | Out-Null
    & py -3 -m venv $VenvPath
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Python = "python"
    & python -c "import sys; assert sys.version_info >= (3,10), sys.version" | Out-Null
    & python -m venv $VenvPath
} else {
    throw "Python 3.10+ was not found. Install Python and enable Add Python to PATH."
}

$VenvPython = Join-Path $ProjectRoot "$VenvPath\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt
& $VenvPython -m pip install -e .
& $VenvPython scripts\doctor.py

Write-Host ""
Write-Host "app_entry_rca installation completed." -ForegroundColor Green
Write-Host "Run: .\windows\run.ps1 -Dut <DUT.perfetto> -Ref <REF.perfetto> -Out <output>"
