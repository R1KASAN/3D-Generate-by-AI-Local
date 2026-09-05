# GPU/AI-Engine Health-Probe Order Decision — T027

**Feature**: `003-outbound-tunnel-entry` | **Decided**: 2026-09-06

Per [contracts/health-chain.md](../../specs/003-outbound-tunnel-entry/contracts/health-chain.md) H2 and FR-023e, the relative order of the GPU and AI-engine health layers is conditional on probe independence, not preference: GPU may be reported ahead of the AI engine only if its probe does not depend on the engine being up.

## Evidence reviewed

| Source | What it shows |
|---|---|
| [evidence/windows/recovery-matrix.md:11](../windows/recovery-matrix.md) | GPU state (`gpu=cuda:0 NVIDIA GeForce RTX 5070 Laptop GPU : cudaMallocAsync`) is currently reported **as part of ComfyUI's own `/system_stats` response** — i.e. through the engine, not independently of it |
| [evidence/windows/gpu-baseline.md:10](../windows/gpu-baseline.md) | `nvidia-smi` reports GPU presence, driver version, and memory **at the OS level**, with no dependency on ComfyUI being started |

## Decision: adopt Option B — independent `nvidia-smi` probe, GPU ordered above the AI engine

**Chosen layer order**: provider edge → origin/connector → private binding → job service → **GPU (via `nvidia-smi`)** → AI engine (via ComfyUI `/system_stats`)

### Why

1. **`nvidia-smi` genuinely does not depend on ComfyUI.** It queries the driver directly; a hung or crashed ComfyUI process does not affect its output. This satisfies FR-023c's rule that a layer must not report healthy on the strength of a downstream layer it did not itself verify.
2. **Diagnostic value.** With GPU ordered independently above the engine, a driver/hardware fault (GPU layer fails, engine layer would also fail) is now distinguishable from an application-only fault (GPU layer healthy, engine layer fails alone) — exactly the ambiguity Option A (keep current) would leave unresolved.
3. **Low implementation cost.** `nvidia-smi` is already installed and already used for this exact purpose in `scripts/windows/capture_gpu_baseline.ps1`; wiring it into the health chain is a small, self-contained addition (`scripts/windows/health_chain.ps1`, T030).

### What this changes

- `scripts/windows/health_chain.ps1` implements the GPU layer as a parsed `nvidia-smi` invocation (presence + driver responsive), independent of the AI-engine layer's `/system_stats` probe.
- The AI-engine layer keeps using ComfyUI's `/system_stats` for engine-specific readiness (queue state, model load), which `nvidia-smi` cannot report.
- `tests/security/test_health_chain_contract.py` (T028) asserts this order and asserts the GPU probe implementation does not call into the ComfyUI client.

### What does not change

Layers 1–4 (edge, origin/connector, private binding, job service) are unaffected by this decision; their relative order is not in question.
