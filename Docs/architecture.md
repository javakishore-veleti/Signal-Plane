# Architecture

## Problem

An organisation's behavioural and operational signals are scattered across systems that were never designed to be read together: endpoint agents, collaboration suites, identity providers, security tooling, and legacy self hosted deployments. Each speaks its own schema, delivery model, and identity scheme.

Two costs follow. Integrating the Nth source is as expensive as the first, because every consumer knows every source. And nothing can be asked across sources, because there is no shared vocabulary in which to ask.

Layered on top is a migration problem: an existing estate of self hosted deployments has to reach the managed plane without a cutover, without losing evidentiary continuity, and without a behavioural change that gets mistaken for a regression.

## Shape

A horizontal integration layer with a strict plane split.

```
sources ──> adapters ──> [authority gate] ──> event bus ──> stores ──> query broker ──> console
                              ^
                        control plane
```

- **Adapters** own exactly one source each. They map into the normalized envelope and emit. Nothing else knows what a source looks like.
- **The control plane** answers control questions synchronously: who is this subject across systems, which sources can observe them, is this capture authorised, is this session still open. It is never on the telemetry path.
- **The authority gate** issues a bounded decision before any capture session opens, and that decision id is stamped on every resulting record.
- **The event bus** carries normalized envelopes. Large payloads travel as references; the bytes live in the object store.
- **The query broker** resolves reads across the managed plane and any remaining self hosted estate, merging on a deterministic `signal_id`.

## The five contracts

Everything structural lives in `schemas/`. These four files are the architecture; the services are an implementation of them.

| Contract | Role |
|---|---|
| `signal-envelope.schema.json` | The one shape every source is mapped into. Adding a source is a mapping exercise. |
| `authority-decision.schema.json` | Bounded, mode specific, jurisdiction aware permission to capture. |
| `blob-reference.schema.json` | Pointer to bytes held under retention, encryption, and legal hold controls. |
| `adapter-manifest.schema.json` | What a source can observe, at what fidelity, under which capture modes. Powers coverage discovery. |

The fifth contract is `taxonomy.yaml`: the governed vocabulary of `signal_type` values. It is additive only within a `schema_version`. This is the asset that compounds, adapter N+1 is cheap precisely because the vocabulary already exists.

## Three workflows

**Coverage discovery.** Given a subject identifier, resolve it to a canonical subject and return which adapters can observe them, at what fidelity, and under which capture modes. This is the question that has no answer at all without a normalized layer.

**Session lifecycle.** A caller requests capture at a named mode. The authority gate resolves the governing jurisdiction from the subject, determines the approving party for that mode, and issues a bounded decision or a denial with a reason. On grant, a session opens with an id, an expiry, and schedule constraints. Adapters cache the decision for the session's lifetime and fail closed at expiry.

**Termination.** Sessions close on a rule, never on an operator remembering: schedule window boundary, decision expiry, retention clock, or case closure. Explicit termination exists but is the exception.

## Why the planes are split

Control interactions are low volume request/response. Telemetry is continuous, bursty, and orders of magnitude larger. Running both through one orchestrator couples workloads with opposite profiles and makes the orchestrator the ceiling on ingest.

The consequence worth naming: a control plane outage stops new sessions from opening but does not drop telemetry already in flight. That is the correct failure mode.

## Migration without cutover

The self hosted estate is modelled as just another source, integrated through the same adapter contract, shipping **outbound only**. No inbound ports, no tunnel. This is a security review decision more than a networking one, see ADR-0007.

Sequencing, each step independently reversible:

1. **Read path first.** Users work in the managed console; the broker federates across both estates. Value is delivered before any data moves.
2. **New capture switches** to the managed plane. The estate stops growing.
3. **History backfills** in the background, or ages out under retention, whichever is cheaper for that tenant. Index and metadata migrate first; bytes can stay behind a resolvable handle.
4. **Decommission.**

The measure that decides whether this succeeds is not latency. It is **cost per tenant migrated** and **rollback rate**. With a large estate, if a migration needs an engineer on a call it reaches only the loudest customers and stalls at the long tail. The tooling is the product.

## Two things that are easy to get wrong

**Behavioural equivalence, not just data equivalence.** A tenant has tuned thresholds and authored rules against a specific scoring model version. If the managed plane scores differently, cutover day buries them in false positives and the migration gets blamed. Pin the model version per tenant, migrate on it, upgrade separately (ADR-0009), and ship a rule compatibility report before cutover.

**Evidentiary continuity.** A score or a captured artefact cited months later must still mean what it meant. Hence `model_version` on every score, `content_hash` and optional `prev_hash` on every envelope, and object lock rather than application level deletion refusal for anything under legal hold.

## Service map

| Component | Language | Why |
|---|---|---|
| `services/control-plane` | Java, Spring Boot | Transactional policy and identity resolution, rich validation, long lived service. |
| `services/query-broker` | Go | Concurrent fan out across estates with strict deadlines, small memory footprint. |
| `edge-shipper` | Go | Single static binary deployed into customer estates. No runtime to install. |
| `adapters/python` | Python | Per source mapping code, changed often, deployed as Lambda. |
| `ui/console` | Angular | Single console across both estates during migration. |

Polyglot is a deliberate cost. It is justified here because the components have genuinely different profiles and communicate only through the schemas in `schemas/`, never through shared code.

## Reading order

1. `schemas/signal-envelope.schema.json`, the contract everything else serves.
2. ADR-0002, why there is one envelope at all.
3. ADR-0004 and ADR-0005, the two decisions that shape the runtime.
4. ADR-0007 and ADR-0008, the migration mechanism.
5. `docs/local-development.md`, to run it.
