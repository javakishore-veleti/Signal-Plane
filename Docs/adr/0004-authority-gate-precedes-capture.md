# ADR-0004: An authority gate precedes every capture session

**Status:** Accepted
**Date:** 2026-08-14

## Context
Capture legality depends on two things the application layer usually ignores: which capture mode is in use, and which jurisdiction governs the subject. Passive metadata from corporate systems and continuous screen capture on a personal endpoint do not have the same approving party. The governing rule follows the subject's location, not the tenant's headquarters.

## Decision
No capture session opens without an authority decision (`schemas/authority-decision.schema.json`) issued by the control plane. The decision names the capture mode, the legal basis, the approver role, bounded constraints, and an expiry. The decision id is stamped on every resulting signal.

Decisions are always bounded. An unbounded grant is treated as a defect, not a configuration choice.

## Options considered

### Option A: Policy checked at query time
**Pros:** Capture is simple. Retroactive policy change applies to history.
**Cons:** Unlawful data is already collected and stored. Deletion is the only remedy and it is imperfect.

### Option B: Policy checked at capture time, stamped on the record
**Pros:** Data that should not exist is never collected. Every record carries its own justification, which is what an audit or a subject access request actually asks for.
**Cons:** Policy changes do not retroactively fix history. Gate availability becomes a capture dependency.

## Trade-off analysis
Option B, because the harm being prevented is collection, not disclosure. The availability concern is handled by short lived cached decisions at the edge with fail closed expiry: if the gate is unreachable past expiry, capture stops rather than continuing unauthorized.

## Consequences
- Easier: audits, subject access requests, proving the negative.
- Harder: gate is on the critical path for session start; cache invalidation on policy change needs care.
- Revisit if: a jurisdiction requires a decision model the schema cannot express.
