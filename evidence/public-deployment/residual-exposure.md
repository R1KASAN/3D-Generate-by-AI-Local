# Provider residual exposure

**Feature:** `002-cloudflare-public-entry`  
**Task:** T055  
**Status:** BLOCKED — provider account access and plan-level logging controls are not available in this repository session.

The owner-approved architecture places a third-party proxy in the request path.
That proxy terminates visitor TLS and can therefore observe request credentials
in cleartext while forwarding them. The project must not claim end-to-end
credential non-logging. The only current claim is limited to project-controlled
logs and project-configurable logging controls.

## Required v1.2.0 conditions

| Condition | Current status | Closure evidence required |
|---|---|---|
| Written owner approval | BLOCKED | The owner-gate records requested design intent, but no verified final exposure approval is present in this workspace. |
| Provider credential logging disabled wherever the plan exposes that control | BLOCKED | Provider account owner records each available control and its applied setting. |
| Residual exposure recorded naming the provider | BLOCKED | Provider name, TLS-termination boundary, observability, and logging-control results must be entered after provider access is granted. |
| Proxy-to-origin hop encrypted and certificate-validated | BLOCKED for live proof | Install the Origin CA material, enable provider origin-pull validation, and attach live validation evidence. |

**Required next action:** The owner or authorized provider administrator must
complete T055 during provider configuration, then update this file without
recording credentials or unmasked network addresses.
