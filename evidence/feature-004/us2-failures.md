# Feature 004 Application Recovery Matrix

- Date/time (UTC): 2026-09-06T21:32:59.8662582Z
- Scope: queued/running reconciliation, orphan-engine reporting, and optional controlled service restarts.
- Engine prompt identifiers, tokens, user content, and private paths are omitted.

| Check | Sanitized observation | Verdict |
|---|---|---|
| service definitions | four approved single-node services installed | **PASS** |
| orphan-engine baseline | queue_running=0; queue_pending=0; identifiers omitted | **PASS** |
| invalid input and pressure | ...........                                                              [100%] 11 passed in 1.60s | **PASS** |
| low disk and orphan cleanup | .....                                                                    [100%] 5 passed in 0.19s | **PASS** |
| hang timeout cancellation missing output | ...........                                                              [100%] 11 passed in 1.30s | **PASS** |
| corrupt and partial output rejection | .........                                                                [100%] 9 passed in 0.10s | **PASS** |
| Local3D-Caddy controlled restart | healthy after 0.6s | **PASS** |
| Local3D-Web controlled restart | healthy after 1.5s | **PASS** |
| Local3D-API controlled restart | healthy after 2.0s | **PASS** |
| Local3D-ComfyUI controlled restart | healthy after 16.3s | **PASS** |
| orphan-engine result | queue_running=0; queue_pending=0; identifiers omitted | **PASS** |

- Controlled service restarts executed: **True**
- Overall verdict: **PASS**
