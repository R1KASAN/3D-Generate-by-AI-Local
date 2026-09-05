# Cloudflare DNS Record Set

**Feature:** `002-cloudflare-public-entry`
**Status:** Intended configuration — not applied
**Owner:** Operator-controlled Cloudflare zone

This file describes the intended public record set. Replace the placeholders
only after the owner supplies the registered domain and confirms the origin
inputs in `evidence/public-deployment/operator-inputs.md`. The origin address
used by the record is the single address approved by
`specs/002-cloudflare-public-entry/contracts/port-policy.md`; the alternate
allocated address is out of scope and must never be configured.

## Records

| Name | Type | Target | Proxy status | TTL | Purpose |
|---|---|---|---|---|---|
| `<PUBLIC_HOSTNAME>` | A | approved origin address | **Proxied** (orange cloud) | Auto | The only visitor-facing application hostname. Cloudflare answers public DNS with its anycast addresses and forwards to the origin over the validated provider-to-origin hop. |

No other application, API, origin, or tunnel record is intended.

## Explicit non-records

- **No record is created for the tunnel endpoint.**
- Do **not** create `tunnel.<zone>`, `wg.<zone>`, or any other DNS record for
  the WireGuard endpoint. The laptop configuration uses the origin address as
  a literal; a DNS-only tunnel record would disclose the origin.
- Do **not** create a DNS-only record for `<PUBLIC_HOSTNAME>`.
- Do **not** create an `_acme-challenge` record for the origin. The origin uses
  Cloudflare Origin CA and does not use public ACME validation.
- Do **not** publish records for the backend, generation engine, management
  service, or internal tunnel addresses.

## Apply and verify

1. Confirm the hostname and account owner in the operator-input record.
2. Create the single A record above with proxying enabled.
3. Set the zone encryption mode to **Full (strict)** and configure
   Authenticated Origin Pulls as specified by the origin-entry contract.
4. From an external vantage point, query the public hostname and confirm that
   its public answers do not contain the origin address.
5. Record masked results in the designated deployment evidence files. Do not
   put credentials, API tokens, or provider dashboard exports in this repo.
