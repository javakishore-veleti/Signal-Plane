# Deployment

**Status:** Defined. Not implemented. No GitHub Actions workflows exist yet.
**Date:** 14 August 2026

Nothing runs by default. Cloud resources cost money whether or not anyone is using them. Deployment is **manual dispatch only**, never on push. Teardown is a first-class operation with the same naming as setup.

CloudFormation is the unit of blast radius. CDK synthesizes one CloudFormation stack per scoped unit. There is **no** monolithic `SignalPlane-All` stack.

---

## How you run it

You do **not** click one "deploy everything" action. You run **Setup N**, wait until that stack is `CREATE_COMPLETE` / `UPDATE_COMPLETE`, then run **Setup N+1**. Destroy is the reverse: **Destroy N** only after every higher-numbered stack that depends on it is already gone.

Each scoped stack has a **pair** of workflows:

| Workflow file | What it does |
|---|---|
| `AWS-NNN-Setup-<Scope>.yml` | `workflow_dispatch` → OIDC → `cdk deploy` **only** that stack |
| `AWS-NNN-Destroy-<Scope>.yml` | `workflow_dispatch` → OIDC → `cdk destroy` **only** that stack |

`<Scope>` is the short name in the table below (`Network`, `ObjectStore`, …). `NNN` is a three-digit sequence that is the **legal order**, not decoration.

Inputs on every workflow:

- `stage`: `dev` \| `staging` \| `prod` (default `dev`)
- Destroy additionally requires typing the stack name to confirm

Concurrency: one in-flight deploy **per stage per stack**. Do not cancel an in-flight CloudFormation update; a cancelled update leaves a stack that someone has to repair by hand.

Authentication: GitHub OIDC → `AWS_DEPLOY_ROLE_ARN`. No long-lived AWS keys in the repository.

---

## Local substitute → scoped cloud stack

Local runtime stays Docker Compose (ADR-0010). The same **protocols** appear in AWS as separately destroyable stacks. Local Kubernetes is **not** the local analogue of these stacks; Fargate and Lambda are.

| Seq | Scope | Local (Compose) | CloudFormation stack id | AWS services |
|---|---|---|---|---|
| 001 | Network | Docker network `signal-plane` | `SignalPlane-Network-<stage>` | VPC, subnets, one NAT (non-prod), security groups |
| 002 | ObjectStore | MinIO | `SignalPlane-ObjectStore-<stage>` | S3 bucket, object lock, lifecycle |
| 003 | PolicyStore | PostgreSQL | `SignalPlane-PolicyStore-<stage>` | DynamoDB policy table. App uses a repository interface, not the DynamoDB SDK in business logic |
| 004 | SignalIndex | PostgreSQL (same engine, different schema) | `SignalPlane-SignalIndex-<stage>` | DynamoDB signal index, tenant-first keys, TTL |
| 005 | Cache | Redis | `SignalPlane-Cache-<stage>` | ElastiCache Redis. Decisions and identity only. Never observations |
| 006 | Bus | Redpanda | `SignalPlane-Bus-<stage>` | Amazon MSK, Kafka protocol, category topics + DLQ |
| 007 | Edge | Caddy / nginx (not built yet) | `SignalPlane-Edge-<stage>` | CloudFront + ALB. Path routing to control plane, broker, portals |
| 008 | ControlPlane | Spring Boot container | `SignalPlane-ControlPlane-<stage>` | ECS Fargate, one service. Authority, identity, sessions, registry, policy APIs. **No telemetry ingest** |
| 009 | QueryBroker | Go container | `SignalPlane-QueryBroker-<stage>` | ECS Fargate. Federated read, merge, deadlines, named partials |
| 010 | Adapters | Python Compose service per source | `SignalPlane-Adapters-<stage>` | One Lambda per source, DLQ, estate ingest HTTP API |
| 011 | Consumers | `Middleware/consumers` (not built yet) | `SignalPlane-Consumers-<stage>` | Lambda or Fargate consumers: validation, index writer. Not the control plane |
| 012 | Etls | `Middleware/etls` (not built yet) | `SignalPlane-Etls-<stage>` | Batch jobs: assessment, compatibility, backfill |
| 013 | Portals | Angular `ng serve` + proxy | `SignalPlane-Portals-<stage>` | Admin and client static apps behind the Edge stack. Shared contract library. No third vendor app |

Today's CDK (`Core`, `Ingest`, `ControlPlane`) is a **coarser** split. The table above is the target split: Core is broken into 001–006 so Network can live while ObjectStore is destroyed, and ControlPlane is not bundled with the broker.

---

## Setup order (one after the other)

Run these GitHub Actions in this order. Skip a number only when that layer is explicitly out of scope for the stage.

```
AWS-001-Setup-Network
AWS-002-Setup-ObjectStore
AWS-003-Setup-PolicyStore
AWS-004-Setup-SignalIndex
AWS-005-Setup-Cache
AWS-006-Setup-Bus
AWS-007-Setup-Edge
AWS-008-Setup-ControlPlane
AWS-009-Setup-QueryBroker
AWS-010-Setup-Adapters
AWS-011-Setup-Consumers
AWS-012-Setup-Etls
AWS-013-Setup-Portals
```

Hard dependencies (Setup of the right-hand side is illegal until the left-hand side is complete):

```
008 ControlPlane  ← 001 Network, 003 PolicyStore, 005 Cache
009 QueryBroker   ← 001 Network, 004 SignalIndex, 007 Edge
010 Adapters      ← 002 ObjectStore, 006 Bus, 008 ControlPlane (session start only)
011 Consumers     ← 004 SignalIndex, 006 Bus
012 Etls          ← 003 PolicyStore, 004 SignalIndex, 002 ObjectStore
013 Portals       ← 007 Edge, 008 ControlPlane, 009 QueryBroker
007 Edge          ← 001 Network
```

Adapters must not take a dependency on 009. Telemetry goes adapter → bus, never through the control plane.

---

## Destroy order (reverse, one after the other)

```
AWS-013-Destroy-Portals
AWS-012-Destroy-Etls
AWS-011-Destroy-Consumers
AWS-010-Destroy-Adapters
AWS-009-Destroy-QueryBroker
AWS-008-Destroy-ControlPlane
AWS-007-Destroy-Edge
AWS-006-Destroy-Bus
AWS-005-Destroy-Cache
AWS-004-Destroy-SignalIndex
AWS-003-Destroy-PolicyStore
AWS-002-Destroy-ObjectStore
AWS-001-Destroy-Network
```

Destroy impact:

| Scope | Non-prod | Prod |
|---|---|---|
| 001 Network | Safe once everything above it is gone | Last |
| 002 ObjectStore | Empties and deletes | **Retain** (legal hold / retention) |
| 003 PolicyStore | Deletes | **Retain** |
| 004 SignalIndex | Deletes | **Retain** |
| 005–007, 008–013 | Safe; 008 stops new sessions only | Safe; data is not in these stacks |

You may destroy 008 without touching 002–004. That is the plane split: control plane availability is not a precondition for stored records.

---

## What each workflow is allowed to do

A Setup workflow:

1. Assumes the OIDC role.
2. Runs `npx cdk synth` (free; no credentials needed for the synth itself, but the workflow still needs the role for context).
3. Runs `npx cdk deploy SignalPlane-<Scope>-<stage> --exclusively`.
4. Fails if CloudFormation reports a dependency on a stack that is not `CREATE_COMPLETE`.
5. Prints the stack outputs (bucket names, URLs, table names).

A Destroy workflow:

1. Assumes the OIDC role.
2. Refuses to run if any **higher** sequence stack still exists (example: Destroy-001 is illegal while 008 exists).
3. Runs `npx cdk destroy SignalPlane-<Scope>-<stage> --exclusively --force` only after the typed confirmation matches.
4. For 002/003/004 on `prod`, refuses destroy (retention policy). Use a dedicated, human-approved exception, not this workflow.

`--exclusively` is the whole point. A workflow named `AWS-008-Setup-ControlPlane` must not create or update 006 or 010.

---

## Repository layout (when implemented)

```
.github/workflows/
  AWS-001-Setup-Network.yml
  AWS-001-Destroy-Network.yml
  AWS-002-Setup-ObjectStore.yml
  AWS-002-Destroy-ObjectStore.yml
  …
  AWS-013-Setup-Portals.yml
  AWS-013-Destroy-Portals.yml

DevOps/Cloud/cdk/
  bin/app.ts                 # instantiates one CDK stack per scope
  lib/network-stack.ts
  lib/object-store-stack.ts
  …
```

Do not introduce a workflow that loops all scopes. Sequential human dispatch is the cost control.

Required GitHub configuration per environment:

- Secret `AWS_DEPLOY_ROLE_ARN`
- Variable `AWS_REGION`
- Variable `AWS_STAGE` optional; the workflow input wins

---

## Cost notes (unchanged)

- One NAT gateway, not one per AZ, below production. NAT dominates idle VPC cost.
- DynamoDB on-demand. No provisioned capacity while idle.
- Fargate desired count is 1 outside production for 008 and 009.
- MSK is the expensive always-on piece; 006 should not sit in `dev` overnight. Destroy 010 then 006 when the stage is idle.
- `npx cdk synth` is free and needs no credentials. Use it to iterate stack splits before any Setup action.

---

## Relation to the three stacks that exist in CDK today

| Today | Becomes |
|---|---|
| `SignalPlane-Core-<stage>` | 001 Network + 002 ObjectStore + 003 PolicyStore + 004 SignalIndex |
| `SignalPlane-ControlPlane-<stage>` | 008 ControlPlane (VPC imported from 001, table from 003) |
| `SignalPlane-Ingest-<stage>` | 010 Adapters |

005 Cache, 006 Bus, 007 Edge, 009 QueryBroker, 011–013 are new scopes. They are defined here so the GitHub Action names stay stable when the CDK classes are split.

---

## Before a release

Local green does not guarantee cloud green. After the stacks you care about are up:

1. Setup 001 through 010 on `dev`.
2. Run the five-divergence smoke (IAM, MSK auth, partition skew, object lock, cold starts). See `Docs/local-development.md`.
3. Destroy 010 down through 001 in reverse.

That smoke is not optional before a release.
