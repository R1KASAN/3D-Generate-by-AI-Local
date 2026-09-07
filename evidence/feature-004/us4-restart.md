# Feature 004 Notebook Restart Trial Preparation

The three-trial runner was executed by the operator for all required Notebook
restart trials. It records only opaque Job IDs and sanitized recovery fields.

## Prepared command (elevated PowerShell)

```powershell
Set-Location 'C:\Users\MetaHosP\Desktop\3D-Generate-by-AI-Local'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\verify_reboot_recovery.ps1 `
  -ProjectRoot (Get-Location).Path `
  -EvidencePath (Join-Path (Get-Location).Path 'evidence\feature-004\us4-restart.md') `
  -TrialNumber 1 -TrialCount 3 -ExecuteReboot
```

The runner prepares a queued or running probe (trial 2 is queued by default,
trials 1 and 3 are running), stores only opaque Job IDs and boot metadata, and
registers a one-shot startup verifier. After each reboot it verifies all four
Local3D services, Caddy/API/Web/ComfyUI readiness within 300 seconds, safe
restart reconciliation, attempt count, and engine queue counts without writing
tokens, content, or engine identifiers. Repeat with `-TrialNumber 2` and `3`
only after the preceding trial evidence is reviewed.

## Current verdict

**PASS** - Trial 1, Trial 2 (queued probe), and Trial 3 each restored the
local service stack within the five-minute limit and recorded a safe probe
outcome without tokens, content, or engine identifiers.

## Re-entry check (2026-09-07)

The evidence now contains the required numbered Trial 1, Trial 2, and Trial 3
records. Earlier duplicate Trial 1 records are retained as historical evidence
and do not change the three-trial verdict.
## Trial 1 of 3 - Running

- Verified at (UTC): 2026-09-06T21:49:58.6735662Z
- Local readiness restored in: 111.4 seconds (limit: 300)
- Boot time changed: true
- Orphan-engine report: running=1; pending=0; identifiers omitted
- Probe $(@{job_id=0d8b4244-ebcd-484b-9ec5-f2548c8452f7; status=failed; error_code=restart_recovery; attempt_count=1; updated_at=2026-09-06T21:49:53.814201+00:00; event_count=4}.job_id): status=failed; error=restart_recovery; attempts=1; events=4
- Verdict: **PASS**

## Trial 1 of 3 - Running

- Verified at (UTC): 2026-09-06T21:54:34.0881284Z
- Local readiness restored in: 11.5 seconds (limit: 300)
- Boot time changed: true
- Orphan-engine report: running=0; pending=0; identifiers omitted
- Probe $(@{job_id=eabacb4e-eb85-49fb-815a-3677a47fc862; status=failed; error_code=restart_recovery; attempt_count=1; updated_at=2026-09-06T21:54:31.397095+00:00; event_count=4}.job_id): status=failed; error=restart_recovery; attempts=1; events=4
- Verdict: **PASS**

## Trial 2 of 3 - Queued

- Verified at (UTC): 2026-09-06T21:58:16.5010523Z
- Local readiness restored in: 12.6 seconds (limit: 300)
- Boot time changed: true
- Orphan-engine report: running=1; pending=0; identifiers omitted
- Probe $(@{job_id=bd76df98-624e-4731-b2e3-ce3f951d1dc6; status=processing; error_code=; attempt_count=1; updated_at=2026-09-06T21:58:13.521173+00:00; event_count=2}.job_id): status=processing; error=; attempts=1; events=2
- Verdict: **PASS**

## Trial 3 of 3 - Running

- Verified at (UTC): 2026-09-06T22:18:21.3955607Z
- Local readiness restored in: 16.7 seconds (limit: 300)
- Boot time changed: true
- Orphan-engine report: running=0; pending=0; identifiers omitted
- Probe $(@{job_id=8387cf73-682a-4ebc-9683-66e8e5b15808; status=failed; error_code=restart_recovery; attempt_count=1; updated_at=2026-09-06T22:18:17.835311+00:00; event_count=4}.job_id): status=failed; error=restart_recovery; attempts=1; events=4
- Verdict: **PASS**
