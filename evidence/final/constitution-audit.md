# Constitution audit — outbound origin

**Feature:** 003-outbound-tunnel-entry | **Constitution:** 1.2.0 | **Reviewed:** 2026-09-06

| Principle | Repository assessment | Remaining evidence |
|---|---|---|
| I. Smallest verified slice | Existing application plus outbound deployment and required admission bounds | External journey |
| II. Evidence-gated completion | Automated results recorded in outbound-implementation.md; live work unchecked | Authorized origin access and target trials |
| III. Private-service boundary | Outbound connector and loopback origin pass-through replace inbound HTTPS/mTLS. The clarified contract permits only a firewall-scoped, authenticated WireGuard UDP transport listener; no application or management listener exists | Local origin inventory, actual provider encryption/certificate validation, external probes, accurate provider exposure |
| IV. Job/file isolation | Admission rejects remove only unaccepted job files; existing isolated storage retained | Public-path isolation |
| V. Single-GPU queue | Serial execution retained; atomic SQLite admission bounds added | Five-job real-GPU trial |
| VI. Replaceable integration | Existing adapter and public job API retained | Real adapter acceptance |
| VII. Cross-platform discipline | Python verifiers and templates; origin service definitions provisional | Origin OS inspection |
| VIII. Test-first behavior | Failing admission/evidence/proxy regressions recorded before fixes | Runtime proxy and hardware trials |
| IX. Ownership decisions | Hostname consent, zrok recovery window and exposure remain owner inputs | Human authorization; licence compatibility must not be replaced by risk acceptance |
| X. Simplicity | Existing SQLite and Caddy used; no new service or paid dependency | Actual account cost/limit review |

Only project-controlled log exclusion may be claimed after verification. The active TLS-terminating provider can observe request content including capability tokens. Cloudflare acceptance does not authorize zrok exposure. This zero-cost split-host service promises no enterprise high availability, geographic redundancy, or paid uptime SLA (FR-039).

**Option A remediation, 2026-09-06.** Principle III now carries two named preconditions rather than an unqualified pass. First, the WireGuard transport listener is the origin's *only* remaining Internet-reachable socket, so its scope is specified and verified in this feature rather than inherited from feature 002 (SC-018, contracts/compute-link.md C1a-1): one UDP port on the approved origin address, WireGuard service only, peer public-key admission, `/32` peer scope, and no application listener, management listener, catch-all rule, or router port forward. A negative verification fixture is mandatory, because a verifier that only confirms the expected rules would also pass a configuration carrying those rules plus a violation. Second, Option A is itself conditional: if the approved origin cannot directly receive that UDP transport without router port forwarding, Option A is not feasible for this target, production stays blocked, and the transport is redesigned (FR-041). Both remain `PENDING TARGET INSPECTION`.

**Production release: BLOCKED.** This audit is a repository review, not live origin, legal, network, or hardware acceptance.
