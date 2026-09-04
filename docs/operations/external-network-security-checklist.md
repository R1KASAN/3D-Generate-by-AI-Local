# External-Network Security Checklist (T094)

Negative-case and mobility verification, run from outside the university
network. Two separate scripts cover this:
`scripts/verify/test_external_acceptance.py` for negative-case probes
against a real job, and `scripts/verify/test_mobility.py` for the
project's core mobility acceptance criterion.

## Negative cases (via `test_public_auth.py` and manual probes)

- [ ] Missing token on `/{job_id}`, `/{job_id}/model`, `/{job_id}/download`
      → uniform 404, not 401/403/500 (a differentiated response leaks
      whether a job ID exists).
- [ ] Wrong-job token on the same three endpoints → uniform 404.
- [ ] Expired job (past `RETENTION_HOURS`) → uniform 404, same shape as a
      never-existed job ID.
- [ ] Invalid upload (corrupt image, unsupported format, oversized file)
      → the branded JSON error codes from `apps/api/src/local3d/api/jobs.py`
      (`upload_too_large`, `unsupported_image`, `corrupt_image`), never a
      raw stack trace or an unhandled 500.
- [ ] Low-disk admission (`MIN_FREE_DISK_PERCENT`) → `507 low_storage`,
      not a silent failure or a job stuck in a queue forever.
- [ ] Internal ports (3000 without the tunnel, 8000, 8188, 3389, 2019) →
      unreachable from outside, per `test_external_ports.py`.
- [ ] Caddy access log does not contain any `X-Job-Token` value in
      cleartext (`test_public_auth.py --caddy-log`).

## Mobility acceptance (the project's core success criterion)

Run `scripts/verify/test_mobility.py --hostname <host> --confirm-off-campus`
and physically stage each of its six scenarios on the GPU laptop as it
prompts. See the script's docstring for the full list; in short:

- [ ] University → generation succeeds.
- [ ] Mobile hotspot → generation succeeds after reconnect, with **no**
      config changes.
- [ ] Home network → generation succeeds after reconnect, with **no**
      config changes.
- [ ] Reboot off-campus → full recovery chain (WireGuard → tunnel address
      → app services → edge reachability) with no manual intervention.
      Repeat at least 3 times — this is a race-condition-prone path.
- [ ] Network cut → maintenance page appears (not a raw 502, not silence).
- [ ] Power off 30 minutes, restart → tunnel recovers on its own.

## Expected result

`evidence/public-deployment/negative-cases.md` and
`evidence/public-deployment/mobility.md` both show
`Overall verdict: **PASS**`, and the mobility run's context lines confirm
DNS, the public IP, the Caddyfile, and WireGuard addressing were not
touched during the run.

## If it fails

A mobility scenario failing is not necessarily a bug to patch around by
loosening a firewall rule or widening `AllowedIPs` — re-read
`docs/operations/tunnel-setup.md`'s troubleshooting section first; most
failures are `PersistentKeepalive`, the McAfee VPN adapter, or a border
firewall that does not actually have 51820/udp open yet, not an
architecture problem.
