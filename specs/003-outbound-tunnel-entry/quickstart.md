# Quickstart: Validating the Public AI Server

**Feature**: `003-outbound-tunnel-entry` | **Date**: 2026-09-06

Runnable validation for the split-host outbound-tunnel deployment. Grouped by what each stage needs, so the ungated work can be validated **now** while hostname authorization is outstanding (FR-012a).

Contracts referenced rather than repeated: [origin-entry](contracts/origin-entry.md), [compute-link](contracts/compute-link.md), [health-chain](contracts/health-chain.md), [evidence-methods](contracts/evidence-methods.md).

---

## Stage 0 — Prerequisites

| Requirement | Needed for | Status |
|---|---|---|
| GPU laptop with feature 001 healthy | everything | available |
| Physical or remote access to the approved origin | stages 2+ | **origin OS unverified** |
| WireGuard binding configured both sides | stages 2+ | carried forward from feature 002 |
| Cloudflare account (any) | stage 3 | needed for Quick Tunnel |
| Cloudflare account managing `mangosgo.com` | stage 5 | **pending authorization** |
| External network (mobile data) | stages 3, 5 | required for acceptance |

> Do **not** run stage 5 until the hostname is authorized. Update 2026-09-06: live-origin work in stages 2–6 is MANUAL/BLOCKED until authorized access is available. No public management probes. Local software checks may continue.

---

## Stage 1 — LAN independence *(no origin required)*

The highest-value check, because it validates the deadlock fix.

```bash
python scripts/verify/test_lan_independence.py --lan-base-url <LAN-URL> --image fixtures/inputs/valid-reference.png --confirm-binding-down
```

**Setup**: stop WireGuard on the laptop, ensure the origin is unreachable, then reboot the laptop.

**Expected**:

| Check | Expected |
|---|---|
| Feature 001 reachable from a LAN peer | ✅ works |
| Upload → generate → preview → download on LAN | ✅ completes |
| Any service bound exclusively to `10.10.0.2` | ❌ none |
| Web service still declares a WireGuard dependency | ❌ none |

Then start WireGuard **without restarting the application**:

| Check | Expected |
|---|---|
| Public path resumes automatically | ✅ (SC-006e) |
| Application restart required | ❌ never |

**Historical pre-fix failure.** `web.xml` binds `10.10.0.2` and declares `<depend>WireGuardTunnel$upstream</depend>`; `start_web_service.ps1` polls for the tunnel address before starting. See [compute-link C4](contracts/compute-link.md).

---

## Stage 2 — Origin pass-through *(origin required, no public name)*

```bash
python -m pytest tests/security/test_caddy_contract.py -v
```

**Expected**:

| Check | Expected | Requirement |
|---|---|---|
| Proxy binds loopback only | ✅ | FR-004 |
| No public `:443` listener | ✅ | FR-003 |
| No Origin CA cert / client-auth config | ✅ removed | [origin-entry O2](contracts/origin-entry.md) |
| `buffer_requests` / `buffer_responses` | ❌ **absent** | FR-014a |
| Body guard above 10 MiB | ✅ | FR-019 |
| `X-Job-Token` / `Cookie` / `Authorization` log-stripped | ✅ | FR-017 |

Streaming proof (SC-002b) — during a maximum-size upload and download:

```bash
python scripts/verify/test_external_acceptance.py --streaming-only
```

Assert no app- or proxy-authored spool or complete-body temp file appears. OS paging is out of scope.

---

## Stage 3 — Interim external journey *(Quick Tunnel)*

```bash
cloudflared tunnel --url http://127.0.0.1:8443
```

Exercises the real path — origin pass-through, private binding, feature 001 — with only the public name differing (FR-012b).

**Valid evidence**: upload, generation, status polling, preview, download, token authorization, unavailable behavior.

**NOT valid evidence**: concurrency or load. Quick tunnels cap at 200 concurrent requests. Do not present interim numbers as production characteristics.

**Not affected**: the no-SSE limitation. The browser polls over HTTP (`apps/web/lib/jobs/use-job-status.ts`) and the only WebSocket use is job-service → ComfyUI on the laptop, which never crosses the tunnel.

---

## Stage 4 — Health chain and recovery *(both machines)*

```bash
pwsh scripts/windows/health_chain.ps1 -All
```

Each layer must report independently ([health-chain H1](contracts/health-chain.md)).

**Induced-fault matrix** — each fault must name its own layer, not a generic outage:

| Induce | Expected named layer | Public response |
|---|---|---|
| Stop connector | origin/connector | provider error (SC-008a) |
| Stop WireGuard | private binding | project page ≤5s |
| Stop job service | job service | project page ≤5s |
| Stop ComfyUI | AI engine | project page ≤5s |

**Reboot matrix** (SC-006 … SC-006b) — 3× each: origin only, laptop only, both origin-first, both laptop-first. Every trial must recover with no operator action.

**Recovery policy** (FR-024): the failed layer restarts first; unrelated healthy layers are left alone; a dependent layer is restarted only if still unhealthy after its dependency returned and a grace period elapsed; looping stops after 3 failures at one layer.

**Mobility matrix** (FR-040, SC-017) — move the GPU laptop between at least two distinct external networks (for example university or home Wi-Fi and a mobile hotspot). It must reconnect on its own, and the public DNS record, public hostname, provider tunnel route, approved-origin configuration, feature 001 application configuration, and WireGuard tunnel addressing must all be unchanged before and after every move. `scripts/verify/test_mobility.py` snapshots the configuration files and fails the run if any of them changed.

```bash
python scripts/verify/test_mobility.py --hostname <public-hostname> --confirm-off-campus
```

**Decide before running**: GPU/AI-engine layer order, per [health-chain H2](contracts/health-chain.md).

---

## Stage 5 — Production cutover *(BLOCKED on authorization)*

> Do not start until written authorization for `twin3dgen.mangosgo.com` exists and the route is created in the Cloudflare account managing that zone (FR-011, FR-033).

```bash
python scripts/verify/test_egress_identity.py --provider cloudflare
python scripts/verify/test_dns_disclosure.py
python scripts/verify/test_origin_lockdown.py
python scripts/verify/test_external_acceptance.py
```

| Check | Criterion |
|---|---|
| Off-LAN journey completes | SC-001 |
| Tagged request correlated at the origin | SC-002 |
| Connector reports the approved origin address | SC-002a |
| No direct Internet-facing application or management response anywhere (the C1a WireGuard transport port is permitted and is never probed as prohibited; `test_origin_lockdown.py` exits non-zero on any dropped or unclassifiable probe rather than reporting a pass) | SC-003 |
| Origin transport boundary matches the C1a declaration | SC-018 |
| Origin directly receives the WireGuard UDP transport without router forwarding | FR-041 |
| Laptop reconnects across at least two external networks with nothing edited | SC-017 |
| DNS returns no origin address; no `A` record to the origin | SC-004, FR-011b |
| Zero cost; no card; no billable fallback | SC-005 |
| Token absent from every project-controlled log | SC-009 |
| Cross-job / missing / expired token indistinguishable | SC-010 |
| Five simultaneous submissions → one GPU job at a time | SC-011 |
| Credential revocation stops traffic; replacement restores | SC-013 |

---

## Stage 6 — Fallback rehearsal *(cause-gated)*

Per [evidence-methods E4](contracts/evidence-methods.md):

| Rehearsal | Expected |
|---|---|
| Hostname never authorized | Public release stays **blocked**; LAN-only; zrok/Quick Tunnel dev-only (SC-014b) |
| Live hostname withdrawn | zrok activates as degraded production; cause, start time, recovery window recorded |
| During fallback | Connector on the **approved origin**; requests traverse it before the laptop (SC-014d) |
| During fallback | Residual-exposure record names **zrok**, not Cloudflare (SC-014e) |

**Blocked input**: the recovery window is an owner value that has not been supplied. Record it before relying on the fallback.

---

## What is blocked, and by what

| Blocker | Blocks | Does not block |
|---|---|---|
| `mangosgo.com` authorization | Stage 5 | Stages 1–4, 6 rehearsal |
| Origin OS unverified | Per-OS service units | OS-independent config and contracts |
| Origin address bindability | Source-address binding | Egress **observation** |
| Recovery-window value | Relying on the fallback | Building it |
| Origin-local access | Live transport-boundary evidence (T066a) | Declaring and statically verifying the boundary (T058a, T058b) |
| Direct UDP reachability unverified | Cutover — **and Option A itself** (FR-041, T066b) | Every other stage |
| Two external networks + live route | Mobility acceptance (T036a) | The mobility design, already fixed by C1/C1b |
