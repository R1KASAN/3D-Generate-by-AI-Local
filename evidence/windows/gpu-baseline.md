# Windows GPU/Runtime Baseline Evidence (T058)

**Gate**: T058 - hardware/runtime inventory capture
**Date/time and operator**: 2026-09-03 17:23:46 +07:00, MetaHosP
**Host/environment**: LAPTOP-9PI3K9F7 (Windows), target production server for Phase 7-12

## nvidia-smi (summary)

```text
NVIDIA GeForce RTX 5070 Laptop GPU, 592.15, 8151 MiB, 0 MiB
```

## nvidia-smi (full)

```text
Thu Sep  3 17:23:47 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 592.15                 Driver Version: 592.15         CUDA Version: 13.1     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                  Driver-Model | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 5070 ...  WDDM  |   00000000:01:00.0 Off |                  N/A |
| N/A   48C    P0             12W /   80W |       0MiB /   8151MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|  No running processes found                                                             |
+-----------------------------------------------------------------------------------------+
```

## Windows version

```text
Caption: Microsoft Windows 11 Home Single Language
Version: 10.0.26200
BuildNumber: 26200
OSArchitecture: 64-bit
```

## Python version

```text
Python 3.12.10
```

## Embedded SQLite version

```text
3.49.1
```

## nvcc / CUDA Toolkit version

```text
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2025 NVIDIA Corporation
Built on Wed_Jan_15_19:38:46_Pacific_Standard_Time_2025
Cuda compilation tools, release 12.8, V12.8.61
Build cuda_12.8.r12.8/compiler.35404655_0
```

## PyTorch / CUDA availability

Interpreter: `C:\Users\MetaHosP\ComfyUI\venv\Scripts\python.exe`

```text
torch_version=2.11.0+cu128
cuda_available=True
device_name=NVIDIA GeForce RTX 5070 Laptop GPU
total_memory_bytes=8546484224
```

## Verdict

PASS - all required baseline facts captured.
