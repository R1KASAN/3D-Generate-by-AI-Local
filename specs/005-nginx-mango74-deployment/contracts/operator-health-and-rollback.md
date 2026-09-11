# Contract: Health, Deployment, Recovery, and Rollback

## Independent health scopes

| ID | Scope | Required evidence | Safe unavailable label |
|---|---|---|---|
| H1 | NT frontend | External `GET /mango74/`, asset checks, release marker | `frontend_unavailable` |
| H2 | Preserved routes | Baseline status/destination/content comparison | `route_regression` |
| H3 | Stable API edge | DNS, HTTPS, and safe `/api/v1/health/live` | `api_route_unavailable` |
| H4 | Named Tunnel | Windows service plus public-to-origin reachability | `tunnel_unavailable` |
| H5 | Nginx | Loopback listener and Host-aware API proxy probe | `reverse_proxy_unavailable` |
| H6 | FastAPI | Loopback liveness | `api_unavailable` |
| H7 | Admission/storage | Readiness, SQLite, storage, queue/disk bounds | `job_service_unavailable` |
| H8 | Workflow/ComfyUI | Manifest/runtime verification and bounded health | `engine_unavailable` |
| H9 | GPU | Driver check plus approved real-workflow evidence | `gpu_unavailable` |
| H10 | Browser CORS | Exact allow and deny matrix | `cors_policy_invalid` |
| H11 | Listener boundary | Local binding inventory; no direct fallback | `listener_boundary_invalid` |

Public health responses remain coarse. Detailed machine, model, storage,
service, or route information is operator-only and sanitized.

## Staged deployment gates

1. **Inventory**: identify the NT Server product/version, authorized operators,
   current Mango74 state, unrelated-route baseline, Cloudflare rollback state,
   Notebook identity, services, listeners, workflow, models, and durable jobs.
2. **Repository validation**: API/security suites, frontend unit/type/lint,
   static production build, Playwright cross-origin scenarios, OpenAPI/YAML,
   Nginx config tests, PowerShell parsing, artifact scan, and secret scan pass.
3. **Local backend**: stop Caddy, start Nginx on loopback, validate preserved
   `/api/v1` paths, exact Host rejection, CORS matrix, ComfyUI readiness, one
   controlled mock flow, and existing real RTX baseline.
4. **Named Tunnel**: authorized administrator provisions the hostname and
   connector; verify stable HTTPS, H3-H5, interruption, reconnection, and no
   alternate public route.
5. **NT frontend**: authorized administrator deploys the reviewed archive only
   under `/mango74/`; verify redirect, assets, navigation, deep links, and H2.
6. **External acceptance**: from a genuinely independent network, complete one
   real generation, refresh/status/cancel scenarios, preview/download byte
   equality, exact CORS checks, and failure behavior.
7. **Recovery and rollback**: run three service-restart trials, Tunnel
   interruption/recovery, independent frontend rollback, independent backend
   rollback, and post-rollback route/data checks.

No later gate converts an earlier failure into success. A blocked
administrator, external-network, or hardware gate remains explicitly pending.

## Startup and shutdown

Production backend startup order:

1. verify configuration, secret locations, free disk, and listener ownership;
2. start ComfyUI and validate the approved workflow runtime;
3. start FastAPI and complete durable reconciliation before readiness;
4. start Nginx after `nginx -t` passes;
5. verify the local route with the exact API Host header;
6. start the named `cloudflared` service;
7. verify the stable API and exact CORS policy.

Shutdown reverses the public path first: stop `cloudflared`, stop Nginx, stop
FastAPI after bounded worker shutdown, and then stop ComfyUI. The NT-hosted
frontend remains available and reports backend unavailability accurately.

## Restart recovery

The Feature 004 durable recovery rules remain authoritative:

- never-submitted queued jobs return to durable FIFO order;
- uncertain submitted/running work is not blindly resubmitted;
- exact engine reattachment requires evidence, otherwise the job fails safely
  with restart recovery;
- orphan engine output is quarantined and never attached to another job;
- completed rows expose results only after artifact revalidation;
- no restart changes job ownership or creates a false completion.

Three controlled project-service restart trials must include Nginx and
`cloudflared` and must demonstrate restoration of the same stable API URL. A
full Notebook reboot is performed only with explicit operator approval and
recorded separately if required by the acceptance task.

## Failure matrix

| Injected failure | Must remain true |
|---|---|
| NT frontend unavailable | Backend and jobs remain intact; unrelated routes remain available |
| Named Tunnel stopped | Frontend loads; API reports unavailable; no direct fallback |
| Nginx stopped | Tunnel cannot reach API; FastAPI/ComfyUI local state remains accurate |
| FastAPI stopped | Frontend shows unavailable; no false missing/completed job |
| ComfyUI unavailable | API liveness and durable reads work; admission fails safely |
| GPU/workflow failure | Job reaches accurate failed state; no partial GLB |
| Queue/capacity limit | New work receives safe `429`; accepted jobs are unchanged |
| Low disk | New work receives safe `507`; protected existing reads remain bounded |
| CORS denial | Browser cannot read response; token checks remain independently enforced |
| Output missing/corrupt | Result URLs/bytes are withheld; job history remains safe |

## Independent rollback

**Frontend rollback** restores the recorded NT Server route/static archive and
rechecks `/mango74`, representative unrelated paths, and cache behavior. It
does not stop or redeploy the AI backend.

**Backend/Tunnel rollback** removes or disables the stable API route, stops the
named connector, restores the recorded reverse-proxy/service state, and
revalidates durable jobs. It does not change the official frontend URL or NT
Server files; the frontend must show backend unavailability.

Rollback evidence includes timestamps, authorized actions, before/after
release hashes, service states, route results, job-state counts, unresolved
blockers, and total elapsed time. It excludes credentials, tokens, user files,
private paths, and generated model bytes.
