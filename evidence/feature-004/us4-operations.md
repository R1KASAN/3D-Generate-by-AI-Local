# Feature 004 Local Operations Evidence

- Date/time (UTC): 2026-09-06T21:41:17.7096567Z
- Scope: installed/start, H2-H9 local health, forced layer failures, clean stop/start, and data preservation.
- Quick Tunnel was not started. Tokens, user content, engine identifiers, and private paths are omitted.

| Check | Sanitized observation | Verdict |
|---|---|---|
| installed-started-stack | four approved services are installed and running | **PASS** |
| loopback-health-baseline | Caddy web/API routes and ComfyUI respond | **PASS** |
| quick-tunnel-absent | no Quick Tunnel process was used | **PASS** |
| caddy-failure-diagnosis | caddy=0; direct_api=200 | **PASS** |
| web-failure-diagnosis | root_through_caddy=0; direct_api=200 | **PASS** |
| api-failure-diagnosis | root_through_caddy=0; direct_web=0; direct_comfy=200 | **PASS** |
| engine-failure-diagnosis | live=0; engine=0; root=0; direct_web=0; direct_comfy=0 | **PASS** |
| clean-stop | all four services stopped in reverse dependency order | **PASS** |
| clean-restart | all local layers recovered within two minutes | **PASS** |
| local-data-preserved | storage_present=True; database_bytes_before=126976; after=126976 | **PASS** |

- Overall verdict: **PASS**
