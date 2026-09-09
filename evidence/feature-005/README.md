# Feature 005 Evidence Rules

Evidence in this directory records only validation that actually occurred.
Each record must include the UTC timestamp, exact command or operator action,
result, and any blocker. Mark administrator, elevated, reboot, external-network,
and real-GPU work explicitly as a manual gate.

Never store Cloudflare/Tunnel credentials, API keys, job tokens, user uploads,
generated GLBs, model bytes, private environment files, raw stack traces, or
unredacted local paths. Use hashes, counts, status codes, and redacted host
names only where the acceptance record requires them.
