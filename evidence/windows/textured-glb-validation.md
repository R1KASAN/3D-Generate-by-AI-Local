# Textured GLB Validation Evidence (T076)

**Validator:** `scripts/verify/validate_glb.py`

**Command:**

```powershell
python scripts/verify/validate_glb.py `
  C:\Users\MetaHosP\ComfyUI\output\jobs\dd365728-1cad-4f65-adb5-9de4f523b735\model_00001_.glb `
  --require-mesh --require-uv --require-material --require-texture
```

**Observed:** `PASS`

| Property | Observed |
|---|---:|
| File size | 3,737,948 bytes |
| SHA-256 | `b2c806a54a070ae9ea26b4bc2ce44edf3f8344ccbb999523fd196fecb635dba1` |
| GLB declared length | 3,737,948 bytes |
| GLB actual length | 3,737,948 bytes |
| glTF asset version | `2.0` |
| Meshes | 1 |
| Primitives | 1 |
| Primitives with POSITION | 1 |
| Primitives with TEXCOORD_0 | 1 |
| Materials | 1 |
| Textures | 1 |
| Images | 1 |

The same validator passed for the two serial-isolation outputs retained in
[two-job-serial.md](two-job-serial.md). No shape-only artifact was used for
this result.

**Verdict: PASS.**
