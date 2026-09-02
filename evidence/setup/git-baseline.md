# Evidence: Git Baseline and GitHub Publication

**Date:** 2026-09-03 | **Run by:** Owner (macOS workstation) | **Verdict:** PASS

**Scope:** Establishes a reviewable source baseline so the Windows NVIDIA server
can clone identical source before Phase 7 (T058–T064). This evidence covers
source publication only. It claims nothing about Windows, GPU, CUDA, ComfyUI,
Hunyuan3D, or GLB results.

## Result

| Item | Value |
|---|---|
| Repository | https://github.com/R1KASAN/3D-Generate-by-AI-Local |
| Visibility | `public` (Owner confirmed before creation) |
| Default branch | `main` |
| Baseline commit | `fefad6ec10d2e96405b34efb0d0e4352258ab3b4` |
| Files committed | 150 |
| Insertions | 22,893 |

GitHub normalised the requested name `3D Generate by AI Local` to
`3D-Generate-by-AI-Local`; GitHub repository names cannot contain spaces.

## Pre-commit secret review

Performed before staging, on the exact file set that `git add -A --dry-run`
resolved (150 files).

Patterns scanned, case-insensitive, with placeholder/example/mock hits excluded:

```text
api[_-]?key            secret[_-]?key         access[_-]?token
password =             aws_secret             AKIA[0-9A-Z]{16}
ghp_[0-9A-Za-z]{36}    sk-[A-Za-z0-9]{20,}    xox[baprs]-
BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY
```

**Result: zero findings.**

### Exclusion checks

| Check | Result |
|---|---|
| `node_modules/` in staged set | 0 files |
| `.venv/` in staged set | 0 files |
| `.mypy_cache/` in staged set | 0 files |
| Real `.env` files in staged set | 0 files (only `.env.example` templates) |
| Model weights (`*.safetensors`, `*.ckpt`, `*.pth`, `*.bin`) | 0 files |
| Largest committed file | `fixtures/inputs/oversized-reference.png`, 10 MB, intentional upload-limit test fixture |

The three committed `.env.example` files contain loopback defaults only
(`127.0.0.1`, `./storage`, `mock` adapter). `PUBLIC_DOMAIN` is a placeholder
literal, `<owner-provided-at-public-deployment>`, not a real hostname.

`.gitignore` was verified to exclude `.env`, `.env.*`, `*.pem`, `*.key`,
`*.p12`, `credentials/`, runtime storage, ComfyUI output/temp, logs, caches,
model artifacts, and the owner-held network-evidence PDF under
`docs/reference/`.

## Commands run

```bash
gh auth status
git add -A --dry-run          # reviewed the resolved 150-file set
# secret-pattern scan over that file set
git add -A
git commit -m "Initial baseline commit for 3D Generate by AI Local"
gh repo create "3D Generate by AI Local" --public --source=. --remote=origin --push
git log -1 --format=%H
```

## Verification for the Windows operator

```powershell
git clone https://github.com/R1KASAN/3D-Generate-by-AI-Local.git
Set-Location 3D-Generate-by-AI-Local
git log -1 --format=%H   # expect fefad6ec10d2e96405b34efb0d0e4352258ab3b4
git status --short       # expect empty
```

## Boundary

This PASS unlocks cloning the source on the Windows machine. It does not
unlock, and must not be cited as progress toward, T058–T064, adapter work,
LAN, or public deployment. Phase 7 begins unrun.

## Related

- [Windows Phase 7 operator runbook (Thai source)](../../docs/operations/windows-phase7-operator-guide.th.md)
- [Windows Phase 7 operator runbook (English)](../../docs/operations/windows-phase7-operator-guide.en.md)
- [AI runtime source register](../../docs/reference/ai-runtime-sources.md)
