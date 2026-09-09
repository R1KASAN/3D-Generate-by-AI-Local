# Feature 005 NT Server frontend deployment

## Linux staging validation

Captured: 2026-09-09 from operator-executed SSH commands. No AI/automation
session connected to the NT Server.

Artifact uploaded as:

```text
/home/[REDACTED_USER]/front-end-472d988b.zip
```

Observed validation:

```text
SHA-256: 472d988bec81333cbc505b2c020efc4335c02841afe801bb22384c072e65929e
PASS: index.html
PASS: static assets
Unreadable/non-searchable directory scan: no output
Extracted size: 1.7M
Staging: /home/[REDACTED_USER]/mango74-staging-472d988b
```

Result: **PASS — artifact transferred intact and extracted with usable Linux
paths/permissions.** This is staging evidence only. It does not yet prove the
production `/mango74/` deployment, redirect, unrelated-route preservation, or
rollback.

## Production deployment gate

Pre-change backup/baseline captured: 2026-09-09 by the authorized operator.

```text
Server: Ubuntu / Nginx 1.28.0
Active configuration backed up: /etc/nginx/sites-available/default
Configuration SHA-256: 5421a2eb22e3bb30db7e067881b52f43e8b6e271c7de9445dfada874fb448fd9
Previous /var/www/mango74 state: ABSENT
Backup ID: /home/[REDACTED_USER]/mango74-backup-20260909T105526Z
GET /: 200
GET /verse: 301 -> https://www.mangosgo.com/verse/
GET /mango74: 404
GET /mango74/: 404
```

Baseline result: **PASS — backup exists and the pre-change state is recorded.**

Deployment status: **NOT YET PERFORMED**.

## Inert release placement

Captured: 2026-09-09 by the authorized operator. The active Nginx
configuration was not changed or reloaded during this step.

```text
Release directory: /var/www/mango74-releases/472d988b
Nginx user can read index.html: PASS
Nginx user can read/traverse _next/static: PASS
Static files: 24
Extracted size: 1.7M
nginx.service: active
```

Result: **PASS — release files are present and readable, with no public route
change yet.**

## First route activation attempt

Captured: 2026-09-09 by the authorized operator.

```text
Release symlink: created
Snippet file: created but not yet trusted/activated
Root location matches in active default file: 2
Safety guard: STOP — configuration not changed
nginx -t: successful with pre-existing warnings
nginx.service after reload: active
GET /: 200
GET /verse: 301 -> https://www.mangosgo.com/verse/
GET /mango74: 404
GET /mango74/: 404
GET selected release asset: 404
```

Result: **SAFE STOP — no Mango74 route was activated and existing observed
routes remained at their pre-change status.** The snippet was not included, so
the successful syntax check does not validate its contents. The body-hash
comparison was not performed because the supplied pipeline contained an
invalid placeholder command; no result is inferred from it.

## Second route activation attempt

Captured: 2026-09-09 by the authorized operator using the hash-verified
activation script and snippet.

```text
nginx -t before reload: PASS (pre-existing warnings retained)
origin /: 200
origin /verse: 301
origin /mango74: 404 (expected 308)
origin /mango74/: 404 (expected 200)
origin selected asset: 404 (expected 200)
automatic rollback: PASS
known-good configuration validation after rollback: PASS
```

Result: **FAILED acceptance with successful rollback.** The evidence indicates
that `/etc/nginx/sites-available/default` is not the effective virtual host for
these requests despite containing a matching `server_name`, consistent with
the pre-existing duplicate `www.mangosgo.com` server-name warning. No deploy
success is inferred and the active site remains on the known-good baseline.

## Third attempt — root cause identified

Captured: 2026-09-10 by the authorized operator running
`deploy/nt-server/mango74-vhost.py diagnose` plus read-only `grep`, `ss`,
`systemctl` and error-log inspection. No configuration was changed.

Effective virtual host and listener:

```text
0.0.0.0:443 owned by the systemd-managed Nginx (MainPID matches /run/nginx.pid)
Docker owns only 127.0.0.1-facing port 4043, the upstream of location /
Two TLS blocks claim www.mangosgo.com: sites-enabled/default (effective) and
sites-enabled/mango (11 lines, no locations, the one Nginx reports as ignored)
No Mango74 include exists anywhere under /etc/nginx (rollback was clean)
```

Mechanism of the 404, confirmed against the error log:

```text
/etc/nginx/sites-available/default:213
    location /mango7 { alias /var/www/kmitlverse; }

GET /mango74            -> alias + "4"           -> /var/www/kmitlverse4
GET /mango74/           -> alias + "4/" + index  -> /var/www/kmitlverse4/index.html
GET /mango74/_next/...  -> alias + "4/_next/..." -> /var/www/kmitlverse4/_next/...
```

All three error-log paths match that substitution exactly. The vhost holds about
ninety `/mangoNN` project routes and **no `/mango74` route**; `/mango7` is a
prefix of `/mango74`, so it captured every Mango74 request. The 404 was never a
missing route, a wrong server block, or a file permission problem.

The 2026-09-09 18:19 log confirms the failed attempt's probes were answered from
`/var/www/kmitlverse4`, and that the probe round recorded in evidence landed on a
pre-reload worker during the reload window.

Consequence for the fix: `location = /mango74` and `location ^~ /mango74/` both
outrank `location /mango7` under Nginx's exact-match and longest-prefix rules, and
neither duplicates an existing location, so the approved snippet is valid as
written. URIs such as `/mango741` continue to reach `/mango7` unchanged.

Result: **root cause established. Activation not yet performed.**

## Route activation — PASS

Captured: 2026-09-10 by the authorized operator running
`mango74-vhost.py activate --targets effective --probe-path /mango7
--probe-path /mango76 --apply`. Dry run reviewed and approved first.

```text
Edited file:      /etc/nginx/sites-available/default (include after line 3)
Snippet included: /etc/nginx/snippets/mango74-static-v2.conf (approved hash)
Backup:           /var/backups/mango74/20260909T193834Z
nginx -t:         successful, pre-existing warnings retained
Reload:           systemctl reload, Nginx never stopped
```

Origin acceptance, public host resolved to the local origin:

| Route | Before | After |
|---|---|---|
| `/` | 200 | 200 |
| `/verse` | 301 | 301 |
| `/mango7` | 301 | 301 |
| `/mango76` | 301 | 301 |
| `/mango74` | 404 | **308** |
| `/mango74/` | 404 | **200** |
| selected release asset | 404 | **200** |

Result: **PASS — the Mango74 origin route is active, release `472d988b`, and
every unrelated route probed holds its pre-change status.** The neighbouring
`/mango7` project route is unaffected.

The script reported the new route serving on retry attempt 2, one second after
the reload. That confirms the reload window seen on 2026-09-09, when the failed
attempt's probe was answered by a pre-reload worker.

Outstanding: external acceptance from an independent network, and the named
Cloudflare Tunnel for the API hostname. The frontend correctly reports the API
as unavailable until that separate change is made.

Before any Nginx or document-root change, capture the active configuration,
the previous `/mango74` state, and representative unrelated-route responses.
Do not mark T043 complete until the release is installed, Nginx validates and
reloads successfully, and post-deployment checks pass.
