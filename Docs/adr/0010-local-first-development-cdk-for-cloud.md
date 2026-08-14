# ADR-0010: Local first development, CDK only for cloud

**Status:** Accepted
**Date:** 2026-08-14

## Context
Cloud managed services are the deployment target, but iterating against them is slow and metered. A platform that can only be run by paying for a live account is one contributors avoid running.

## Decision
The entire data path runs locally against API compatible substitutes: Redpanda for the Kafka API, MinIO for the S3 API, PostgreSQL for the policy and index store. Services depend on the protocol, never on a vendor SDK feature with no local equivalent.

Cloud deployment is AWS CDK synthesizing CloudFormation, split into small stacks so any part can be destroyed independently. Deployment is manual dispatch only, never on push.

## Options considered

### Option A: Develop against a shared AWS dev account
**Pros:** No substrate divergence. Tests the real thing.
**Cons:** Cost accrues continuously. Slow iteration. Contention on shared resources. Contributors need account access.

### Option B: Local compose stack, CDK for cloud
**Pros:** Near zero cost, fast loop, contributors need only Docker. CloudFormation stacks give a clean destroy.
**Cons:** Local substitutes diverge from managed services in ways that surface late (IAM, quotas, MSK auth).

## Trade-off analysis
Option B, with the divergence risk handled explicitly: a small deploy-and-destroy smoke stack exercises the real services on demand, and anything relying on a managed service behaviour with no local equivalent is called out in `docs/local-development.md`.

## Consequences
- Easier: contribution, iteration speed, cost control.
- Harder: local green does not guarantee cloud green; the smoke test is not optional before a release.
