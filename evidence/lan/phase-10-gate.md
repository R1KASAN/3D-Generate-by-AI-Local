# Phase 10 LAN Gate (T084)

- Date/time (UTC): 2026-09-03T18:41:16.266976+00:00
- Host: `LAPTOP-9PI3K9F7`, Windows 11, RTX 5070 Laptop GPU
- Approved LAN entry: `http://172.20.10.6:3000/`
- Phase 9 prerequisite: **PASS**
- Phase 10 purpose: prove unattended services and the real application flow
  from a second device on the private LAN without exposing API or ComfyUI.

| Task | Evidence | Verdict |
|---|---|---|
| T080 services | [service-startup.md](service-startup.md); service verification at `2026-09-03T16:33:59.3673216Z`; post-service Job `5fe7fa05-ad26-40ab-8dcf-07b9b0ead925`, SHA `cdd4e0db15eea92c4cd76d120ed258a5661037b068cfeeb6a96c45a1889f7f8a` | **PASS** |
| T081 reboot recovery | [reboot-recovery.md](reboot-recovery.md); reboot verification at `2026-09-03T16:34:00.0717036Z`; recovered Job `5fe7fa05-ad26-40ab-8dcf-07b9b0ead925` completed | **PASS** |
| T082 LAN full flow | [full-flow.md](full-flow.md); second-client Job `8cb6b67e-4fda-4350-a6ee-7bc2a1a0c638` completed and downloaded with matching SHA `7d013674048ec81ad15193f0c1eb61428f70a9d4b19e985844262bb9d5241fd2` | **PASS** |
| T083 LAN boundary | [isolation-and-ports.md](isolation-and-ports.md); second-client run at `2026-09-03T17:23:48.152736+00:00`; ports `8000`/`8188` blocked and cross-job responses `404,404` | **PASS** |

## Gate checks

- All three Windows services are installed, automatic, running as
  `NT AUTHORITY\LocalService`, and ordered ComfyUI → API → Web.
- The reboot evidence proves automatic startup, restart reconciliation, and a
  new real textured generation without manually opening terminals.
- The second LAN client used only port `3000`; API and ComfyUI remained
  loopback-only.
- The full-flow output is byte-identical: `4,088,380` bytes and SHA-256
  `7d013674048ec81ad15193f0c1eb61428f70a9d4b19e985844262bb9d5241fd2`.
- Evidence contains no raw capability tokens, private traces, or credentials.

**Phase 10 verdict: PASS.** T080–T083 are complete.
