# ADR-0003: One adapter per source, not a shared ingest service

**Status:** Accepted
**Date:** 2026-08-14

## Context
Sources differ in delivery model (poll, webhook, stream), rate limits, auth, and failure modes. A shared ingest service accumulates conditionals and couples the release cadence of unrelated integrations.

## Decision
Each source gets its own adapter: an independently deployed, independently versioned unit that owns exactly one source system and emits the envelope. Adapters register a manifest (`schemas/adapter-manifest.schema.json`) with the control plane.

## Options considered

### Option A: Shared ingest service with per source plugins
**Pros:** One deployment, shared retry and observability.
**Cons:** One source's rate limit backs up others. A plugin bug takes the whole ingest path down. Every source change is a release of the shared service.

### Option B: Adapter per source
**Pros:** Blast radius is one source. Independent scaling and release. Onboarding does not add load to existing integrations.
**Cons:** More deployment units. Cross cutting concerns must be a shared library, which drifts if not enforced.

## Trade-off analysis
Isolation is worth the operational multiplicity because the failure mode being avoided (one noisy source degrading all ingest) is both likely and customer visible. The drift risk is mitigated by putting envelope construction, hashing, and emission in `adapters/python/common` and failing CI on schema violations.

## Consequences
- Easier: adding sources, isolating incidents, per source cost attribution.
- Harder: keeping the shared library version current across adapters.
- Revisit if: adapter count stays under about five permanently.
