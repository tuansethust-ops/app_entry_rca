param(
    [Parameter(Mandatory=$true)][string]$Dut,
    [Parameter(Mandatory=$true)][string]$Ref,
    [string]$Out = "app_entry_rca_out",
    [string]$Target,
    [int]$LaunchIndex = 0,
    [ValidateSet("auto", "perfetto", "systrace")][string]$Backend = "auto",
    [string]$TraceProcessor,
    [string]$Traceconv,
    [switch]$IncludeBetterFinal,
    [switch]$IncludeCorrelationCandidates,
    [switch]$StrictValidation,
    [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot "$VenvPath\Scripts\python.exe"
if (Test-Path $VenvPython) { $Python = $VenvPython }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $Python = "py" }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $Python = "python" }
else { throw "Python was not found. Run .\windows\install.ps1 first." }

$ArgsList = @()
if ($Python -eq "py") { $ArgsList += "-3" }
$ArgsList += @("scripts\run_app_entry_rca.py", "--dut", $Dut, "--ref", $Ref, "--out", $Out, "--launch-index", "$LaunchIndex", "--backend", $Backend)
$DefaultTraceProcessor = Join-Path $ProjectRoot "tools\perfetto\trace_processor_shell.exe"
if (-not $TraceProcessor -and (Test-Path $DefaultTraceProcessor)) { $TraceProcessor = $DefaultTraceProcessor }
if ($Target) { $ArgsList += @("--target", $Target) }
if ($TraceProcessor) { $ArgsList += @("--trace-processor", $TraceProcessor) }
if ($Traceconv) { $ArgsList += @("--traceconv", $Traceconv) }
if ($IncludeBetterFinal) { $ArgsList += "--include-better-final" }
if ($IncludeCorrelationCandidates) { $ArgsList += "--include-correlation-candidates" }
if ($StrictValidation) { $ArgsList += "--strict-validation" }

& $Python @ArgsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Workflow completed." -ForegroundColor Green
foreach ($name in @("final_leaf.json", "final_leaves.json", "all_leaf_nodes.json", "report.md", "provenance.json")) {
    $path = Join-Path $Out $name
    if (Test-Path $path) { Write-Host "$name`: $path" }
}
