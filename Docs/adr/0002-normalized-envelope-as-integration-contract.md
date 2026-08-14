# ADR-0002: A normalized signal envelope is the only integration contract

**Status:** Accepted
**Date:** 2026-08-14

## Context
The platform integrates an open ended set of heterogeneous sources: endpoint agents, collaboration suites, identity providers, security tooling, and self hosted legacy deployments. Each has its own schema, delivery model, and identity representation. The cost that matters is not the first integration, it is the Nth.

## Decision
Define one envelope (`schemas/signal-envelope.schema.json`) that every source is mapped into. Downstream consumers, scoring, rules, storage, and the read API, know only the envelope. A `signal_type` taxonomy carries source specific meaning inside a governed vocabulary; `attributes` carries type specific fields.

## Options considered

### Option A: Per source schemas, consumers handle variants
| Dimension | Assessment |
|---|---|
| Complexity | Low at first, superlinear later |
| Nth integration cost | High, every consumer changes |
| Query surface | Fragmented |

**Pros:** No modelling effort up front. No lossy mapping.
**Cons:** Every new source touches scoring, rules, storage, and UI. The taxonomy ends up implicit and inconsistent across consumers.

### Option B: Single normalized envelope
| Dimension | Assessment |
|---|---|
| Complexity | High up front, flat later |
| Nth integration cost | Low, adapter only |
| Query surface | Uniform |

**Pros:** Adapter N+1 is a mapping exercise. One query surface. One retention model.
**Cons:** Mapping is lossy for exotic fields. Taxonomy governance becomes a standing obligation.

## Trade-off analysis
Option A wins for a fixed, small source set. This platform's premise is that the source set grows indefinitely, so the flat curve wins even though the first three integrations cost more.

The lossy mapping objection is handled by keeping `attributes` open and preserving `source_native_id`, so the raw record is always retrievable from the source of record.

## Consequences
- Easier: onboarding sources, uniform retention, uniform authorization, one read API.
- Harder: taxonomy changes are now breaking changes and need versioning discipline.
- Revisit if: a source's semantics cannot be expressed without abusing `attributes` as a dumping ground.

## Action items
1. [ ] Publish `taxonomy.yaml` as the governed vocabulary, additive only within a `schema_version`.
2. [ ] Contract tests: every adapter validates output against the envelope schema in CI.
