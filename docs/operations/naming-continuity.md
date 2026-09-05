# Naming and Certificate Continuity Record

**Feature:** `002-cloudflare-public-entry`  
**Status:** **BLOCKED — owner inputs required**

This document is the handover template required by FR-029 and SC-014. It is
deliberately incomplete until the owner supplies the actual registrar, provider
account identity, hostname, and Origin CA certificate dates. Do not put account
passwords, API tokens, private keys, or dashboard exports here.

## Ownership record

| Item | Value | Status |
|---|---|---|
| Registered domain | `PENDING — owner input` | Required before DNS activation |
| Registrar | `PENDING — owner input` | Required for transfer/recovery |
| Cloudflare account identity | `PENDING — owner input; no credential` | Record the account identity or recovery contact, never a password or token |
| Zone renewal date | `PENDING — owner input` | Required for continuity |
| Public hostname | `PENDING — owner input` | Must remain one stable proxied subdomain |

## Origin certificate record

| Item | Value | Status |
|---|---|---|
| Origin CA certificate issued | `PENDING — record after issuance` | Record date only |
| Origin CA certificate expires | `PENDING — record after issuance` | Set renewal reminder at least 30 days ahead |
| Renewal owner | `PENDING — owner input` | Name a role/person, not a secret |
| Certificate/key installation path | See `deploy/cloudflare/origin-cert.README.md` | OS-specific path is selected after origin OS confirmation |

## Recovery procedure

1. Recover access to the registrar and Cloudflare account using the owner
   organization's approved account-recovery process.
2. Recreate the zone and the one proxied application record from
   `deploy/cloudflare/dns-records.md`.
3. Reissue an Origin CA certificate for the documented hostname, install it
   through a protected channel, and record only its issue/expiry dates.
4. Restore Full (strict) and Authenticated Origin Pulls.
5. Restore the origin Caddy configuration and verify the origin management
   path before applying the boundary.
6. Run the DNS disclosure, origin lockdown, HTTPS, port, authentication, and
   full-flow checks from `docs/operations/public-cutover.md`.

Until the pending ownership and certificate dates are filled, another operator
cannot independently reconstruct the naming layer. This is an owner-input
block, not a reason to weaken the public boundary.
