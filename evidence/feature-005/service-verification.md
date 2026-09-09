# Windows Service Startup Evidence (T080)

- Date/time (UTC): 2026-09-09T07:31:29.6822778Z
- Host: LAPTOP-9PI3K9F7
- Service wrapper: WinSW v2 definitions; no wrapper binary or credentials are committed.
- Required order: Local3D-ComfyUI -> Local3D-API -> Local3D-Web.
- Restricted identity: built-in `LocalService`; services bind to loopback only.

| Check | Observed | Expected | Verdict |
|---|---|---|---|
| definition:Local3D-ComfyUI | id=Local3D-ComfyUI; account=NT AUTHORITY\LocalService; bind=127.0.0.1:8188; paths_exist=True; startmode=Automatic; dependency= | valid XML, LocalService, existing executable/workdir, automatic start, required private bind and dependency | **PASS** |
| definition:Local3D-API | id=Local3D-API; account=NT AUTHORITY\LocalService; bind=127.0.0.1:8000; paths_exist=True; startmode=Automatic; dependency=Local3D-ComfyUI | valid XML, LocalService, existing executable/workdir, automatic start, required private bind and dependency | **PASS** |
| definition:Local3D-Nginx | id=Local3D-Nginx; account=NT AUTHORITY\LocalService; bind=127.0.0.1:8080; paths_exist=True; startmode=Automatic; dependency=Local3D-API | valid XML, LocalService, existing executable/workdir, automatic start, required private bind and dependency | **PASS** |
| installed:Local3D-ComfyUI | state=Running; start_mode=Auto; start_name=NT AUTHORITY\LocalService | running under LocalService | **PASS** |
| installed:Local3D-API | state=Running; start_mode=Auto; start_name=NT AUTHORITY\LocalService | running under LocalService | **PASS** |
| installed:Local3D-Nginx | state=Running; start_mode=Auto; start_name=NT AUTHORITY\LocalService | running under LocalService | **PASS** |
| health | api=200; comfyui=200; nginx=200 | API, ComfyUI, and Nginx healthy after ordered startup | **PASS** |
| post-service-generation | not attempted; rerun with -RunGeneration | one new real textured GLB through the installed services | **BLOCKED** |

- Static definitions are reviewable and keep API, web, and ComfyUI on `127.0.0.1`; no direct LAN bind is introduced.
- A PASS requires installed/running restricted services and a new real textured generation after service startup.
- Overall verdict: **BLOCKED**

The three-trial recovery runner was also preflighted after adding an explicit
cloudflared requirement. It returned **BLOCKED** because the `cloudflared`
Windows service is not installed; no service was restarted and no trial was
counted.
