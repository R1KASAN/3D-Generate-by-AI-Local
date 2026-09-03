# LAN Boundary Evidence (T083)

- Date/time (UTC): 2026-09-03T17:23:48.152736+00:00
- Client label: เครื่องที่สอง
- Server LAN address: 172.20.10.6
- Approved entry path: http://172.20.10.6:3000/
- Credentials, capability tokens, uploaded content, and private traces are omitted.

| Check | Observed | Expected | Verdict |
|---|---|---|---|
| second-client-identity | client=เครื่องที่สอง; server=172.20.10.6 | script runs on a separate LAN device | **PASS** |
| approved-entry | HTTP 200 | approved LAN entry path returns 2xx | **PASS** |
| internal-port-8000 | connection refused/blocked | 172.20.10.6:8000 is unreachable from the LAN client | **PASS** |
| internal-port-8188 | connection refused/blocked | 172.20.10.6:8188 is unreachable from the LAN client | **PASS** |
| cross-job-denial | wrong-token responses=404,404 | wrong-job token receives uniform 404 responses | **PASS** |

- A PASS requires execution from a separate LAN device; a server-local or missing-client probe is BLOCKED.
- Overall verdict: **PASS**
