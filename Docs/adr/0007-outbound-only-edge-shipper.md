# ADR-0007: The self hosted estate ships outbound only

**Status:** Accepted
**Date:** 2026-08-14

## Context
Existing customers run self hosted deployments, frequently because a security or compliance function required it. Migrating them to the managed plane is the primary business objective. The first objection in every such conversation is inbound network access.

## Decision
The self hosted estate integrates as a source, using the same adapter contract as any third party system. The edge shipper establishes outbound connections only: no inbound ports, no listener, no VPN, no site to site tunnel. It checkpoints its position durably and resumes from the checkpoint after any interruption.

## Options considered

### Option A: Managed plane pulls from the estate
**Pros:** Central control of pace and retries.
**Cons:** Requires inbound access into the customer network. Fails the primary objection outright.

### Option B: Estate pushes outbound
**Pros:** No firewall change. Customer keeps egress control and can inspect the traffic. Same shape as any SaaS integration they already permit.
**Cons:** Backpressure must be handled at the edge. Checkpoint correctness becomes the estate's responsibility.

## Trade-off analysis
Option B, decisively. The technical cost is checkpoint discipline; the cost of Option A is that the migration never starts.

## Consequences
- Easier: security review, which is the actual gating step.
- Harder: debugging a shipper you cannot reach; needs strong self reported health telemetry over the same outbound channel.
