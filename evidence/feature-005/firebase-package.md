# Firebase preview package

- Build command: `scripts/windows/build_frontend_package.ps1 -DeploymentEnv firebase-preview`.
- Result: PASS; static validator accepted the tree and archive, and staged a
  second copy under `/mango74/` for Firebase Hosting asset resolution.
- API mode: stable configured API base only; no Firebase credentials or
  backend files included.
- Archive/hash: kept in local operator output and must be supplied through the
  approved handoff, not committed here.
- Frontend-only preview deployment and no-API-permission behavior are recorded
  in `firebase-preview-disabled.md`.
- Enabling/removing Firebase-origin CORS permission remains the T098
  administrator gate.
