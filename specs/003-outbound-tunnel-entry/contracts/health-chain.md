# Contract: Layered Health and Recovery

**Feature**: `003-outbound-tunnel-entry` | **Date**: 2026-09-06

Defines the FR-023c health chain, its probe-independence rule, and the per-layer recovery policy across two machines.

---

## H1 — The chain

| # | Layer | Owner | Probe must not depend on |
|---|---|---|---|
| 1 | Provider edge reachable | external | anything below |
| 2 | Approved origin + connector up | origin | the private binding |
| 3 | Private binding live | origin/laptop | the job service |
| 4 | Job service responding | laptop | the AI engine |
| 5 | AI engine responding | laptop | GPU probe internals |
| 6 | GPU present and usable | laptop | — |

**Core rule (FR-023c)**: each layer is checkable on its own, and **a layer must not report healthy on the strength of a downstream layer it did not actually verify.**

## H2 — Ordering of layers 5 and 6 — decision required

FR-023e makes this conditional on probe independence, not preference.

| Option | Probe | Ordering permitted | Consequence |
|---|---|---|---|
| **A** — keep current | GPU read from the AI engine's status response | GPU **below** engine only | A driver fault and an engine fault look the same |
| **B** — independent probe | GPU read at OS level (`nvidia-smi`) | GPU **above** engine allowed | Driver and engine faults become distinguishable |

**Evidence**: the repository currently reports GPU state as part of a ComfyUI health line (`evidence/windows/recovery-matrix.md`), while an independent OS-level probe is already used elsewhere (`evidence/windows/gpu-baseline.md`).

**Recommendation**: adopt **B**. Small task, real diagnostic payoff. Choosing A is valid but must keep GPU below the engine — placing it above while deriving it from the engine violates H1.

## H3 — Reporting

| Property | Rule |
|---|---|
| Granularity | The failing layer is named, never a generic outage (SC-006c) |
| Disclosure | No internal address, port, hostname, or stack detail in any public response (FR-025) |
| Split ownership | Each machine reports the layers it owns; neither infers the other's layers |
| Unknown ≠ healthy | A layer that cannot be probed reports `unknown`, never `healthy` |

## H4 — Recovery policy (FR-024)

```text
on layer failure:
  1. restart the FAILED layer first
  2. do not restart unrelated healthy layers
  3. after the dependency returns, allow a grace period
  4. if a dependent layer is still unhealthy after grace
       → reconnect or restart that dependent layer
  5. stop after 3 consecutive failures at the same layer
       → record a safe diagnostic event, surface the layer, stop looping
```

Each machine acts only on the layers it owns. The origin never restarts laptop services and the laptop never restarts the connector.

**Why the grace period**: a dependent process can hold a stale connection after its dependency recovers. Immediate restart would violate rule 2; never restarting would leave it permanently wedged. Rule 3–4 is the narrow, evidence-driven exception.

## H5 — Startup independence (FR-023a, FR-023d)

| Machine | Starts independently of | Requirement |
|---|---|---|
| Approved origin | The GPU laptop | FR-023, O7 |
| GPU laptop | The origin **and** the private binding | FR-023a |

Either machine may boot first, in either order, and the public service returns automatically once both are up and the binding is re-established (FR-023b, SC-006b).

Layer 3 failing must degrade layers 1–2 to "public path down" while leaving layers 4–6 fully operational for LAN use. **A binding failure is not an application failure.**

## H6 — Acceptance mapping

| Criterion | Test |
|---|---|
| SC-006 | 3× origin reboot → public health restored ≤5 min |
| SC-006a | 3× laptop reboot → binding, job service, queue, engine restored; journey ≤5 min |
| SC-006b | Both machines, both boot orders → automatic return |
| SC-006c | Induced single-layer fault → that layer named specifically |
| SC-006d | Origin down + binding absent → LAN fully usable; no service bound exclusively to the private address |
| SC-006e | Binding returns → public path resumes without restarting the application |
| SC-008 | Engine / binding / job service down separately → project-controlled page ≤5s |
| SC-008a | Origin powered down → provider error; no direct Internet-facing application or management listener reachable (the C1a WireGuard transport listener is excluded from that prohibition); auto-resume |
