# Runbook: Windows NVIDIA Compatibility Gate (Phase 7)

**Owner:** Windows Server Operator; GitHub publication requires Owner approval | **Frequency:** As needed, once per target server build | **Last Updated:** 2026-09-03 | **Last Run:** Not yet run

**Document version:** 1.1 | **Source language:** Thai | **English translation:** [windows-phase7-operator-guide.en.md](windows-phase7-operator-guide.en.md), version 1.1

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

## Scope boundary (อ่านก่อนเริ่ม)

Phase 7 พิสูจน์ **compatibility ของ runtime** เท่านั้น ไม่ใช่คุณภาพของโมเดลและไม่ใช่ deployment

**อยู่ในขอบเขต Phase 7:** T058–T064 คือ inventory, pinned install, compatibility check, native shape smoke, manifest verification, checklist และ gate verdict

**อยู่นอกขอบเขต — ห้ามทำใน Phase นี้:**

| หัวข้อ | สถานะ | เหตุผล |
|---|---|---|
| SDXL re-texturing / ControlNet texture projection | Post-MVP quality lane | เป็น reference เท่านั้น ห้ามเพิ่มเข้า MVP workflow, dependency หรือ task completion criteria |
| Blender retopology, Quad Remesher, texture painting, texture baking | Post-MVP quality lane | เป็นงาน manual หลัง MVP ไม่ใช่ส่วนของ FastAPI/ComfyUI pipeline |
| Textured GLB acceptance, FastAPI-to-ComfyUI integration | Phase 8 ขึ้นไป | shape smoke ที่ผ่านไม่นับเป็น MVP acceptance |
| LAN, Caddy, firewall, DNS, HTTPS, public deployment | Phase 9 ขึ้นไป | ต้องผ่าน Phase 7 gate ก่อน |

**ค่าที่ห้ามยึดเป็น requirement:** ตัวเลข tuning ที่พบในวิดีโอหรือ tutorial ภายนอก เช่น `steps=100`, octree resolution `900–1000` หรือ face count `1,000,000` เป็น **ค่าทดลอง** ไม่ใช่ข้อกำหนดของ MVP ต้องพิสูจน์กับ VRAM ของเครื่องจริงและบันทึกค่าที่ใช้จริงลง manifest

**CUDA 12.6** เป็น planning candidate ที่สอดคล้องกับ wrapper แต่ห้ามติดตั้งตามวิดีโอแบบ blind ต้องผ่าน T058–T060 และ pin เวอร์ชันลง manifest ก่อน

**สถานะของวิดีโอ/tutorial ภายนอก:** เป็น *reference only* ตาม [source register](../reference/ai-runtime-sources.md) ห้ามใช้แทน Windows evidence จริง และห้ามใช้ปิด task ใด ๆ

## ComfyUI API integration rules

กฎเหล่านี้มีผลตั้งแต่ Phase 7 และบังคับต่อเนื่องใน Phase 8

**เส้นทางที่อนุญาต:**

```text
Browser
  -> FastAPI only
      -> upload image safely
      -> create opaque Job ID + isolated directory
      -> map allowed API-workflow fields
      -> POST /prompt to 127.0.0.1:8188
      -> observe /ws, /queue, /history
      -> validate exactly one GLB
      -> publish controlled result to application storage
      -> browser preview/download
```

**สิ่งที่ห้ามเด็ดขาด:**

```text
Browser -> ComfyUI directly
User filename/path -> workflow output path
Shared ComfyUI input/output without Job ID prefix
overwrite=True on shared input directory
Search newest output file
Automatic resubmit after timeout/restart
Expose :8188, :8000, :3000, or :3389 publicly
```

ต้องใช้ workflow ที่ export เป็น **API format** เท่านั้น (ไม่ใช่ไฟล์ workflow ปกติ) และ prompt ID ของ ComfyUI ต้องไม่รั่วออกไปยัง public API model

## Prerequisites

- [x] Owner ยืนยัน GitHub repository ปลายทางแล้ว: [`R1KASAN/3D-Generate-by-AI-Local`](https://github.com/R1KASAN/3D-Generate-by-AI-Local) visibility `public` — baseline commit `fefad6e` push แล้ว (ดู Step 0)
- [ ] Operator มีสิทธิ์ local administrator เฉพาะเมื่อ installer ที่ pin แล้วต้องใช้สิทธิ์นั้น
- [ ] Operator มีสิทธิ์เขียนใน project root, evidence directory และ local runtime directory
- [ ] Windows PC มี NVIDIA GPU ที่พร้อมทดสอบ และมีพื้นที่ว่างเพียงพอสำหรับ runtime/model ตาม manifest
- [ ] ComfyUI, FastAPI และ browser ยังไม่ถูกเปิดออก Internet; ports `3000`, `8000`, `8188`, `3389` ต้องเป็น private
- [ ] Operator อ่าน artifact ใน Source of truth ครบแล้ว

## Procedure

### Step 0: Clone และตรวจ Git baseline บนเครื่อง Windows

> **สถานะ: baseline สร้างและ push เรียบร้อยแล้ว** operator ไม่ต้องสร้าง commit หรือ repository ใหม่ หน้าที่ของขั้นนี้คือ *ดึงและตรวจสอบ* ว่าเครื่อง Windows ได้ source ตรงกับที่ owner review แล้ว

Baseline ที่ยืนยันแล้ว:

| รายการ | ค่า |
|---|---|
| Repository | [`R1KASAN/3D-Generate-by-AI-Local`](https://github.com/R1KASAN/3D-Generate-by-AI-Local) |
| Visibility | `public` (owner ยืนยันแล้ว) |
| Default branch | `main` |
| Baseline commit | `fefad6ec10d2e96405b34efb0d0e4352258ab3b4` |
| ขอบเขต | 150 ไฟล์ source/spec/docs — ผ่าน secret review, ไม่มี model weights, runtime artifacts หรือ credentials |

Clone บนเครื่อง Windows:

```powershell
Set-Location <PARENT_DIRECTORY>
git clone https://github.com/R1KASAN/3D-Generate-by-AI-Local.git
Set-Location 3D-Generate-by-AI-Local
git log -1 --format=%H
git status --short
```

**Expected result:** `git log -1 --format=%H` คืนค่า `fefad6ec10d2e96405b34efb0d0e4352258ab3b4` (หรือ commit ที่ใหม่กว่าซึ่ง owner ประกาศแล้ว) และ `git status --short` ว่าง

**If it fails:** หยุดเป็น `BLOCKED` บันทึก command/error ที่ sanitize แล้วใน `evidence/setup/git-baseline.md` และขอ owner ยืนยัน repository หรือ access ห้ามสร้าง repository หรือ commit baseline ใหม่เอง

สร้าง local environment file จาก template (ไฟล์ `.env` จริงถูก ignore และต้องไม่ถูก commit):

```powershell
Copy-Item .env.example .env
Copy-Item apps\api\.env.example apps\api\.env
Copy-Item apps\web\.env.example apps\web\.env
```

**Expected result:** มี `.env` สำหรับ local run และ `git status --short` ยังคงว่าง (ยืนยันว่า `.gitignore` ทำงาน)

**If it fails:** หาก `.env` โผล่ใน `git status` ให้หยุดทันทีและแจ้ง owner ห้าม commit

#### ก่อน commit ใด ๆ ในอนาคต (กฎถาวร)

ทุกครั้งที่ operator จะ commit evidence หรือ script ใหม่ ต้อง scan ก่อน ห้ามใช้ `git add .` โดยไม่ตรวจไฟล์ ห้าม commit `.env` จริง, credentials, password hash, token, private key, production/public IP, router configuration, model weights, ComfyUI output/temp, local storage, logs, caches หรือ `node_modules`

```powershell
git status --short
rg -n --hidden --glob '!node_modules/**' --glob '!.git/**' --glob '!*.pdf' `
  '(?i)(api[_-]?key|secret|password|token|-----begin .*private key-----)' <PATHS_TO_STAGE>
git add <REVIEWED_PATHS_ONLY>
```

**Expected result:** ไม่มี secret และไม่มี runtime artifact เข้า commit

**If it fails:** เอาข้อมูลลับออก, ย้ายไป `.env` ที่ ignore แล้ว scan ซ้ำ ห้าม commit หรือ push จนกว่าจะสะอาด

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

- [x] Git baseline: commit `fefad6e` push ไปยัง `R1KASAN/3D-Generate-by-AI-Local` แล้ว ผ่าน secret review — ดู [`evidence/setup/git-baseline.md`](../../evidence/setup/git-baseline.md)
- [ ] เครื่อง Windows clone baseline commit เดียวกันสำเร็จและ `git status --short` ว่าง
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
| 2026-09-03 | Owner (macOS) | v1.1 — Git baseline `fefad6e` สร้างและ push ไปยัง `R1KASAN/3D-Generate-by-AI-Local` (public) หลังผ่าน secret review; Step 0 เปลี่ยนจาก "สร้าง baseline" เป็น "clone และตรวจ baseline"; เพิ่ม Scope boundary และ ComfyUI API integration rules; ยังไม่มี Windows evidence ใด ๆ |
