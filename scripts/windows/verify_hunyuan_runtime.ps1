<#
.SYNOPSIS
    T060: PyTorch/CUDA/native-wheel compatibility checks for the ComfyUI +
    Hunyuan3D wrapper Python environment.

.DESCRIPTION
    Verifies CUDA is available, the intended GPU is selected, every wrapper
    import succeeds, and records an exact package freeze so a future run can
    detect an unintended (silent) dependency upgrade.

.PARAMETER PythonExe
    Path to the ComfyUI venv's Python interpreter.

.PARAMETER ExpectedDeviceName
    Substring expected in torch.cuda.get_device_name(0).

.PARAMETER LockFile
    Path to the frozen pip package list from the previous verified run. If
    present, the current freeze is diffed against it and any changed package
    version is reported as a potential silent upgrade. If absent, the current
    freeze becomes the new lock file (first run).

.PARAMETER OutFile
    Path to write the Markdown evidence report.
#>
param(
    [string]$PythonExe = "$HOME\ComfyUI\venv\Scripts\python.exe",
    [string]$ExpectedDeviceName = "RTX 5070",
    [string]$LockFile = "$PSScriptRoot\..\..\evidence\windows\hunyuan-runtime.lock.txt",
    [string]$OutFile = "$PSScriptRoot\..\..\evidence\windows\runtime-compatibility.md"
)

$ErrorActionPreference = "Stop"
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss K"
$operator = $env:USERNAME
$hostName = $env:COMPUTERNAME

# 1. CUDA availability + intended GPU selection
$cudaCheckScript = @"
import torch
print('torch_version=' + torch.__version__)
print('cuda_available=' + str(torch.cuda.is_available()))
if torch.cuda.is_available():
    print('device_name=' + torch.cuda.get_device_name(0))
    print('device_count=' + str(torch.cuda.device_count()))
    x = torch.rand(4, 4, device='cuda:0')
    y = (x @ x).sum().item()
    print('cuda_matmul_smoke=ok value=' + str(y))
else:
    print('device_name=NONE')
"@
$cudaCheckOut = & $PythonExe -c $cudaCheckScript 2>&1 | Out-String
$cudaOk = ($LASTEXITCODE -eq 0) -and ($cudaCheckOut -match "cuda_available=True") -and ($cudaCheckOut -match [regex]::Escape($ExpectedDeviceName)) -and ($cudaCheckOut -match "cuda_matmul_smoke=ok")

# 2. Hunyuan3D wrapper import checks (requirements.txt modules)
$importCheckScript = @"
import importlib
modules = ['trimesh', 'diffusers', 'accelerate', 'huggingface_hub', 'einops', 'cv2', 'xatlas', 'pymeshlab', 'pygltflib', 'sklearn', 'skimage', 'pybind11']
failures = []
for m in modules:
    try:
        importlib.import_module(m)
        print('import_ok=' + m)
    except Exception as e:
        failures.append(m)
        print('import_fail=' + m + ' error=' + str(e))
print('all_imports_ok=' + str(len(failures) == 0))
"@
$importCheckOut = & $PythonExe -c $importCheckScript 2>&1 | Out-String
$importsOk = ($LASTEXITCODE -eq 0) -and ($importCheckOut -match "all_imports_ok=True")

# 3. Freeze current packages and diff against the lock file (silent-upgrade gate)
$currentFreeze = & $PythonExe -m pip freeze 2>&1
$currentFreezeText = $currentFreeze -join "`n"

$upgradeReport = @()
$lockExists = Test-Path $LockFile
if ($lockExists) {
    $previousFreeze = Get-Content $LockFile
    $prevMap = @{}
    foreach ($line in $previousFreeze) {
        if ($line -match "^([A-Za-z0-9_.\-]+)==(.+)$") { $prevMap[$matches[1].ToLower()] = $matches[2] }
    }
    $currMap = @{}
    foreach ($line in $currentFreeze) {
        if ($line -match "^([A-Za-z0-9_.\-]+)==(.+)$") { $currMap[$matches[1].ToLower()] = $matches[2] }
    }
    foreach ($pkg in $prevMap.Keys) {
        if ($currMap.ContainsKey($pkg) -and $currMap[$pkg] -ne $prevMap[$pkg]) {
            $upgradeReport += "CHANGED: $pkg $($prevMap[$pkg]) -> $($currMap[$pkg])"
        } elseif (-not $currMap.ContainsKey($pkg)) {
            $upgradeReport += "REMOVED: $pkg $($prevMap[$pkg])"
        }
    }
    $noSilentUpgrade = ($upgradeReport.Count -eq 0)
} else {
    $noSilentUpgrade = $true
    $upgradeReport += "No prior lock file found at $LockFile - this run establishes the baseline lock."
    $outDir = Split-Path -Parent $LockFile
    if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
    $currentFreezeText | Out-File -FilePath $LockFile -Encoding utf8
}

$overallPass = $cudaOk -and $importsOk -and $noSilentUpgrade

$report = @"
# Hunyuan3D Runtime Compatibility Evidence (T060)

**Gate**: T060 - PyTorch/CUDA/native-wheel compatibility checks
**Date/time and operator**: $timestamp, $operator
**Host/environment**: $hostName (Windows), ComfyUI venv at $PythonExe

## 1. CUDA availability and intended GPU selection

Expected device substring: ``$ExpectedDeviceName``

``````text
$cudaCheckOut
``````

Result: $(if ($cudaOk) { "PASS" } else { "FAIL" })

## 2. Hunyuan3D wrapper dependency imports

``````text
$importCheckOut
``````

Result: $(if ($importsOk) { "PASS" } else { "FAIL" })

## 3. Silent-upgrade gate (pip freeze diff against lock file)

Lock file: ``$LockFile`` ($(if ($lockExists) { "existing baseline compared" } else { "created this run" }))

``````text
$($upgradeReport -join "`n")
``````

Result: $(if ($noSilentUpgrade) { "PASS" } else { "FAIL - unexpected dependency change detected" })

## Verdict

$(if ($overallPass) { "PASS - CUDA available on the intended GPU, all wrapper imports succeeded, no silent dependency upgrade." } else { "BLOCKED - see failing section(s) above." })
"@

$outDir2 = Split-Path -Parent $OutFile
if (-not (Test-Path $outDir2)) { New-Item -ItemType Directory -Path $outDir2 -Force | Out-Null }
$report | Out-File -FilePath $OutFile -Encoding utf8

Write-Output "Evidence written to $OutFile"
Write-Output $report
