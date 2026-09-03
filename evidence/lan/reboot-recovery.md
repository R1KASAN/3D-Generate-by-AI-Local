# Windows Reboot Recovery Evidence (T081)

- Date/time (UTC): 2026-09-03T16:34:00.0717036Z
- Host: LAPTOP-9PI3K9F7
- Scope: automatic service startup, durable-state reconciliation, and one new real generation after reboot.

| Check | Observed | Expected | Verdict |
|---|---|---|---|
| services installed | True | all three WinSW services installed | **PASS** |
| automatic startup | True | all three services configured for automatic startup | **PASS** |
| restricted identity | True | all three services run as LocalService | **PASS** |
| machine reboot and health | previous_boot=2026-08-27T02:49:59.9538430Z; current_boot=2026-09-03T16:26:04.5000000Z; api/comfyui/web=200 | boot time changed and all loopback health checks passed without opening terminals | **PASS** |
| non-terminal reconciliation | job_id=708ad848-525c-4eb9-adce-869ad5c0d6f5; status=failed; error_code=restart_recovery; attempt_count=1 | pre-reboot processing job becomes failed/restart_recovery without duplicate submission | **PASS** |
| new real generation | job_id=5fe7fa05-ad26-40ab-8dcf-07b9b0ead925; size=3664968; sha256=cdd4e0db15eea92c4cd76d120ed258a5661037b068cfeeb6a96c45a1889f7f8a | one new textured GLB after automatic startup | **PASS** |

- No raw job token is persisted in reboot state or evidence.
- Smallest next action: none; retain this evidence.
- Overall verdict: **PASS**
