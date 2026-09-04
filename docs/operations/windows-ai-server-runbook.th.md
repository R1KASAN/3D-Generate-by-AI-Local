# Runbook: Windows NVIDIA AI Server — Hardware Gate ถึง Public Deployment (Phase 7–12)

**Owner:** Windows Server Operator; การเปิด public access ต้องผ่าน T085 owner-approval gate ก่อนทุกครั้ง | **Frequency:** As needed, ครั้งเดียวต่อการ build server หนึ่งเครื่อง | **Last Updated:** 2026-09-03 | **Last Run:** Not yet run

**Document version:** 3.0 | **Source language:** Thai | **English translation:** [windows-ai-server-runbook.en.md](windows-ai-server-runbook.en.md), version 3.0

> เอกสารนี้เป็นคู่มือทำงานซ้ำได้สำหรับ Phase 7 ถึง Phase 12 การเขียนหรืออ่านเอกสารนี้ไม่ใช่หลักฐานว่า Windows, NVIDIA GPU, ComfyUI, Hunyuan3D, GLB, LAN flow หรือ public deployment ผ่านแล้ว หลักฐานต้องมาจากการรันบนเครื่องจริงเท่านั้น

## Purpose

นำ Windows NVIDIA server จาก "เครื่องเปล่า" ไปถึง "AI server ที่คนนอกเครือข่ายใช้งานได้จริงผ่าน HTTPS" โดยผ่าน gate ตามลำดับ:

| Phase | ผลลัพธ์ที่ต้องพิสูจน์ | Tasks |
|---|---|---|
| 7 | runtime ที่ pin แล้วรัน native shape smoke ได้ | T058–T064 |
| 8 | FastAPI คุย ComfyUI จริงได้ผ่าน adapter เดียวกับ mock | T068, T072–T074 |
| 9 | สร้าง **textured GLB จริง** ได้ และ isolate ระหว่าง job ได้ | T075–T079 |
| 10 | เว็บครบ flow ใช้งานได้จาก **เครื่องอื่นใน LAN** | T080–T084 |
| 11 | เปิด HTTPS ออก public หลัง Owner อนุมัติ พร้อมการป้องกันด้วย per-job token | T085–T092 |
| 12 | ทดสอบจากนอกเครือข่ายจริง + audit ปิดงานทั้งโปรเจกต์ | T093–T097 |

หยุดทันทีเมื่อ task ใด FAIL หรือ BLOCKED ห้ามข้าม gate เพื่อรายงานความคืบหน้า **Phase 11 มีเงื่อนไขพิเศษ**: ต้องได้ Owner approval แบบเจาะจงเป็นลายลักษณ์อักษรก่อนแตะ public infrastructure ใดๆ (ดู T085) — เป็นเงื่อนไขถาวรของ phase นี้ ไม่ใช่แค่ checklist ทั่วไป

## Hardware boundary (ข้อบังคับ อ่านก่อนทุกอย่าง)

**เครื่องที่รัน AI server ต้องเป็น Windows + NVIDIA GPU เท่านั้น**

| เครื่อง | บทบาท | ทำอะไรได้ / ไม่ได้ |
|---|---|---|
| Windows + NVIDIA GPU | **AI server จริง** | รัน ComfyUI, Hunyuan3D, FastAPI, GPU generation, LAN service ทั้งหมด — evidence ทุกชิ้นใน Phase 7–10 ต้องมาจากเครื่องนี้ |
| macOS (MacBook ของ Owner) | **เครื่องพัฒนาเท่านั้น** | เขียนโค้ด, รัน mock adapter, รัน test ที่ไม่ใช้ GPU — **ห้ามใช้เป็น AI server และห้ามใช้ผล mock แทน Windows evidence** |

เหตุผล: MacBook ไม่มี NVIDIA GPU/CUDA จึงรัน Hunyuan3D จริงไม่ได้ ผลจาก macOS ที่ผ่านคือ mock lane (Phase 6 ปิดไปแล้ว) ไม่ใช่หลักฐานของ hardware gate นี้

ถ้ามีใครเสนอให้รัน AI server บน macOS หรือใช้ผล macOS ปิด task Phase 7–10 ให้ปฏิเสธและรายงาน `BLOCKED`

## Network boundary (สำคัญสำหรับ Phase 11)

**อัปเดต 2026-09-04:** โปรเจกต์นี้ไม่ได้ใช้วิธี port forward ผ่าน router บ้าน/ที่ทำงานแล้ว Owner ได้รับ Public IP ที่จัดสรรตรงจากมหาวิทยาลัย (`161.200.90.4` ตามบันทึกข้อความ วฟ.2174/2567) สำหรับ **edge server** ซึ่งเป็นคนละเครื่องกับ Windows GPU server ที่ runbook นี้อธิบายอยู่ GPU server ไม่ได้ถือ public IP เอง แต่เชื่อมต่อออกไปหา edge ผ่าน WireGuard tunnel ดูรายละเอียดเต็มที่ `C:\Users\MetaHosP\.claude\plans\router-ai-eventual-tide.md` และ `docs/operations/public-cutover.md`

- ไม่มีการตัดสินใจเรื่อง "router ของ operator" อีกต่อไป — ผู้มีอำนาจอนุมัติคือ **border firewall ของมหาวิทยาลัย** ไม่ใช่ router ทั่วไป ต้องอนุญาต inbound `443/tcp`, `80/tcp`, และ `51820/udp` มาที่ `161.200.90.4` เท่านั้น
- Windows GPU server อยู่บนเครือข่ายจริงที่มันเสียบอยู่ตอนนั้น (มหาวิทยาลัย/บ้าน/hotspot มือถือ) และเข้าถึงได้ผ่าน tunnel เท่านั้น — ออกแบบมาให้ย้ายเครือข่ายได้อิสระโดยเจตนา ห้าม forward port บน router ของเครื่องนั้นเอง ไม่มีส่วนใดของ deployment นี้พึ่งพาสิ่งนั้น
- `161.200.90.3` ถูกจัดสรรไว้ใช้งานอื่น ห้ามตั้งค่า, forward, หรือ probe ด้วยสิ่งใดที่เกี่ยวข้องกับโปรเจกต์นี้เด็ดขาด
- domain ที่ใช้จะชี้ไปที่ IP คงที่ของ edge server (`161.200.90.4`) ไม่ใช่ IP เครือข่ายของ GPU server เองซึ่งเปลี่ยนไปตามที่มันย้ายไป

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

**อยู่ในขอบเขตของ runbook นี้:** Phase 7 → 8 → 9 → 10 → 11 → 12 ตามลำดับ จบที่ external user ใช้งานผ่าน HTTPS ได้จริง

**อยู่นอกขอบเขต — ห้ามทำแม้ผ่าน Phase 11-12 แล้ว:**

| หัวข้อ | สถานะ | เหตุผล |
|---|---|---|
| SDXL re-texturing / ControlNet texture projection | Post-MVP quality lane | เป็น reference เท่านั้น ห้ามเพิ่มเข้า MVP workflow, dependency หรือ task completion criteria |
| Blender retopology, Quad Remesher, texture painting, texture baking | Post-MVP quality lane | เป็นงาน manual หลัง MVP ไม่ใช่ส่วนของ FastAPI/ComfyUI pipeline |
| แก้ access control จาก "public entry + per-job token" เป็นแบบอื่น | ต้อง Owner ตัดสินใจใหม่ | [tasks.md T085](../../specs/001-local-3d-generation/tasks.md) บันทึก approved decision นี้ไว้แล้ว การเปลี่ยนต้องขออนุมัติใหม่เป็นลายลักษณ์อักษร ห้ามเปลี่ยนเอง |
| เปิด public ก่อนที่ T085 owner-approval gate จะผ่าน | ต้องหยุดเสมอ | ดู "Phase 11 — T085" ด้านล่าง เป็นเงื่อนไขที่ยกเว้นไม่ได้ |

**เกี่ยวกับ Public IP:** ไม่ใช่ secret แต่ไม่แนะนำให้พิมพ์ตัวเลข IP ตรงๆ ลงในแชท/LINE — ให้บันทึกไว้ใน `evidence/public-deployment/dns-router.md` (redacted ตามที่ T089 กำหนด) แล้วให้ Owner เปิดดูจาก evidence file หรือ repo แทน

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
- [ ] ComfyUI, FastAPI และ browser ยังไม่ถูกเปิดออก Internet ก่อนถึง Phase 11; ports `3000`, `8000`, `8188`, `3389` ต้องเป็น private เสมอ
- [ ] Operator อ่าน artifact ใน Source of truth ครบแล้ว
- [ ] (สำหรับ Phase 11) IT มหาวิทยาลัยยืนยันแล้วว่า border firewall อนุญาต inbound 443/tcp, 80/tcp, และ 51820/udp (WireGuard) มาที่ `161.200.90.4` เท่านั้น — ไม่มีการตัดสินใจเรื่อง router ของ operator ใน topology นี้

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

---

## Phase 11 — Protected Caddy HTTPS deployment (T085–T092)

> เข้า phase นี้ได้เมื่อ `evidence/lan/phase-10-gate.md` = PASS **และ** T085 (owner-approval gate) อนุมัติแล้วเท่านั้น ห้ามแตะ domain/DNS/Caddy/firewall ก่อนถึงขั้นนี้

**Hard gate ที่ยกเว้นไม่ได้:** access control ที่ approve ไว้คือ **public HTTPS entry โดยไม่มี site-wide login และมี per-job `X-Job-Token` สำหรับข้อมูลของแต่ละงาน** เท่านั้น ถ้า decision นี้หายไปหรือถูกแทนที่โดยไม่มี Owner อนุมัติใหม่ ให้หยุด phase ทันที ห้ามเปิด port 3000, 8000, 8188 หรือ 3389 ออก public ไม่ว่ากรณีใด

### Step 22: T085 — Owner approval gate (ทำก่อนทุกอย่างใน phase นี้)

ส่งข้อมูลนี้ให้ Owner แล้ว **รอการอนุมัติเป็นลายลักษณ์อักษร** ก่อนแตะ public infrastructure ใดๆ:

| # | ข้อมูลที่ต้องได้รับอนุมัติ |
|---|---|
| 1 | นโยบาย public entry ที่ไม่มี site-wide login |
| 2 | ขอบเขต model-license/territory ของผู้ใช้ที่อนุญาต |
| 3 | โดเมนที่จะใช้ หรือ DDNS provider |
| 4 | ใครเป็นเจ้าของบัญชี DNS/DDNS |
| 5 | Public IP ปัจจุบัน (revalidate สดๆ กับ `161.200.90.4` จริง ไม่ใช่จากบันทึกการจัดสรร) |
| 6 | สถานะ static/dynamic/CGNAT ของ IP นั้น (การจัดสรรเป็นแบบ static/ตรง แต่ต้องวัดจริง ไม่ใช่สมมติเอา) |
| 7 | border firewall ของมหาวิทยาลัยอนุญาต inbound 443/tcp, 80/tcp, และ 51820/udp มาที่ `161.200.90.4` ไหม |

บันทึกการอนุมัติ (หรือ BLOCKED) ลง `evidence/public-deployment/owner-gate.md`

**Expected result:** ทุกข้อได้รับอนุมัติชัดเจนจาก Owner เป็นลายลักษณ์อักษร

**If it fails:** ถ้าข้อใดข้อหนึ่งยังไม่ได้รับอนุมัติ ให้บันทึกเป็น `BLOCKED` **โดยไม่แตะ public infrastructure เลย** ห้ามเดาหรือเริ่ม Step 23 ต่อ

### Step 23: T086 — Caddy configuration contract tests

เขียน `tests/security/test_caddy_contract.py` ทดสอบ HTTPS-only public entry ที่ไม่มี `basic_auth`, request-body limit, `/api` proxying, การส่งต่อ job token และแบน public upstream bind

```powershell
uv run --project apps/api pytest tests/security/test_caddy_contract.py
```

**Expected result:** test fail เพราะยังไม่มี Caddy config จริง (ตามหลัก test-first) และมี assertion ที่แบน public 3000/8000/8188/3389 ครบ

**If it fails:** ถ้า test เขียนไม่ครบตาม T086 ให้แก้ test ก่อน ห้ามข้ามไป implement โดยไม่มี test คุม

### Step 24: T087 — Implement Caddy configuration

สร้าง `deploy/caddy/Caddyfile` และ `deploy/caddy/.env.example` สำหรับ hostname ที่อนุมัติแล้วโดยไม่มี `basic_auth`

```powershell
caddy validate --config deploy/caddy/Caddyfile
```

**Expected result:** `caddy validate` ผ่าน, T086 ผ่าน, public HTTPS routing และการส่งต่อ job token ทำงาน และ **ไม่มี secret ถูก commit**

**If it fails:** ห้ามฝัง token หรือ secret อื่นใน Caddyfile ถ้าจำเป็นต้องใช้ secret ให้ใช้ environment variable แล้ว scan ซ้ำก่อน commit

### Step 25: T088 — Windows Firewall boundary

สร้าง `deploy/firewall/configure-public-boundary.ps1` (least-privilege) และ `deploy/firewall/verify-public-boundary.ps1` (read-only verifier)

**Expected result:** `evidence/public-deployment/firewall.md` บันทึกว่า 443 allowed, 80 (ถ้าเปิด) จำกัดแค่ redirect/certificate เท่านั้น และ 3000/8000/8188/3389 **blocked**

**If it fails:** ถ้า verifier เจอ port internal เปิดอยู่ ให้หยุดทันที เป็น security boundary ที่ห้ามผ่อน

### Step 26: T089 — DNS และยืนยัน border firewall ของมหาวิทยาลัย

สร้าง DNS A record ที่ Owner อนุมัติใน T085 ชี้ไปที่ `161.200.90.4` ยืนยันเป็นลายลักษณ์อักษรกับ IT มหาวิทยาลัยว่า border firewall อนุญาตเฉพาะ inbound 443/tcp, 80/tcp, และ 51820/udp (WireGuard) มาที่ address นั้น — ไม่มี router ให้ forward port ใน topology นี้

บันทึกหลักฐานแบบ redacted (ปิดบัง IP บางส่วนตามความเหมาะสม) ใน `evidence/public-deployment/dns-router.md`

**Expected result:** public DNS resolve ไปยัง Public IP ที่ revalidate แล้ว, ไม่มี CGNAT/routing blocker เหลืออยู่, และ **ไม่มี internal port forward เลย** — WireGuard tunnel ไปหา GPU laptop คือ private point-to-point link ระหว่าง edge กับ laptop เท่านั้น ไม่ใช่ port forward และไม่เคยพาไปไกลกว่า tunnel address ของ laptop

**If it fails:** ถ้าเจอ CGNAT หรือ border firewall ไม่อนุญาต 443/80/51820 จริงตามที่รายงานไว้ใน T085 ให้หยุดและกลับไปหา Owner ทันที ห้ามหาทาง port หรือ protocol อื่นทดแทน

### Step 27: T090 — TLS certificate + redirect validation

รัน `scripts/verify/test_https_boundary.py`

**Expected result:** `evidence/public-deployment/tls.md` แสดง trusted hostname validation, HTTPS 443 สำเร็จ, HTTP 80 ทำแค่ redirect/certificate issuance และ **ไม่มี certificate warning**

**If it fails:** ห้ามใช้ self-signed certificate หรือ bypass warning เพื่อให้ผ่าน หยุดและแก้ที่ domain/DNS config

### Step 28: T091 — Auth boundary tests จาก external client

รัน `scripts/verify/test_public_auth.py` จากเครื่องนอกเครือข่าย

**Expected result:** `evidence/public-deployment/auth.md` แสดงว่าเข้า HTTPS และส่งงานที่ถูกต้องได้โดยไม่มี site-wide login, token ที่ไม่มีหรือผิด job คืน 404 แบบเดียวกันสำหรับข้อมูลของ job (ไม่บอกใบ้ว่า job มีจริงไหม) และ **ไม่มี token หลุดใน URL หรือ log ที่ capture ไว้**

**If it fails:** ถ้า token หลุดใน log หรือ URL ให้หยุดทันที เป็นข้อมูลอ่อนไหวที่รั่วออกไปแล้ว

### Step 29: T092 — External port scan

รัน `scripts/verify/test_external_ports.py` จากนอกเครือข่าย

**Expected result:** `evidence/public-deployment/ports.md` แสดงว่า 443 (และ 80 ถ้าเปิด) ทำงานตามคาด และ **3000, 8000, 8188, 3389 เชื่อมต่อไม่ได้จากภายนอกเลย**

**If it fails:** ถ้า internal port ใดเชื่อมได้จากภายนอก ให้หยุดและปิดทันที ก่อนดำเนินการต่อ

**Phase 11 exit criteria:** T085 owner gate อนุมัติแล้ว, TLS และ per-job access control ผ่านครบ, มีแค่ทางเข้า public ที่ตั้งใจเท่านั้นที่เข้าถึงได้ และไม่มี secret ถูก commit

---

## Phase 12 — External-network acceptance และ final audit (T093–T097)

> เข้า phase นี้ได้เมื่อ Phase 11 exit criteria ผ่านครบแล้วเท่านั้น

### Step 30: T093 — External-network full-flow acceptance

สร้างและรัน checklist ที่ `docs/operations/external-acceptance.md`

**Expected result:** `evidence/public-deployment/full-flow.md` บันทึกว่า public submission ได้จริง, เห็น queue/process state จริง, preview textured GLB ได้ครบ (rotate/zoom/pan/reset), และ download ได้ไฟล์ byte-identical ด้วย job token ที่ระบบคืนให้ ผ่าน HTTPS จริงจากนอกเครือข่าย

**If it fails:** บันทึกจุดที่ flow ขาดและหยุด ห้ามใช้ผลจาก LAN แทน external evidence

### Step 31: T094 — External-network security checklist

สร้าง `docs/operations/external-network-security-checklist.md` และรัน `scripts/verify/test_external_acceptance.py` ครอบคลุม public entry, missing/wrong-token, expired-job, invalid upload, low-disk admission และ internal-port cases

**Expected result:** `evidence/public-deployment/negative-cases.md` แสดง response ที่ปลอดภัยทุกกรณีและ **zero information leakage**

**If it fails:** ถ้า error message เผยข้อมูล internal (path, stack trace, job existence) ให้หยุดและแก้ก่อน

### Step 32: T095 — Operator runbook drill

สร้าง `docs/operations/operator-runbook.md` แล้วซ้อมจริง

**Expected result:** `evidence/operations/runbook-drill.md` trace Job ID ได้ตลอด lifecycle: submission, queue, processing, result, download, failure, restart, 24-hour expiry และ low-disk recovery โดยไม่เผย user content หรือ secret

**If it fails:** ถ้า trace ขาดช่วงไหน ให้ระบุจุดที่ recovery ไม่ครบและหยุด

### Step 33: T096 — Final acceptance matrix

สร้าง `evidence/final/mvp-acceptance.md`

**Expected result:** ทุก SC-001–SC-007 และ FR-001–FR-018 ใน [spec.md](../../specs/001-local-3d-generation/spec.md) ต้อง map ไปยัง evidence จริงที่ผ่านแล้ว รายการที่ยังไม่ผ่านต้องระบุ `BLOCKED` ตรงๆ

**If it fails:** ห้ามใช้ checkbox หรือ report เฉยๆ เป็นหลักฐาน ต้องอ้าง evidence file จริงเท่านั้น

### Step 34: T097 — Final constitution and scope audit

ตรวจกับ [constitution.md](../../.specify/memory/constitution.md) แล้วบันทึก `evidence/final/constitution-audit.md`

**Expected result:** ไม่มี Post-MVP component (SDXL, Blender retopo ฯลฯ) หลุดเข้ามา, exception ทุกอันมี reason/risk/owner/review trigger ครบ, internal port ยังคง private และ verdict เป็น `PASS` หรือ `BLOCKED` อย่างซื่อสัตย์

**If it fails:** รายงาน `BLOCKED` พร้อมสิ่งที่ต้องแก้ ห้ามปิดเป็น PASS ทั้งที่ยังมีข้อค้างคา

**Phase 12 exit criteria:** external core flow, negative security check, operator recovery drill, requirement evidence matrix และ constitution audit ผ่านครบทุกข้อ — **นี่คือจุดจบของ MVP**

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
- [ ] `evidence/public-deployment/owner-gate.md` มีการอนุมัติทั้ง 6 ข้อจาก Owner เป็นลายลักษณ์อักษร
- [ ] `evidence/public-deployment/firewall.md` ยืนยัน 3000/8000/8188/3389 blocked จากภายนอก
- [ ] `evidence/public-deployment/dns-router.md` ยืนยัน DNS ชี้ IP ที่ revalidate แล้ว ไม่มี CGNAT blocker
- [ ] `evidence/public-deployment/tls.md` ยืนยัน HTTPS ผ่านไม่มี certificate warning
- [ ] `evidence/public-deployment/auth.md` ยืนยันไม่มี job token หรือ secret อื่นหลุดใน log
- [ ] `evidence/public-deployment/ports.md` ยืนยัน internal port ทั้งหมดเชื่อมไม่ได้จากภายนอก
- [ ] `evidence/public-deployment/full-flow.md` มี external user flow ที่ผ่านจริงผ่าน HTTPS
- [ ] `evidence/public-deployment/negative-cases.md` ยืนยัน zero information leakage
- [ ] `evidence/operations/runbook-drill.md` trace Job ID ได้ครบ lifecycle
- [ ] `evidence/final/mvp-acceptance.md` map ทุก SC/FR ไปยัง evidence จริง
- [ ] `evidence/final/constitution-audit.md` มี verdict PASS หรือ BLOCKED ที่ซื่อสัตย์

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
| owner-gate.md ยังมีข้อค้างไม่อนุมัติ | ยังไม่ได้ถาม Owner ครบ หรือ Owner ยังไม่ตอบ | หยุดที่ T085; ห้ามเริ่ม T086 ก่อนอนุมัติครบ |
| Border firewall มหาวิทยาลัยไม่ยอมเปิด 443/80/51820 มาที่ `161.200.90.4` | นโยบาย IT ยังไม่อนุมัติ หรือคำขอชี้ไป address ผิด | หยุด T089; รายงาน Owner ห้ามใช้ `161.200.90.3` หรือพอร์ตอื่นแทนเด็ดขาด |
| WireGuard tunnel ระหว่าง edge กับ laptop ต่อไม่ขึ้น | border firewall ยังไม่เปิด 51820/udp จริง, ลืมใส่ `PersistentKeepalive`, หรือมี VPN adapter อื่นแย่ง default route | ดู `docs/operations/tunnel-setup.md` หัวข้อ Troubleshooting — วินิจฉัยที่ชั้น tunnel เสมอ อย่าแก้โดย restart web service |
| Certificate warning หรือ self-signed cert โผล่ | DNS ยังไม่ propagate หรือ domain ผิด | หยุด T090; ห้าม bypass warning ห้าม deploy ทั้งที่ยังมี warning |
| Job token หรือ secret อื่นโผล่ใน log ที่ capture ไว้ | logging ไม่ mask ค่า sensitive | หยุด T091 ทันที; ถือเป็นข้อมูลรั่วแล้ว ต้อง invalidate token ที่ได้รับผลกระทบ หรือ rotate secret นั้น |
| Internal port เข้าได้จากภายนอกใน T092 | firewall rule ยังไม่ครอบคลุมพอ | หยุดทันที; ปิด service จนกว่าจะแก้ firewall เสร็จ |

## Rollback

- ก่อนเปลี่ยน runtime ให้บันทึก version/hash และ backup configuration ที่แก้
- ถอน/ย้อนเฉพาะ component ที่ operator เพิ่งติดตั้งและมี documented rollback
- ห้ามลบ models, evidence, database หรือ project storage เพื่อ "ลองใหม่"
- ถ้า service ของ Phase 10 มีปัญหา ให้ stop service แล้วกลับไปรันแบบ manual เพื่อ debug ห้ามเปิด port เพิ่มเพื่อแก้
- ถ้า Phase 11 มีปัญหาหลังเปิด public แล้ว ให้**ปิด/ลบ firewall rule ของ edge ก่อน** (ที่สร้างจาก `deploy/firewall/configure-public-edge.ps1`) แล้วค่อย debug — อย่าปล่อยให้ public เปิดอยู่ระหว่างแก้ปัญหา
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
| ยังไม่ยืนยันช่องทาง management (SSH/console) ของ edge server | Project Owner / IT มหาวิทยาลัย | แจ้งก่อนรัน `configure-public-edge.ps1` — สคริปต์เช็กก่อนทำเองอยู่แล้ว แต่ต้องตัดสินใจเลือกช่องทางก่อน (Stage 0.1 ของแผน deployment) |
| ข้อมูลใน T085 ข้อใดข้อหนึ่งตอบไม่ได้ | Project Owner | บันทึก `BLOCKED` ใน `owner-gate.md` โดยไม่แตะ public infra |
| Job token หรือ secret อื่นรั่วระหว่าง T091 | Project Owner | รายงานทันทีเป็น security incident แล้ว invalidate token ที่ได้รับผลกระทบ หรือ rotate secret นั้น |
| Public exposure request ที่ยังไม่ผ่าน owner-gate | Project Owner | ปฏิเสธและอ้าง Constitution ข้อ IX + T085 |

## History

| Date | Run By | Notes |
|---|---|---|
| 2026-09-03 | Not yet run | Runbook created from approved project artifacts; no Windows evidence claimed. |
| 2026-09-03 | Owner (macOS) | v1.1 — Git baseline สร้างและ push ไปยัง `R1KASAN/3D-Generate-by-AI-Local` (public) หลังผ่าน secret review; Step 0 เปลี่ยนจาก "สร้าง baseline" เป็น "clone และตรวจ baseline"; เพิ่ม Scope boundary และ ComfyUI API integration rules |
| 2026-09-03 | Owner (macOS) | v2.0 — เปลี่ยนชื่อไฟล์จาก `windows-phase7-operator-guide.*` เป็น `windows-ai-server-runbook.*`; ขยายขอบเขตจาก Phase 7 อย่างเดียวเป็น Phase 7–10 (จบที่ LAN ใช้งานได้); เพิ่ม Hardware boundary ห้ามใช้ macOS เป็น AI server; เพิ่มหัวข้อเตรียมเข้า Phase 11 ที่ขอเพียงโดเมน/DDNS, ชนิด IP และ router 80/443 โดยยังไม่ขอตัวเลข Public IP; ยังไม่มี Windows evidence ใด ๆ |
| 2026-09-03 | Owner (macOS) | v3.0 — แก้ความเข้าใจผิดว่า Phase 10 ต้องการเครื่อง Owner โดยตรง (จริงๆ ใช้เครื่องอื่นของ operator เองก็พอ); ขยายขอบเขตจาก Phase 7–10 เป็น Phase 7–12 เต็มตาม spec เดิม ตาม Owner ตัดสินใจให้ดำเนินการต่อจนถึง public deployment; เพิ่ม Network boundary section อธิบายว่า Phase 11 เปิด port บน router ของ operator เอง ต้องได้ความยินยอมจาก operator ด้วย ไม่ใช่แค่ Owner สั่ง; เพิ่ม Step 22–34 ครอบคลุม T085–T097 เต็มรูปแบบ (owner-approval gate, Caddy, firewall, DNS/router, TLS, external auth test, port scan, external acceptance, negative-case security test, operator runbook drill, final acceptance matrix, constitution audit); เพิ่ม verification/troubleshooting/escalation ที่เกี่ยวกับ public deployment; ยังไม่มี Windows evidence ใด ๆ |
| 2026-09-04 | Claude (public-deployment planning) | v4.0 — แทนที่โมเดล router-ของ-operator-เอง ด้วย topology ที่อนุมัติจริง: Public IP จากมหาวิทยาลัย (`161.200.90.4`) บน edge server แยกเครื่อง เชื่อมกับ GPU laptop ผ่าน WireGuard tunnel เพื่อให้ laptop ย้ายเครือข่ายได้ เขียนใหม่ Network boundary section, รายการ owner-gate ใน Step 22, Step 26 (T089 เปลี่ยนจาก router forwarding เป็นการยืนยัน border firewall), และรายการ checklist/troubleshooting/escalation ที่เกี่ยวข้อง แก้ constitution เป็น 1.1.0 ในการเปลี่ยนแปลงเดียวกันเพื่ออนุญาตนโยบายไม่มี site-wide login อย่างชัดเจน ดูเหตุผลเต็มที่ `C:\Users\MetaHosP\.claude\plans\router-ai-eventual-tide.md`; ยังไม่มี Windows evidence ใด ๆ |
