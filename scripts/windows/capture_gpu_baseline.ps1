<#
.SYNOPSIS
    Captures GPU/runtime hardware baseline evidence for T058 (Phase 7).

.DESCRIPTION
    Records GPU model, driver version, VRAM, Windows version, Python version,
    PyTorch version/CUDA availability, and the embedded SQLite version on the
    target Windows NVIDIA server. Writes a Markdown evidence report.

.PARAMETER TorchPython
    Path to a Python interpreter with torch installed (defaults to the
    ComfyUI venv's interpreter, since apps/api's environment does not
    depend on torch).

.PARAMETER OutFile
    Path to write the Markdown evidence report.
#>
param(
    [string]$TorchPython = "$HOME\ComfyUI\venv\Scripts\python.exe",
    [string]$OutFile = "$PSScriptRoot\..\..\evidence\windows\gpu-baseline.md"
)

$ErrorActionPreference = "Stop"

# Refresh PATH from the registry so recently installed tools (py launcher,
# nvcc, etc.) are visible even in a session that predates their install.
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

function Get-CommandOutput {
    param([string]$Description, [scriptblock]$Command)
    try {
        $output = & $Command 2>&1 | Out-String
        return [pscustomobject]@{ Description = $Description; Output = $output.Trim(); Ok = $true }
    } catch {
        return [pscustomobject]@{ Description = $Description; Output = $_.Exception.Message; Ok = $false }
    }
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss K"
$operator = $env:USERNAME
$hostName = $env:COMPUTERNAME

$nvidiaSmi = Get-CommandOutput "nvidia-smi" { nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used --format=csv,noheader }
$nvidiaSmiFull = Get-CommandOutput "nvidia-smi (full)" { nvidia-smi }
$osInfo = Get-CommandOutput "Windows version" {
    $ci = Get-CimInstance Win32_OperatingSystem
    "Caption: $($ci.Caption)`nVersion: $($ci.Version)`nBuildNumber: $($ci.BuildNumber)`nOSArchitecture: $($ci.OSArchitecture)"
}
$pythonVersion = Get-CommandOutput "System Python (py -3.12)" { py -3.12 --version }
$sqliteVersion = Get-CommandOutput "Embedded SQLite version (py -3.12)" { py -3.12 -c "import sqlite3; print(sqlite3.sqlite_version)" }

$torchExists = Test-Path $TorchPython
if ($torchExists) {
    $torchInfo = Get-CommandOutput "PyTorch / CUDA (ComfyUI venv)" {
        & $TorchPython -c "import torch; print('torch_version=' + torch.__version__); print('cuda_available=' + str(torch.cuda.is_available())); print('device_name=' + (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')); print('total_memory_bytes=' + str(torch.cuda.get_device_properties(0).total_memory if torch.cuda.is_available() else 0))"
    }
} else {
    $torchInfo = [pscustomobject]@{ Description = "PyTorch / CUDA (ComfyUI venv)"; Output = "Interpreter not found at $TorchPython"; Ok = $false }
}

$nvccVersion = Get-CommandOutput "nvcc (CUDA Toolkit)" { nvcc --version }

$report = @"
# Windows GPU/Runtime Baseline Evidence (T058)

**Gate**: T058 - hardware/runtime inventory capture
**Date/time and operator**: $timestamp, $operator
**Host/environment**: $hostName (Windows), target production server for Phase 7-12

## nvidia-smi (summary)

``````text
$($nvidiaSmi.Output)
``````

## nvidia-smi (full)

``````text
$($nvidiaSmiFull.Output)
``````

## Windows version

``````text
$($osInfo.Output)
``````

## Python version

``````text
$($pythonVersion.Output)
``````

## Embedded SQLite version

``````text
$($sqliteVersion.Output)
``````

## nvcc / CUDA Toolkit version

``````text
$($nvccVersion.Output)
``````

## PyTorch / CUDA availability

Interpreter: ``$TorchPython``

``````text
$($torchInfo.Output)
``````

## Verdict

$(if ($nvidiaSmi.Ok -and $osInfo.Ok -and $pythonVersion.Ok -and $sqliteVersion.Ok -and $torchInfo.Ok) { "PASS - all required baseline facts captured." } else { "BLOCKED - one or more captures failed; see sections above." })
"@

$outDir = Split-Path -Parent $OutFile
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
$report | Out-File -FilePath $OutFile -Encoding utf8

Write-Output "Evidence written to $OutFile"
Write-Output $report
