# Runbook: Windows NVIDIA AI Server — Hardware Gate ถึง LAN Delivery (Phase 7–10)

**Owner:** Windows Server Operator; การเปิด public access ต้องรอ Owner approval | **Frequency:** As needed, ครั้งเดียวต่อการ build server หนึ่งเครื่อง | **Last Updated:** 2026-09-03 | **Last Run:** Not yet run

**Document version:** 2.0 | **Source language:** Thai | **English translation:** [windows-ai-server-runbook.en.md](windows-ai-server-runbook.en.md), version 2.0

> เอกสารนี้เป็นคู่มือทำงานซ้ำได้สำหรับ Phase 7 ถึง Phase 10 การเขียนหรืออ่านเอกสารนี้ไม่ใช่หลักฐานว่า Windows, NVIDIA GPU, ComfyUI, Hunyuan3D, GLB หรือ LAN flow ผ่านแล้ว หลักฐานต้องมาจากการรันบนเครื่องจริงเท่านั้น

## Purpose

นำ Windows NVIDIA server จาก "เครื่องเปล่า" ไปถึง "AI server ที่ใช้งานได้จริงผ่าน LAN" โดยผ่าน gate ตามลำดับ:

| Phase | ผลลัพธ์ที่ต้องพิสูจน์ | Tasks |
|---|---|---|
| 7 | runtime ที่ pin แล้วรัน native shape smoke ได้ | T058–T064 |
| 8 | FastAPI คุย ComfyUI จริงได้ผ่าน adapter เดียวกับ mock | T068, T072–T074 |
| 9 | สร้าง **textured GLB จริง** ได้ และ isolate ระหว่าง job ได้ | T075–T079 |
| 10 | เว็บครบ flow ใช้งานได้จาก **เครื่องอื่นใน LAN** | T080–T084 |

หยุดทันทีเมื่อ task ใด FAIL หรือ BLOCKED ห้ามข้าม gate เพื่อรายงานความคืบหน้า

## Hardware boundary (ข้อบังคับ อ่านก่อนทุกอย่าง)

**เครื่องที่รัน AI server ต้องเป็น Windows + NVIDIA GPU เท่านั้น**

| เครื่อง | บทบาท | ทำอะไรได้ / ไม่ได้ |
|---|---|---|
| Windows + NVIDIA GPU | **AI server จริง** | รัน ComfyUI, Hunyuan3D, FastAPI, GPU generation, LAN service ทั้งหมด — evidence ทุกชิ้นใน Phase 7–10 ต้องมาจากเครื่องนี้ |
| macOS (MacBook ของ Owner) | **เครื่องพัฒนาเท่านั้น** | เขียนโค้ด, รัน mock adapter, รัน test ที่ไม่ใช้ GPU — **ห้ามใช้เป็น AI server และห้ามใช้ผล mock แทน Windows evidence** |

เหตุผล: MacBook ไม่มี NVIDIA GPU/CUDA จึงรัน Hunyuan3D จริงไม่ได้ ผลจาก macOS ที่ผ่านคือ mock lane (Phase 6 ปิดไปแล้ว) ไม่ใช่หลักฐานของ hardware gate นี้

ถ้ามีใครเสนอให้รัน AI server บน macOS หรือใช้ผล macOS ปิด task Phase 7–10 ให้ปฏิเสธและรายงาน `BLOCKED`

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

**อยู่ในขอบเขตของ runbook นี้:** Phase 7 → 8 → 9 → 10 ตามลำดับ จบที่ LAN ใช้งานได้จริง

**อยู่นอกขอบเขต — ห้ามทำ:**

| หัวข้อ | สถานะ | เหตุผล |
|---|---|---|
| SDXL re-texturing / ControlNet texture projection | Post-MVP quality lane | เป็น reference เท่านั้น ห้ามเพิ่มเข้า MVP workflow, dependency หรือ task completion criteria |
| Blender retopology, Quad Remesher, texture painting, texture baking | Post-MVP quality lane | เป็นงาน manual หลัง MVP ไม่ใช่ส่วนของ FastAPI/ComfyUI pipeline |
| Caddy, DNS, DDNS, HTTPS certificate, router port-forward, public firewall | **Phase 11 — hard gate** | ต้องมี Owner approval สดตาม T085 ก่อนเริ่ม ดูหัวข้อ "เตรียมเข้า Phase 11" |
| การส่ง Public IP ให้ Owner ตอนนี้ | ยังไม่ต้องทำ | ดูหัวข้อ "เตรียมเข้า Phase 11" — ตอนนี้ต้องการแค่ 3 อย่าง ไม่รวมตัวเลข IP |

**ค่าที่ห้ามยึดเป็น requirement:** ตัวเลข tuning ที่พบในวิดีโอหรือ tutorial ภายนอก เช่น `steps=100`, octree resolution `900–1000` หรือ face count `1,000,000` เป็น **ค่าทดลอง** ไม่ใช่ข้อกำหนดของ MVP ต้องพิสูจน์กับ VRAM ของเครื่องจริงและบันทึกค่าที่ใช้จริงลง manifest

**CUDA 12.6** เป็น planning candidate ที่สอดคล้องกับ wrapper แต่ห้ามติดตั้งตามวิดีโอแบบ blind ต้องผ่าน T058–T060 และ pin เวอร์ชันลง manifest ก่อน

**สถานะของวิดีโอ/tutorial ภายนอก:** เป็น *reference only* ตาม [source register](../reference/ai-runtime-sources.md) ห้ามใช้แทน Windows evidence จริง และห้ามใช้ปิด task ใด ๆ

## ComfyUI API integration rules

กฎเหล่านี้มีผลตั้งแต่ Phase 7 และบังคับต่อเนื่องทุก phase หลังจากนั้น

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

- [x] Owner ยืนยัน GitHub repository ปลายทางแล้ว: [`R1KASAN/3D-Generate-by-AI-Local`](https://github.com/R1KASAN/3D-Generate-by-AI-Local) visibility `public` — baseline push แล้ว (ดู Step 0)
- [ ] เครื่องเป้าหมายเป็น **Windows + NVIDIA GPU** ไม่ใช่ macOS (ดู Hardware boundary)
- [ ] Operator มีสิทธิ์ local administrator เฉพาะเมื่อ installer ที่ pin แล้วต้องใช้สิทธิ์นั้น
- [ ] Operator มีสิทธิ์เขียนใน project root, evidence directory และ local runtime directory
- [ ] Windows PC มีพื้นที่ว่างเพียงพอสำหรับ runtime/model ตาม manifest
- [ ] ComfyUI, FastAPI และ browser ยังไม่ถูกเปิดออก Internet; ports `3000`, `8000`, `8188`, `3389` ต้องเป็น private
- [ ] Operator อ่าน artifact ใน Source of truth ครบแล้ว

## Procedure

### Step 0: Clone และตรวจ Git baseline บนเครื่อง Windows

> **สถานะ: baseline สร้างและ push เรียบร้อยแล้ว** operator ไม่ต้องสร้าง commit หรือ repository ใหม่ หน้าที่ของขั้นนี้คือ *ดึงและตรวจสอบ* ว่าเครื่อง Windows ได้ source ตรงกับที่ owner review แล้ว

| รายการ | ค่า |
|---|---|
| Repository | [`R1KASAN/3D-Generate-by-AI-Local`](https://github.com/R1KASAN/3D-Generate-by-AI-Local) |
| Visibility | `public` (owner ยืนยันแล้ว) |
| Default branch | `main` |
| ขอบเขต baseline | source/spec/docs — ผ่าน secret review, ไม่มี model weights, runtime artifacts หรือ credentials |

Clone บนเครื่อง Windows:

```powershell
Set-Location <PARENT_DIRECTORY>
git clone https://github.com/R1KASAN/3D-Generate-by-AI-Local.git
Set-Location 3D-Generate-by-AI-Local
git log -1 --format=%H
git status --short
```

**Expected result:** ได้ commit เดียวกับที่ Owner ประกาศไว้ และ `git status --short` ว่าง

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

---

## Phase 7 — Windows compatibility gate (T058–T064)

### Step 1: T058 — เก็บ hardware/runtime inventory

สร้างและรัน `scripts/windows/capture_gpu_baseline.ps1` ตาม task T058 แล้วบันทึก output ที่ sanitize ใน `evidence/windows/gpu-baseline.md`

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

**If it fails:** ห้ามไป Phase 8 ห้ามไป LAN หรือ public deployment

---

## Phase 8 — FastAPI-to-ComfyUI adapter (T068, T072–T074)

> เข้า phase นี้ได้เมื่อ `evidence/windows/phase-7-gate.md` = PASS เท่านั้น

**เป้าหมาย:** เปลี่ยนจาก mock adapter เป็น adapter จริง โดยใช้ contract เดียวกัน และไม่ให้ ComfyUI protocol/ID รั่วไปถึง frontend

### Step 8: T068 — hardware-gated adapter smoke test

สร้าง `apps/api/tests/integration/test_comfy_adapter_smoke.py` ตาม task T068

**Expected result:** test collection ผ่านบน macOS พร้อม documented skip และบนเครื่อง Windows fail ตรงจุด assertion ที่คาดไว้ (adapter/runtime ยังไม่มี)

**If it fails:** ห้ามแก้ test ให้ผ่านแบบหลอก บันทึก error จริงและหยุด

### Step 9: T072 — implement adapter จริง

สร้าง `apps/api/src/local3d/adapters/generation/comfy.py` ตาม task T072

```powershell
$env:GENERATION_ADAPTER="comfy"
uv run --project apps/api pytest apps/api/tests/contract/test_generation_adapter.py
```

**Expected result:** adapter suite เดียวกันผ่านทั้ง mock และ comfy โดยไม่คืน prompt ID ออกทาง public model

**If it fails:** ห้ามแก้ contract ให้หลวมลงเพื่อให้ผ่าน หยุดและรายงาน mismatch

### Step 10: T073 — manifest verification + fail-closed readiness

แก้ `apps/api/src/local3d/adapters/generation/factory.py` และ `apps/api/src/local3d/main.py` ตาม task T073

**Expected result:** mock test ยังเขียว และเมื่อ manifest จริงไม่ถูกต้อง `/api/v1/health/ready` ต้องคืน 503 แบบปลอดภัย (ไม่เผย path/internal detail)

**If it fails:** ห้ามปล่อยให้ readiness ผ่านทั้งที่ manifest ไม่ตรง — ต้อง fail closed เสมอ

### Step 11: T074 — real integration smoke test

```powershell
$env:RUN_COMFY_INTEGRATION="1"
uv run --project apps/api pytest apps/api/tests/integration/test_comfy_adapter_smoke.py
```

บันทึก request/result ที่ sanitize แล้วใน `evidence/windows/comfy-adapter-smoke.md`

**Expected result:** ผ่านโดย ComfyUI bind อยู่ที่ loopback เท่านั้น

**If it fails:** เก็บ error ที่ sanitize แล้ว หยุดก่อน Phase 9

---

## Phase 9 — Real textured-GLB validation (T075–T079)

> นี่คือ phase ที่พิสูจน์ผลลัพธ์จริงของ MVP ไม่ใช่แค่ shape

### Step 12: T075 — รัน full shape+texture workflow

pin และรัน workflow ที่ `workflows/hunyuan3d/editable/hunyuan3d-textured-glb.json` และ `workflows/hunyuan3d/api/hunyuan3d-textured-glb.json`

**Expected result:** หนึ่ง job ที่ส่งผ่าน API สร้าง GLB ที่ไม่ว่างเปล่าได้ **หนึ่งไฟล์พอดี** และมี evidence ใน `evidence/windows/textured-generation-1.md`

**If it fails:** บันทึก workflow hash, node error และ VRAM ที่ใช้; ถ้า OOM ให้ลดค่าที่ manifest อนุญาตและบันทึกค่าจริง ห้ามลด acceptance criterion

### Step 13: T076 — validate GLB จริง

```powershell
python scripts/verify/validate_glb.py <GLB_PATH>
```

บันทึก mesh, primitive, UV, material, texture, size และ SHA-256 ใน `evidence/windows/textured-glb-validation.md`

**Expected result:** ทุก property ที่ required ผ่านครบ

**If it fails:** ห้ามใช้ GLB ที่ไม่มี texture/UV เป็นผลผ่าน หยุดและรายงาน

### Step 14: T077 — สอง job เรียงกัน ตรวจ isolation

**Expected result:** GLB ทั้งสองผ่าน validation, isolate จากกัน, และจำนวน GPU job ที่ active สูงสุด = 1 พร้อมบันทึก Job ID, hash, duration, peak VRAM, overwrite check ใน `evidence/windows/two-job-serial.md`

**If it fails:** ถ้าพบ job ปนกันหรือ concurrent > 1 ให้หยุดทันที เป็นปัญหา isolation ที่ห้ามข้าม

### Step 15: T078 — recovery matrix

รัน `scripts/windows/run_recovery_matrix.ps1` ครอบคลุม engine failure, timeout, disconnect, missing output, backend restart และ ComfyUI restart

**Expected result:** `evidence/windows/recovery-matrix.md` แสดง terminal/reconciled state ที่ปลอดภัยและ **duplicate execution = 0**

**If it fails:** ถ้าพบ auto-resubmit หรืองานซ้ำ ให้หยุด เป็นการละเมิดกฎ ComfyUI API integration

### Step 16: T079 — ออก Phase 9 gate verdict

สร้าง `evidence/windows/phase-9-gate.md` พร้อม pinned revision/hash set

**Expected result:** PASS เมื่อ T075–T078 ผ่านครบ และไม่ใช้ shape-only evidence แทน textured completion

**If it fails:** ห้ามไป Phase 10

---

## Phase 10 — LAN end-to-end delivery (T080–T084)

> จบ phase นี้ = Owner เริ่มใช้งาน AI server และเว็บได้จริงผ่าน LAN

### Step 17: T080 — Windows services

สร้าง `deploy/windows/services/api.xml`, `web.xml`, `comfyui.xml` (WinSW) โดย bind loopback ทั้งหมด แล้วรัน `scripts/windows/verify_services.ps1`

**Expected result:** `evidence/lan/service-startup.md` บันทึก restricted identity, dependency order, service healthy และ generation จริงสำเร็จหลังรันเป็น service

**If it fails:** ห้าม bind service ออก 0.0.0.0 เพื่อให้ผ่าน หยุดและรายงาน

### Step 18: T081 — reboot recovery

รัน `scripts/windows/verify_reboot_recovery.ps1`

**Expected result:** `evidence/lan/reboot-recovery.md` พิสูจน์ว่า start อัตโนมัติหลัง reboot, reconcile state และสร้าง job ใหม่สำเร็จ **โดยไม่ต้องเปิด terminal เอง**

**If it fails:** ถ้าต้องเปิด terminal ด้วยมือถือว่าไม่ผ่าน

### Step 19: T082 — LAN full flow จากเครื่องที่สอง

สร้างและรัน checklist ที่ `docs/operations/lan-acceptance.md`

**Expected result:** เครื่องที่สองใน LAN ทำได้ครบ: upload → queued/processing → textured preview (rotate/zoom/pan/reset) → download ที่ byte-identical บันทึกใน `evidence/lan/full-flow.md`

**If it fails:** บันทึกจุดที่ flow ขาดและหยุด

### Step 20: T083 — LAN security checklist

สร้าง `docs/operations/lan-security-checklist.md` และรัน `scripts/verify/test_lan_boundary.py`

**Expected result:** `evidence/lan/isolation-and-ports.md` พิสูจน์ว่า cross-job access ถูกปฏิเสธ และ **port 8000 กับ 8188 เข้าไม่ได้จากเครื่อง LAN** ขณะที่ทางเข้า LAN ที่อนุมัติแล้วยังทำงาน

**If it fails:** ถ้า 8000/8188 เข้าถึงได้จาก LAN ให้หยุดทันที เป็น security boundary ที่ห้ามผ่อน

### Step 21: T084 — ออก Phase 10 gate verdict

สร้าง `evidence/lan/phase-10-gate.md` พร้อม command, timestamp, Job ID, log, screenshot และ GLB hash

**Expected result:** PASS เมื่อ T080–T083 ผ่านครบ

**If it fails:** รายงาน BLOCKED พร้อม blocker ที่เล็กที่สุด

---

## เตรียมเข้า Phase 11 (Public Deployment) — หยุดและรายงาน

> **หยุดที่นี่** Phase 11 เป็น hard gate ตาม T085 และ [Constitution ข้อ IX](../../.specify/memory/constitution.md) — public access control และ deployment exposure ต้องมี Owner approval ห้าม operator ตัดสินใจเอง

**ห้ามแตะก่อนได้ไฟเขียว:** domain, DNS, DDNS, Caddy config, HTTPS certificate, router port-forward, public firewall rule

**สิ่งที่ต้องรายงานให้ Owner เมื่อ Phase 10 = PASS** (สามข้อนี้เท่านั้น):

| # | ข้อมูลที่ต้องการ | ทำไมถึงจำเป็น |
|---|---|---|
| 1 | มีโดเมนอยู่แล้วหรือจะใช้ DDNS ตัวไหน | Caddy ออก HTTPS certificate จากชื่อโดเมน ไม่ใช่จากตัวเลข IP |
| 2 | Public IP เป็น **static**, **dynamic** หรืออยู่หลัง **CGNAT** | ถ้าอยู่หลัง CGNAT จะ forward port ไม่ได้ ต้องเปลี่ยนวิธี deploy ทั้งหมด |
| 3 | Router เปิด port forward `80/443` ได้หรือไม่ | ถ้าเปิดไม่ได้ Phase 11 ต้องออกแบบใหม่ก่อนเริ่ม |

**ยังไม่ต้องส่งตัวเลข Public IP ตอนนี้** — Public IP ไม่ใช่ secret แต่ยังไม่จำเป็นจนกว่าจะถึงขั้นตั้ง DNS จริงและทดสอบจาก Internet ตอนนั้น Owner จะขอให้ revalidate ค่าปัจจุบันอีกครั้ง เพราะค่าที่ส่งล่วงหน้าอาจเปลี่ยนไปแล้ว

**Expected result:** Owner ได้รับสามข้อข้างบน + link ไป `evidence/lan/phase-10-gate.md` แล้วตอบกลับเป็น approval หรือ BLOCKED

**If it fails:** ถ้าข้อใดข้อหนึ่งตอบไม่ได้ ให้รายงานว่าตอบไม่ได้ ห้ามเดา และห้ามเริ่ม Phase 11

## Verification

- [x] Git baseline: push ไปยัง `R1KASAN/3D-Generate-by-AI-Local` แล้ว ผ่าน secret review — ดู [`evidence/setup/git-baseline.md`](../../evidence/setup/git-baseline.md)
- [ ] เครื่องที่ใช้เป็น Windows + NVIDIA GPU (ไม่ใช่ macOS)
- [ ] เครื่อง Windows clone baseline commit เดียวกันสำเร็จและ `git status --short` ว่าง
- [ ] `evidence/windows/gpu-baseline.md` มี inventory จริง
- [ ] `evidence/windows/runtime-compatibility.md` มี compatibility result จริง
- [ ] `evidence/windows/shape-smoke.md` มี API-driven shape artifact จริง
- [ ] `evidence/windows/object-info-check.md` มี manifest/node validation จริง
- [ ] `docs/operations/windows-gpu-validation.md` มี checklist ครบ
- [ ] `evidence/windows/phase-7-gate.md` มี PASS/FAIL/BLOCKED ที่อ้าง evidence ได้
- [ ] `evidence/windows/comfy-adapter-smoke.md` มีผล adapter จริง
- [ ] `evidence/windows/textured-glb-validation.md` มี GLB จริงที่ผ่าน validation ครบ
- [ ] `evidence/windows/two-job-serial.md` พิสูจน์ isolation และ concurrency = 1
- [ ] `evidence/windows/recovery-matrix.md` มี duplicate execution = 0
- [ ] `evidence/windows/phase-9-gate.md` มี verdict ที่อ้าง evidence ได้
- [ ] `evidence/lan/service-startup.md` และ `evidence/lan/reboot-recovery.md` ครบ
- [ ] `evidence/lan/full-flow.md` มี flow ครบจากเครื่องที่สอง
- [ ] `evidence/lan/isolation-and-ports.md` พิสูจน์ว่า 8000/8188 เข้าไม่ได้จาก LAN
- [ ] `evidence/lan/phase-10-gate.md` มี verdict ที่อ้าง evidence ได้
- [ ] รายงานสามข้อของ Phase 11 ให้ Owner แล้ว (โดเมน/DDNS, ชนิด IP, router 80/443)

## Troubleshooting

| Symptom | Likely cause | Safe action |
|---|---|---|
| `nvidia-smi` ไม่ทำงาน | driver/GPU environment ไม่พร้อม | หยุด T058, เก็บ output, ให้ owner/administrator แก้ driver ก่อน |
| `torch.cuda.is_available()` เป็น `False` | PyTorch/CUDA/driver mismatch | หยุด T060, บันทึก versions, ห้าม upgrade แบบสุ่ม |
| `/object_info` ติดต่อไม่ได้ | ComfyUI ไม่ได้ run หรือ bind ผิด | ตรวจ process/local bind เท่านั้น; ห้ามเปิด firewall เพื่อแก้ |
| Node class/hash ไม่ตรง manifest | custom node/runtime drift | หยุด T062, pin/review exact revision ก่อน retry |
| Shape workflow ผ่านใน GUI แต่ API fail | API workflow export/mapping ไม่ถูกต้อง | export API format ใหม่และเก็บ evidence API เท่านั้น |
| OOM หรือ native wheel import fail | VRAM หรือ runtime incompatibility | หยุดและรายงาน BLOCKED; ห้ามลด acceptance criterion เอง |
| adapter test ผ่าน mock แต่ fail comfy | contract drift ระหว่าง adapter สองตัว | แก้ adapter ให้ตรง contract ห้ามแก้ contract ให้หลวม |
| GLB ออกมามากกว่าหนึ่งไฟล์ | output resolver หรือ Job ID prefix ผิด | หยุด T075; ห้ามเลือก "ไฟล์ล่าสุด" เป็นทางแก้ |
| GLB ไม่มี texture/UV | รัน shape workflow แทน shape+texture | ตรวจว่าใช้ workflow ที่ถูก ห้ามรับ shape-only เป็นผลผ่าน |
| job ซ้ำหลัง restart | มี auto-resubmit อยู่ | หยุด T078; ต้อง reconcile ผ่าน `/history` ไม่ใช่ส่งใหม่ |
| service ไม่ start หลัง reboot | dependency order หรือ service identity ผิด | แก้ service definition; ห้าม start ด้วยมือแล้วบอกว่าผ่าน |
| เครื่อง LAN เข้า 8000/8188 ได้ | bind หรือ firewall rule ผิด | หยุด T083 ทันที เป็น security boundary |

## Rollback

- ก่อนเปลี่ยน runtime ให้บันทึก version/hash และ backup configuration ที่แก้
- ถอน/ย้อนเฉพาะ component ที่ operator เพิ่งติดตั้งและมี documented rollback
- ห้ามลบ models, evidence, database หรือ project storage เพื่อ "ลองใหม่"
- ถ้า service ของ Phase 10 มีปัญหา ให้ stop service แล้วกลับไปรันแบบ manual เพื่อ debug ห้ามเปิด port เพิ่มเพื่อแก้
- หลัง rollback ให้รัน T058 inventory ซ้ำและบันทึกความเปลี่ยนแปลง

## Escalation

| Situation | Contact | Method |
|---|---|---|
| มีคนเสนอให้ใช้ macOS เป็น AI server | Project Owner | ปฏิเสธและอ้าง Hardware boundary ในเอกสารนี้ |
| GitHub repository/visibility/access ไม่ชัดเจน | Project Owner | รายงาน `BLOCKED` พร้อม repository ที่ต้องยืนยัน |
| GPU/driver/CUDA mismatch | Project Owner + Windows administrator | แนบ sanitized inventory และ requested version decision |
| Manifest/node/license mismatch | Project Owner | แนบ manifest evidence; ห้ามเลือก revision เอง |
| GLB ไม่ผ่าน validation ซ้ำหลายครั้ง | Project Owner | แนบ validation output; ห้ามลดเกณฑ์เอง |
| LAN client เข้าถึง internal port ได้ | Project Owner | รายงานทันทีเป็น security issue |
| Security/public exposure request ก่อน Phase 10 PASS | Project Owner | ปฏิเสธและอ้าง constitution/security boundary |
| พร้อมเข้า Phase 11 | Project Owner | ส่งสามข้อ (โดเมน/DDNS, ชนิด IP, router 80/443) + link `evidence/lan/phase-10-gate.md` |

## History

| Date | Run By | Notes |
|---|---|---|
| 2026-09-03 | Not yet run | Runbook created from approved project artifacts; no Windows evidence claimed. |
| 2026-09-03 | Owner (macOS) | v1.1 — Git baseline สร้างและ push ไปยัง `R1KASAN/3D-Generate-by-AI-Local` (public) หลังผ่าน secret review; Step 0 เปลี่ยนจาก "สร้าง baseline" เป็น "clone และตรวจ baseline"; เพิ่ม Scope boundary และ ComfyUI API integration rules |
| 2026-09-03 | Owner (macOS) | v2.0 — เปลี่ยนชื่อไฟล์จาก `windows-phase7-operator-guide.*` เป็น `windows-ai-server-runbook.*`; ขยายขอบเขตจาก Phase 7 อย่างเดียวเป็น Phase 7–10 (จบที่ LAN ใช้งานได้); เพิ่ม Hardware boundary ห้ามใช้ macOS เป็น AI server; เพิ่มหัวข้อเตรียมเข้า Phase 11 ที่ขอเพียงโดเมน/DDNS, ชนิด IP และ router 80/443 โดยยังไม่ขอตัวเลข Public IP; ยังไม่มี Windows evidence ใด ๆ |
