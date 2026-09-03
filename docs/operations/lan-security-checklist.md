# LAN Security Checklist (T083)

Run from the second LAN client, not from the Windows server. This checklist
proves that the approved LAN entry path is the only route exposed to the
client. It does not authorize Internet exposure or firewall changes.

## Boundary checks

- [ ] Run `scripts/verify/test_lan_boundary.py` with the server's private LAN IP
      and approved entry URL.
- [ ] The approved entry path returns a successful page response.
- [ ] Direct TCP access from the LAN client to server port 8000 is refused or
      blocked.
- [ ] Direct TCP access from the LAN client to server port 8188 is refused or
      blocked.
- [ ] The browser network log contains no request to port 8000 or 8188.
- [ ] Two real Job IDs are used; token A against Job B and token B against Job A
      both return the same safe 404 response.
- [ ] No token, credential, engine ID, local path, or uploaded image content is
      copied into the evidence.

## Required invocation

The recommended one-command helper creates two real jobs on this LAN client,
keeps both opaque tokens in process memory, and invokes the boundary verifier:

```powershell
python scripts/verify/run_lan_boundary.py `
  --server-host <server-private-lan-ip> `
  --entry-url http://<server-private-lan-ip>:3000/ `
  --client-label <second-device-label> `
  --image <path-to-valid-jpeg-or-png>
```

It does not replace the T082 browser flow or the requirement to exercise the
preview controls. It only removes manual token handling from T083.

```powershell
$env:LAN_JOB_A = '<first-job-id>'
$env:LAN_TOKEN_A = '<first-job-token>'
$env:LAN_JOB_B = '<second-job-id>'
$env:LAN_TOKEN_B = '<second-job-token>'
python scripts/verify/test_lan_boundary.py `
  --server-host <server-private-lan-ip> `
  --entry-url http://<approved-lan-entry>/ `
  --client-label <second-device-label>
```

The environment variables are process-local inputs. Clear them after the run;
the verifier never prints or persists their values.

## Evidence

Record the exact sanitized command, client/server labels, timestamps, status
codes, port results, and screenshots in `evidence/lan/isolation-and-ports.md`.
Any reachable internal port is an immediate security failure and blocks the
Phase 10 gate.
