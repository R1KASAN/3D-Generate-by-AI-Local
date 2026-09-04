# Specification Quality Checklist: Cloudflare Public Entry for the 3D Generation Service

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-05
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

**Status: 16/16 pass. Ready for `/speckit-plan`.**

## Notes

### Iteration 1 — initial draft

- *Vendor naming*: "Cloudflare" appears throughout. Intentional, not a violation — the owner directed the vendor choice, so it is an input constraint recorded in Assumptions rather than a design decision leaking from the plan phase. All other requirements stay behavior-focused, naming no product for the reverse proxy, the compute link, or the certificate mechanism.
- *Stale premise in the request*: the request asked the spec to resolve a contradiction at `.specify/memory/constitution.md:42` regarding site-wide login. Verification showed the constitution was already amended to v1.1.0 on 2026-09-04 and now explicitly permits the per-resource capability-token policy, and further classifies a private point-to-point link to a non-public compute node as an internal binding. Recorded as a resolved assumption; no amendment work carried forward.
- *"Define the port for the API"*: settled by Constitution Principle III (single Internet-facing port), which reaches the conclusion before the cross-origin argument does. Captured as FR-006/FR-007 with an Assumptions entry explaining that a second public port would require a constitution exception, not merely a cross-origin design.
- *SC-009 rewritten*: the first draft presupposed the answer to the then-open mode question. Re-scoped to measure that inbound permissions are enumerated and confirmed up front — testable under any mode.

### Iteration 2 — after clarifications resolved

Both markers resolved by owner decision on 2026-09-05:

1. **Public-entry mode → proxied, origin stays at the allocated address.** The allocated address remains the project's real origin; the provider layer sits in front of it. Routing production traffic through a provider tunnel was explicitly rejected because it would leave the allocation unused.
2. **Domain and provider account → held personally by the operator.**

**This answer invalidated part of the iteration-1 draft and required correction, not just insertion.** The draft had declared the edge-server-plus-tunnel design "superseded". Under a proxied origin that is wrong: the edge machine remains mandatory, must stay powered, must hold the allocated address, and must run the reverse proxy. The Context section was rewritten to state what the proxy layer actually changes (origin no longer advertised, public certificate burden removed, inbound permission narrowed to provider ranges) rather than claiming it replaces the origin.

Requirements added as direct consequences of the decisions:

- **FR-001b, FR-005, FR-005a, SC-011, SC-012** — hiding the origin is only a real benefit if the origin also refuses non-proxy traffic. Without these the address is merely unadvertised, which is not a control.
- **FR-003a** — the proxy-to-origin hop must be encrypted *and validated*. Encrypted-but-unvalidated is a common misconfiguration in this topology and would leave the hop trivially interceptable; called out explicitly so the plan cannot select it by default.
- **FR-003b** — the origin certificate must not depend on public validation, which is what removes the plain-HTTP inbound permission entirely.
- **FR-029, SC-013** — personal ownership of the naming layer over an institutionally allocated address is a real continuity risk for a funded deliverable. Not blocked, but required to be documented well enough that the programme can recover without the operator.
- **FR-030** — the superseded planning round missed a required inbound permission until after the architecture was fixed. This makes full enumeration before cutover an explicit requirement and names late discovery as a planning defect.

Assumptions extended to state plainly that the edge machine and the compute link both survive this change, so the plan does not inherit the draft's incorrect implication that they were removed.

**Key Entities** was restructured from a flat list into three ownership tiers (name / proxy / origin), because the failure modes and the responsible parties differ per tier, and because origin failure and GPU-machine failure produce materially different outcomes that the plan must not conflate.
