# ADR-0006: Large payloads travel by reference, never on the bus

**Status:** Accepted
**Date:** 2026-08-14

## Context
Screen captures, attachments, and recordings dominate storage volume by orders of magnitude while being a small fraction of event count. Putting them on the event bus destroys the bus's latency profile, breaks message size limits, and makes retention deletion impossible because copies exist in every consumer's offset range.

## Decision
The bus carries a `blob-reference`: object store URI, content hash, size, media type, encryption key id, retention class, legal hold flag. Bytes go to the object store on write, with object lock for anything under legal hold.

## Consequences
- Easier: retention and deletion have exactly one enforcement point. Chain of custody comes free from the content hash plus object lock.
- Harder: two write paths must be made atomic enough; the reference must not be published before the blob is durable.
- Revisit if: a consumer genuinely needs inline bytes for low latency inference. Prefer moving inference to the object store side.

## Action items
1. [ ] Write blob first, publish reference second. Orphaned blobs are reconciled by a sweeper; dangling references are not acceptable.
