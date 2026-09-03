# Hunyuan3D Runtime Compatibility Evidence (T060)

**Gate**: T060 - PyTorch/CUDA/native-wheel compatibility checks
**Date/time and operator**: 2026-09-03 17:26:39 +07:00, MetaHosP
**Host/environment**: LAPTOP-9PI3K9F7 (Windows), ComfyUI venv at C:\Users\MetaHosP\ComfyUI\venv\Scripts\python.exe

## 1. CUDA availability and intended GPU selection

Expected device substring: `RTX 5070`

```text
torch_version=2.11.0+cu128
cuda_available=True
device_name=NVIDIA GeForce RTX 5070 Laptop GPU
device_count=1
cuda_matmul_smoke=ok value=11.062681198120117

```

Result: PASS

## 2. Hunyuan3D wrapper dependency imports

```text
import_ok=trimesh
import_ok=diffusers
import_ok=accelerate
import_ok=huggingface_hub
import_ok=einops
import_ok=cv2
import_ok=xatlas
import_ok=pymeshlab
import_ok=pygltflib
import_ok=sklearn
import_ok=skimage
import_ok=pybind11
all_imports_ok=True

```

Result: PASS

## 3. Silent-upgrade gate (pip freeze diff against lock file)

Lock file: `C:\Users\MetaHosP\Desktop\3D-Generate-by-AI-Local\scripts\windows\..\..\evidence\windows\hunyuan-runtime.lock.txt` (created this run)

```text
No prior lock file found at C:\Users\MetaHosP\Desktop\3D-Generate-by-AI-Local\scripts\windows\..\..\evidence\windows\hunyuan-runtime.lock.txt - this run establishes the baseline lock.
```

Result: PASS

## Verdict

PASS - CUDA available on the intended GPU, all wrapper imports succeeded, no silent dependency upgrade.
