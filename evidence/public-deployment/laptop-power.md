# Laptop power-policy evidence

**Feature:** `002-cloudflare-public-entry`  
**Task:** T033  
**Checked:** 2026-09-05  
**Host:** Local Lenovo Windows 11 laptop; NVIDIA GeForce RTX 5070 Laptop GPU

## Applied AC policy

The active power scheme was updated with `powercfg` and reactivated:

```text
powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP STANDBYIDLE 0
powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP HIBERNATEIDLE 0
powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /setactive SCHEME_CURRENT
```

## Verification

| Setting | AC result | Meaning |
|---|---:|---|
| `STANDBYIDLE` | `0` | Never automatically suspend while powered. |
| `HIBERNATEIDLE` | `0` | Never automatically hibernate while powered. |
| `LIDACTION` | `0` | Do nothing when the lid is closed while powered. |

**Overall verdict: PASS.** No machine identifiers, credentials, network
addresses, or private configuration were recorded.
