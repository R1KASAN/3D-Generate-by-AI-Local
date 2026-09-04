# Phase 0 Research: Cloudflare Public Entry

**Feature**: `002-cloudflare-public-entry` | **Date**: 2026-09-05

Each decision below resolves an unknown in the plan's Technical Context or a design fork left open by the spec.

---

## R1 — Origin certificate: Cloudflare Origin CA, not public ACME

**Decision**: Issue a Cloudflare Origin CA certificate for the subdomain and install it on the origin. Do not use Let's Encrypt or any public CA for the origin.

**Rationale**: With the subdomain proxied, the visitor-facing certificate is Cloudflare's and is renewed by Cloudflare with no operator involvement. The origin's certificate is only ever presented to Cloudflare, so it does not need public trust. Origin CA certificates are free, are valid for years rather than weeks, and — the decisive property — require **no inbound validation path**. That single fact removes the need to open port 80 at all, which was one of the two inbound permissions the superseded design depended on.

It also removes an entire failure mode the spec explicitly worried about (FR-003): a renewal that fails while nobody is watching. There is no periodic renewal to fail.

**Alternatives considered**:
- *Public ACME on the origin (superseded design)*: needs port 80 open to the whole Internet for HTTP-01, and puts renewal on the operator. Rejected.
- *Let's Encrypt DNS-01 via Cloudflare API*: avoids port 80 and would work, but requires an API token with DNS-edit rights stored on the origin — a standing credential with real blast radius, to obtain public trust the origin does not need. Rejected as strictly worse than Origin CA here.
- *Self-signed origin certificate*: free and needs no validation, but cannot be validated by the provider, forcing a non-strict SSL mode. Rejected — see R2.

**Sources**: [Cloudflare origin CA](https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/)

---

## R2 — Provider SSL mode: Full (strict)

**Decision**: Set the zone's SSL/TLS encryption mode to **Full (strict)**.

**Rationale**: FR-003a requires the proxy-to-origin hop to be encrypted *and validated*. Full (strict) validates the origin certificate; plain Full encrypts but accepts any certificate, including an expired or attacker-supplied one, which makes the hop interceptable by anyone positioned between the provider and the origin. Origin CA certificates are explicitly compatible with strict validation, so choosing R1 makes this mode available at no extra cost.

This is called out as its own decision because "Full" and "Full (strict)" differ by one word in the dashboard and the weaker one is a common default. Selecting the wrong one would satisfy a casual reading of "encrypted end to end" while leaving FR-003a unmet.

**Alternatives considered**:
- *Flexible*: provider connects to the origin over plain HTTP. Rejected — traffic including uploaded images and job credentials would cross the campus network unencrypted.
- *Full (non-strict)*: rejected as above.

**Sources**: [Full (strict)](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/)

---

## R3 — Origin lockdown: Authenticated Origin Pulls as primary, IP allowlist as secondary

**Decision**: Enable Authenticated Origin Pulls (mTLS) and configure the origin reverse proxy to require and verify Cloudflare's client certificate. Additionally restrict the origin's inbound 443 rule to Cloudflare's published address ranges. Treat mTLS as the control and the IP restriction as defence-in-depth.

**Rationale**: FR-005 requires the origin to *refuse* traffic that did not arrive through the proxy. Hiding the address (FR-001b) is concealment, not a control — the address appears in the allocation memo, in campus records, and in any TLS certificate transparency entry or historical DNS data. Concealment must not be the thing standing between the Internet and the service.

An IP allowlist alone is fragile in a specific way that matters here: the provider's published ranges change, and when they do an allowlist fails *closed for legitimate traffic* (outage) or, if maintained carelessly with wide ranges, fails *open*. mTLS does not have this property — it is a cryptographic check that does not drift. Keeping both means a range update that has not yet been applied causes a visible outage rather than a silent security regression, which is the correct direction to fail.

**Alternatives considered**:
- *IP allowlist only*: rejected as the sole control for the reasons above; retained as a second layer.
- *Shared secret header injected by the provider and checked at the origin*: workable, but it is a bearer secret that would have to live in origin configuration, and the application's configuration loader rejects secret-shaped keys by design. mTLS avoids introducing a secret at all.
- *No origin restriction, relying on the address being unpublished*: rejected — this is exactly the concealment-as-control failure described above.

**Sources**: [Authenticated Origin Pulls](https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/), [How AOP works](https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/explanation/)

---

## R4 — Port 80 is not opened

**Decision**: Do not open inbound 80/tcp at the origin. Remove the `-EnableHttp` path and the `:80` handling from the origin reverse proxy configuration.

**Rationale**: The two reasons port 80 existed in the superseded design are both gone. Certificate validation no longer touches the origin (R1). HTTP-to-HTTPS redirection for visitors now happens at the provider edge, before any request reaches the origin. Leaving the port open would therefore be an inbound permission with no consumer — and one the project would have to justify in the security checklist.

This directly reduces the request to university network staff from three permissions to two.

**Alternatives considered**:
- *Keep 80 open for redirect*: unnecessary; the provider redirects. Rejected.
- *Keep 80 open "just in case" for a future ACME fallback*: rejected. If the design ever needs public ACME again, opening the port is a deliberate change that should be re-approved, not a standing permission held in reserve.

---

## R5 — Compute link endpoint is an address literal, never a hostname

**Decision**: The GPU laptop's tunnel configuration points at `161.200.90.4:51820` as a literal address. No DNS record is created for the tunnel endpoint.

**Rationale**: This is the non-obvious way this design leaks its own origin. UDP cannot traverse the provider's HTTP proxy, so any DNS record created for the tunnel endpoint would have to be DNS-only (unproxied) — and an unproxied record publishes the origin address to anyone who queries it, defeating FR-001b entirely while the operator believes the address is hidden.

Using a literal in a configuration file avoids this: the address is known to the two machines that need it and is not published. The cost is that a future origin address change requires editing the laptop's tunnel configuration. That is acceptable — the origin is explicitly not relocatable, whereas the laptop is, and the laptop-mobility requirement is unaffected because the laptop dials outbound.

**Alternatives considered**:
- *A DNS-only subdomain such as `tunnel.<zone>`*: convenient, and publishes the origin. Rejected.
- *Routing the compute link through the provider's tunnel product instead*: rejected at the spec level — the owner requires the allocated address to remain the production origin.

---

## R6 — Compute link protocol unchanged; inbound UDP is still required

**Decision**: Retain WireGuard on 51820/udp, open to any source address, authenticated by public key. The existing tunnel configuration and startup chain are carried forward unchanged.

**Rationale**: FR-016 requires an outbound-initiated link so the laptop needs no inbound reachability anywhere it travels. WireGuard satisfies this, the configuration already exists and is correct, and the source address must remain unrestricted because the laptop's public address changes every time it moves — an allowlist would defeat the mobility requirement. Security is per-packet key authentication, and unauthenticated packets are dropped silently.

**This is the permission the superseded planning round discovered late**, and FR-030 exists because of it. It is stated here explicitly so it is enumerated before cutover rather than after: **the Cloudflare change does not remove the UDP requirement.** It removes port 80, not 51820.

**Alternatives considered**:
- *SSH reverse tunnel over TCP*: works where UDP is blocked and is retained as the documented fallback for hostile networks (hotel, guest, some corporate Wi-Fi), not as the primary.
- *A mesh VPN with provider-operated relays*: would remove the inbound UDP requirement entirely, at the cost of a second third-party in the path. Recorded as the escalation option if network staff refuse UDP.

---

## R7 — One authoritative port policy governing two possible firewall implementations

**Decision**: `contracts/port-policy.md` is the single source of truth for inbound permissions. The PowerShell implementation and any future nftables implementation both derive from it, and the verifier asserts against it rather than against a hard-coded rule list.

**Rationale**: The origin's operating system is an operator input that has not yet been reported, so the concrete firewall implementation cannot be finalised. The risk is not the delay — it is that two implementations eventually exist and drift, which Principle VII warns about directly. Resolving the fork at the *policy* layer rather than the *script* layer means the unknown no longer blocks design, and the drift risk is structurally prevented rather than merely noted.

**Operator input still required before cutover**: origin OS and version; whether the allocated address is already assigned to it; whether anything currently listens on 443; the management path and its source range; the registered domain name.

**Alternatives considered**:
- *Block all design work until the OS is known*: rejected — nothing else in the design depends on it.
- *Write only the PowerShell version and adapt later*: rejected — this is precisely how the two drift.

---

## R8 — Request-body limit at the provider is not a constraint

**Decision**: No provider-side body-limit configuration is required. Keep the origin reverse proxy's own limit at 12 MB.

**Rationale**: The owner's plan permits request bodies up to 100 MB, an order of magnitude above the service's 10 MiB policy. The spec asked for this to be confirmed during planning rather than assumed at cutover; it is confirmed. The origin's 12 MB limit remains as the absurdity guard, deliberately above 10 MiB so that multipart framing overhead never causes the network layer to reject a file the application would have accepted — the application stays the component that enforces policy and returns the explanatory error (FR-015).

**Sources**: [Cloudflare Workers platform limits](https://developers.cloudflare.com/workers/platform/limits/)

---

## Carried-forward risks

| Risk | Consequence | Handling |
|---|---|---|
| Network staff refuse inbound UDP for the compute link | Mobility requirement unmet; laptop tethered to the origin's network | R6 fallbacks: SSH reverse tunnel, or mesh VPN with relays. Escalate before cutover, not during. |
| Provider address ranges change and the origin's allowlist is stale | Legitimate traffic refused — visible outage | Accepted direction of failure (R3). mTLS keeps the security property intact; a scheduled range refresh limits the outage window. |
| Naming layer is personally owned while the origin is institutional | Programme cannot restore reachability without the operator | FR-029 / `docs/operations/naming-continuity.md`; verified by SC-013. |
| Origin machine is a single point of failure | Origin down takes the whole service down, unlike the laptop which degrades to a notice | Stated plainly in `data-model.md`; not mitigated in this feature. |
