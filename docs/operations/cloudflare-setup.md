# HISTORICAL — do not execute for feature 004

Feature 004 does not configure DNS, an origin certificate, or a custom
hostname. Use the operator-run Quick Tunnel launcher and the single-host guide.

# Cloudflare Public Entry Setup

This runbook configures the provider layer for the existing origin. It does
not replace the origin reverse proxy or the outbound-initiated WireGuard link.
Use the exact hostname supplied in
`evidence/public-deployment/operator-inputs.md`; do not invent a domain or put
credentials in this repository.

## Provider configuration

1. Add the owner-controlled zone to the provider account.
2. Create the single application A record described in
   `deploy/cloudflare/dns-records.md`, pointing at the approved origin and
   enabling **Proxied** status.
3. Set SSL/TLS encryption mode to **Full (strict)**.
4. Enable Authenticated Origin Pulls for the zone/hostname and download the
   provider pull CA certificate for installation on the origin.
5. Issue an Origin CA certificate for the exact hostname. The provider-managed
   visitor certificate is separate and is renewed by the provider.
6. Configure provider controls that suppress request-header or credential
   logging wherever those controls exist. Record the available controls and
   their settings in `evidence/public-deployment/residual-exposure.md` during
   provider configuration.

## Origin installation

Install the Origin CA server certificate, matching private key, and provider
pull CA at the paths documented in
`deploy/cloudflare/origin-cert.README.md`. Render the origin environment from
`deploy/caddy/.env.example` locally on the origin and run Caddy validation
before starting the service.

The origin-to-provider hop must be encrypted and certificate-validated in both
directions: Full (strict) validates the origin certificate, and Authenticated
Origin Pulls validates the provider client certificate. A plain Full mode is
not sufficient.

## Certificate renewal record

Cloudflare renews the visitor-facing certificate; it does not renew the Origin
CA certificate installed on the origin. After issuance, record these values in
owner-visible documentation without copying certificate or key material:

| Certificate | Issued | Expires | Renewal owner | Next action |
|---|---|---|---|---|
| Origin CA server certificate | `PENDING — record after issuance` | `PENDING — record after issuance` | `PENDING — owner input` | Reissue before expiry, install the replacement, validate Caddy, then reload and verify the provider hop |

At least 30 days before expiry, issue a replacement for the same hostname,
install it through a protected channel, validate the rendered Caddy
configuration, reload Caddy, and run the origin-lockdown and HTTPS boundary
checks. Retain the old certificate until the replacement is verified, then
remove it from the origin securely. Never commit either private key.

## Verification and rollback

Before public activation, confirm the origin management path and firewall
permissions are already proven. Verify that direct origin traffic is rejected,
the public DNS answer does not disclose the origin, and port 80 remains closed.

If provider configuration is incomplete, leave the DNS record unactivated and
keep the origin unavailable to direct clients. This design has no unproxied
rollback path because the Origin CA certificate is not publicly trusted.
