# Firebase preview without API permission

Validation timestamp (UTC): `2026-09-09T08:17:53Z`.

## Scope

This evidence covers the frontend-only Firebase Hosting preview with no
Firebase-origin CORS permission enabled. It does not represent production
deployment or named-Tunnel activation.

## Commands and results

1. Built the static preview artifact:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\build_frontend_package.ps1 `
     -ProjectRoot (Get-Location).Path `
     -OutputPath .\tmp\feature005-firebase-preview.zip `
     -DeploymentEnv firebase-preview
   ```

   Result: PASS. The static validator accepted both the tree and archive.
   The build staged the `/mango74/` tree for Firebase Hosting while keeping
   the production `/mango74` base path. The archive hash was not committed.

2. Deployed only the frontend to a temporary Firebase Hosting channel:

   ```powershell
   npx -y firebase-tools@latest hosting:channel:deploy feature005-disabled `
     --project inw3d-ai-local --expires 1d
   ```

   Result: PASS. Channel URL:
   `https://inw3d-ai-local--feature005-disabled-jikpad5o.web.app`
   The channel expires on 2026-09-10. No FastAPI, ComfyUI, model, workflow,
   upload, generated-output, or credential file was deployed. The CLI showed
   an Auth-channel synchronization warning; no Auth or API permission was
   enabled.

3. Verified the static route and base path:

   - `/` returned a 301 to `/mango74/`.
   - `/mango74/` returned HTTP 200 with the application HTML.
   - `/mango74/_next/static/chunks/2o_dwpqs6eksx.css` returned HTTP 200.
   - `/mango74` returned a 301 to `/mango74/`.

4. Ran a headless Chromium check against the channel URL at `/mango74/`.
   The page loaded, the reference image was accepted, and submitting the form
   produced `The AI service is temporarily unavailable. Please retry.` It did
   not display `This job is no longer available`. The browser request to
   `https://mango74-api.mangosgo.com/api/v1/jobs` failed with DNS
   `net::ERR_NAME_NOT_RESOLVED`, which is the expected unavailable state while
   the named Tunnel/stable API is not configured.

5. Read-only channel inventory:

   ```powershell
   npx -y firebase-tools@latest hosting:channel:list --project inw3d-ai-local
   ```

   Result: the temporary `feature005-disabled` channel is separate from the
   existing `live` channel. No production-channel deploy command was run.

## Conclusion

The frontend-only Firebase preview and its no-API-permission behavior are
validated. Production `https://www.mangosgo.com/mango74/` and production CORS
configuration were not changed. T098 remains an administrator gate because
the stable API and named Tunnel are not available for the temporary CORS-on,
controlled-flow, and permission-removal trial.
