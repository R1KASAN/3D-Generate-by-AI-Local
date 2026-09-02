# Phase 1 Setup Evidence

**Feature**: `001-local-3d-generation`
**Phase**: Repository Setup and Shared Contracts
**Environment**: macOS development host, CPython 3.12.12 provisioned by `uv`,
Node.js v24.13.0, npm 11.6.2
**Scope**: T001–T007 only. No GPU, Windows, LAN, router, DNS, firewall, or
public-network evidence is claimed.

## Commands and results

### T001

```text
git init
Initialized empty Git repository in /Users/ark1/Public/3D Generate by AI Local/.git/

git rev-parse --is-inside-work-tree
true

git check-ignore -v storage/test .env.production
.gitignore:42:storage/  storage/test
.gitignore:10:.env.*    .env.production
```

No files were staged or committed.

### T002

```text
uv sync --project apps/api --group dev --locked
Resolved 36 packages
Audited 35 packages

uv run --project apps/api python -c "import local3d; print(local3d.__version__)"
0.1.0

uv run --project apps/api python --version
Python 3.12.12
```

### T003

The original task command omitted a project selector for `npm exec` and ran
TypeScript from the repository root. The task was corrected to use the equivalent
explicit command below; this is a command-path correction, not a scope change.

```text
npm --prefix apps/web ci
added 508 packages, and audited 509 packages
found 0 vulnerabilities

The install emitted non-blocking deprecation warnings for `whatwg-encoding` and
the unsupported ESLint 9.39.5 release; no dependency vulnerability was reported.

npm --prefix apps/web exec -- tsc --noEmit --project apps/web/tsconfig.json
exit 0
```

### T004

```text
rg -n "(password|secret|token|api_key)=[^<[:space:]]+" .env.example apps/*/.env.example
no matches

rg -n "161\.200\.90\.3|161\.200\.90\.4|203\.[0-9]" .env.example apps/*/.env.example
no matches
```

All environment templates contain loopback development defaults and placeholders
only; no Public IP or credential was written.

### T005

```text
uv run --project apps/api python scripts/verify/validate_contracts.py \
  specs/001-local-3d-generation/contracts/openapi.yaml \
  specs/001-local-3d-generation/contracts/comfyui-workflow-manifest.md
PASS: specs/001-local-3d-generation/contracts/openapi.yaml
PASS: specs/001-local-3d-generation/contracts/comfyui-workflow-manifest.md
```

A temporary OpenAPI `3.0.0`/empty-path document exited `1` with version, path,
and JobToken errors as expected.

### T006

```text
uv run --project apps/api python scripts/verify/verify_fixture_manifest.py fixtures/inputs/README.md
PASS: verified 5 fixtures from fixtures/inputs/README.md
```

A temporary manifest with one altered SHA exited `1` with the expected mismatch.
Fixture hashes are recorded in `fixtures/inputs/README.md`.

### T007

```text
uv run --project apps/api python scripts/verify/validate_glb.py \
  fixtures/models/sample-textured.glb --require-mesh --require-uv \
  --require-material --require-texture
PASS: fixtures/models/sample-textured.glb
```

Temporary malformed and shape-only GLBs exited `1`; errors were respectively
`invalid GLB header` and missing textures/images. Sample SHA-256:
`5039d930f833b34e65ded1117e0d94a897eef954e87c2b2a3ea21426e53bb916`.

## Phase verdict

`PASS` — T001–T007 verification conditions passed. The next incomplete task is
T008, the first foundational test task. This evidence does not unlock any
Windows, GPU, LAN, router, DNS, certificate, firewall, credential, or public
deployment phase.

The requirements checklist has all 16 checkboxes checked. Its Notes paragraph
still contains the pre-clarification text saying that three owner decisions are
open; the current `spec.md` and `plan.md` record those A/A/A decisions as locked.
This documentation inconsistency is non-blocking for Phase 1 and remains for a
later artifact cleanup.
