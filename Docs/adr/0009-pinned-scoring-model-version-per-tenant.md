# ADR-0009: Scoring model version is pinned per tenant and stamped on every score

**Status:** Accepted
**Date:** 2026-08-14

## Context
Derived risk scores are used two ways with incompatible requirements. Operationally, thresholds and alert rules are tuned against a specific model's output distribution. Evidentially, a score cited months later in an investigation must mean what it meant when it was produced.

Changing the model silently breaks both: tuned thresholds fire wrongly, and historical scores become incomparable to current ones.

## Decision
Each tenant is pinned to a scoring model version. Every score carries the `model_version` that produced it. Platform migration and model upgrade are separate, separately scheduled changes: a tenant migrates on the model version they are already running.

## Options considered

### Option A: Single global model, upgrade everyone together
**Pros:** One code path, simple operations.
**Cons:** Every upgrade is a fleet wide behavioural change. Migration and upgrade collide, and the resulting false positive spike gets attributed to the migration.

### Option B: Version pinned per tenant
**Pros:** Migration is behaviour preserving. Upgrades are opt in with a comparison period.
**Cons:** Multiple model versions in production. Support burden and a long tail of stragglers.

## Trade-off analysis
Option B. Coupling platform migration to a behavioural change is the specific mistake that gets migration programmes rolled back and blamed on the platform.

## Consequences
- Easier: migration is defensible as behaviour preserving; scores remain admissible.
- Harder: multiple model versions live simultaneously; needs a deprecation policy or the tail never ends.
- Revisit if: version skew exceeds an agreed window.

## Action items
1. [ ] Publish a rule and threshold compatibility report per tenant before any cutover: which rules fire identically, which depend on changed signal types.
