# Public Edge Firewall Evidence

**Task:** T019  
**Status:** BLOCKED — live Edge state is unavailable.

This is a non-claiming evidence placeholder for
`deploy/firewall/verify-public-edge.ps1`. The verifier must replace this file
after an authorized live run; no firewall result is inferred from the authored
policy or from this template.

| Check | Observed | Expected | Verdict |
|---|---|---|---|
| 443/tcp source scope | PENDING live Edge observation | Cloudflare published ranges only | **BLOCKED** |
| 51820/udp availability | PENDING live Edge observation | Present from any source | **BLOCKED** |
| Management rule | PENDING owner-approved path | Approved source and port only | **BLOCKED** |
| Port 80 | PENDING live Edge observation | No allow rule or listener | **BLOCKED** |
| Internal service ports | PENDING live Edge observation | Explicitly blocked | **BLOCKED** |

Required prerequisites: T007 written network permission, T008 proven
management path, authorized Edge access, and a safe rollback plan.
