# HISTORICAL — do not execute for feature 004

Feature 004 has no edge server, WireGuard, inbound origin, DNS record, or
custom hostname. Use [single-host-tunnel-setup.md](single-host-tunnel-setup.md)
for the temporary test path; any custom-hostname work requires a separately
approved future requirement.

# Runbook: Feature 003 production cutover

**Owner:** Responsible human operator | **Frequency:** Initial cutover or provider/network change
**Updated:** 2026-09-06 (Option A remediation) | **Last live run:** BLOCKED

Follow `tunnel-setup.md` for preparation. The origin pass-through is loopback-only. Cloudflare's outbound connector owns the provider connection; no inbound HTTPS listener, Origin CA, or Authenticated Origin Pulls remains. The laptop job service and LAN workflow stay independent of the public route.

## Complete FR-033 gate

Each row requires dated, masked evidence from the appropriate target. A local unit test cannot close a live gate.

| Gate | Evidence / criterion |
|---|---|
| External upload, generation, preview, download | Off-LAN browser journey, SC-001 |
| Approved-origin traversal | Origin-generated request ID correlated with the external request and job, SC-002 |
| Connector egress from approved address | Active connections API for Cloudflare; origin-local connector and egress evidence for zrok, SC-002a/SC-014d |
| No direct Internet-facing application or management listener | Local inventory plus authorized external boundary trial, SC-003. The narrowly scoped WireGuard UDP transport listener defined by the Option A compute-link contract (C1a) is explicitly excluded from this prohibition; it is isolated from every application and management service. `test_origin_lockdown.py` exits non-zero on any silently dropped or unclassifiable probe, so a clean remote run is corroboration, never the whole gate |
| Origin WireGuard transport boundary verified | Static verification against the C1a declaration plus origin-local evidence that the running configuration matches it: one UDP port on the approved origin address, WireGuard service only, peer-key admission, `/32` scope, and no TCP application listener, management listener, catch-all rule, or router port forward, SC-018 |
| Direct WireGuard UDP reachability | Target inspection showing the approved origin receives the transport directly on its approved network path **without router port forwarding**, FR-041. A negative result voids Option A: cutover stays blocked and the compute-link transport is redesigned. Router forwarding, a public application port, a public GPU-laptop listener, and a paid relay are all forbidden as workarounds |
| Zero cost | Dependency and actual account review: zero recurring price, no required card, no paid fallback |
| Written hostname authorization and compatible route | Human-obtained consent for `twin3dgen.mangosgo.com`, account managing `mangosgo.com`, provider-facing DNS |
| Credential-log exclusion | Known synthetic token absent from connector, origin pass-through, application, and diagnostic logs; provider exposure documented accurately |
| Restart recovery | Both machines, both boot orders, three reboots and interruption trials; LAN independence |
| Safe compute-unavailable behavior | Engine, binding, and job-service failures individually within five seconds; origin-down provider error |
| Model/workflow licence verification | FR-035 audience/use compatibility; owner risk acceptance is not independent legal verification |

Hostname authorization gates **cutover only**. Local implementation and configuration preparation continue. Actual origin configuration and trials are now MANUAL/BLOCKED because the operator confirmed no authorized connection exists. Account-specific quotas, logging controls, and acceptable-use terms must be recorded by the account operator before cutover.

## Procedure after all gates are satisfied

1. Validate the rendered Caddyfile and connector ingress on the inspected origin. Keep credentials outside Git with service-only read permissions. Confirm local listeners and LAN independence. On any mismatch stop and repair the failing layer.
2. The authorized account operator creates the named tunnel route for the consented hostname in the Cloudflare account managing the zone. Do not point an A record at the origin or invent an unrelated account/delegation workaround.
3. From the authorized external test network run the verifiers with explicit inputs. Examples, replacing placeholders locally:

   `python scripts/verify/test_dns_disclosure.py --hostname <hostname> --confirm-off-campus`

   `python scripts/verify/test_egress_identity.py --provider cloudflare --cloudflare-account-id <account> --cloudflare-tunnel-id <tunnel>`

   Supply the read-only API credential through `CLOUDFLARE_API_TOKEN`, never in evidence or command history. Zero exit status means the specific checks passed; it does not replace the other gates.
4. Capture the browser journey, negative tokens, upload failures, five-job serial execution, retention/low-disk behavior, log exclusion, and reboot matrices. Observe origin filesystem activity throughout maximum-size transfers; before/after directory snapshots alone cannot prove transient files were absent.
5. Review the complete E6 evidence set in `specs/003-outbound-tunnel-entry/contracts/evidence-methods.md`. Enable production traffic only when every gate has appropriate evidence. Record active provider and time, and re-capture after provider or origin-network changes.

## Correlation and admission controls

Caddy assigns `X-Request-ID`, forwards it to the job service, and records `request_id`; the client-supplied value is overwritten. Resource paths contribute only a validated `job_id`. Raw URLs, queries, headers, response headers, and client addresses are omitted from access logs. For acceptance, capture the response request ID and match the origin access record. Verify the association with the job-service observation without recording tokens or content. Live timing/path proof remains required.

The API atomically bounds queued plus processing jobs (default 20), accepted submissions in a rolling minute (30), and identical input hashes in that minute (5). All use the existing SQLite transaction and survive restart. HTTP 429 uses one safe message, `Retry-After: 60`, and `Cache-Control: no-store`. These global bounds do not identify clients or guarantee fairness against distributed abuse. Accepted jobs remain untouched. Upload size remains 10 MiB, GPU concurrency one, retention 24 hours, and low-disk admission 10%.

## Rollback and fallback

Stop and disable the connector from the origin's authorized console, independently of its config. Preserve local jobs/results and verify LAN operation. Do not reopen a public listener. A never-authorized hostname means no public release; temporary tunnels are dev/demo only. A withdrawn live hostname permits degraded zrok only after the owner supplies the recovery window and separately accepts zrok's TLS exposure. Record cause, start, window, active provider, origin locality and egress, and tagged traversal. No paid fallback, automatic permanent identity, enterprise HA, geographic redundancy, or paid uptime SLA is promised.

Escalate failed access/transport checks to the lab/network operator and consent/account issues to the responsible human domain/account operator. Use existing authorized channels; no contacts or management ports are assumed.

## Streaming evidence metadata

T019 accepts a sanitized JSON metadata file through `--streaming-observation`; `--streaming-only` validates it without networking. The responsible operator must observe filesystem events on the approved origin throughout both maximum-size transfers, including transient creates/deletes, and preserve the protected trace separately. It is manual attestation, not independent trace capture by this script. Required fields are `operator_attested: true`, `approved_origin: true`, `trace_complete: true`, `maximum_download_tested: true`, `upload_bytes: 10485760`, positive `download_bytes`, and integer `project_spool_or_complete_body_files` (zero for PASS). Include the actual capture time and trial reference in the operator record. Never prefill a success record, include raw paths/content, or substitute a before/after snapshot. Missing/incomplete metadata stays BLOCKED.

## Implementation references

The local proxy behavior was checked against [Caddy request pre-checks](https://caddyserver.com/docs/caddyfile/directives/forward_auth), [early log fields](https://caddyserver.com/docs/caddyfile/directives/log_append), and [log filtering](https://caddyserver.com/docs/caddyfile/directives/log). The origin uses the expanded request pre-check only for engine health; it adds no login. Provider egress parsing follows the [Cloudflare connections API](https://developers.cloudflare.com/api/resources/zero_trust/subresources/tunnels/subresources/cloudflared/subresources/connections/methods/get/).
