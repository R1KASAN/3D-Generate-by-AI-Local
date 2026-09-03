# Windows Real-Engine Recovery Matrix (T078)

- Date/time (UTC): 2026-09-03T12:41:40.2310098Z to 2026-09-03T12:41:57.8540678Z
- Host: LAPTOP-9PI3K9F7
- ComfyUI: 0.34.0, loopback http://127.0.0.1:8188
- GPU: cuda:0 NVIDIA GeForce RTX 5070 Laptop GPU : cudaMallocAsync
- Scope: controlled failure/recovery cases; no automatic resubmission is performed by this runner.

| Case | Observed | Expected | Verdict |
|---|---|---|---|
| baseline | healthy version=0.34.0; gpu=cuda:0 NVIDIA GeForce RTX 5070 Laptop GPU : cudaMallocAsync; queue_running=0; queue_pending=0 | loopback ComfyUI healthy with an empty queue before recovery cases | **PASS** |
| engine failure | POST /prompt returned HTTP 400 for an unknown node | 4xx rejection before engine execution | **PASS** |
| timeout | pytest exit 0: .                                                                        [100%] 1 passed, 9 deselected in 0.06s | client timeout maps to a safe unknown/generation_timeout observation | **PASS** |
| disconnect | connection refused/unreachable as expected; pytest exit 0: .                                                                        [100%] 1 passed, 9 deselected in 0.05s | engine disconnect maps safely and no alternate endpoint is contacted | **PASS** |
| missing output | pytest exit 0: .                                                                        [100%] 1 passed, 5 deselected in 0.01s | zero GLB candidates are rejected and never published | **PASS** |
| backend restart | pytest exit 0: ...                                                                      [100%] 3 passed, 4 deselected in 0.37s | queued work rehydrates safely; processing uncertainty becomes restart_recovery; duplicate submissions=0 | **PASS** |
| ComfyUI restart | stopped=True; restarted_pid=31912; healthy_version=0.34.0; queue_running=0; queue_pending=0; glb_snapshot_unchanged=True; duration=12.7s | same pinned loopback instance returns healthy with empty queue and no new/overwritten job outputs | **PASS** |

- Phase 9 output GLB snapshot before/after ComfyUI restart: 4 / 4 files; changed outputs: False.
- Duplicate execution verdict: **0** observed in the controlled matrix; no case resubmitted a prompt after timeout, disconnect, missing output, backend restart, or ComfyUI restart.
- Sensitive engine payloads, credentials, uploaded image content, and private stack traces are intentionally omitted.

Verdict: **PASS**
