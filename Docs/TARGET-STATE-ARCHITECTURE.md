# Target State Architecture

**System:** Signal Plane — multi source telemetry integration platform with estate migration
**Document status:** Draft for review
**Version:** 1.1
**Date:** 14 August 2026
**Scope:** Architecture description only. No implementation detail.
**Revision 1.1:** Adds enterprise principle alignment, architecture risk management, operating model, governance, cloud adoption model, and execution roadmap.

---

## 1. Architectural intent

The system is a horizontal integration layer. Its purpose is to make the cost of integrating an additional signal source approximately constant rather than linear, to make collection governable at the point of collection rather than at the point of query, and to allow an installed base of self hosted deployments to be drained into a managed plane without a cutover event.

Three properties follow from that intent and constrain every subsequent decision.

**Uniformity at the boundary.** Heterogeneity is absorbed at the edge, in adapters, and never propagates inward. Every component beyond the adapter layer sees one shape.

**Governance ahead of collection.** Permission is established before data exists, and travels with the data thereafter. This is not an access control decision; it is a collection decision, and it cannot be retrofitted.

**Reversibility of migration.** Every migration step is independently reversible, because an installed base of thousands cannot be moved by a sequence of irreversible events that customers must each individually accept.

---

## 2. Architectural principles

| # | Principle | Consequence |
|---|---|---|
| P1 | One vocabulary, absorbed at the edge | Consumers never learn source specifics; the Nth integration is a mapping exercise |
| P2 | Isolation per source | One source's failure, saturation, or release cadence never affects another |
| P3 | Authority precedes collection, and is bounded | No unbounded grants; every record carries its justification |
| P4 | Separate the control plane from the data plane | Two workloads with opposite profiles scale and fail independently |
| P5 | Bulk travels by reference | Retention and hold have exactly one enforcement point |
| P6 | The estate is a source, not a peer | Migration reuses the integration mechanism rather than inventing a second one |
| P7 | Deterministic identity | Idempotent replay, and merge across estates without double counting |
| P8 | Report degradation honestly | Silence and partial results are distinguishable to every consumer |
| P9 | Structural isolation over filtered isolation | Out of scope access is inexpressible rather than merely forbidden |
| P10 | Depend on protocols, not products | Local development is possible; substrate is replaceable |

---

## 3. Logical architecture

### 3.1 Layers

**Source layer.** External systems producing signals. Outside the trust boundary. Includes customer operated self hosted deployments, which are treated as sources rather than as peer deployments.

**Adaptation layer.** One adapter per source. Owns all knowledge of that source's schema, delivery model, authentication, rate limits, and identifier conventions. Emits the normalized record and nothing else. Declares its capability in a manifest.

**Governance layer.** Resolves identity to a canonical subject, evaluates collection authority against jurisdictional policy, issues bounded decisions, manages session lifecycle, and answers coverage questions from registered manifests. Synchronous, low volume, request and response.

**Transport layer.** Carries normalized records, partitioned so that ordering within a subject is preserved. Carries references to bulk content, never the content.

**Persistence layer.** Two distinct stores with different obligations. An index optimised for retrieval by subject and time, partitioned so tenant scope is structural. An object store holding bulk content under retention lock, where retention and hold are enforced by the store rather than by application logic.

**Access layer.** Federates retrieval across estates, merges on deterministic identity, bounds every read by deadline, and reports which estates answered.

**Presentation layer.** A single interface spanning both estates during migration, obliged to surface degradation and to reflect only scope actually held.

### 3.2 Plane separation

The system divides along a line that matters more than the layer boundaries.

**Control plane.** Identity resolution, authority evaluation, session lifecycle, adapter registration, coverage discovery, policy administration. Traffic is low volume, steady, transactional, and latency sensitive in the human sense rather than the machine sense.

**Data plane.** Record ingestion, transport, indexing, payload storage, retrieval. Traffic is continuous, bursty, and several orders of magnitude larger.

These are separate because they have opposite profiles. Combining them makes the control component the ceiling on ingest throughput, and makes its availability a precondition for collection that is already authorised and in flight.

The interaction between them is deliberately narrow: an adapter consults the control plane once when opening a session, caches the resulting decision for that session's bounded lifetime, and thereafter emits without further consultation. The decision's expiry is what bounds the staleness of that cache, and therefore bounds how long a withdrawn authority can still be acted upon. This is a designed trade, and the expiry interval is the tuning parameter.

The resulting failure mode is intentional: loss of the control plane prevents new sessions from opening but does not interrupt or drop collection already permitted. That is the correct behaviour, because the alternative loses data that was lawfully collected.

---

## 4. Core contracts

Contracts are the architecture. Components are implementations of them. Five contracts define the system, and a change to any of them is an architectural change requiring a recorded decision.

### 4.1 Normalized record

The universal unit. Every source is mapped into it; no consumer sees anything else.

It carries: deterministic identity; tenant; source provenance including adapter, adapter version, native source identifier, and originating estate; resolved subject with the raw identifier claims that produced it; occurrence, observation, and ingestion times as three distinct values; category; signal type drawn from the governed vocabulary; typed attributes; an optional reference to bulk content; a reference to the authority decision that permitted it; optional derived scoring stamped with its model version; and integrity fields comprising a content hash and, optionally, the hash of the preceding record for that subject.

Three of these deserve emphasis.

**Deterministic identity** is derived from source facts rather than assigned on arrival. This is what makes replay idempotent, and what allows records arriving from two estates during a migration overlap window to collapse rather than double count. It is the single mechanism on which migration without cutover depends.

**Three timestamps** exist because they diverge, and the divergence is diagnostic. Occurrence and observation separate when a source batches; observation and ingestion separate when transport is degraded. Collapsing them discards the ability to distinguish a slow source from a slow pipeline.

**The hash chain** allows a reader to verify ordering and detect omission without trusting the store that returned the records. This matters when records are used evidentially, where the credibility of the store is exactly what may be challenged.

### 4.2 Governed vocabulary

The enumerated set of valid signal types, their categories, and their attribute definitions. Versioned, and additive only within a version.

This is the asset that compounds. Integrating the Nth source is cheap precisely because the vocabulary that source's events must map into already exists. Where the vocabulary is allowed to fragment, each adapter effectively defines its own schema and the normalized layer has stopped normalizing while continuing to appear to work. Governance is therefore enforced mechanically at release time, not by convention.

An event that cannot be mapped forces an explicit decision: extend the vocabulary additively, or determine that this event does not belong in the system. Emitting an unclassified record is not an available option.

### 4.3 Authority decision

Bounded permission to collect. It names the capture mode, the grant or denial, the legal basis, the approving party role, the governing jurisdiction, the policy version applied, the evaluation time, the expiry, and constraints comprising permitted schedule windows, excluded categories, excluded destinations, and a redaction profile. A denial names its reason.

Two structural properties carry most of the weight.

**Capture mode determines the approving party.** Modes form an escalating scale of intrusiveness, and different points on that scale have materially different approvers. Treating collection as a single binary permission is the modelling error this contract exists to prevent.

**Jurisdiction is resolved from the subject.** The governing rule follows the person observed, not the organisation's registered address. Multi jurisdiction customers are the normal case, and resolving jurisdiction from the tenant produces confidently wrong answers at scale.

Every granted decision expires. An unbounded grant is treated as a defect rather than a configuration option, because an unbounded grant makes revocation latency unbounded too.

### 4.4 Payload reference

The stand in for bulk content on the transport layer. It carries location, content hash, media type, size, encryption key identity, retention class, hold status, and which estate can resolve it.

Bulk content dominates storage volume while being a small fraction of record count. Carrying it inline collapses transport latency, exceeds message size limits, and makes retention deletion impossible because copies persist in every consumer's retained offsets. By reference, retention has exactly one enforcement point and hold is enforceable by the store.

The write ordering is a contract, not an implementation detail: content is durable before its reference is published. Unreferenced content is recoverable by reconciliation; a reference to absent content is not recoverable at all.

### 4.5 Adapter manifest

The declared capability of a source: emitted signal types with fidelity per type, supported capture modes, delivery model, minimum interval, and identifier kinds supplied.

Coverage discovery is generated from registered manifests. This makes "which sources can observe this subject" a derived answer rather than institutional knowledge, and makes an inaccurate manifest produce confidently wrong coverage answers. Manifest accuracy is therefore validated at release rather than trusted.

---

## 5. Component architecture

### 5.1 Adapters

One per source, independently deployed and versioned, each owning exactly one source system.

The alternative, a shared ingestion service with per source plugins, was rejected. It couples the release cadence of unrelated integrations, allows one source's rate limiting to back up others, and makes a defect in one plugin an outage for all ingestion. The cost of the chosen approach is operational multiplicity and the risk of drift between adapters; drift is contained by placing record construction, identity handling, integrity computation, and authority enforcement in a shared library that is the only supported path to producing a record, with conformance validated at release.

Adapters are stateless between invocations except for a session scoped cache of the authority decision. Their execution profile is bursty and event driven, which suits ephemeral compute.

### 5.2 Edge transmission component

Deployed inside a customer's self hosted estate. Reads locally spooled records and transmits them to the managed plane.

Its defining constraint is directional. All connections are outbound. There is no listening port, no inbound rule, and no tunnel. This is not a networking preference; it is the property that determines whether a customer's security function permits migration at all. Customers operating self hosted deployments frequently do so because that function required it, and a design requiring inbound access ends the conversation before technical merit is considered.

Correctness rests on checkpointing. Position is durable before a batch is acknowledged as complete, and advances only after the managed plane confirms receipt. Interruption between transmission and checkpoint persistence causes replay, which deterministic identity absorbs. Skipping is not a possible outcome. The asymmetry is deliberate: duplicate delivery is recoverable and observable, silent omission is neither.

Health is self reported over the same outbound channel, because the component cannot be reached to be interrogated.

### 5.3 Control plane services

Long lived, transactional, holding connection pools and policy caches. Their traffic is steady and low volume, which is the opposite of the adapters' profile and the reason they are deployed differently.

They provide: identity resolution from raw identifier claims to a canonical subject with confidence, where ambiguity resolves to no subject rather than to a guess; authority evaluation as described in 4.3, deny by default with every denial carrying an actionable reason; session lifecycle where termination is rule driven on schedule boundary, decision expiry, retention threshold, or case closure, with explicit termination available but exceptional; adapter registration; and coverage discovery derived from manifests.

Silent merging of two individuals into one subject is the identity failure that matters. It is prevented by resolving ambiguity to nothing, and by making resolution auditable and correctable with correction applying retroactively.

### 5.4 Transport

An event stream partitioned so that ordering within a subject is preserved, with topics separated by category so consumers subscribe to what concerns them.

Records only. Bulk content travels by reference. Records failing structural or vocabulary validation are diverted to an isolated channel per adapter, from which they can be inspected and reprocessed. Diverted volume by adapter is a data quality signal, not merely an error count.

### 5.5 Persistence

**Index.** Optimised for retrieval by subject and time. Partitioned so that every read is naturally tenant scoped and a cross tenant read is inexpressible rather than merely denied. This distinction matters: a filter can be omitted, a partition key cannot.

**Object store.** Holds bulk content. Retention is enforced here, not in application code. Legal hold suspends expiry and causes deletion to be refused by the store. Enforcement at the storage layer rather than the application layer is deliberate, because an application level refusal is one incorrect code path away from being bypassed, and the failure is silent.

Where a tenant requires key custody, encryption keys are customer supplied. Residency is selected per tenant and enforced by deployment topology rather than by policy.

### 5.6 Access services

A federation component resolving reads across the managed plane and any remaining self hosted estate.

Its behaviour is defined by three properties. Fan out is concurrent and bounded by an explicit deadline, so that a degraded estate cannot stall a response. Merge is on deterministic record identity, so the overlap window during migration produces one result rather than two. And partial results are reported explicitly, naming each estate that failed to answer.

The third property is the important one. During an investigation, a response that silently omits an unavailable estate leads a competent investigator to a false conclusion, and does so invisibly. Reporting an error is better; reporting partial results with the gap named is better still. This obligation propagates: the response contract carries estate status, and every consumer including the interface is required to surface it.

Access is itself recorded. Who read what, when, and under which case is part of the audit surface, because in an evidentiary context the reading is as significant as the collecting.

### 5.7 Presentation

A single interface spanning both estates throughout migration. This is what allows the read path to move first, delivering value before any data moves.

Two obligations are architectural rather than cosmetic. Degradation is displayed, naming the unavailable estate. And scope offered reflects only scope actually held, with enforcement at the data layer and the interface merely reflecting it, because a scope control that is only presentational is not a control.

---

## 6. Cross cutting concerns

### 6.1 Identity

Deterministic record identity, derived from source facts, underpins idempotent replay and cross estate merge.

Canonical subject identity, resolved from identifier claims, underpins aggregation, retrieval, and erasure. Ambiguity resolves to no subject.

Adapter identity and version travel with every record, so behaviour can be attributed to a specific adapter release when a data quality question arises months later.

### 6.2 Time

Three timestamps are retained because they diverge and the divergence is informative. Retention and expiry are computed from occurrence, since that is what the obligation attaches to.

### 6.3 Integrity and evidential weight

Content hashing at construction, optional chaining to the preceding record for the subject, content hashing of stored bulk content, and storage layer hold combine to produce a record whose credibility does not depend on trusting the system that stored it. This is the difference between data that is useful operationally and data that survives challenge.

### 6.4 Derived values

Any derived value carries the model version that produced it. The model version is pinned per tenant, and platform migration never coincides with a model version change.

The reason is specific and is the most commonly repeated failure in this class of migration. Operational thresholds and customer authored rules are calibrated against a particular model's output distribution. Changing the model during migration produces a wave of misfiring alerts on the first day, the migration is identified as the cause, and it is reversed. Separating the two changes makes migration defensible as behaviour preserving, which is a claim that can be demonstrated in advance.

Derived values are distinguishable from observed facts at every point of presentation.

### 6.5 Multi tenancy

Isolation is structural. Storage partitioning is tenant first, residency is a deployment property, and where key custody is required the tenant holds the keys. Scope within a tenant is enforced at the data layer.

### 6.6 Observability

Beyond conventional telemetry, three measures are architectural because they detect failures nothing else surfaces: authority coverage, the proportion of records resolvable to a decision, where anything below complete indicates a bypass; dangling reference count, which must be zero and where any occurrence indicates broken write ordering; and cross adapter interference, the correlation between one adapter's error rate and others', where any correlation indicates isolation has failed.

---

## 7. Estate migration architecture

### 7.1 Position

The self hosted estate is a source, integrated through the adapter contract, not a peer deployment maintained in parallel. This is a deliberate stance: investing in indefinite parity funds the thing being retired.

### 7.2 Topology during transition

The presentation layer addresses the managed plane exclusively. The federation component resolves reads across both estates. New collection is directed to whichever plane the tenant's migration state specifies. The estate transmits outbound only, both for ongoing signals and for historical backfill.

The tenant experiences one interface throughout. The location of their data is an internal property of the platform rather than something they interact with.

### 7.3 Sequence

**Read path.** Retrieval moves to the managed interface while data remains in the estate. Value is delivered and nothing irreversible has occurred. If the programme halts here the tenant is still better off, which is what makes the first step easy to agree to.

**New collection.** Collection is directed to the managed plane. The estate stops growing. Reversible by redirecting collection back.

**History.** Index and metadata migrate. Bulk content either backfills or expires under existing retention, whichever is cheaper for that tenant. For most tenants the retention window is shorter than the migration programme, which makes expiry the common answer and materially reduces cost.

**Decommission.** After a rollback window elapses without reversal, under explicit human approval.

### 7.4 Preconditions

**Compatibility classification.** Before cutover, every tenant authored rule and threshold is classified as behaviour preserving, changed, or dependent on a retired vocabulary entry. Any changed classification requires explicit recorded acknowledgement. This is what converts cutover from an act of faith into a reviewable decision.

**Hold verification.** Legal holds are confirmed effective after crossing the boundary by asserting that deletion is refused, not by inspecting a flag. A hold that lapsed silently is the failure that ends a migration programme, and a flag can be set correctly while the underlying enforcement is absent.

**Jurisdiction check.** The subject population's jurisdiction distribution is assessed first, because it determines whether the managed plane may lawfully hold the tenant's data at all. Discovering this late invalidates the rest of the assessment.

### 7.5 Reversibility

Each step is independently reversible within a stated window, and migration state is a persisted, queryable state machine rather than an operator's recollection.

Rollback is a supported operation, not an incident. A rollback rate of zero is more likely to indicate that rollback is impractical than that it is unnecessary.

### 7.6 Economics

Cost per tenant migrated and rollback rate are emitted as first class metrics from the first migration.

With an installed base of thousands, per tenant cost dominates. If each migration requires an engineer, the programme serves only escalating customers and stalls at the long tail. The architecture's contribution to this is that assessment, compatibility classification, cutover, and rollback are automated operations rather than runbooks. The tooling is the deliverable.

---

## 8. Deployment architecture

### 8.1 Topology

Ephemeral compute for adapters, matching their bursty event driven profile. Long lived containers for control plane services, matching their steady profile and connection pooling needs. Managed event streaming for transport. Managed object storage with retention lock. A partitioned index store. Regional deployment per residency requirement.

### 8.2 Composition

Infrastructure is composed of small, independently destroyable units separated by lifecycle and blast radius. Destroying the control plane must not lose data. Redeploying ingestion must not disturb shared substrate. This composition is what makes teardown a routine operation rather than a risk, which in turn is what makes non production environments affordable.

### 8.3 Development posture

The full path is exercisable locally against protocol compatible substitutes. Dependencies are on protocols with more than one viable implementation, which is what makes this possible.

The reasoning is practical. A platform that can only be exercised against a running metered account is a platform contributors do not exercise, and unexercised code paths rot. The known divergences between local substitutes and managed services, principally authorisation, quota behaviour, partition behaviour under skew, retention lock semantics, and cold start characteristics, are enumerated explicitly and covered by a verification path executed before release. Local success does not imply cloud success, and the architecture says so rather than implying otherwise.

Deployment is deliberate and manually initiated. Teardown is first class. The default posture of a non production environment is nothing running.

---

## 9. Architecture decisions

| # | Decision | Rejected alternative | Determining reason |
|---|---|---|---|
| D1 | Single normalized record contract | Per source schemas handled by consumers | The source set grows indefinitely; the flat cost curve wins despite higher initial cost |
| D2 | Adapter per source | Shared ingestion with plugins | Blast radius and release independence outweigh operational multiplicity |
| D3 | Authority at collection, stamped on the record | Policy evaluated at query time | The harm prevented is collection, not disclosure; deletion is an imperfect remedy |
| D4 | Control and data planes separated | Single orchestrator | Opposite load profiles; avoids making control availability a precondition for in flight collection |
| D5 | Bulk content by reference | Inline payloads | Single enforcement point for retention and hold; preserves transport latency |
| D6 | Estate integrates as a source, outbound only | Managed plane pulls from the estate | Inbound access fails customer security review, and that gate precedes technical merit |
| D7 | Federated read path | Cutover per tenant | Reversibility at every step; time to first value measured in days |
| D8 | Model version pinned per tenant | Single global model | Prevents coupling migration to a behavioural change |
| D9 | Structural tenant isolation | Query time filtering | A filter can be omitted; a partition key cannot |
| D10 | Protocol dependencies, local first development | Development against a shared cloud account | Unexercised architecture decays; cost is a design constraint |

---

## 10. Quality attribute scenarios

| Attribute | Scenario | Required response |
|---|---|---|
| Availability | Control plane unavailable | New sessions refused; in flight collection continues; no records dropped |
| Availability | One estate unreachable | Reads return available results, labelled partial, naming the unreachable estate |
| Fault isolation | One source rate limits severely | No change to any other adapter's error rate or latency |
| Integrity | Failure between payload write and reference publication | Orphaned payload, reconciled later; never a reference to absent content |
| Security | Authority withdrawn mid session | Collection ceases within the decision expiry interval |
| Security | Query attempted outside authorised scope | Inexpressible at the data layer, not merely denied at the application layer |
| Compliance | Erasure requested for a subject | Satisfied across all sources and both estates, subject to hold precedence |
| Compliance | Hold applied to a record due for expiry | Expiry suspended; deletion refused by the store |
| Modifiability | New source added | Only the new adapter and the vocabulary change |
| Modifiability | Vocabulary entry added | No consumer changes |
| Migration | Cutover reversed within window | Prior configuration restored; no data loss; no hold lapse |
| Evidential | Stored record challenged | Authority, provenance, integrity hash, and chain position all derivable from the record |

---

## 11. Alignment to enterprise architecture principles

This platform conforms to the enterprise application architecture strategy rather than claiming exception from it. The mapping below is stated explicitly so that conformance can be assessed rather than asserted.

| Enterprise principle | How this architecture expresses it | Conformance evidence |
|---|---|---|
| Modularity and composability | Adapters, control plane services, access services, and presentation are independently deployable and versioned, communicating only through published contracts | Adding a source changes only the new adapter and the vocabulary |
| APIs everywhere | The five contracts are the interface surface; no component reads another's internal state | No shared internal libraries between components; the shared adapter library is a published contract implementation, not a coupling |
| Cloud native orientation | Ephemeral compute for bursty adapters, long lived containers for steady control services, managed streaming and object storage | No self managed message brokers or databases in the target state |
| Domain driven design | Bounded contexts are the plane and layer boundaries; the governed vocabulary is an executable ubiquitous language | Terms in the vocabulary are the terms used in code, in the interface, and in customer conversations |
| Observability by design | Authority coverage, dangling reference count, and cross adapter interference are architectural measures, not operational afterthoughts | Each detects a failure class nothing else surfaces |

### 11.1 Domain driven design in practice

The bounded contexts are not arbitrary service boundaries. Each owns a distinct model of the same real world entities and refuses to leak that model outward.

| Bounded context | Owns | Deliberately does not own |
|---|---|---|
| Adaptation | Source specific semantics, delivery mechanics, native identifiers | Any notion of authority, retention, or scoring |
| Governance | Subject identity, jurisdiction, capture authority, session lifecycle | Signal content, storage, retrieval |
| Ingestion | Transport, partitioning, validation, quality diversion | Interpretation of what a signal means |
| Persistence | Retention, hold, encryption, residency, indexing | Which records ought to exist |
| Retrieval | Federation, merge, scope, deadline, degradation reporting | Collection decisions |
| Migration | Estate state, assessment, cutover, reversibility | The signals themselves |

The **governed vocabulary is the ubiquitous language**, and this is the strongest DDD claim the architecture makes. Most systems have a ubiquitous language that exists in documentation and erodes in code. Here the language is a machine readable artefact validated at release, so drift between what the business says and what the system stores is mechanically prevented rather than periodically corrected.

### 11.2 Strategic patterns applied

| Pattern | Where it appears | Why it was the right instrument |
|---|---|---|
| Hexagonal architecture | Adapters are ports; source systems are the driven side; the normalized record is the domain model at the boundary | Source volatility is confined to the edge; the core never learns a vendor's schema |
| Strangler | The self hosted estate migration in its entirety: read path first, then writes, then history, then decommission | The estate is drained rather than cut over, which is what makes each step reversible |
| API gateway | The estate ingest endpoint and the console API | Cross cutting authentication, rate limiting, and tenant attribution in one place |
| Anti corruption layer | The adapter's mapping function | Prevents a source's model from entering the domain, which is the specific decay this system is built to resist |
| Published language | The five contracts plus the vocabulary | Multiple teams and eventually multiple organisations integrate without negotiation |
| Federated query | The access layer across estates | Migration without cutover depends on it |

Micro frontends were considered and rejected for the console. The interface has a single audience, a single deployment cadence, and no independent team boundaries to respect. Adopting the pattern would import coordination cost with no corresponding benefit.

A service mesh is deliberately not adopted at this scale. The cross cutting concerns it would provide, namely mutual authentication and observability between services, are satisfied by the managed platform. Revisit if service count exceeds roughly twenty or if multi cluster topology becomes necessary.

---

## 12. Architecture risk management

Risk is managed as an architectural concern with an owner, a score, a trigger, and a review cadence, not as a list reviewed once at design time.

### 12.1 Risk taxonomy

| Code | Category | Definition in this context |
|---|---|---|
| TO | Technology obsolescence | A dependency reaching end of support, or a pattern superseded, faster than the system can absorb the change |
| VL | Vendor lock in | A dependency on a proprietary behaviour with no viable substitute, constraining residency, cost, or exit |
| SB | Scalability bottleneck | A component whose capacity ceiling is reached before demand plateaus |
| IF | Integration fragility | Coupling that causes one integration's failure to propagate |
| CE | Compliance exposure | Collection, retention, residency, or disclosure that cannot be defended |
| EI | Evidentiary integrity | Loss of the ability to demonstrate what was collected, when, and under what authority |
| MP | Migration programme | Risk that the estate is not drained within a commercially viable period or cost |
| OK | Organisational knowledge | Architecture whose rationale exists only in individuals |
| DQ | Data quality | Signals that are present but wrong, or absent without anyone noticing |

### 12.2 Scoring model

Likelihood and impact are each rated 1 to 5. Score is the product. The bands determine the response, not merely the presentation.

| Band | Score | Required response |
|---|---|---|
| Critical | 20 to 25 | Named owner, remediation plan with dates, reviewed monthly at ARB, blocks the next major release if unaddressed |
| High | 12 to 19 | Named owner, mitigation in the backlog with a target quarter, reviewed quarterly |
| Medium | 6 to 11 | Owner assigned, monitored against a stated trigger, reviewed half yearly |
| Low | 1 to 5 | Recorded, reviewed annually or on trigger |

Impact is assessed against business outcome rather than technical severity. A defect that degrades throughput scores lower than one that causes a legal hold to lapse, regardless of engineering effort to fix.

### 12.3 Architecture risk register

| ID | Cat | Risk | L | I | Score | Band | Owner | Mitigation | Escalation trigger |
|---|---|---|---|---|---|---|---|---|---|
| AR-01 | CE | Authority checking is bypassed under delivery pressure, producing collection with no defensible basis | 3 | 5 | 15 | High | Chief Architect | Record construction is possible only through the shared library; refusal proven by test; no override path exists | Authority coverage below 100 percent for any period |
| AR-02 | EI | A legal hold lapses during estate migration | 2 | 5 | 10 | Medium | Migration lead | Hold verified by asserting refusal of deletion, not by inspecting a flag; verification is a gated cutover step | Any single occurrence |
| AR-03 | MP | Cost per tenant migrated does not fall, so the programme reaches only escalating customers | 4 | 4 | 16 | High | Migration lead | Cost per tenant tracked from the first migration; assessment, compatibility, cutover, and rollback are automated operations | Cost per tenant flat across three consecutive migrations |
| AR-04 | IF | Vocabulary governance lapses and adapters invent terms, so the normalized layer stops normalizing while appearing to work | 3 | 5 | 15 | High | Platform lead | Mechanical cross validation blocking release; additive only policy; recorded decision required for any change | Any release requiring a governance exception |
| AR-05 | CE | Migration is coupled to a scoring model change, producing a false positive wave attributed to the migration | 3 | 4 | 12 | High | Product owner | Model version pinned per tenant; upgrade separately scheduled; compatibility report precedes cutover | Any proposal to combine the two changes |
| AR-06 | SB | The control plane is drawn onto the telemetry path and becomes the ingest ceiling | 2 | 4 | 8 | Medium | Platform lead | Plane separation is architectural; decisions cached for bounded session lifetimes; reviewed at ARB for any change touching the boundary | Control plane request rate correlating with signal volume |
| AR-07 | EI | Partial results presented as complete, leading an investigator to a false conclusion | 3 | 4 | 12 | High | Access services owner | Estate status is part of the response contract; interface obligation covered by test | Any consumer found not surfacing estate status |
| AR-08 | CE | Identity resolution silently merges two individuals | 2 | 5 | 10 | Medium | Governance owner | Ambiguity resolves to no subject; resolution auditable and retroactively correctable | Any confirmed misattribution |
| AR-09 | VL | Dependence on a proprietary streaming or storage behaviour with no local or alternative equivalent | 3 | 3 | 9 | Medium | Chief Architect | Dependencies restricted to protocols with more than one implementation; local substitutes exercised continuously | Any proposal to use a service specific feature on the critical path |
| AR-10 | SB | Payload volume overwhelms transport | 2 | 4 | 8 | Medium | Platform lead | Payloads by reference only, enforced structurally rather than by convention | Any message approaching the size limit |
| AR-11 | DQ | Signals silently stop arriving from a source and nobody notices | 3 | 4 | 12 | High | Adapter owners | Per adapter expected volume baselines with absence alerting; diverted volume monitored as a quality signal, not an error count | Any source silent beyond its declared minimum interval multiple |
| AR-12 | TO | Local development substitutes diverge from managed services, so defects surface first in production | 4 | 2 | 8 | Medium | Platform lead | Divergences enumerated explicitly; pre release verification path mandatory | Any production defect traceable to an unenumerated divergence |
| AR-13 | OK | Architectural rationale exists only in individuals, so decisions are reversed by people who did not hold the constraint | 3 | 4 | 12 | High | Chief Architect | Every structural decision recorded with rejected alternatives and a revisit trigger; decisions are tracked work items linked from the features they govern | Any structural change proposed without reference to the governing decision |
| AR-14 | MP | Multiple concurrent scoring model versions accumulate beyond the supportable | 3 | 3 | 9 | Medium | Product owner | Deprecation policy with a maximum supported version skew | Version skew exceeding the agreed window |
| AR-15 | CE | A jurisdiction requires an approval model the decision contract cannot express | 2 | 4 | 8 | Medium | Governance owner | Contract reviewed against each new jurisdiction before tenant onboarding | Any onboarding blocked by contract expressiveness |

### 12.4 Legacy exposure index

The self hosted estate is the principal legacy exposure. Rather than treating it as a single undifferentiated risk, each deployment is scored so that the migration backlog can be ordered by exposure rather than by customer volume or by who asked most recently.

| Dimension | What it measures | Contribution to exposure |
|---|---|---|
| Version age | Distance from the current supported release | Older increases risk of unsupported dependencies |
| Data volume | Stored records and payload bytes | Larger increases migration cost and prolongs exposure |
| Hold count | Active legal holds | Higher increases the consequence of an error |
| Jurisdictional spread | Distinct jurisdictions in the subject population | Wider increases the chance of a blocking constraint |
| Customisation depth | Tenant authored rules and thresholds | Deeper increases behavioural change risk on cutover |
| Investigation activity | Open cases in the period | Higher narrows the window in which migration is acceptable |

Deployments with high exposure and low migration cost are sequenced first. Deployments with high exposure and high cost are the ones that determine whether the tooling investment is sufficient, and their assessment should not be deferred to the end of the programme, which is the natural but incorrect instinct.

### 12.5 Conformance scoring

Architecture conformance is measured rather than assumed. Each component is scored against the principles it is obliged to honour.

| Dimension | Conformant | Partially conformant | Non conformant |
|---|---|---|---|
| Contract adherence | Emits and consumes only published contracts | Uses a contract with undocumented extensions | Reads another component's internal state |
| Vocabulary discipline | All signal types governed; additions are additive | Additions pending governance approval | Emits unclassified or invented types |
| Authority enforcement | No emission path without an unexpired decision | Enforcement present but bypassable in a documented case | Any unenforced path |
| Isolation | No shared runtime, no shared failure channel | Shared failure channel only | Shared runtime with another source |
| Observability | Authority coverage, quality, and volume baseline all emitted | Partially instrumented | No absence detection |
| Decision record coverage | Every structural choice has a recorded decision | Some choices undocumented | Structural choices contradicting a recorded decision |

The score is reported per component and per domain, trended over time. A falling conformance trend is treated as a leading indicator of the risks in 12.3 rather than as a documentation problem.

---

## 13. Operating model

### 13.1 Ownership structure

The model is federated. A small platform group owns the contracts and the shared substrate; delivery teams own their components and run what they build.

| Function | Owns | Accountable for |
|---|---|---|
| Chief Architect | Contracts, principles, decision records, risk register, conformance | Coherence across domains; adjudicating exceptions |
| Platform group | Shared adapter library, transport, persistence substrate, deployment automation, the paved road | Making the conformant path the easiest path |
| Adapter owners | One or more adapters, end to end | Their source's data quality, availability, and isolation |
| Governance services team | Identity resolution, authority, session lifecycle, policy administration | Correctness of collection decisions |
| Access services team | Federation, indexing, retrieval, scope enforcement | Completeness and honesty of results |
| Migration operations | Assessment, compatibility, cutover, rollback, estate decommissioning | Cost per tenant and rollback success |
| Compliance owner | Jurisdiction policy content, retention configuration, audit responsiveness | Defensibility of what the system holds |
| Reliability engineering | Service levels, on call, incident response, capacity | Availability and the correctness of failure behaviour |

### 13.2 Decision rights

| Decision | Chief Architect | Platform | Component team | ARB | Compliance |
|---|---|---|---|---|---|
| Change to any of the five contracts | Accountable | Consulted | Consulted | Approves | Consulted |
| Vocabulary addition, additive | Informed | Approves | Proposes | Informed | Informed |
| Vocabulary removal or version increment | Accountable | Consulted | Consulted | Approves | Consulted |
| New adapter following the paved road | Informed | Informed | Decides | Informed | Informed |
| New adapter departing from the paved road | Consulted | Consulted | Proposes | Approves | Informed |
| Capture mode or approver model change | Accountable | Informed | Informed | Approves | Approves |
| Retention or residency policy change | Consulted | Consulted | Informed | Informed | Accountable |
| Substrate technology selection | Accountable | Proposes | Consulted | Approves | Informed |
| Tenant cutover with a changed compatibility classification | Informed | Informed | Proposes | Informed | Approves |
| Scoring model version promotion | Consulted | Informed | Proposes | Approves | Informed |
| Accepting an architecture exception | Accountable | Consulted | Requests | Approves | Consulted |

### 13.3 Build and run

Teams run what they build. The platform group provides the paved road and the operational primitives; it does not operate other teams' components, because separating build from run is what allows an adapter owner to be indifferent to their source's data quality.

The paved road for the highest frequency change, adding a source, is a defined sequence: map the source vocabulary, declare capability, confirm identity resolution, implement the mapping through the shared library, prove fail closed behaviour, register, and review. Departing from it is permitted but requires review, which is the enablement over control posture made concrete: the conformant path is not mandatory, it is simply the fastest.

### 13.4 Service levels

| Component | Availability objective | Latency objective | Failure behaviour when breached |
|---|---|---|---|
| Control plane | High, with degradation permitted | Human interactive | New sessions refused; in flight collection continues |
| Ingest per adapter | Independent per source | Bounded by declared minimum interval | Diverted to the adapter's own failure channel |
| Transport | Highest in the system | Sub second end to end | Backpressure to adapters; no record loss |
| Index and retrieval | High | Bounded by explicit deadline | Partial results, explicitly labelled |
| Object store | Highest for durability | Not latency critical | Reference publication blocked until durable |
| Estate transmission | Best effort, resumable | Bounded by checkpoint interval | Replay on resume; never skip |

Two service levels are non negotiable regardless of cost: durability of stored records under hold, and correctness of the authority gate. Both are correctness properties rather than availability properties, and degrading them is not an acceptable trade under load.

### 13.5 Incident response

Severity is assessed by consequence class rather than by component.

| Class | Example | Response |
|---|---|---|
| Governance breach | Collection occurring without valid authority | Immediate stop of the affected collection path; compliance owner engaged before restoration |
| Evidentiary loss | Hold lapse, dangling reference, broken chain | Immediate containment; scope of affected records established before any remediation |
| Silent degradation | A source stopped emitting; partial results presented as complete | Treated as severe despite absent alarms, because the failure is invisible to users |
| Availability | Component unavailable | Conventional response; verify the failure behaviour matched the designed one |
| Quality | Elevated diversion rate | Adapter owner engaged; source contract re verified |

Silent failures are rated above loud ones. A component that is down is known to be down; a source that stopped emitting looks identical to a subject who did nothing, and in an investigative context that distinction is the whole point.

### 13.6 Cost model and FinOps

Cost is an architectural constraint, not an operational afterthought, because a system that is expensive to run in non production environments will be developed against production or not developed at all.

| Practice | Mechanism |
|---|---|
| Attribution | Every resource tagged by project, stage, and where meaningful by tenant |
| Non production default | Nothing running unless deliberately deployed; teardown is a first class supported operation |
| Local first development | Full path exercisable against protocol compatible substitutes at no cost |
| Unit economics | Cost per tenant migrated, cost per million records ingested, cost per gigabyte retained |
| Guardrails | Budget alarms per stage; anomaly detection on the largest line items |
| Right sizing review | Network egress and always on components reviewed quarterly, as these dominate at low utilisation |

The migration programme's economics are the single most important cost measure. Cost per tenant migrated determines whether the installed base is reachable at all, and it is tracked from the first migration rather than derived retrospectively.

### 13.7 Knowledge continuity

Architectural rationale is captured as decision records with the alternatives that were rejected and the condition that should cause the decision to be revisited. Decisions are tracked as work items linked from the components they govern, so that a team encountering a constraint can reach its justification without asking an individual.

This is a direct mitigation for AR-13. A decision recorded without its rejected alternatives is an instruction rather than a rationale, and instructions are reversed by the next competent person who sees an obvious better way.

---

## 14. Architecture governance

Governance guides rather than gates. Its purpose is to make the conformant path the fastest path and to ensure that departures are visible, deliberate, and time bounded.

### 14.1 Review scope

| Change | Review required |
|---|---|
| New adapter on the paved road | None; conformance validated automatically at release |
| New adapter departing from the paved road | ARB, lightweight |
| Vocabulary addition, additive | Platform approval; no ARB |
| Vocabulary removal or version increment | ARB, with a migration plan |
| Change to any of the five contracts | ARB, with a decision record |
| Change touching the plane boundary | ARB; this is where erosion begins |
| Capture mode or approver model change | ARB and compliance |
| New substrate dependency | ARB, with the local equivalent identified |
| Residency or retention model change | Compliance, with ARB informed |

The scope is deliberately narrow. Reviewing everything trains teams to route around review; reviewing the boundary changes and the irreversible ones preserves the review's authority.

### 14.2 Decision records

Every structural decision is recorded with context, at least two genuine options, trade off analysis, consequences, and a revisit trigger. Records are immutable once accepted; a superseding decision receives a new record with a back reference.

Two disciplines make the difference between a record that guides and one that is ignored. Both options must be ones a competent engineer would actually choose, since a straw man alternative renders the record worthless. And every record names the condition that should cause it to be reopened, because a decision with no revisit trigger becomes dogma and is eventually broken rather than revised.

### 14.3 Policy as code

Governance is automated wherever the rule is mechanically checkable. The following are enforced in the delivery pipeline rather than in review:

| Policy | Enforcement point |
|---|---|
| Every emitted signal type exists in the governed vocabulary | Release validation, blocking |
| Every adapter's output conforms to the record contract | Contract tests, blocking |
| No emission path exists without authority enforcement | Contract tests, blocking |
| Every planned work item carries a specification reference and acceptance criteria | Plan validation, blocking |
| The dependency graph is acyclic and every declared edge resolves | Plan validation, blocking |
| Infrastructure synthesises without credentials | Pipeline, blocking, and free to run |
| Resources carry attribution tags | Deployment policy |

The mechanically checked policies are the ones that hold. Everything left to review erodes at the rate that delivery pressure increases.

### 14.4 Exceptions

An exception is a recorded, owned, and time bounded departure from a standard. It names the standard departed from, the reason, the compensating control, the owner, and the expiry date. Exceptions without expiry dates are not granted, because a permanent exception is a change to the standard and should be processed as one.

Exception count and age are reported alongside conformance score. A rising exception count against a stable conformance score usually indicates that a standard has become impractical and should be revised rather than more strictly enforced.

### 14.5 Federated participation

Domain and component owners apply the standards within their context and participate in the review body. The Chief Architect adjudicates rather than designs, and the platform group's contribution to governance is the paved road rather than the rulebook.

---

## 15. Cloud adoption model

### 15.1 Posture

Cloud native rather than lift and shift. The target state uses ephemeral compute, managed streaming, managed object storage, and managed key services. No self managed brokers or databases exist in the target state.

The self hosted estate is explicitly not a hybrid architecture to be sustained. It is a legacy estate to be drained, and no investment is made in maintaining indefinite parity between it and the managed plane. This distinction matters commercially: hybrid architectures accumulate permanent dual running cost, whereas an estate under a strangler pattern has a declining cost curve with a defined end.

### 15.2 Landing zone

Each environment is a standardised account structure with pre configured network isolation, identity federation, encryption defaults, logging destinations, tagging policy, and budget guardrails. Regional separation implements residency, so residency is a deployment property rather than an application concern.

### 15.3 Infrastructure as code

All infrastructure is declared and version controlled, composed into small independently destroyable units separated by lifecycle and blast radius. The composition is what makes teardown routine, and routine teardown is what makes non production environments affordable, which in turn is what makes the architecture something people actually exercise.

Deployment is deliberate and manually initiated rather than automatic on merge, and teardown is an equally supported operation invoked the same way.

### 15.4 Multi cloud posture

Portability is preserved at the protocol level, not the service level. Dependencies are on interfaces with more than one viable implementation, and the local development substrate is the continuous proof that this holds, because a portability claim that is never exercised is not a claim.

Full multi cloud operation is not a current objective. The realistic objectives are exit capability and residency flexibility, and the architecture supports both without paying the ongoing cost of lowest common denominator design.

### 15.5 Adoption sequencing

Contracts first, then governed collection, then ingest, then retrieval, then migration tooling, then interface and full deployment. Each stage exits on a demonstrated behaviour rather than on a completion claim, and the exit conditions are stated in the product requirements.

---

## 16. Execution roadmap and measures

### 16.1 Phases

| Phase | Focus | Key deliverables | Exit condition |
|---|---|---|---|
| Baseline | Establish the contracts and the assessment | Record contract, governed vocabulary, shared library, conformance validation, estate inventory with exposure scoring, risk register | Validation passes across all declared adapters; construction invariants proven, including refusal without authority |
| Blueprint | Governed collection and the reference path | Authority evaluation against persisted policy, identity resolution, session lifecycle, coverage discovery, reference adapters, decision records, ARB stood up | A subject in a restrictive jurisdiction is denied an impermissible mode with an actionable reason |
| Modernize | Ingest and retrieval at production quality | Payload ordering, isolation, estate ingest, index backed retrieval, federation, partial result reporting, structural scope enforcement | With one estate unavailable, results return labelled and the unavailable estate named |
| Scale | Migration at programme rate | Assessment, compatibility reporting, cutover state machine, backfill, rollback, unit economics, interface, deployment automation, policy as code | A tenant migrates and rolls back end to end without bespoke engineering |

### 16.2 Measures by phase

| Phase | Leading measures | Lagging measures |
|---|---|---|
| Baseline | Vocabulary coverage of known source events; conformance validation in the pipeline | Contract change rate after acceptance |
| Blueprint | Authority coverage; unexplained denial count | Revocation latency |
| Modernize | Cross adapter interference; dangling reference count; partial result honesty | Time to first signal for a new source |
| Scale | Cost per tenant migrated; rollback success rate | Tenants migrated per quarter; hold lapse count |

### 16.3 Standing architecture measures

Reported continuously rather than per phase.

| Measure | Why it is architectural |
|---|---|
| Adapter change ratio, files changed outside the new adapter per integration | Directly measures whether the central design claim holds. Target is zero |
| Vocabulary reuse rate for new adapters | Measures whether the compounding asset is compounding |
| Authority coverage | Any value below complete indicates a bypass |
| Dangling reference count | Any value above zero indicates broken write ordering |
| Cross adapter interference correlation | Any correlation indicates isolation has failed |
| Conformance score by component and domain | Leading indicator for the risk register |
| Exception count and median age | Distinguishes a standard being enforced from a standard being routed around |
| Decision record coverage of structural changes | Mitigates knowledge continuity risk |
| Cost per tenant migrated | Determines whether the installed base is reachable |
| Legacy exposure index, aggregate and trend | Measures whether the estate is actually shrinking |

The first measure is the one to watch. If the number of files changed outside a new adapter is not zero, the normalized layer is leaking and every other benefit claimed by this architecture is at risk regardless of what the other measures say.

---

## 17. Constraints and known limitations

**The decision cache bounds revocation.** Adapters act on cached decisions for the session's bounded lifetime, so withdrawal takes effect within that interval rather than immediately. Shortening the interval increases control plane load. This is a tuning decision, not a defect, but it is a real bound and must be stated to customers rather than implied away.

**Vocabulary governance is a standing obligation.** The compounding value depends on discipline that must be enforced mechanically and indefinitely. It will erode the moment enforcement is relaxed.

**Local development diverges from managed services.** Enumerated in section 8.3 and covered by a pre release verification path, but the gap is real and defects will occasionally surface first in the cloud.

**Multiple concurrent model versions carry a support burden.** Per tenant pinning is what makes migration behaviour preserving, and it produces a long tail of versions requiring a deprecation policy.

**Historical backfill has no cheap option for bulk content.** Index and metadata migrate economically; bytes do not. Expiry under existing retention is the common answer and is not always available.

**The platform cannot originate policy.** It enforces jurisdictional rules and approval records that customers supply. Where a customer's own governance is absent or incorrect, the platform enforces the absence faithfully.

---

## 18. Evolution

**Additional sources** are the expected direction of growth and are accommodated by design.

**Additional estates**, such as a second managed region or an acquired platform, integrate through the same federation mechanism. The read path was built for two and generalises to N.

**Vocabulary versioning** is the change with the widest blast radius and the one most likely to be forced eventually. The additive only policy defers it; the migration procedure for a version increment should be designed before it is needed rather than during.

**Deprecating self hosted deployment** is the terminal state of the migration programme, at which point the federation component's second estate has no members and the component can be simplified rather than removed, preserving the mechanism for the next estate.
