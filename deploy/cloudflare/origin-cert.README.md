> **RETIRED — feature 003 removes this procedure.** Do not issue/install Origin CA or Authenticated Origin Pulls material for the outbound deployment. `cloudflared` owns the encrypted provider connection; Caddy is the loopback origin pass-through. The remainder is feature-002 history only. See `../cloudflared/README.md`.

# Cloudflare Origin CA Certificate Procedure

This document is an installation procedure, not certificate or key storage.
The origin certificate is used only on the origin-to-provider hop. Visitors
receive a separate provider-managed certificate.

## Required certificate material

Issue an Origin CA certificate for the exact public hostname and install both
parts on the origin:

1. The origin server certificate, including its chain as supplied by the
   provider.
2. The matching private key.

Separately install the provider's Authenticated Origin Pulls CA certificate.
That CA validates the provider client certificate presented to the origin; it
is not the server certificate and must not be confused with it.

The hostname, certificate issue date, expiry date, and renewal owner must be
recorded in owner-visible deployment documentation after issuance. Do not
record the certificate value or private key in that documentation.

## Approved file locations

The origin OS is still an operator input. Use the location matching the
confirmed OS and keep the same logical filenames:

### Linux origin

```text
/etc/caddy/certs/local3d-origin.crt
/etc/caddy/certs/local3d-origin.key
/etc/caddy/certs/cloudflare-origin-pull-ca.pem
```

### Windows origin

```text
C:\ProgramData\Caddy\certs\local3d-origin.crt
C:\ProgramData\Caddy\certs\local3d-origin.key
C:\ProgramData\Caddy\certs\cloudflare-origin-pull-ca.pem
```

Create the directory with permissions that allow the Caddy service account to
read the files and prevent ordinary users from reading the private key. On
Linux, use a service-readable directory and a private key mode no broader than
`0600`; on Windows, use an ACL granting read access only to the Caddy service
identity and administrators.

## Installation sequence

1. Confirm the hostname and origin OS in
   `evidence/public-deployment/operator-inputs.md`.
2. In the provider dashboard, issue an Origin CA certificate for that
   hostname. Select the provider's long-lived Origin CA validity appropriate
   for the owner's renewal process.
3. Copy the certificate, matching private key, and provider pull CA to the
   OS-specific paths above using a protected channel.
4. Configure the Caddy environment values for the certificate path, key path,
   and provider pull CA path. Keep those values host-local.
5. Run `caddy validate` against the rendered Caddy configuration.
6. Confirm the origin accepts the provider client certificate and refuses a
   direct client without it before enabling public traffic.
7. Record only masked verification results, plus issue/expiry dates and the
   renewal procedure, in the deployment evidence and operations docs.

## Non-negotiable secret handling

**Never commit certificate private keys or any other key material.** Do not put
the private key in Git, `.env.example`, task output, screenshots, logs, shell
history, or evidence files. The repository may contain this procedure and
public certificate paths only; it must not contain the certificate's private
key, provider API tokens, dashboard exports, or copied secret values.

If key material is accidentally copied into the repository, stop deployment,
remove it from the working tree and history using the repository's approved
incident procedure, and revoke/reissue the certificate before continuing.
