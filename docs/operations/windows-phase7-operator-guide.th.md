# Runbook: Windows NVIDIA Compatibility Gate (Phase 7)

**Owner:** Windows Server Operator; GitHub publication requires Owner approval | **Frequency:** As needed, once per target server build | **Last Updated:** 2026-09-03 | **Last Run:** Not yet run

**Document version:** 1.0 | **Source language:** Thai | **English translation:** [windows-phase7-operator-guide.en.md](windows-phase7-operator-guide.en.md), version 1.0

> เอกสารนี้เป็นคู่มือทำงานซ้ำได้สำหรับ Phase 7 เท่านั้น การเขียนหรืออ่านเอกสารนี้ไม่ใช่หลักฐานว่า Windows, NVIDIA GPU, ComfyUI, Hunyuan3D หรือ GLB ผ่านแล้ว

## Purpose

ยืนยันว่า Windows PC เป้าหมายมี runtime ที่ pin แล้วและรองรับ native Hunyuan3D 2.1 shape smoke ก่อนเริ่ม real ComfyUI adapter หรือ textured-GLB generation ให้ทำตาม `T058 → T059 → T060 → T061 → T062 → T063 → T064` และหยุดทันทีเมื่อ task ใด FAIL หรือ BLOCKED

## Source of truth

อ่านก่อนเปลี่ยนไฟล์หรือติดตั้ง software:

- [Constitution](../../.specify/memory/constitution.md)
- [Specification](../../specs/001-local-3d-generation/spec.md)
- [Plan](../../specs/001-local-3d-generation/plan.md)
- [Tasks](../../specs/001-local-3d-generation/tasks.md)
- [Research decisions](../../specs/001-local-3d-generation/research.md)
- [Quickstart and gates](../../specs/001-local-3d-generation/quickstart.md)
- [AI runtime source register](../reference/ai-runtime-sources.md)
- [GenerationAdapter contract](../../specs/001-local-3d-generation/contracts/generation-adapter.md)
- [Workflow-manifest contract](../../specs/001-local-3d-generation/contracts/comfyui-workflow-manifest.md)

หากวิดีโอหรือ README ภายนอกขัดกับเอกสารข้างต้น ให้เอกสารใน project และ owner-approved decision มีผลเหนือกว่า

## Prerequisites

- [ ] Owner ระบุ GitHub repository แบบ `owner/repository` และยืนยัน `private` หรือ `public` ก่อน push
- [ ] Operator มีสิทธิ์ local administrator เฉพาะเมื่อ installer ที่ pin แล้วต้องใช้สิทธิ์นั้น
- [ ] Operator มีสิทธิ์เขียนใน project root, evidence directory และ local runtime directory
- [ ] Windows PC มี NVIDIA GPU ที่พร้อมทดสอบ และมีพื้นที่ว่างเพียงพอสำหรับ runtime/model ตาม manifest
- [ ] ComfyUI, FastAPI และ browser ยังไม่ถูกเปิดออก Internet; ports `3000`, `8000`, `8188`, `3389` ต้องเป็น private
- [ ] Operator อ่าน artifact ใน Source of truth ครบแล้ว

## Procedure

### Step 0: ตรวจ Git baseline และเตรียม GitHub publication

> ทำขั้นนี้ก่อนงาน Windows เพื่อให้เครื่อง Windows clone source เดียวกับที่ตรวจสอบได้

```powershell
Set-Location <PROJECT_ROOT>
git status --short
git remote -v
git diff --check
git ls-files --others --exclude-standard
```

ตรวจรายการก่อน stage ทุกครั้ง ห้ามใช้ `git add .` โดยไม่ตรวจไฟล์ ห้าม commit `.env` จริง, credentials, password hash, token, private key, production/public IP, router configuration, model weights, ComfyUI output/temp, local storage, logs, caches หรือ `node_modules`

ใช้ secret scan ที่ owner อนุมัติ; อย่างน้อยตรวจ source ที่จะ stage ด้วย:

```powershell
rg -n --hidden --glob '!node_modules/**' --glob '!.git/**' --glob '!*.pdf' `
  '(?i)(api[_-]?key|secret|password|token|-----begin .*private key-----)' <PATHS_TO_STAGE>
```

**Expected result:** ไม่มี secret ที่จะถูก commit และ owner อนุมัติรายการไฟล์/visibility/repository ปลายทาง

**If it fails:** เอาข้อมูลลับออกจากไฟล์ที่จะ stage, ย้ายไป local secret manager หรือ `.env` ที่ ignore แล้ว scan ซ้ำ ห้าม commit หรือ push

เมื่อ review ผ่านแล้วเท่านั้น จึงสร้าง initial commit ด้วย message นี้หรือ equivalent ที่ owner อนุมัติ:

```powershell
git add <REVIEWED_PATHS_ONLY>
git commit -m "chore: establish local 3d generation MVP baseline"
git status --short
```

เพิ่ม remote และ push เฉพาะเมื่อ Owner ให้ค่า `<OWNER_REPOSITORY>` และ visibility ที่ยืนยันแล้ว:

```powershell
git remote add origin https://github.com/<OWNER_REPOSITORY>.git
git push -u origin main
```

**Expected result:** `git status --short` ว่าง, remote ชี้ไปยัง owner-approved repository และ GitHub แสดง commit SHA เดียวกัน

**If it fails:** หยุดเป็น `BLOCKED`; บันทึก command/error ที่ sanitize แล้วใน `evidence/setup/git-baseline.md` และขอ owner ยืนยัน repository, visibility หรือ access ไม่เดา/สร้าง repository เอง

### Step 1: T058 — เก็บ hardware/runtime inventory

สร้างและรัน `scripts/windows/capture_gpu_baseline.ps1` ตาม task T058 แล้วบันทึก output ที่ sanitize ใน `evidence/windows/gpu-baseline.md`

คำสั่งขั้นต่ำที่ต้องบันทึกผล:

```powershell
nvidia-smi
py -3.12 -c "import platform; print(platform.platform())"
py -3.12 -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); print(torch.cuda.get_device_properties(0).total_memory)"
py -3.12 -c "import sqlite3; print(sqlite3.sqlite_version)"
Get-PSDrive -PSProvider FileSystem
```

**Expected result:** ได้ Windows version, GPU model, driver, VRAM, Python, PyTorch, CUDA availability, SQLite version และ disk capacity จริง

**If it fails:** อย่าติดตั้งหรือเปลี่ยน version แบบสุ่ม บันทึก component ที่หาย/ผิดเวอร์ชันและหยุด `BLOCKED`

### Step 2: T059 — ติดตั้งและ pin ComfyUI/custom nodes

ใช้ [runtime source register](../reference/ai-runtime-sources.md) เพื่ออ่านแนวทาง installation แต่เลือก revision, package, model และ node จาก workflow manifest ที่ผ่านการ review เท่านั้น

- Bind ComfyUI กับ loopback เช่น `127.0.0.1:8188`
- บันทึก commit/hash/version/license ของ ComfyUI, wrapper, custom nodes และ model files
- ห้ามให้ ComfyUI Manager update node แบบ unattended
- restart แล้วตรวจ health จาก localhost เท่านั้น

```powershell
Invoke-WebRequest http://127.0.0.1:8188/object_info -UseBasicParsing
```

**Expected result:** ComfyUI ตอบจาก loopback และ revision/hash ตรง manifest

**If it fails:** หยุดก่อน T060; บันทึก exact mismatch โดยไม่เผย path/user credential แล้วแก้ manifest หรือ runtime ตาม owner decision

### Step 3: T060 — ตรวจ PyTorch/CUDA/native wheel compatibility

สร้างและรัน `scripts/windows/verify_hunyuan_runtime.ps1` ตาม task T060 ห้าม auto-upgrade dependencies เพื่อให้ import ผ่าน

```powershell
py -3.12 -c "import torch; assert torch.cuda.is_available(); print(torch.version.cuda); print(torch.cuda.get_device_name(0))"
```

**Expected result:** Python environment ที่ใช้รันจริง import required packages ได้, CUDA พร้อมใช้งาน, GPU ถูกเลือกถูกต้อง และไม่มี version drift จาก manifest

**If it fails:** บันทึก installed version และ error ที่ sanitize ใน `evidence/windows/runtime-compatibility.md`; หยุด `BLOCKED` เพื่อขอ owner decision ก่อนเปลี่ยน dependency

### Step 4: T061 — Native Hunyuan3D 2.1 shape smoke

export workflow ทั้ง editable และ API format ไปยัง paths ที่ task T061 ระบุ รันผ่าน API และเก็บ shape artifact ที่ parse ได้

**Expected result:** shape smoke ผ่านและมี evidence ใน `evidence/windows/shape-smoke.md`

**If it fails:** เก็บ workflow hash, node/version mismatch และ safe error; ห้ามใช้ GUI-only success เป็นผลผ่าน API

> Shape-only artifact ไม่ใช่ textured GLB และไม่ปลดล็อก MVP acceptance

### Step 5: T062 — ตรวจ manifest/hash และ `/object_info`

สร้างและรัน `scripts/verify/verify_comfy_manifest.py` ตาม task T062 และ deliberate mismatch fixture ที่ task กำหนด

**Expected result:** runtime ที่ pin แล้ว PASS; missing/changed node หรือ hash mismatch FAIL closed

**If it fails:** หยุดก่อน T063; บันทึก mismatch ใน `evidence/windows/object-info-check.md` โดยไม่แก้ version แบบ guessing

### Step 6: T063 — Windows GPU validation checklist

สร้าง [windows-gpu-validation.md](windows-gpu-validation.md) ตาม task T063 และกรอกทุก prerequisite พร้อม command output, artifact paths และ verdict `PASS`, `FAIL` หรือ `BLOCKED`

**Expected result:** checklist ไม่มีข้อที่ถูกข้าม และทุกผลอ้าง evidence จริง

**If it fails:** ระบุ blocker ที่เล็กที่สุดและ owner action ที่ต้องการ

### Step 7: T064 — ออก Phase 7 gate verdict

สร้าง `evidence/windows/phase-7-gate.md` ด้วยรูปแบบ:

```text
Gate: Phase 7 — Windows ComfyUI and Hunyuan3D Compatibility
Date/time and operator:
Host/environment:
Pinned revisions/hashes:
Tasks T058–T063 and evidence links:
Verdict: PASS | FAIL | BLOCKED
Blocker and smallest owner action:
```

**Expected result:** PASS ได้ต่อเมื่อ T058–T063 ผ่านทั้งหมด มิฉะนั้นต้องเป็น FAIL หรือ BLOCKED อย่างซื่อสัตย์

**If it fails:** ห้ามไป T068, T072, T075, LAN หรือ public deployment

## Verification

- [ ] Git baseline evidence ระบุ reviewed paths, commit SHA และ GitHub URL โดยไม่มี secret
- [ ] `evidence/windows/gpu-baseline.md` มี inventory จริง
- [ ] `evidence/windows/runtime-compatibility.md` มี compatibility result จริง
- [ ] `evidence/windows/shape-smoke.md` มี API-driven shape artifact จริง
- [ ] `evidence/windows/object-info-check.md` มี manifest/node validation จริง
- [ ] `docs/operations/windows-gpu-validation.md` มี checklist ครบ
- [ ] `evidence/windows/phase-7-gate.md` มี PASS/FAIL/BLOCKED ที่อ้าง evidence ได้

## Troubleshooting

| Symptom | Likely cause | Safe action |
|---|---|---|
| `nvidia-smi` ไม่ทำงาน | driver/GPU environment ไม่พร้อม | หยุด T058, เก็บ output, ให้ owner/administrator แก้ driver ก่อน |
| `torch.cuda.is_available()` เป็น `False` | PyTorch/CUDA/driver mismatch | หยุด T060, บันทึก versions, ห้าม upgrade แบบสุ่ม |
| `/object_info` ติดต่อไม่ได้ | ComfyUI ไม่ได้ run หรือ bind ผิด | ตรวจ process/local bind เท่านั้น; ห้ามเปิด firewall เพื่อแก้ |
| Node class/hash ไม่ตรง manifest | custom node/runtime drift | หยุด T062, pin/review exact revision ก่อน retry |
| Shape workflow ผ่านใน GUI แต่ API fail | API workflow export/mapping ไม่ถูกต้อง | export API format ใหม่และเก็บ evidence API เท่านั้น |
| OOM หรือ native wheel import fail | VRAM หรือ runtime incompatibility | หยุดและรายงาน BLOCKED; ห้ามลด acceptance criterion เอง |

## Rollback

- ก่อนเปลี่ยน runtime ให้บันทึก version/hash และ backup configuration ที่แก้
- ถอน/ย้อนเฉพาะ component ที่ operator เพิ่งติดตั้งและมี documented rollback
- ห้ามลบ models, evidence, database หรือ project storage เพื่อ “ลองใหม่”
- หลัง rollback ให้รัน T058 inventory ซ้ำและบันทึกความเปลี่ยนแปลง

## Escalation

| Situation | Contact | Method |
|---|---|---|
| GitHub repository/visibility/access ไม่ชัดเจน | Project Owner | รายงาน `BLOCKED` พร้อม repository ที่ต้องยืนยัน |
| GPU/driver/CUDA mismatch | Project Owner + Windows administrator | แนบ sanitized inventory และ requested version decision |
| Manifest/node/license mismatch | Project Owner | แนบ manifest evidence; ห้ามเลือก revision เอง |
| Security/public exposure request ก่อน Phase 7 PASS | Project Owner | ปฏิเสธและอ้าง constitution/security boundary |

## History

| Date | Run By | Notes |
|---|---|---|
| 2026-09-03 | Not yet run | Runbook created from approved project artifacts; no Windows evidence claimed. |
