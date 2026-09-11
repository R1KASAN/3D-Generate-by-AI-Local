# Feature 003 — Outstanding Issues Handoff Prompt

**Generated**: 2026-09-06 | **Repo**: `3D-Generate-by-AI-Local` | **Branch**: `main` @ `3b0a361`

Paste this whole file as your opening prompt in a fresh session.

---

## Your role

You are continuing work on feature `003-outbound-tunnel-entry`: promoting a LAN-only
local 3D AI generation service into a public service through an **outbound** Cloudflare
Tunnel, at zero additional cost. The authoritative artifacts are:

- `specs/003-outbound-tunnel-entry/spec.md` — 56 FRs, 31 SCs
- `specs/003-outbound-tunnel-entry/plan.md`, `tasks.md` (91 tasks), `contracts/`
- `.specify/memory/constitution.md` v1.2.0 — **non-negotiable**

**Task state**: 52 complete, 39 blocked on live-target/owner/provider access, 0 open and
locally actionable. Working tree is clean except an untracked `output/` (an unrelated
`.docx` export — leave it alone).

---

## HIGHEST PRIORITY — an unresolved factual contradiction, resolve before anything else

The owner stated: *"PC โน็ตบุ็คที่เราใช้ก็คือ server 161.200.90.4 ครับ สามารถทำได้เลยครับ"*
(the laptop we use **is** server 161.200.90.4, go ahead immediately).

**Direct measurement on 2026-09-06 contradicts this:**

| Check | Result |
|---|---|
| Local IPv4 on this laptop | `172.20.10.6` (mobile-hotspot range), plus link-local only |
| Is `161.200.90.4` bound locally? | **No** |
| Actual public egress | **`223.24.180.35`** (Thai mobile carrier) |
| ICMP / TCP 443 / TCP 80 to `161.200.90.4` | No response (also recorded 2026-09-05) |
| WireGuard installed on this laptop | **Not installed at all** — no service, no binary, no config |

### Why this matters more than anything else on the list

A full public journey was demonstrated end-to-end today through a Cloudflare Quick Tunnel
(details below). It proves the **mechanism** works. It does **not** satisfy FR-002,
FR-002a, SC-002 or SC-002a, because the traffic never touched the Approved Origin — it
went laptop → mobile hotspot → Cloudflare. Do not let that demo be recorded, summarised,
or carried forward as approved-origin evidence. It is not.

### What to do

Do **not** silently pick an interpretation. Ask the owner to disambiguate, offering these
readings:

1. A **different** physical PC in the lab holds `161.200.90.4`, and this laptop is a
   separate machine → the split-host design (FR-014) stands as written.
2. The laptop is normally on a lab network whose **egress** is `161.200.90.4`, and was
   merely on a hotspot during testing → verify by re-running the egress check while on
   the lab network. Note this still would not make the address *bindable* (FR-002a, T066).
3. The topology genuinely changed to single-host → then **FR-013 vs FR-014 must be
   formally re-decided**, and the WireGuard compute link, Option A, C1a, SC-018, FR-040,
   FR-041, T066a and T066b all become moot or need rewriting. This is a spec change, not
   an implementation detail.

Until this is settled, do not modify the spec's topology requirements and do not mark any
approved-origin task complete.

---

## Already fixed this session — do not redo, but do read the reasoning

All four were found only by running real traffic through a real public tunnel; every one
was invisible to local testing.

| Commit | Issue | Why local tests missed it |
|---|---|---|
| `bf8a177` | Caddy site address `http://127.0.0.1:8443` also acted as a **Host-header matcher**, so every request the connector forwarded (carrying the public hostname) fell through unmatched and returned an empty 200. Confirmed identical with `Host: twin3dgen.mangosgo.com` — it would have broken production cutover too. Fixed with `:8443` + `bind 127.0.0.1`. | `curl` to `127.0.0.1` sends the one Host value that happened to match |
| `4989119` | **Capability token written to Caddy's error log in cleartext** — 3 occurrences during a single 504, while the access log correctly held 0. Violated FR-017 / SC-009. Fixed with a filtered `log default` in global options. | Needed a real error and a real token at the same moment; prior checks grepped only the access-log file |
| `fc14beb` | Maintenance page root hardcoded to the Unix path `/srv/caddy/maintenance`; on a host without it, `handle_errors` 404s and the visitor gets a bare empty 504 instead of the FR-025 page. Parameterised as `CADDY_MAINTENANCE_ROOT`. | Required the engine to actually fail |
| `3b0a361` | A single stalled ComfyUI status read became terminal `generation_timeout`, discarding healthy in-flight GPU work. Bounded retry (2 extra reads, 0.5s/1.5s backoff) added. | Needed sustained GPU load |

---

## Issue 1 — Verify the status-poll retry actually works under live load

**Status**: implemented and unit-tested, **not yet validated live**.

Evidence that motivated it: jobs failed at 125s and 194s while others on the same engine
**completed at 240s and 306s** — successes ran longer than failures, ruling out generation
duration and pointing at the status read.

**Do this**: restart Caddy and a Quick Tunnel, submit several jobs under real GPU load, and
measure whether `generation_timeout` failures still occur.

The owner has already pre-authorised the follow-up:

> "If transient retry still proves insufficient in live testing, then evaluate history
> reconciliation (Option C) as a second-stage improvement."

So if failures persist, evaluate Option C — reconcile against ComfyUI's `/history` before
marking a job failed — but **do not** broaden it into a larger feature-001 redesign.

**Acceptance**: ≥5 consecutive jobs complete under load with zero `generation_timeout`, or
a documented finding that the retry is insufficient plus an Option C proposal.

---

## Issue 2 — Caddy's engine health gate returns raw 504s under load

`deploy/caddy/Caddyfile` pre-checks `/api/v1/health/engine` before relaying each request,
with `response_header_timeout 2s`. During a genuine engine stall this produced runs of
504s — measured at exactly 2.00s each — meaning **the public site was intermittently
unusable for over a minute at a time** while a generation ran.

Two sub-problems, and they are separate:

1. The gate adds an extra hop (Caddy → Next.js → FastAPI → ComfyUI) on **every single
   request**, so any engine stall becomes a site-wide outage.
2. Even when it fires correctly, the visitor should get the FR-025 project page. That
   half is fixed by `fc14beb`, but only if `CADDY_MAINTENANCE_ROOT` is actually set —
   verify it is set wherever Caddy runs.

**Consider**: raising the gate timeout, caching the health result for a few seconds, or
dropping the per-request gate in favour of Caddy's existing passive `fail_duration`
health checking. Any change must keep FR-025 (project-controlled unavailable response
within 5s, no internal detail disclosed) and must not add a login or credential
dependency.

---

## Issue 3 — Deployed services can silently run stale code

`Local3D-API` was running a build without the `/api/v1/health/engine` endpoint even though
the code was committed and its tests passed. Caddy's health gate therefore saw 404, judged
the engine down, and served the unavailable path for **every** request. Restarting the
service fixed it.

There is no deployment step that restarts services after a code change, and nothing
detects the drift.

**Do this**: add a post-deploy service-restart step to
`docs/operations/windows-ai-server-runbook.en.md` and its Thai counterpart, and consider a
health-chain check that compares the running API's advertised routes against what the repo
expects. Note `Restart-Service` needs Administrator — the agent session does not have it,
so the runbook must say so explicitly.

---

## Issue 4 — Leftover test jobs in the live database

`storage/jobs.sqlite3` holds 18 rows: 4 completed, 14 failed. Many failures are artifacts
of this session's service restarts (`restart_recovery`, `engine_unavailable`) rather than
real defects. Several stale `queued` rows from 2026-09-05 were re-dispatched today and
consumed real GPU time before failing.

**Do this**: decide with the owner whether to purge test rows. Do **not** purge
unilaterally — `evidence/` records reference job outcomes, and FR-028's 24-hour retention
policy governs cleanup. If purging is approved, confirm the retention job is what performs
it rather than a manual delete.

---

## Open decisions that only the owner can make

These block cutover, not implementation (FR-012a). Do not invent answers.

| # | Decision | Blocks | Where recorded |
|---|---|---|---|
| 1 | The address contradiction above | Everything origin-related | — |
| 2 | Which Cloudflare account, and written authorization to use it | T045, T081–T083 | `evidence/public-deployment/hostname-authorization.md` |
| 3 | Final hostname — `twin3dgen.mangosgo.com` (in spec) vs `yami.one` (seen in the owner's dashboard screenshots) | FR-011, naming continuity | spec Owner Decisions |
| 4 | Remotely-managed tunnel (dashboard + token, what the owner already uses) vs locally-managed (`config.yml` + credentials file, what the repo prepared) | T021, T022, `deploy/cloudflared/` | — |
| 5 | zrok degraded-fallback recovery window | T046 | `evidence/public-deployment/fallback-policy.md` |
| 6 | Written acceptance of zrok's separate TLS residual exposure | T048 | same file |
| 7 | Management channel for the lab origin — console-only / VPN-scoped SSH / Internet-facing SSH | All live-origin tasks | `evidence/public-deployment/management-access.md` (template ready, all `PENDING`) |

For #4, note the token in a remotely-managed tunnel **is** a credential under FR-032 — it
must never reach Git or shell history.

---

## Hard constraints — do not violate these

- **No inbound application or management listener** on the approved origin. The single
  permitted inbound socket is the narrowly scoped WireGuard UDP transport listener defined
  by compute-link contract C1a — and only if Option A survives the topology question above.
- **No router port forwarding**, no public application port, no public GPU-laptop
  listener, no paid relay or VPS. FR-041 makes these forbidden even as workarounds: if the
  origin cannot receive the transport directly, Option A is void and the transport must be
  redesigned.
- **Zero additional project cost** (FR-007, FR-008). No payment card, no paid plan.
- **Do not probe `161.200.90.4`** to discover ports or management services. The owner
  instructed this explicitly and the runbooks forbid it; the IP allocation memo names a
  *different* project, so a scan would be hard to justify.
- **Do not treat the Quick Tunnel hostname as production identity** (FR-012).
- **Do not mark a hardware- or network-dependent task complete** without real evidence
  from the real target. 39 tasks are legitimately blocked; leaving them blocked is correct.

---

## Verification commands

```bash
# Full local suites — both must stay green
cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/ -q    # 131 passed, 4 skipped
cd ../.. && python -m pytest tests/security -q                    # 116 passed, 1 skipped

# Caddy config validity
./tmp/caddy-validation/caddy.exe validate --config deploy/caddy/Caddyfile --adapter caddyfile

# Re-check the address contradiction
python -c "import urllib.request; print(urllib.request.urlopen('https://api.ipify.org',timeout=10).read().decode())"
```

To bring the public path back up (three env vars matter — the maintenance root is the one
most easily forgotten):

```powershell
$env:UPSTREAM_ORIGIN='http://127.0.0.1:3000'
$env:CADDY_MAINTENANCE_ROOT='C:\Users\MetaHosP\Desktop\3D-Generate-by-AI-Local\deploy\caddy\maintenance'
$env:CADDY_LOG_PATH='<a writable path>'
.\tmp\caddy-validation\caddy.exe run --config deploy\caddy\Caddyfile --adapter caddyfile
```

```powershell
& "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://127.0.0.1:8443
```

---

## Working style expected here

Report findings honestly, including negative ones — today's most valuable output was three
bugs and one contradiction, not the demo that worked. State plainly when something was not
verified rather than implying it was. When a measurement contradicts what you were told,
say so directly and show the measurement.
