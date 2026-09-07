# Research: Single-Node AI Generation with Secure Public Test Access

**Date**: 2026-09-06

**Feature**: `004-secure-ai-test-access`

**Status**: Complete; no unresolved clarification remains

This research combines a read-only repository assessment with current official
Cloudflare, Caddy, and ComfyUI documentation. Decisions here apply to feature
004. Historical features 002 and 003 remain useful records but are not active
topology authority where they conflict with Constitution 2.0.0.

## R1. Preserve the existing application stack

**Decision**: Keep Python 3.12/FastAPI/Uvicorn, SQLite with per-job filesystem
storage, Next.js 16/React 19/TypeScript, Caddy, cloudflared, WinSW, the existing
ComfyUI adapter boundary, and the pinned Hunyuan3D workflow. Keep one FastAPI
process and one in-process serial dispatcher.

**Rationale**: The repository already implements the primary user journey,
content validation, job capability tokens, durable admission, one-job GPU
queue, recovery, GLB validation/publication, preview, and download. Baseline
validation was green before planning:

- `uv run --project apps/api pytest`: 247 passed, 5 skipped.
- `npm --prefix apps/web test`: 8 passed.
- `npm --prefix apps/web run typecheck`: passed.
- `npm --prefix apps/web run lint`: passed.

The exact dependencies are already pinned in `apps/api/pyproject.toml` and
`apps/web/package.json`. One API process is necessary because the dispatcher is
in-process; adding Uvicorn workers without shared coordination would violate
the one-active-job guarantee.

**Alternatives considered**:

- Redis/Celery, a remote database, or a cloud queue: rejected because they add
  infrastructure and a second trust/availability boundary without a proven
  requirement.
- Framework migration: rejected because the present stack is compatible and
  tested.
- Multiple Uvicorn workers: rejected because independent dispatchers could run
  simultaneous GPU work.

## R2. Make the Notebook the entire application origin

**Decision**: Use exactly one server and this path:

```text
Public browser
  -> Cloudflare HTTPS edge
  -> outbound-established Cloudflare Tunnel
  -> cloudflared on the Notebook
  -> Caddy 127.0.0.1:8080
     -> Next.js 127.0.0.1:3000
     -> FastAPI 127.0.0.1:8000
        -> ComfyUI 127.0.0.1:8188
           -> RTX 5070
```

`161.200.90.4` identifies the Notebook's lab-network interface only. No
application binds to it and no public client uses it.

**Rationale**: This is the explicit feature requirement and constitutional
boundary. `cloudflared` creates outbound connections, so the university network
needs egress, not inbound NAT or application-port forwarding. Cloudflare
documents Tunnel firewall requirements as outbound TCP/UDP 7844, with QUIC and
HTTP/2 transports. See [Tunnel with firewall](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-with-firewall/)
and [connectivity pre-checks](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/troubleshoot-tunnels/connectivity-prechecks/).

**Alternatives considered**:

- Separate edge/origin or GPU host over WireGuard: rejected by Constitution
  2.0.0 and unnecessary for the available hardware.
- Direct inbound 443 or direct FastAPI ingress: rejected because it changes the
  trust boundary and requires university inbound firewall/TLS design.
- Cloud GPU or cloud application server: rejected as out of scope.

## R3. Put Caddy on loopback port 8080 and preserve the API prefix

**Decision**: Replace the current feature-003 Caddy shape with a host-agnostic
`:8080` site plus `bind 127.0.0.1`. Match exact `/api` and `/api/*`, route both
to FastAPI, and route everything else to Next.js. Use `handle`, not
`handle_path`, and do not preflight the AI engine before every request.

**Rationale**: A Caddy address containing `127.0.0.1` becomes a Host matcher,
which can reject the public host forwarded by Cloudflare. `:8080` accepts that
Host while `bind` still limits the socket. Caddy `handle` blocks are mutually
exclusive and `reverse_proxy` preserves the URI unless explicitly rewritten;
`handle_path` would strip `/api` and break FastAPI's `/api/v1/...` routes.
Caddy's relevant behavior is documented in [Caddyfile addresses](https://caddyserver.com/docs/caddyfile/concepts#addresses),
[`bind`](https://caddyserver.com/docs/caddyfile/directives/bind),
[`handle`](https://caddyserver.com/docs/caddyfile/directives/handle), and
[`reverse_proxy`](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).

Removing the old global engine gate lets the frontend and diagnostic API remain
available when ComfyUI is down. FastAPI owns safe admission refusal, while
Caddy owns only transport/routing failure handling.

**Alternatives considered**:

- Keep port 8443: rejected because the approved origin is exactly 8080.
- Send all traffic to Next.js and depend on its rewrite: rejected because the
  required boundary assigns `/api/*` directly to FastAPI.
- Use `handle_path /api/*`: rejected because it changes the application URI.
- Bind `0.0.0.0` or `161.200.90.4`: rejected because it exposes an internal
  service beyond loopback.

## R4. Use an operator-started Cloudflare Quick Tunnel only

**Decision**: Start a test session with:

```powershell
cloudflared tunnel --url http://127.0.0.1:8080
```

Accept the generated `https://<random>.trycloudflare.com` address as disposable
runtime data. Do not create a named tunnel, credentials file, token, ingress
configuration, custom hostname, DNS record, or automatic production service.
Before startup, detect both `%USERPROFILE%\.cloudflared\config.yaml` and
`config.yml` and stop with guidance rather than renaming operator-owned files.

**Rationale**: Cloudflare defines Quick Tunnels as development/test only,
generates a random hostname, provides no SLA, limits them to 200 concurrent
in-flight requests, does not support SSE, and warns that a default config file
is incompatible. See [Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/).
The current installed binary also documents `--url`, automatic metrics binding,
and the risk that debug logging can expose request headers.

**Alternatives considered**:

- Named Tunnel with token and custom DNS: rejected until parent-domain use is
  explicitly authorized and a new production design is approved.
- Buy a domain: rejected because ownership and spending are not authorized.
- Automatically persist/reuse the random URL: rejected because it can change on
  each connector restart.

## R5. Keep public progress on HTTP polling

**Decision**: Retain bounded HTTP polling with the current 2-second, then
5-second, then 10-second cadence. Public routes do not depend on SSE or
WebSockets. ComfyUI WebSocket use, if retained, remains a private loopback
adapter detail.

**Rationale**: Quick Tunnel explicitly does not support SSE. The current web
client already handles polling/reconnect and safely falls back when an edge or
proxy returns a non-JSON error. Caddy supports WebSockets, but exposing one is
not necessary for the approved journey. The authoritative state is SQLite, so
polling naturally recovers after browser refresh or a changing Tunnel session.

Status endpoints must read persisted state quickly. Potentially long ComfyUI
observation stays in the background worker; otherwise the current bounded
ComfyUI retry path could block a status request for tens of seconds and violate
SC-004.

**Alternatives considered**:

- SSE: rejected because Quick Tunnel does not support it.
- Public WebSocket: rejected because it adds session/reconnect complexity and
  is not needed for truthful progress.
- Hold the upload request until generation ends: rejected because generation is
  long-running and failure-prone.

## R6. Expose `running`, preserve `processing` only as storage compatibility

**Decision**: The feature-004 API, browser types, UI, and tests use exactly
`queued`, `running`, `completed`, `failed`, and `cancelled`. Existing SQLite and
domain code may retain `processing` internally for a compatible first
implementation, with one tested serialization mapping `processing -> running`.
No public payload or contract exposes `processing` after feature rollout.

**Rationale**: `running` is mandatory in FR-008 and Constitution 2.0.0. A
boundary mapping meets that requirement without rebuilding an existing SQLite
table merely to rename a private value. Engine-specific state names already
belong behind the adapter.

**Alternatives considered**:

- Continue exposing `processing`: rejected because it violates the approved
  feature and constitution.
- Rebuild/migrate the SQLite status constraint immediately: rejected as an
  unnecessary persistence risk for a vocabulary-only public change.
- Accept both names publicly: rejected because it leaves the contract
  ambiguous.

## R7. Keep durable serial admission and define duplicate behavior

**Decision**: Keep one active GPU job, FIFO order for accepted work, a maximum
of 20 non-terminal jobs, 30 submissions per minute, and five identical inputs
per minute. Keep the durable single engine-submission reservation. A repeated
browser upload is a new isolated attempt; request-level idempotency is not added
by this feature.

**Rationale**: The repository already enforces these limits atomically in
SQLite and uses a one-attempt guard before calling the engine. This bounds the
RTX 5070 and public test capacity without another queue service. The spec's
duplicate requirement is isolation and no overwrite/cross-link, not guaranteed
deduplication. A client retry after a lost `201` may consume a second job, but
it must never reuse the first job's directory, token, or output.

**Alternatives considered**:

- Client idempotency keys: deferred because product semantics, retention, and
  credential recovery for a lost response need a separate requirement.
- Multiple active jobs: rejected without GPU memory/runtime evidence.
- In-memory-only admission: rejected because restart recovery requires durable
  accepted state.

## R8. Keep the ComfyUI adapter but remove event-loop blocking

**Decision**: Preserve the existing adapter interface and pinned Hunyuan3D
manifest. Run blocking adapter calls outside FastAPI's event loop (initially
with `asyncio.to_thread` or an equivalent tested async boundary), make the
600-second job timeout configurable and validated, close the adapter
deterministically at shutdown, and persist the real manifest workflow revision
for real jobs.

**Rationale**: The current adapter validates loopback, allowlists workflow
fields, uploads through `/upload/image`, submits through `/prompt`, observes
private `/history` and `/queue` state, and restricts output resolution to the
job directory. ComfyUI documents these routes and its optional `/ws` updates in
[server routes](https://docs.comfy.org/development/comfyui-server/comms_routes)
and [server communications](https://docs.comfy.org/development/comfyui-server/comms_overview).
The adapter's private event-loop thread currently ends in a synchronous
`future.result()` call from FastAPI, so moving that wait off the request loop is
the lowest-change responsiveness fix.

The direct `websockets` import should be pinned explicitly if retained, rather
than relying on `uvicorn[standard]` to provide it transitively.

**Alternatives considered**:

- Replace ComfyUI or the Hunyuan workflow: rejected as explicitly out of scope.
- Rewrite the complete adapter to a new async API immediately: deferred because
  the thread offload preserves the tested boundary with less migration risk.
- Expose ComfyUI to the browser: rejected on security and contract grounds.

## R9. Preserve SQLite/file ownership and strengthen recovery

**Decision**: Keep SQLite as the authoritative job/event/asset store and local
per-job directories as content storage. Add bounded cleanup for orphan UUID
directories without a database row, revalidate published output before serving,
and keep safe restart behavior:

- queued and never submitted: rehydrate in durable FIFO order;
- reserved/running with uncertain engine outcome: fail `restart_recovery` and
  never resubmit automatically;
- possible orphan engine execution: operator detects and interrupts/quarantines
  it;
- completed but missing published output: record `output_missing`, suppress
  result links, and return a safe unavailable result.

**Rationale**: Existing job directories are path-contained and atomic output
publication is strong. A crash between file creation and database admission can
currently leave content indefinitely, and an already-running ComfyUI prompt may
survive an API restart even though the job is safely failed. Explicit cleanup
and operator handling close those gaps without inventing uncertain recovery.

SQLite uses WAL only after a verified runtime-safety decision. The existing
simple `>=3.22` check must be reconciled with the repository's documented
version-specific WAL safety policy rather than assumed sufficient.

**Alternatives considered**:

- Automatically resubmit or reattach every running job: rejected because an
  uncertain engine handle could duplicate GPU work or attach the wrong result.
- External object storage/database: rejected because it violates single-node
  scope.
- Delete all work directories at startup: rejected because it could destroy
  valid queued/completed data.

## R10. Retain per-job capability access and fail closed

**Decision**: Keep the 256-bit per-job token, persist only its SHA-256 digest,
compare it in constant time, return it once in the `201`, and require it in
`X-Job-Token` for status/model/download. Missing, wrong, cross-job, and expired
access all return the same safe `404`. The Quick Tunnel URL grants no job access
and must be treated as public.

**Rationale**: This is existing tested behavior and matches FR-005 through
FR-007 without adding accounts. Input is already bounded, content-decoded, and
path-sanitized before AI work; output endpoints accept no user-supplied path.
FastAPI must also return a controlled `503` when the real adapter failed to
initialize rather than dereferencing a missing service.

**Alternatives considered**:

- Rely on the random hostname: rejected because URL obscurity is not
  authentication.
- Add site-wide user accounts: rejected as out of scope.
- Put the token in a query string: rejected because URLs leak through history,
  referrers, and logs.

## R11. Use layered local health plus public-route validation

**Decision**: Keep safe public `/api/v1/health/live`, `/ready`, and `/engine`
responses, and add an operator-local composite procedure that independently
checks Caddy, web, API, SQLite/storage admission, workflow manifest, ComfyUI,
GPU, and the current Quick Tunnel session. Do not publish a detailed topology
or GPU inventory endpoint.

**Rationale**: Current health routes distinguish API process, startup adapter
configuration, and engine reachability, but they do not prove the complete
single-node chain. The existing `health_chain.ps1` still includes WireGuard
assumptions, so it cannot serve as feature-004 evidence until revised. A local
layered report can identify the failed capability without revealing addresses,
paths, model data, or user content to public users.

**Alternatives considered**:

- One generic public `/health` boolean: rejected because the operator cannot
  diagnose the failed layer.
- Expose full hardware/process details publicly: rejected as unnecessary
  information disclosure.
- Let Caddy's ability to serve a page prove AI readiness: rejected because
  transport and generation readiness are independent.

## R12. Supervise local services; keep Quick Tunnel session-scoped

**Decision**: Preserve WinSW supervision and loopback bindings for ComfyUI,
FastAPI, and Next.js, supervise Caddy locally, and start them in dependency
order. Start Quick Tunnel manually only after local readiness and stop it first.
After a Notebook restart, restore local health first and advertise the newly
generated test URL.

**Rationale**: Current service definitions already bind ComfyUI 8188, API 8000,
and web 3000 to loopback with automatic restart and dependencies. A disposable
Quick Tunnel URL is not a production service identity; automatic boot cannot
guarantee the same URL and could accidentally expose an unhealthy test build.

**Alternatives considered**:

- Install Quick Tunnel as a named token service: rejected because it changes
  the authorized environment and implies stable configuration.
- Start Tunnel before local health: rejected because it exposes avoidable
  failure windows.
- Container orchestration: rejected as unnecessary infrastructure.

## R13. Preserve streaming and strengthen log redaction

**Decision**: Do not configure Caddy request or response buffering. Retain a
12 MB proxy-level multipart guard and FastAPI's authoritative 10 MiB decoded
file limit. Keep bounded log rotation and explicitly remove `X-Job-Token`,
cookies, authorization, arbitrary headers, query values, bodies, user content,
engine IDs, private paths, and temporary public URLs. Keep cloudflared at
`info`; do not use debug during user traffic.

**Rationale**: Caddy streams request bodies by default and its request-body
limit can reject oversized whole requests without application buffering. The
limit needs framing headroom above the allowed file. Caddy documents that
custom headers such as `X-Job-Token` are not among its default credential
redactions, so the repository's explicit filters remain necessary. See
[`request_body`](https://caddyserver.com/docs/caddyfile/directives/request_body),
[`reverse_proxy` streaming](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy#streaming),
and [access-log filtering](https://caddyserver.com/docs/caddyfile/directives/log).

**Alternatives considered**:

- Buffer complete uploads/downloads at Caddy: rejected because it increases
  disk/memory pressure and duplicates application storage.
- Set Caddy's guard to exactly 10 MiB: rejected because multipart framing would
  reject a legal 10 MiB file.
- Log all request headers for debugging: rejected because job credentials and
  user metadata could leak.

## R14. Replace obsolete deployment evidence, not historical records

**Decision**: Update active deployment files, operator tooling, contract tests,
and runbooks to feature-004 semantics during implementation. Do not delete
historical specs, but do not reuse their WireGuard, second-host, port 8443,
named-Tunnel, token, DNS, or custom-domain assertions as proof.

**Rationale**: The checked-in Caddyfile and cloudflared example still implement
feature 003. Untracked single-host drafts also use port 8443 and named/custom
Tunnel assumptions. Existing direct-origin and Caddy security tests encode that
older topology. Silently passing those tests would certify the wrong system.

The active validation set must cover Caddy route preservation, loopback
listeners, safe API admission failures, public `running`, polling through Quick
Tunnel, changing URL recovery, near-limit upload/download, log sentinel scans,
five-user serial execution, real GPU generation, and three controlled Notebook
restart trials.

**Alternatives considered**:

- Delete all older feature artifacts: rejected because they are project
  history and may contain reusable evidence methods.
- Accept old tests unchanged: rejected because a green result would contradict
  the approved architecture.
- Expand feature 004 into production hostname migration: rejected pending
  explicit parent-domain authorization and a separate approved design.
