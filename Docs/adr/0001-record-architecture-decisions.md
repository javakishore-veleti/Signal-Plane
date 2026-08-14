# ADR-0001: Record architecture decisions

**Status:** Accepted
**Date:** 2026-08-14

## Context
This platform makes structural commitments that are expensive to reverse. Decisions that look arbitrary later are the ones reversed by someone who did not hold the constraint that produced them.

## Decision
Every structural decision gets an ADR in `docs/adr`, numbered sequentially, never edited after acceptance. Superseding decisions get a new number and a back reference.

## Consequences
- A reader can reconstruct why the system looks the way it does.
- Reversal becomes a deliberate act with a paper trail.
- Small decisions will be under documented; that is acceptable.
