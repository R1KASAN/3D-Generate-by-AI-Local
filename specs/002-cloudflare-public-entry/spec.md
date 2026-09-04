# Feature Specification: Cloudflare Public Entry for the 3D Generation Service

**Feature Branch**: `002-cloudflare-public-entry`

**Created**: 2026-09-05

**Status**: Draft

**Input**: User description: "แก้ไขสถาปัตยกรรม public access ของฟีเจอร์ 001-local-3d-generation จากเดิมที่วางแผนใช้ Edge server + WireGuard tunnel เปลี่ยนมาใช้ Cloudflare เป็นชั้นหน้าบ้าน (public entry) แทน — ให้ผู้ใช้ภายนอกเข้าถึงเว็บและสั่งงาน AI ผ่าน subdomain ที่จัดการด้วย Cloudflare โดยที่เครื่อง GPU ยังคงย้ายเครือข่ายได้อิสระโดยไม่ต้องแก้ DNS หรือ config ใดๆ"

## Context

Feature `001-local-3d-generation` delivers a working image-to-3D generation service that today is reachable only from the machine that runs it. Its public-deployment phase is gated at `evidence/public-deployment/owner-gate.md`.

The previously planned public architecture placed a reverse proxy on the university-allocated public address and reached the GPU machine over a self-hosted point-to-point tunnel. That structure is retained. The university-allocated address remains the project's real origin, in keeping with the terms under which it was allocated.

What this feature adds is a Cloudflare-managed naming and proxy layer **in front of** that origin. Visitors resolve and connect to Cloudflare; Cloudflare connects to the allocated address. This is an addition to the public path, not a replacement for the allocated address.

The change is worth making for three concrete reasons, in descending order of practical weight:

1. **The origin address stops being publicly advertised.** Visitors never learn it, and the origin can then refuse every connection that did not come through Cloudflare.
2. **Public certificate management moves off the operator entirely.** Cloudflare terminates the visitor-facing connection with a certificate it renews itself. The origin's own certificate no longer has to be publicly trusted, which removes the need for public certificate validation — and therefore the need for any inbound permission on the plain-HTTP port.
3. **The remaining inbound permission narrows.** Instead of opening the secure port to the whole Internet, it need only be opened to Cloudflare's published address ranges.

The generation service itself is unchanged: no application code, no internal port bindings, no upload policy, and no job-authorization behavior is modified by this feature.

**Not adopted**: routing production traffic through a provider-operated tunnel in place of the allocated address. It was evaluated and rejected — it would have left the allocation unused, which is not acceptable for this project.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An external visitor generates a 3D model (Priority: P1)

A person outside the university network opens the project's subdomain in a browser, uploads an image, watches the job progress, previews the resulting textured 3D model, and downloads it — without creating an account, without being asked for a site-wide password, and without ever learning where the machine doing the work physically is.

**Why this priority**: This is the entire purpose of the feature. If only this story ships, the project has a publicly usable AI service, which is the outcome the whole public-deployment phase exists to produce.

**Independent Test**: From a network with no relationship to the university (mobile data or an off-site host), complete the full upload → generate → preview → download journey against the public subdomain and byte-compare the downloaded model against the file the server produced.

**Acceptance Scenarios**:

1. **Given** the service is running and both tiers of the public path are configured, **When** a visitor opens the subdomain over an insecure link, **Then** they are redirected to the secure address and the browser reports a valid, trusted certificate with no warning.
2. **Given** a visitor has uploaded a valid image, **When** the job completes, **Then** they can preview and download the model using only the job credential issued to them at submission, with no login step anywhere in the journey.
3. **Given** a visitor holds the credential for one job, **When** they request another job's status, preview, or download, **Then** the response is indistinguishable from a request for a job that does not exist.
4. **Given** a visitor submits a file above the accepted upload size, **When** the request is rejected, **Then** they receive the service's own explanatory error rather than an unexplained failure from the network layer.

---

### User Story 2 - The GPU machine moves to a different network (Priority: P2)

The operator carries the GPU machine from the university lab to a home network, and later to a mobile hotspot. The public subdomain keeps working throughout. No DNS record, no proxy configuration, and no address in any configuration file is edited at any point.

**Why this priority**: This is the constraint that rules out several otherwise-simpler designs, and it is the reason the operator can own the machine rather than leaving it permanently racked. It is P2 only because P1 must work somewhere before it can be proven to work everywhere.

**Independent Test**: Complete a full generation from an external network with the GPU machine on the university network, then move it to a mobile hotspot and repeat, with a reviewer confirming no configuration file or DNS record was touched in between.

**Acceptance Scenarios**:

1. **Given** the service is reachable and the GPU machine is on the university network, **When** the machine is moved to an entirely different network and reconnects, **Then** the public subdomain serves the application again without operator intervention.
2. **Given** the GPU machine is on a network it has never used before, **When** it finishes starting up, **Then** public reachability is restored automatically without anyone running a command.
3. **Given** the GPU machine has been restarted away from the university, **When** it returns to service, **Then** the generation engine, the API, and the web entry all recover in an order that leaves no component bound to an address that does not yet exist.

---

### User Story 3 - A visitor arrives while the GPU machine is unavailable (Priority: P3)

The GPU machine is switched off, asleep, or without connectivity. A visitor opening the subdomain sees a clear, courteous notice that the generation service is temporarily unavailable — not a raw network error, and not a broken page.

**Why this priority**: It does not add capability, but it is what distinguishes "the service is resting" from "the project is broken" for anyone evaluating the work, including the research programme it is funded under.

**Independent Test**: Disconnect the GPU machine, then load the public subdomain from an external network and confirm a purpose-written unavailability notice is served over a valid secure connection.

**Acceptance Scenarios**:

1. **Given** the GPU machine is unreachable, **When** a visitor loads the subdomain, **Then** they receive a human-readable unavailability notice rather than a generic gateway error code.
2. **Given** the GPU machine is unreachable, **When** a visitor loads the subdomain, **Then** the address still resolves and the secure connection still validates — the domain itself never appears broken or unclaimed.
3. **Given** the GPU machine returns to service, **When** a visitor reloads, **Then** the application is served again without any operator action.

---

### Edge Cases

- The GPU machine joins a network that blocks the outbound path the compute link depends on (some hotel, guest, and corporate networks). The service must degrade to the unavailability notice, and the operator must have a documented fallback path rather than discovering the limitation during a demonstration.
- Connectivity is lost mid-generation. A job already accepted must not report success it did not achieve, and the queue must not be left holding a job that can never finish.
- Two components fail at once — the outbound path is healthy but the web entry is not, or the reverse. Recovery must diagnose which layer is at fault and act on that layer only; restarting the wrong component must not be the response.
- Repeated failed recovery attempts must stop and escalate rather than loop indefinitely, so that a condition automated recovery cannot fix stays visible instead of being buried in restart noise.
- A visitor reaches the underlying address directly, or with an unexpected host name, and must not be served the application.
- The GPU machine sleeps because its lid was closed. This must be prevented by configuration, not by operator discipline.
- Certificate renewal falls due while the operator is away; renewal must not depend on anyone being present.

## Requirements *(mandatory)*

### Functional Requirements

> **Terminology.** The public path has two tiers with different owners and different enforceability, and every requirement below names the tier it binds:
>
> - **Proxy layer** — the Cloudflare edge. Operated by the provider. The project can configure it but cannot inspect or guarantee its internals.
> - **Origin** — the project-operated machine at the allocated address. Fully under project control.
>
> The collective term "public entry" is deliberately not used in any normative requirement, because the two tiers are not equally enforceable and a requirement that spans both cannot be honestly verified.

#### Public entry and naming

- **FR-001**: The service MUST be reachable from the public Internet at a single stable subdomain whose DNS is managed through Cloudflare.
- **FR-001a**: The subdomain MUST be served through Cloudflare's proxy with the university-allocated address configured as the origin. The allocated address remains the project's real public origin; the proxy layer sits in front of it and does not replace it.
- **FR-001b**: The origin address MUST NOT be discoverable from the published subdomain's DNS records.
- **FR-002**: Visitors MUST reach the application only over a secure connection presenting a certificate that public browsers trust without warnings, and insecure requests MUST be redirected to the secure address.
- **FR-003**: The visitor-facing certificate MUST renew without human intervention.
- **FR-003a**: The connection between the proxy layer and the origin MUST also be encrypted, and the proxy MUST be configured to validate the origin's certificate rather than accepting any certificate presented. A connection that is encrypted but unvalidated is not sufficient.
- **FR-003b**: The origin's own certificate MUST NOT depend on public certificate-authority validation, so that no inbound permission on the plain-HTTP port is required for issuance or renewal, and no renewal can fail because a validation path was unavailable.
- **FR-003c**: The origin certificate's issue date, expiry date, and renewal procedure MUST be recorded in operator-visible documentation. Unlike the visitor-facing certificate, the origin certificate is not renewed by the provider — it is long-dated, which means its expiry will fall outside the memory of whoever installed it and will, when it arrives, break the validated proxy-to-origin hop required by FR-003a. A long renewal interval is a reason to record the date, not a reason to omit it.
- **FR-004**: The published address MUST remain unchanged when the GPU machine changes network, location, or underlying network address.
- **FR-005**: The origin MUST refuse connections that did not arrive through the proxy layer. A request sent directly to the origin address, or carrying an unexpected host name, MUST NOT be served the application.
- **FR-005a**: The origin's inbound permission MUST be scoped to the proxy provider's published address ranges rather than to the whole Internet, and MUST be re-verified whenever those published ranges change.

#### Request routing

- **FR-006**: All public traffic MUST enter through the single secure port that the project constitution designates as the sole Internet-facing entry point. A second public port MUST NOT be opened for the API or for any other component. *(Constitution Principle III; see Assumptions for why this also settles the browser-origin question.)*
- **FR-007**: The **origin** MUST route application requests and API requests to their respective internal destinations by request path, so that both are served from one origin as far as the browser is concerned.
- **FR-008**: The generation engine MUST NOT be reachable from the **origin**, from the **proxy layer**, or from the Internet by any path, directly or indirectly.
- **FR-009**: The frontend, backend, generation engine, and remote-administration services MUST remain unreachable from outside, verified by probing from an external network.

#### Job credential handling

- **FR-010**: The **origin** MUST forward the per-job credential header to the backend unmodified — never stripped, rewritten, or renamed.
- **FR-011**: The per-job credential MUST NOT appear in any access log, error log, or diagnostic output produced by the **origin**, or by any other project-operated or project-configured component.
- **FR-011a**: Where the **proxy layer** exposes a control governing whether request headers or credentials are logged or retained, the project MUST configure that control to suppress the credential. Where no such control exists on the owner's plan, the resulting exposure MUST be recorded as residual risk in `evidence/public-deployment/residual-exposure.md`, naming the provider and what it is able to observe.
- **FR-011b**: The project MUST NOT claim the credential is unlogged end-to-end. Because the proxy layer terminates TLS, it necessarily processes the credential in cleartext in order to forward it. Every claim about credential logging MUST state the boundary it applies to. *(Constitution Principle III, as amended in v1.2.0.)*
- **FR-012**: The per-job credential MUST NOT appear in any URL, so that it cannot be captured by intermediate logging, browser history, or referrer headers.
- **FR-013**: A request with a missing credential and a request with another job's credential MUST produce responses that are indistinguishable from each other and from a request for a nonexistent job.

#### Upload handling

- **FR-014**: Any request-size limit configured at the **origin** MUST be set above the service's own upload limit by a margin sufficient to cover multipart encoding overhead, so that a file the service accepts is never rejected by the network layer first. The **proxy layer**'s own ceiling MUST be confirmed to exceed the service's limit, but is not configured by this project.
- **FR-015**: The service — not the **origin**, and not the **proxy layer** — MUST remain the component that enforces the upload policy and returns the explanatory error.

#### Continuity and recovery

- **FR-016**: The connection between the **origin** and the GPU machine MUST be established outbound from the GPU machine, so that it requires no inbound reachability to that machine on any network it joins.
- **FR-017**: The connection MUST re-establish itself automatically after network loss, network change, and machine restart, with no operator command.
- **FR-018**: Service components that depend on an address created by the connection MUST NOT start until that address exists and is confirmed usable, and MUST recover if it later disappears and returns.
- **FR-019**: Automated recovery MUST determine which layer has failed — the connection or the application — and act only on that layer.
- **FR-020**: Automated recovery MUST enforce a cooldown between attempts, and MUST stop and escalate after a bounded number of unsuccessful attempts rather than retrying indefinitely.
- **FR-021**: When the GPU machine is unavailable, the **origin** MUST serve a purpose-written unavailability notice; the domain and its secure connection, both provided by the **proxy layer**, MUST continue to work.
- **FR-022**: The GPU machine MUST be configured not to suspend while powered, including when its lid is closed.

#### Governance and evidence

- **FR-023**: Neither the **origin** nor the **proxy layer** MUST be configured to require any site-wide login, in accordance with the owner-approved access policy of 2026-09-04.
- **FR-024**: Components MUST NOT be bound to a wildcard network address. Internal components MUST remain bound to loopback or to the private connection interface only.
- **FR-025**: Only the network address allocated for this purpose MUST be used in any configuration or network-applying script. The alternate address from the same allocation MUST NOT appear in any such file, and MUST NOT be probed by any verification script. It MAY appear in documentation, evidence, and in the tests that assert its exclusion.
- **FR-026**: Every evidence artifact MUST mask network addresses, and MUST NOT record credentials, tokens, or passwords.
- **FR-027**: Acceptance MUST be evidenced from outside the university network; verification performed from inside it MUST NOT be accepted as proof of external reachability.
- **FR-028**: Any inbound network permission this design still requires MUST be verified by a positive test that proves traffic actually traverses it, not only by a negative test showing an absence of response — a closed path and a correctly silent one are otherwise indistinguishable.
- **FR-029**: Because the published name and the account controlling it are held personally while the origin address is institutional, the project MUST record — in owner-visible documentation, not only in one person's memory — the domain registrar, the provider account identity, the renewal dates, and the procedure for transferring or reconstructing the naming layer. This MUST be sufficient for the research programme to restore public reachability without the original operator.
- **FR-030**: The complete set of inbound permissions the design requires MUST be enumerated and confirmed in writing before any cutover step begins. Discovering a further required permission during cutover MUST be treated as a planning defect, not as a routine follow-up request.

### Key Entities

There are now three tiers in the public path, and keeping them distinct matters because each fails differently and each is owned by a different party.

- **Public subdomain**: The single stable name at which the service is published. Personally owned; independent of where the GPU machine is.
- **Proxy layer**: Terminates the visitor-facing secure connection, manages that certificate, and forwards to the origin. Operated by the provider; not under project control.
- **Origin**: The machine holding the university-allocated address. Runs the reverse proxy that routes by path, serves the unavailability notice, and forwards job credentials untouched. Accepts connections only from the proxy layer. Institutionally allocated; must stay powered and in place.
- **Compute link**: The connection between the origin and the GPU machine, established outbound from the GPU machine so that no inbound reachability to it is ever required.
- **GPU machine**: The mobile compute node running the generation engine, backend, and web application, all on non-public bindings. Freely relocatable.
- **Job credential**: The per-job capability issued at submission that authorizes status, preview, and download for exactly one job. Must survive the full path untouched and unlogged.
- **Allocated network address**: The university-assigned public address, subject to the single-address restriction in FR-025.

Availability is the product of the origin and the GPU machine both being up: the origin failing takes the service down entirely, whereas the GPU machine failing degrades it to the unavailability notice. These are different outcomes and the plan should not treat them as one.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A person outside the university completes the full journey — upload, generation, preview, download — through the public address, and the downloaded model is byte-identical to the file the server produced.
- **SC-002**: The same journey succeeds with the GPU machine on at least three distinct networks, including one mobile connection, with zero configuration or DNS edits between runs.
- **SC-003**: After the GPU machine is restarted on a network away from the university, the service becomes publicly usable again with no operator command, in at least 3 consecutive restart trials.
- **SC-004**: An external port scan finds no reachable frontend, backend, generation-engine, or remote-administration service.
- **SC-005**: Requests with a missing credential and with another job's credential are byte-identical in response to a request for a nonexistent job.
- **SC-006**: A search of every project-controlled log — the origin's access and error logs, and the application's logs on the GPU machine — for a known job credential returns zero matches. Provider-side logs are out of scope for this criterion because they are not retrievable on the owner's plan; that gap is measured by SC-006a instead.
- **SC-006a**: `evidence/public-deployment/residual-exposure.md` exists, names the provider, states that it terminates TLS and therefore processes credentials in cleartext, records which provider-side logging controls were available and how each was set, and is reviewed against the four conditions in Constitution Principle III.
- **SC-007**: With the GPU machine disconnected, the public address still resolves, still presents a valid certificate, and returns a purpose-written unavailability notice rather than a raw gateway error.
- **SC-008**: The public address becomes usable again within 5 minutes of the GPU machine regaining connectivity, without operator action.
- **SC-009**: Every inbound network permission the chosen mode requires is either zero, or is enumerated, requested, and confirmed in writing before cutover begins — with none discovered mid-deployment. *(The superseded design failed this: a required UDP permission surfaced only after the architecture was settled.)*
- **SC-010**: A reviewer confirms every evidence artifact masks network addresses and contains no credential material.
- **SC-011**: A request sent directly to the origin address, bypassing the published name, is refused — confirmed from an external network.
- **SC-012**: The published name's public DNS records do not disclose the origin address.
- **SC-013**: A person other than the operator can, using only project documentation, state where the domain is registered, which account controls it, when it renews, and how to restore public reachability if that account becomes unavailable.
- **SC-014**: The origin certificate's issue date, expiry date, and renewal procedure are recorded in operator documentation and can be stated by someone who did not install it.
- **SC-015**: From a machine on the same physical network as the GPU machine, the web entry port is refused — proving the internal binding is enforced by the machine itself and not merely hidden by whatever network it currently occupies.

## Assumptions

- **The API is not given its own public port, and this is settled rather than open.** Constitution Principle III designates one secure port as the sole Internet-facing entry, which alone decides the question. Independently, the backend carries no cross-origin permissions, so serving it from a second port or origin would cause browsers to block the application's own requests; and the frontend already forwards API calls internally, so no second public port is needed. Any future proposal to split the API onto its own port would therefore require a constitution exception, a cross-origin permissions design, and a fresh security review.
- **The constitution has been amended twice for this work, and both amendments are complete.** v1.1.0 (2026-09-04) permits a per-resource capability-token policy with no site-wide login and classifies a private point-to-point link to a non-public compute node as an internal binding rather than public VPN access. v1.2.0 (2026-09-05) scopes the no-token-logging rule to logs the project controls or configures, and bounds the residual exposure created by a TLS-terminating proxy under four conjunctive conditions. The second was made in response to `/speckit-analyze` finding N1 — the proxied mode could not comply with the prior absolute wording, because the provider's logging behaviour is outside project control. No exception entry is required, because the principle was amended rather than reinterpreted.
- The generation service's own behavior is unchanged by this feature: no application code, upload limit, retention policy, job-authorization rule, or internal port binding is modified.
- The GPU machine is a single mobile workstation with one GPU, so generation remains serial; this feature does not change throughput or concurrency.
- Availability is bounded by the GPU machine being powered, awake, and connected. Continuous availability is not a goal of this feature; a clear unavailability notice is.
- Perceived download speed for finished models is bounded by the upload bandwidth of whatever network the GPU machine currently occupies. This is accepted, not solved here.
- **The owner-gate decision on model-license and permitted-user territory scope is now resolved by explicit owner decision (2026-09-05).** Permitted users: individuals learning 3D modeling, non-commercial use only, expected to be predominantly in Asia. Territory: **Asia, excluding South Korea**, with no geographic access restriction technically enforced at the proxy layer as of this decision.

  South Korea's exclusion is not incidental — the Hunyuan3D LICENSE text (as published in the Tencent-Hunyuan GitHub repository at the time of this decision) names South Korea explicitly, alongside the European Union and the United Kingdom, as outside its defined "Territory," and limits the license grant to that Territory. Because South Korea is geographically part of Asia, an "Asia" scope stated without that exclusion would directly overlap the license's own named restriction — this is a closer conflict than a worldwide scope would have been, not a smaller one.

  This is recorded as an **owner risk-acceptance decision**, not a verified-compliant determination. No geographic filtering is technically enforced yet — the stated scope currently describes intended audience, not an enforced boundary. If geographic enforcement is added later (e.g. Cloudflare country-level rules excluding South Korea, the EU, and the UK), that is separate follow-on work, not assumed complete by this decision. This project has not obtained a separate legal opinion or a commercial license from Tencent confirming the deployment is compliant. `evidence/public-deployment/owner-gate.md` MUST record this decision in these terms — the stated territory, the specific named overlap with South Korea, and that no technical enforcement exists yet — rather than as a compliance verification, so the evidence remains accurate to what was actually established.
- Cloudflare is the chosen provider for the public naming and proxy layer, as directed by the owner. Vendor selection is treated as an input constraint, not an open design question.
- **The edge machine at the allocated address remains part of the architecture.** Choosing a proxied origin means the origin still has to exist, stay powered, hold the allocated address, and run the reverse proxy. This feature narrows what must be opened to it and removes its public certificate burden; it does not remove the machine or the need for administrative access to it.
- **A link from the edge to the GPU machine is still required**, and it must be initiated outbound from the GPU machine to satisfy the mobility requirement (FR-016). Its mechanism is a plan-phase decision. Whatever is chosen, any inbound permission it needs at the origin counts under FR-030 and must be enumerated before cutover — this is precisely the class of requirement that was missed in the superseded planning round.
- The provider's request-size limit on the owner's plan is assumed to exceed the service's own upload limit by a wide margin. This should be confirmed once during planning rather than assumed at cutover.
- Placing a proxy in front of the origin introduces a third party into the request path for all public traffic, including uploaded images and generated models. This is accepted as the cost of the benefits listed in Context.

## Dependencies

- **A domain and Cloudflare account held personally by the operator.** Recorded as the owner's decision under Constitution Principle IX. Two consequences follow and MUST be recorded in the owner gate rather than left implicit:
  - The published address depends on one individual's registrar and provider accounts. If those lapse or become inaccessible, the service becomes unreachable and the research programme has no independent route to restore it. FR-029 exists to bound this.
  - The allocated network address is institutional while the name in front of it is personal. Any handover, publication, or final report should state this split plainly so it is not discovered later.
- The existing generation service from feature `001-local-3d-generation`, running and healthy.
- The owner-gate decisions recorded in `evidence/public-deployment/owner-gate.md`, which this feature updates rather than bypasses.
- An external vantage point (mobile data or off-site host) for acceptance evidence.

## Out of Scope

- Moving the web application off the GPU machine so that it stays available while that machine is off. That is a different availability tier and would change how API traffic flows; it is explicitly not attempted here.
- Routing production traffic through a provider-operated tunnel instead of the allocated address. Evaluated and rejected — it would leave the allocation unused.
- Caching generated models at the proxy layer, or serving them from provider storage.
- Migrating the naming layer to institutional ownership. Recorded as a known consequence of the ownership decision (FR-029), not scheduled here.
- Any change to generation quality, model selection, job queuing, or the 3D viewer.
- High availability, horizontal scaling, or a second GPU worker.
- Remote administration of the GPU machine over the public path.
