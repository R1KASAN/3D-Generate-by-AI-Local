# Windows Service Startup Evidence (T080)

- Date/time (UTC): 2026-09-03T16:33:59.3673216Z
- Host: LAPTOP-9PI3K9F7
- Service wrapper: WinSW v2 definitions; no wrapper binary or credentials are committed.
- Required order: Local3D-ComfyUI -> Local3D-API -> Local3D-Web.
- Restricted identity: built-in `LocalService`; services bind to loopback only.

| Check | Observed | Expected | Verdict |
|---|---|---|---|
| definition:Local3D-ComfyUI | id=Local3D-ComfyUI; account=NT AUTHORITY\LocalService; bind=127.0.0.1:8188; paths_exist=True; startmode=Automatic; dependency= | valid XML, LocalService, existing executable/workdir, automatic start, required private bind and dependency | **PASS** |
| definition:Local3D-API | id=Local3D-API; account=NT AUTHORITY\LocalService; bind=127.0.0.1:8000; paths_exist=True; startmode=Automatic; dependency=Local3D-ComfyUI | valid XML, LocalService, existing executable/workdir, automatic start, required private bind and dependency | **PASS** |
| definition:Local3D-Web | id=Local3D-Web; account=NT AUTHORITY\LocalService; bind=127.0.0.1:3000; paths_exist=True; startmode=Automatic; dependency=Local3D-API | valid XML, LocalService, existing executable/workdir, automatic start, required private bind and dependency | **PASS** |
| installed:Local3D-ComfyUI | state=Running; start_mode=Auto; start_name=NT AUTHORITY\LocalService | running under LocalService | **PASS** |
| installed:Local3D-API | state=Running; start_mode=Auto; start_name=NT AUTHORITY\LocalService | running under LocalService | **PASS** |
| installed:Local3D-Web | state=Running; start_mode=Auto; start_name=NT AUTHORITY\LocalService | running under LocalService | **PASS** |
| health | api=200; comfyui=200; web=200 | API, ComfyUI, and web service healthy after ordered startup | **PASS** |
| post-service-generation | job_id=5fe7fa05-ad26-40ab-8dcf-07b9b0ead925; size=3664968; sha256=cdd4e0db15eea92c4cd76d120ed258a5661037b068cfeeb6a96c45a1889f7f8a | one new real textured GLB through the installed services | **PASS** |

- Static definitions are reviewable and keep API, web, and ComfyUI on `127.0.0.1`; no direct LAN bind is introduced.
- A PASS requires installed/running restricted services and a new real textured generation after service startup.
- Overall verdict: **PASS**
