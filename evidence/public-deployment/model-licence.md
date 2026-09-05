# AI Model / Workflow Licence Record — Feature 003

**Feature**: `003-outbound-tunnel-entry` | **Task**: T044 | **Recorded**: 2026-09-06

This file records the licence terms governing the model this project deploys publicly, and flags the specific compatibility questions the spec (FR-035, FR-033) requires answered before production traffic is enabled. **This is a research record, not legal advice and not independent legal verification.** Only the project owner can accept the residual risk, exactly as `owner-gate.md` already treats the model-license/territory decision — recorded there as `PENDING`, unresolved as of this writing.

## What is deployed

Per `specs/001-local-3d-generation/research.md` and `plan.md`: **Tencent Hunyuan3D-2.1** (native shape workflow) plus the Hunyuan3D 2.0 wrapper workflow (texture), both running locally on the GPU laptop.

## Licence terms (fetched from the upstream repository, 2026-09-06)

**Licence name**: Tencent Hunyuan 3D 2.1 Community License Agreement
**Source**: `https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/LICENSE`

| Term | Text |
|---|---|
| **Territory** | "THIS LICENSE AGREEMENT DOES NOT APPLY IN THE EUROPEAN UNION, UNITED KINGDOM AND SOUTH KOREA" — the grant is "the worldwide territory, excluding the territory of the European Union, United Kingdom and South Korea." |
| **MAU threshold** | "If... the monthly active users of all products or services made available by or for Licensee is greater than 1 million monthly active users in the preceding calendar month, You must request a license from Tencent." |
| **Hosted-service disclosure** | Must "clearly, accurately, and prominently disclose to all end users the full legal name and entity of the actual provider" and "expressly and conspicuously state that Tencent is not affiliated with, associated with, sponsoring, or endorsing any such service." |
| **Attribution** | Must include: "Tencent Hunyuan 3D 2.1 is licensed under the Tencent Hunyuan 3D 2.1 Community License Agreement, Copyright © 2025 Tencent. All Rights Reserved." |
| **Encouraged (not required)** | A technology-introduction post, and marking the product "Powered by Tencent Hunyuan." |

## Compatibility with this project's intended public use — flagged for owner decision

| Question (FR-035) | Finding | Status |
|---|---|---|
| Does the license permit the intended audience? | **The spec's audience is any anonymous Internet visitor with no stated geographic restriction** (spec.md US1: "An external visitor... without... signing in"). The licence **excludes the EU, UK, and South Korea by territory**. Feature 003 has **no geographic gating** anywhere in its requirements. | ⚠️ **Owner decision required** — either accept the compliance gap (visitors from excluded territories can reach the service with no license coverage), or add geographic restriction, which is currently out of scope and would need a new requirement |
| MAU threshold | 1,000,000 MAU. Given a single-GPU serial queue (FR-021) and realistic load (research.md R8 estimates ~250-570 jobs/day at saturation), this project is many orders of magnitude below the threshold. | ✅ Not a practical concern at this scale |
| Hosted-service disclosure | The licence requires disclosing "the full legal name and entity of the actual provider" to end users and disclaiming Tencent affiliation. **Feature 001/003 have no about/legal page anywhere in their requirements.** | ⚠️ **Owner decision required** — a disclosure surface does not currently exist and is not in either feature's scope |
| Attribution | Required copyright/licence notice. Not currently present anywhere in the deployed application per repository search. | ⚠️ **Owner decision required** — same gap as disclosure |

## What this record does NOT do

- It does not decide whether the project may proceed with the territory gap, the missing disclosure page, or the missing attribution notice — those are the owner's calls, per Constitution Principle IX (Ownership-Critical Decisions).
- It does not constitute legal advice. The owner's risk acceptance, once given, is recorded as an owner decision under the same terms `owner-gate.md` already uses for this exact gate — not as verified legal compliance.
- It does not change `owner-gate.md`'s row for this gate, which remains `PENDING` until the owner actually decides. FR-033's cutover gate (which now explicitly includes licence verification per this session's `/speckit.analyze` remediation) stays blocked until that happens.

## Recommended next step for the owner

Three concrete choices exist, not mutually exclusive:
1. Accept the territory/disclosure/attribution gaps as project risk (matching the existing pattern in `owner-gate.md` for the allocation-memo scope mismatch).
2. Add a minimal attribution + provider-disclosure notice to the frontend (small, addresses two of the three gaps; does not address the territory exclusion).
3. Defer public cutover until legal counsel is consulted on the territory question specifically — this is the one gap a UI change cannot resolve.
