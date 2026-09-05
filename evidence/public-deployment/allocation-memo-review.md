# Allocation Memo Review — What the Source Document Actually Says

**Feature:** `002-cloudflare-public-entry` / `003-outbound-tunnel-entry`
**Reviewed:** 2026-09-05
**Purpose:** Record what the operator-supplied source document actually
contains, since prior evidence in this repository cited it inaccurately, and
record the owner's decision to use the allocated address for this project
despite a scope mismatch between that document and this project.

This file corrects earlier evidence rather than replacing it silently. It
does not claim institutional pre-approval this project does not have.

## What was reviewed

A single PDF supplied by the operator: a two-page university memo
("บันทึกข้อความ") from the Electrical Engineering Department, Chulalongkorn
University, dated 26 ธันวาคม 2567. Page 2 contains no extractable text or
image content — no signature block, no approval stamp, no continuation text.

## What the document actually states

| Field | Content |
|---|---|
| Reference number ("ที่") | **Blank in the source document.** No memo number is present. |
| Date | 26 ธันวาคม 2567 |
| Subject | "ขอยกเว้นการระบุตัวตน (Authentication)" — a request for an authentication exemption |
| Addressee | รองคณบดี (รศ.ดร.อติวงศ์ สุชาโต), through the head of the Electrical Engineering Department |
| Named project | **"An Organic Food Tracking by using Blockchain in Lao PDR"**, funded by ASEAN IVO |
| Named equipment | One server, installed at the Information and Communication Engineering Research Laboratory, 13th floor, Charoenwitwa Engineering Building |
| Stated need | Continuous outbound connectivity to the public Internet, to control and process blockchain transactions with three external universities |
| What is requested | Exemption from the university's identity-verification (authentication) requirement, so the named server can reach the outside Internet without going through it |
| IP addresses named | `161.200.90.3` and `161.200.90.4`, prepared for this purpose |
| Signatories | ศาสตราจารย์ ดร.ลัญฉกร วุฒิสิทธิกุลกิจ (หัวหน้ากลุ่มวิจัยระบบนิเวศน์การสื่อสารไร้สาย) and รองศาสตราจารย์ ดร.เชาวน์ดิศ อัศวกุล (หัวหน้าภาควิชาวิศวกรรมไฟฟ้า) |

## What the document does not state

- It does not name this project (`001-local-3d-generation` /
  `002-cloudflare-public-entry` / `003-outbound-tunnel-entry`) or the AI 3D
  generation service.
- It does not request or grant permission to accept inbound connections from
  the public Internet, to run a public-facing web service, or to host content
  for anonymous external visitors. The stated need is the reverse — outbound
  connectivity for a private research link between four universities.
- It carries no reference number, so it cannot be cited by number. Earlier
  evidence in this repository (`network-permissions.md`,
  `network-permission-request.md`, both runbook files, and
  `specs/002-cloudflare-public-entry/tasks.md`) cited it as
  "วฟ.2174/2567" — **that citation was incorrect and has been corrected** to
  describe the document by date and subject instead of by an invented
  reference number.
- It does not appear to bear a signed approval from the addressed Associate
  Dean; page 2, which might carry that, is blank in the copy supplied.

## Live reachability check performed alongside this review

From the GPU laptop, on the network available at review time (2026-09-05):

| Check | Result |
|---|---|
| ICMP ping to `161.200.90.4` | No response |
| TCP 443 to `161.200.90.4` | Connection failed |
| TCP 80 to `161.200.90.4` | Connection failed |

This is consistent with either an unconfigured listener or a network path
that blocks the probe; it does not distinguish between the two, and it is not
authoritative evidence about the machine itself. It is recorded because it
directly informs the architecture choice below: a design that does not depend
on this address being inbound-reachable is not weakened by this result,
whereas a design that does depend on it (the original `002` inbound-proxy
plan) has no confirmed listener to build on.

## Owner statement and risk-acceptance decision

Recorded 2026-09-05, in the operator's own words, in response to being asked
whether use of `161.200.90.4` for this project is authorized:

> "ได้รับอนุมัติ เพราะ ผมพัฒนาโปรเจคคนเดียว" (approved, because I am the sole
> developer of this project) — regarding the server: "เป็นเครื่องเดียวที่จะใช้กัน
> เเละ มีสิทธิตามในเอกสารเลย" (it is the one machine that will be used, and I
> have rights per the document) — regarding a new filing: "ไม่จำเป็นต้องยื่นอะไร
> เพราะ เขาโยนทุกอย่างให้ผม DEV" (no new filing is needed, because they handed
> everything to me as the developer).

This is recorded as an **owner risk-acceptance decision**, on the same terms
`owner-gate.md` already uses for the model-license/territory decision — not
as a verified institutional approval, because the source document does not
support that stronger reading. Specifically:

- The document's stated project, stated purpose, and stated traffic direction
  (outbound-only, private, four-university research link) do not match this
  project's stated purpose (a public-facing web service accepting uploads
  from anonymous Internet visitors).
- "I am the sole developer of this project" establishes the operator's
  authority over *this project's* architecture and decisions under
  Constitution Principle IX. It does not, by itself, establish that a
  document written for a different, named project extends to this one — that
  is an institutional fact, not a project-architecture decision, and this
  project has no independent written confirmation of it.
- The verbal statement that "they handed everything to me as the developer"
  is recorded here as the operator's account. It is not itself the kind of
  written confirmation this project's own evidence practice otherwise
  requires (compare `network-permissions.md`'s treatment of the border
  firewall permission, which is recorded as approved only because an
  explicit written record exists).

**What follows from this, stated plainly rather than left implicit:**

1. The project proceeds using `161.200.90.4` on the operator's explicit
   instruction and at the operator's own risk, per the statement above.
2. Because the chosen architecture (`003-outbound-tunnel-entry`) requires no
   inbound permission at the university border firewall at all, the specific
   risk this scope mismatch creates is narrower than it would have been under
   `002`'s inbound-proxy design: there is no firewall rule to be revoked, and
   no default-deny boundary that a revocation could turn into a lockout.
   The remaining risk is narrower but not zero: the allocated address could
   still be reassigned or the machine's network access revoked if the
   department determines the address is being used for a purpose the cited
   document does not cover.
3. A short written confirmation from the lab head or advisor — even a single
   line — that this address may also serve the AI 3D generation project would
   close this gap. This is a recommendation, not a blocking gate; the
   operator has been informed of the trade-off and has chosen to proceed
   without it.

## What this file corrects

- `network-permissions.md`, `network-permission-request.md`,
  `windows-ai-server-runbook.en.md`, `windows-ai-server-runbook.th.md`, and
  `specs/002-cloudflare-public-entry/tasks.md` cited the source document as
  "Memo วฟ.2174/2567." That reference number does not appear in the document
  and has been replaced in each file with a description by date and subject.
- `operator-inputs.md`'s row on whether the origin holds the allocated
  address is updated to reflect that a physical server at the stated location
  is confirmed by the operator to exist and to be the intended machine, while
  the live-reachability and OS rows remain open for the reasons stated above.
