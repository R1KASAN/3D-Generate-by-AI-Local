# Origin transport-boundary rule snippets (provisional)

**Status**: Provisional. The approved origin's operating system is
unverified (`PENDING TARGET INSPECTION`, research.md R1, tasks.md T065).
Do not apply either snippet below without first confirming which OS the
origin actually runs — applying the wrong one is worse than applying
neither.

Both snippets implement the exact same declared boundary in
[`deploy/wireguard/origin-transport-boundary.md`](../../wireguard/origin-transport-boundary.md):
allow `51820/udp` from any source (peer identity is proven by WireGuard's
own handshake, not by source-address filtering — the laptop changes
networks), to the approved origin address only, and nothing else inbound.

## `linux.md` / `windows.md`

Each file is a short, human-readable rule sketch (not a script to be piped
into a shell) for one candidate OS. They exist so the operator has a
starting point at inspection time, not so this repository can silently
configure a live firewall it has never touched. Convert the relevant one
into an actual applied rule only after:

1. confirming the origin OS (T065),
2. confirming the origin directly receives `51820/udp` without router port
   forwarding (T066b, FR-041) — if it does not, stop; Option A is not
   feasible for this target and no rule snippet here should be applied,
3. re-reading `deploy/wireguard/origin-transport-boundary.md` for the
   current declared values in case they changed since this snippet was
   written.

After applying a rule, the live boundary must still be verified
origin-locally (T066a) — no per-OS snippet, however carefully copied,
substitutes for that evidence.
