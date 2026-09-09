# NT Server Mango74 Handoff Contract

The NT Server hosts only the compiled static Frontend under
`https://www.mangosgo.com/mango74/`. It must not run FastAPI, ComfyUI, the AI
models, GPU workloads, or the Notebook's runtime files.

The authorized NT administrator must confirm the server product/version and
deployment mechanism before using platform-specific commands. The handoff
contains only `artifacts/front-end.zip`, its SHA-256/integrity manifest, and a
release/rollback identifier. Deployments must preserve all paths outside
`/mango74`, redirect `/mango74` to `/mango74/`, and serve deep links/assets from
the `/mango74/` base path.

Before changing the server, capture the current Mango74 and representative
unrelated-route baseline and identify a recoverable backup. Rollback restores
only the static Frontend release; it must not move or redeploy the AI Backend.
Record commands and outcomes in `evidence/feature-005/` without credentials or
user content.

## Confirmed Ubuntu/Nginx adapter

The authorized operator confirmed Ubuntu with Nginx 1.28.0, the active
`www.mangosgo.com` server block in `/etc/nginx/sites-available/default`, and an
initially absent `/var/www/mango74`. Stage immutable releases below
`/var/www/mango74-releases/<release-id>` and point `/var/www/mango74` at the
approved release. Copy `mango74-static.conf` to the server and include it only
inside that active HTTPS server block. Always back up the active file, run
`nginx -t`, and use a reload rather than stopping Nginx.

If validation or reload fails, restore the recorded configuration backup and
reload the known-good configuration. Preserve the inactive release and snippet
as rollback evidence instead of deleting them.

For the initial `472d988b` release, the authorized operator may upload
`mango74-static.conf` and `activate-mango74.sh` to their home directory and run
the activation script with the uploaded snippet and the recorded
`default.nginx.before` backup as arguments. The script verifies both hashes,
targets the unique `www.mangosgo.com` server block, validates before reload,
checks the local-origin routes, and restores the backup automatically if any
post-change gate fails.

## Superseded: `activate-mango74.sh`

That script reasons about one file instead of the configuration Nginx actually
merges, and cannot show why its own attempt failed. Measurement on 2026-09-09
established that `sites-enabled/default` **is** the effective vhost — the
shadowed duplicate is the empty `sites-enabled/mango` block — so the include
went into the right file and `/mango74` still returned `404` while `/` and
`/verse` held their exact pre-change statuses. `location = /mango74` is a bare
`return 308` that touches no file, so a `404` there means those locations were
not in the block that answered. The host also runs several containerised Nginx
masters beside the `/etc/nginx` one, so which process owns port 443 has to be
confirmed before any further edit.

`mango74-vhost.py` replaces it. It parses `nginx -T`, reports every server block
that can match the host with its real file and line number, and by default
installs the include into every TLS block with an exact `www.mangosgo.com` name
so the outcome does not depend on which duplicate wins — including when the
IPv4 and IPv6 sockets resolve to different blocks. It keeps every guarantee of
the old script (hash-verified snippet, per-file backups, `nginx -t` before
reload, reload rather than stop, automatic restore on any failed gate) and adds
a read-only `diagnose` mode, a dry run, a before/after comparison that protects
unrelated routes against their measured baseline rather than hardcoded values,
and a `rollback` subcommand.

`activate-mango74.sh` is kept only as the record of the attempt. Do not run it.
The procedure is `docs/runbooks/mango74-vhost-activation.md`.
