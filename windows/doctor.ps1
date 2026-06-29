param(
    [string]$Dut,
    [string]$Ref,
    [ValidateSet("auto", "perfetto", "systrace")][string]$Backend = "auto",
    [string]$TraceProcessor,
    [string]$Traceconv,
    [string]$VenvPath = ".venv"
)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$Python = Join-Path $ProjectRoot "$VenvPath\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$argsList = @("scripts\doctor.py", "--backend", $Backend)
if ($Dut) { $argsList += @("--dut", $Dut) }
if ($Ref) { $argsList += @("--ref", $Ref) }
if ($TraceProcessor) { $argsList += @("--trace-processor", $TraceProcessor) }
if ($Traceconv) { $argsList += @("--traceconv", $Traceconv) }
& $Python @argsList
exit $LASTEXITCODE
