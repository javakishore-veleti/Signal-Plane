# ADR-0008: A federated read path, so migration has no cutover

**Status:** Accepted
**Date:** 2026-08-14

## Context
Migrating a large estate one tenant at a time fails if each migration is a single irreversible event. Investigations in flight, legal holds, and years of history mean a tenant cannot be asked to lose access to their past in exchange for the new platform.

## Decision
A query broker sits behind the console API and resolves reads across both estates, merging by `signal_id` (deterministic, so duplicates collapse). The migration then sequences as:

1. **Read path** moves first. Users work in the managed console while data still lives in the estate. Value delivered, nothing irreversible.
2. **New capture** switches to the managed plane. The estate stops growing.
3. **History** backfills in the background, or ages out under retention, whichever is cheaper for that tenant.
4. **Decommission.**

Every step is independently reversible.

## Consequences
- Easier: reversibility at each step; time to first value is measured in days rather than at the end of a data migration.
- Harder: the broker must degrade gracefully when one estate is unreachable, and must be explicit in the response about which estates answered.
- Revisit if: broker fan out latency becomes the dominant term in console response time.

## Action items
1. [ ] Broker responses carry per estate status so the UI can say "estate results unavailable" rather than silently returning partial data.
