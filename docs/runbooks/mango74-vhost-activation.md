# Mango74 vhost activation runbook

Fixes the failed `/mango74` activation on the NT Server. Every command below is
run by the authorized NT operator over their own SSH session. No automation
session connects to the NT Server.

## What the failure looks like

The second activation attempt inserted the include into
`/etc/nginx/sites-available/default` and produced no route change at all:
`/` stayed `200`, `/verse` stayed `301`, `/mango74` stayed `404`. `nginx -t`
passed and the reload succeeded. A change that is genuinely live cannot leave
the new route at its pre-change status — `location = /mango74` is a bare
`return 308` that touches no file and cannot 404 — so the locations were not in
the server block that answered the request.

## Established on 2026-09-09 by `diagnose`

- Two TLS server blocks claim `www.mangosgo.com`: `sites-enabled/default`
  (568 lines, ~135 locations, `location / { proxy_pass http://localhost:4043; }`)
  and `sites-enabled/mango` (11 lines, **no locations at all**).
- `sites-enabled/*` is included by glob, which Nginx expands in sorted order, so
  `default` loads first and **`mango` is the block Nginx reports as ignored**.
  `default` is the effective vhost — the file the previous attempt edited was
  the right one.
- No `include` of a Mango74 snippet exists anywhere under `/etc/nginx` today, so
  the automatic rollback was clean.
- `/etc/nginx/snippets/mango74-static-v2.conf` is present with the approved hash
  `1d75836a…`. `/etc/nginx/snippets/mango74-static.conf` (`31931eb4…`) is an
  unreferenced hand-made copy from the first attempt; it is inert and is left
  alone.

## Root cause, confirmed 2026-09-10

`/etc/nginx/sites-available/default:213` holds another project's route:

```nginx
location /mango7 { alias /var/www/kmitlverse; }
```

`/mango7` is a prefix of `/mango74`, so it captured every Mango74 request, and
`alias` substituted the matched prefix — producing `/var/www/kmitlverse` + `4`.
The error log shows exactly that path for all three probes. The vhost carries
about ninety `/mangoNN` routes and no `/mango74`.

So the earlier failures were never about the server block: the file edited was
the right one, the snippet was correct, and port 443 belongs to the
systemd-managed Nginx (Docker owns only the 4043 upstream behind `location /`).

The snippet still wins, because Nginx resolves `location = /mango74` as an exact
match and `location ^~ /mango74/` as a longer prefix than `/mango7`. Nothing in
the vhost duplicates those locations, so validation passes. Neighbouring URIs
such as `/mango741` keep reaching `/mango7` untouched.

Protect the neighbour explicitly when applying:

```bash
--probe-path /mango7 --probe-path /mango76
```

## The fix

`deploy/nt-server/mango74-vhost.py` reads the merged configuration, lists every
server block that can match the host with its real file and line number, and
installs the include into the blocks that can actually serve the request.

By default (`--targets all-exact`) it patches **every** TLS server block with an
exact `www.mangosgo.com` name, not just the one it believes wins. That removes
the guesswork: whichever duplicate Nginx picks — and the choice can also differ
between the IPv4 and IPv6 sockets — the route is present in it. The snippet owns
`/mango74` only, and `/mango74` currently returns `404` in all of them, so no
existing route can change.

Use `--targets effective` only if the site owner requires a single-block edit.

## Preconditions

- FortiClient VPN connected; SSH session open as the authorized operator.
- Release `472d988b` staged: `/var/www/mango74-releases/472d988b/index.html`
  exists and `/var/www/mango74` points at it.
- The recorded backup from 2026-09-09 is still available.
- `sha256sum`, `curl`, and `python3` are present on the server (Ubuntu default).

## Step 1 — upload (from the Notebook, PowerShell)

```powershell
scp deploy\nt-server\mango74-vhost.py deploy\nt-server\mango74-static.conf <operator>@<nt-host>:~/
```

Expected SHA-256 (verify on both sides):

| File | SHA-256 |
|---|---|
| `mango74-vhost.py` | `769e3f836f993353ad0874f4a0044eb8d61f4f4609e05f6e2f6965aed9a6c7bc` |
| `mango74-static.conf` | `1d75836affbe0b4843364eeae5cb4b6c1486e360e5ae2240ed8f1a72c0dc936a` |

```powershell
Get-FileHash deploy\nt-server\mango74-vhost.py, deploy\nt-server\mango74-static.conf -Algorithm SHA256 | Format-List
```

## Step 2 — verify on the server (read-only)

```bash
sha256sum ~/mango74-vhost.py ~/mango74-static.conf
```

## Step 3 — diagnose (read-only, changes nothing)

```bash
sudo python3 ~/mango74-vhost.py diagnose
```

Read the output before going further:

- **`conflicting server names`** — confirms the duplicate and names the file.
- **candidate list** — each block with `file:start-end`, ports, and matched name.
  The block marked `<-- EFFECTIVE` is the one Nginx uses for `https://`.
- **origin route status** — the pre-change baseline to compare against.

Stop and escalate if:

- no TLS block matches the host — TLS terminates on another device and the
  static route must be added there instead;
- the effective block lives in a file owned by another team — get their approval
  before editing it;
- `/var/www/mango74` does not point at `472d988b` — restage the release first.

## Step 4 — dry run

```bash
sudo python3 ~/mango74-vhost.py activate --snippet ~/mango74-static.conf
```

Prints the exact files and line numbers it would edit. Nothing is written.

## Step 5 — apply

```bash
sudo python3 ~/mango74-vhost.py activate --snippet ~/mango74-static.conf --apply
```

The include points at `/etc/nginx/snippets/mango74-static-v2.conf`, which is
already installed with the approved hash; override with `--snippet-dest` only if
that changes.

The script, in order: records the before-statuses of `/`, `/verse`, `/mango74`,
`/mango74/` and a real release asset; hash-verifies the snippet at that
destination;
backs up every file it edits under `/var/backups/mango74/<timestamp>/`; inserts
the include; runs `nginx -t`; `systemctl reload nginx` (never a stop); re-probes
for up to 15s; and requires all of:

- `/mango74` → `308`
- `/mango74/` → `200`
- release asset → `200`
- `/` and `/verse` → **byte-identical status to before the change**
- `nginx` still `active`

Any failure prints the response headers for `/mango74` and the tail of the Nginx
error log — which identifies the server that actually answered — then restores
every backed-up file, reloads the known-good configuration, and exits non-zero.
`PASS:` on the last line is the only success signal.

Add more routes to the protected set with repeated `--probe-path`, e.g.
`--probe-path /about --probe-path /contact`.

## Step 6 — verify publicly

From a network that is not the NT LAN and not the Notebook:

- `https://www.mangosgo.com/mango74` → `308` to `/mango74/`
- `https://www.mangosgo.com/mango74/` → the application shell
- one `/mango74/_next/static/...` asset → `200` with a JavaScript content type
- the site's own pre-existing routes → unchanged

The application will report the API as unavailable until the named Cloudflare
Tunnel for `mango74-api.mangosgo.com` is activated. That is expected at this
stage and is a separate change.

## Rollback

```bash
sudo python3 ~/mango74-vhost.py rollback --backup-dir /var/backups/mango74/<timestamp>
```

Restores every file recorded in that directory's `manifest.json`, validates, and
reloads. The release directory and the snippet are left in place as rollback
evidence; they are inert once the include is gone.

## Evidence

Record in `evidence/feature-005/nt-frontend-deployment.md`: the command run, the
candidate list with file paths, the before/after route table, the backup
directory id, and the pass/fail line. The script masks IP addresses in its own
output; do not paste raw `nginx -T` dumps, certificate paths, tokens, or user
content into evidence.
