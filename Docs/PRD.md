# Product Requirements Document

**Product:** Signal Plane — a multi source telemetry integration platform with a self hosted estate migration path
**Document status:** Draft for review
**Version:** 1.0
**Date:** 14 August 2026

---

## 1. Summary

Signal Plane is a horizontal integration layer that unifies behavioural and operational signals from an open ended set of source systems into a single normalized vocabulary, governs the collection of those signals against jurisdictional authority rules, and provides a federated read path that allows an existing estate of self hosted deployments to migrate to the managed plane without a cutover.

The product solves two problems that usually arrive in sequence. The first is integration economics: in a landscape of heterogeneous sources, the cost of integrating the Nth source is as high as the first, because every downstream consumer knows every source. The second is estate migration: an installed base of self hosted deployments must reach a managed plane without losing evidentiary continuity, without requiring inbound network access into customer environments, and without a behavioural change that customers experience as a regression.

---

## 2. Problem statement

### 2.1 Fragmentation

Signals about the same entities are produced by systems that were never designed to be read together. Endpoint agents, collaboration suites, identity providers, security tooling, network infrastructure, and legacy self hosted deployments each expose their own schema, delivery model, authentication scheme, rate limits, and identity representation.

Two costs follow directly.

**Linear integration cost.** Without a normalizing layer, each new source requires changes to every consumer: scoring, rules, storage, retention, reporting, and user interface. Integration effort does not amortise.

**No cross source questions.** Analysis that spans sources is impossible to express because there is no shared vocabulary in which to ask. Answering a question about an entity requires knowing in advance which systems observed it and querying each separately, reconciling by hand.

### 2.2 Identity fragmentation

The same subject appears under different identifiers in different systems: a directory principal name, an email address, a device identifier, an account security identifier, an employee number. Without deterministic resolution to a canonical subject, records cannot be aggregated, cannot be retrieved on request, and cannot be reliably deleted.

### 2.3 Collection governance

Collection legality is not a single global policy. It depends on two variables that most implementations conflate or ignore.

**Capture mode.** Reading metadata produced by corporate systems and capturing content from an endpoint are materially different acts with different approving parties.

**Subject jurisdiction.** The governing rule follows the subject's location, not the organisation's headquarters. A multinational customer with staff across jurisdictions is the normal case rather than an edge case.

Systems that check policy at query time rather than at collection time have already collected data they may not lawfully hold. Deletion is an imperfect remedy.

### 2.4 Estate migration

An existing installed base of self hosted deployments must reach the managed plane. This is rarely blocked by engineering capability. It is blocked by:

- Security functions that will not permit inbound network access into the customer environment.
- Years of accumulated history subject to retention obligations, legal holds, and open investigations that cannot be discarded.
- Operational tuning, including alert thresholds and customer authored rules, that is calibrated against current system behaviour and breaks when that behaviour changes.
- The all or nothing character of a cutover, which makes each migration an irreversible event that customers reasonably resist.

### 2.5 Scale of the migration problem

With an installed base numbering in the thousands of deployments, per tenant migration cost dominates the programme economics. If a single migration requires an engineer on a call, the programme reaches only the customers who escalate loudest and stalls indefinitely at the long tail. Migration tooling is therefore a product requirement, not an internal convenience.

---

## 3. Goals and non goals

### 3.1 Goals

| # | Goal | Measure |
|---|---|---|
| G1 | Make the Nth source integration cheap | Median elapsed time from source identified to signals flowing in production |
| G2 | Enable cross source questions | Proportion of analytical queries that span two or more sources |
| G3 | Make collection defensible | Every stored record resolves to the authority decision that permitted it |
| G4 | Migrate the self hosted estate | Tenants migrated per quarter; cost per tenant migrated |
| G5 | Make migration reversible | Rollback rate, and rollback success rate within the stated window |
| G6 | Preserve evidentiary continuity | Zero legal hold lapses; historical records remain interpretable after migration |

### 3.2 Non goals

| # | Non goal | Rationale |
|---|---|---|
| N1 | Replacing source systems | The platform integrates sources; it does not seek to become the system of record for any of them |
| N2 | Real time enforcement or blocking | The platform observes and reports; interdiction belongs to systems designed for it |
| N3 | Indefinite parity between managed and self hosted deployment | Self hosted is an estate to be drained, not a co equal deployment target maintained in perpetuity |
| N4 | Automated adjudication of subjects | The platform surfaces evidence; conclusions about individuals are made by accountable humans |
| N5 | A general purpose analytics platform | Export to customer analytics tooling is supported; competing with it is not attempted |

### 3.3 Explicit anti goal

The platform must not make it easy to collect signals for which no authority exists. Any design choice that trades governance for convenience is out of scope regardless of customer demand, because the resulting data is a liability rather than an asset.

---

## 4. Users and stakeholders

### 4.1 Primary users

**Platform integrator.** Builds and maintains adapters. Success means adding a source without touching anything that already works.

**Investigator.** Reviews signals about a specific subject within a bounded case. Needs completeness, provenance, and the ability to tell whether what they are seeing is all of it.

**Compliance owner.** Answers what was collected, under what authority, and for how long. Needs the answer to be derivable from the data rather than reconstructed from process documentation.

**Administrator.** Configures policy, scope, retention, and monitoring windows. Needs the configuration surface to make unsafe states difficult to express.

**Migration operator.** Moves tenants from the self hosted estate to the managed plane. Needs assessment, execution, and rollback to be tooling rather than judgement.

### 4.2 Secondary stakeholders

**Subject of collection.** Not a user, but a party with rights. Needs collection to be bounded, disclosed where required, and retrievable and deletable on request.

**Customer security function.** Gates whether migration may proceed. Needs the network posture and key custody model to be reviewable and to require no inbound access.

**Works councils, data protection officers, and equivalent bodies.** Approve or refuse particular capture modes in particular jurisdictions.

---

## 5. Use cases

### UC1 — Integrate a new source

An integrator identifies a source, maps its event vocabulary onto the platform taxonomy, declares what it can observe and at what fidelity, implements the mapping, and deploys. No consumer changes. No coordination with other integrations.

**Success:** signals flow within days, and no existing adapter's error rate or latency changes.

### UC2 — Establish coverage for a subject

Given any identifier, the platform resolves it to a canonical subject and reports which sources can observe that subject, at what fidelity, and under which capture modes. Where identity is ambiguous, it reports ambiguity rather than guessing.

**Success:** the coverage answer is derived from declared adapter capability rather than from tribal knowledge.

### UC3 — Open a bounded collection session

An administrator requests collection at a named capture mode. The platform resolves the governing jurisdiction from the subject, determines the approving party for that mode, verifies approval is on record, and issues a bounded decision or a denial with a stated reason.

**Success:** an unapproved or impermissible request is denied with an explanation an administrator can act on, and no granted session lacks an expiry.

### UC4 — Terminate collection

Collection stops on a rule: a schedule window boundary, a decision expiry, a retention threshold, or a case closure. Explicit termination exists but is the exception.

**Success:** no session outlives its authority because a human forgot to close it.

### UC5 — Investigate a subject

An investigator retrieves the signal history for a subject across all sources and both estates within their authorised scope, in one view, with provenance and with explicit indication of any source or estate that failed to respond.

**Success:** the investigator can distinguish "nothing happened" from "we could not see."

### UC6 — Answer a compliance enquiry

A compliance owner selects a stored record and derives the authority decision, legal basis, approving party, policy version, and jurisdiction that permitted its collection, plus its retention class and hold status.

**Success:** the answer comes from the record, not from a reconstruction.

### UC7 — Assess a tenant for migration

A migration operator runs an assessment producing data volume, retention profile, active legal holds, open investigations, subject jurisdiction distribution, and a rule and threshold compatibility classification.

**Success:** the assessment is generated, and every rule is classified as behaviour preserving, changed, or dependent on a retired vocabulary entry.

### UC8 — Migrate a tenant

The tenant's read path moves first, then new collection, then history. Each step is independently reversible within a stated window.

**Success:** completed without bespoke engineering, and reversible at every step.

### UC9 — Roll back a migration

Within the rollback window, a migrated tenant returns to their prior configuration with no data loss and no hold lapse.

**Success:** rollback is a supported operation rather than an incident.

### UC10 — Retire a self hosted deployment

After the rollback window elapses with no reversal, the deployment is decommissioned under explicit human approval, with holds verified as carried across.

---

## 6. Functional requirements

### 6.1 Normalization

| ID | Requirement | Priority |
|---|---|---|
| FR-1.1 | All sources are represented in a single normalized record structure. No consumer receives source specific shapes. | Must |
| FR-1.2 | A governed vocabulary defines every valid signal type and the attributes it carries. | Must |
| FR-1.3 | The vocabulary is additive only within a version. Removal or repurposing requires a version increment and a recorded decision. | Must |
| FR-1.4 | Every record identifies its originating adapter, adapter version, and originating estate. | Must |
| FR-1.5 | Record identity is deterministic from source facts, so that the same source event ingested more than once collapses to a single record. | Must |
| FR-1.6 | Records preserve a reference to their native source identifier, so the original may be retrieved from the system of record. | Must |
| FR-1.7 | Consecutive records for a subject are chained by content hash, allowing a reader to verify ordering and detect omission without trusting the store. | Should |
| FR-1.8 | An adapter that cannot map an event declares the gap explicitly rather than emitting an unclassified record. | Must |

### 6.2 Source integration

| ID | Requirement | Priority |
|---|---|---|
| FR-2.1 | Each source is served by an independently deployed and versioned adapter. | Must |
| FR-2.2 | An adapter declares a manifest stating emitted signal types, fidelity per type, supported capture modes, delivery model, minimum interval, and identifier kinds supplied. | Must |
| FR-2.3 | Coverage discovery is derived from registered manifests, never from static configuration. | Must |
| FR-2.4 | Saturation, failure, or rate limiting in one adapter must not degrade any other adapter. | Must |
| FR-2.5 | Each adapter has an isolated failure channel for records that cannot be processed, with operator initiated reprocessing. | Must |
| FR-2.6 | Adding an adapter requires no modification to existing adapters, consumers, or the shared runtime. | Must |
| FR-2.7 | Adapter output is validated against the normalized structure and the governed vocabulary before release. | Must |

### 6.3 Identity resolution

| ID | Requirement | Priority |
|---|---|---|
| FR-3.1 | Raw identifiers of declared kinds resolve to a canonical subject with an associated confidence. | Must |
| FR-3.2 | Ambiguous or conflicting identity claims resolve to no subject and raise a diagnostic. Silent merging of distinct individuals is prohibited. | Must |
| FR-3.3 | Identity mappings are auditable and correctable, and correction is retroactive across stored records. | Should |
| FR-3.4 | Records are retrievable and deletable by canonical subject across all sources and both estates. | Must |

### 6.4 Collection authority

| ID | Requirement | Priority |
|---|---|---|
| FR-4.1 | No collection session opens without an authority decision issued in advance. | Must |
| FR-4.2 | The decision names the capture mode, legal basis, approving party role, governing jurisdiction, policy version, and expiry. | Must |
| FR-4.3 | Governing jurisdiction is resolved from the subject, not the tenant. | Must |
| FR-4.4 | Capture modes form an escalating scale, and the approving party is a function of mode and jurisdiction. | Must |
| FR-4.5 | Every granted decision carries an expiry. An unbounded grant is invalid. | Must |
| FR-4.6 | Every denial carries a reason sufficient for an administrator to act on it. | Must |
| FR-4.7 | Decisions carry constraints: permitted schedule windows, excluded categories, excluded destinations, and a redaction profile. | Must |
| FR-4.8 | Every stored record carries the identifier of the decision that permitted it. | Must |
| FR-4.9 | Where authority cannot be established or has expired, collection stops. Continuing is prohibited. | Must |
| FR-4.10 | Withdrawal of approval takes effect within a bounded and documented interval. | Must |
| FR-4.11 | All decisions, granted and denied, are retained with their inputs. | Must |
| FR-4.12 | Certain destinations are never collected regardless of tenant configuration, by jurisdictional policy. | Must |

### 6.5 Transport and storage

| ID | Requirement | Priority |
|---|---|---|
| FR-5.1 | Normalized records are distributed on an event stream partitioned so that ordering within a subject is preserved. | Must |
| FR-5.2 | Large payloads are stored in an object store and referenced from the record. Payload content is never carried on the event stream. | Must |
| FR-5.3 | A payload is durable before its reference is published. Unreferenced payloads are reconciled by a background process; references to absent payloads are prohibited. | Must |
| FR-5.4 | Payload references carry content hash, size, media type, retention class, hold status, and encryption key identity. | Must |
| FR-5.5 | Retention is enforced at the storage layer. | Must |
| FR-5.6 | Legal hold suspends retention expiry and causes deletion to be refused at the storage layer rather than by application logic. | Must |
| FR-5.7 | Tenants requiring key custody may supply their own encryption keys. | Should |
| FR-5.8 | Data residency is selectable per tenant, and records do not leave the selected region. | Must |

### 6.6 Read path

| ID | Requirement | Priority |
|---|---|---|
| FR-6.1 | A single read interface serves both the managed plane and any self hosted estate. | Must |
| FR-6.2 | Results from multiple estates are merged on deterministic record identity, so overlap during migration does not double count. | Must |
| FR-6.3 | Reads are bounded by a deadline. A slow estate does not stall the response. | Must |
| FR-6.4 | Partial results are reported explicitly, naming each estate that failed to respond. Silent partial results are prohibited. | Must |
| FR-6.5 | Authorisation scope is enforced at the data layer, structurally, so that an out of scope query cannot be expressed. | Must |
| FR-6.6 | Payloads resident in a self hosted estate are made available by time bounded reference. | Should |
| FR-6.7 | Read access is itself recorded: who read what, when, under which case. | Must |

### 6.7 Derived signals and scoring

| ID | Requirement | Priority |
|---|---|---|
| FR-7.1 | Derived values carry the model version that produced them. | Must |
| FR-7.2 | Model version is pinned per tenant. | Must |
| FR-7.3 | Platform migration and model version change are separately scheduled and never combined. | Must |
| FR-7.4 | Model upgrade is preceded by a comparison period during which both versions are computed and their divergence reported. | Should |
| FR-7.5 | Tenant authored rules are validated at authoring time and rejected if unbounded or ill formed. | Must |
| FR-7.6 | A rule cannot be authored against a vocabulary entry that does not exist. | Must |
| FR-7.7 | Derived values are distinguishable from observed facts at every point of presentation. | Must |

### 6.8 Estate integration and migration

| ID | Requirement | Priority |
|---|---|---|
| FR-8.1 | The self hosted estate integrates through the same adapter contract as any third party source. | Must |
| FR-8.2 | The estate initiates all connections outbound. No inbound access, listening port, or tunnel into the customer environment is required. | Must |
| FR-8.3 | Estate transmission position is checkpointed durably, and the checkpoint advances only after upstream acknowledgement. | Must |
| FR-8.4 | Repeated transmission after an interruption is absorbed idempotently. Skipping is prohibited. | Must |
| FR-8.5 | Estate health is reported over the same outbound channel. | Must |
| FR-8.6 | The read path may be migrated independently of, and before, the data. | Must |
| FR-8.7 | New collection may be switched to the managed plane independently of historical migration. | Must |
| FR-8.8 | Historical migration offers both backfill and expiry under existing retention, with cost of each presented. | Must |
| FR-8.9 | Each migration step is independently reversible within a stated window. | Must |
| FR-8.10 | Legal holds are verified as effective after crossing the boundary, by asserting refusal of deletion rather than by inspecting a flag. | Must |
| FR-8.11 | Before cutover, a compatibility report classifies every tenant rule and threshold as behaviour preserving, changed, or dependent on a retired vocabulary entry. | Must |
| FR-8.12 | A tenant with any changed classification cannot be cut over without explicit recorded acknowledgement. | Must |
| FR-8.13 | Migration state per tenant is a persisted, queryable state machine. | Must |
| FR-8.14 | Cost per tenant migrated and rollback rate are emitted as first class metrics. | Must |

### 6.9 Administration and presentation

| ID | Requirement | Priority |
|---|---|---|
| FR-9.1 | A single interface serves both estates during migration. | Must |
| FR-9.2 | Partial results are visibly indicated with the unavailable estate named. | Must |
| FR-9.3 | Scope selection reflects only the scope the caller actually holds. | Must |
| FR-9.4 | Any record can be traced to its collecting adapter and permitting authority decision. | Must |
| FR-9.5 | Bulk export is available in a documented, stable format. | Must |
| FR-9.6 | Configuration presents the consequence of a setting, particularly where a change widens collection. | Should |

---

## 7. Non functional requirements

### 7.1 Availability and failure behaviour

| ID | Requirement |
|---|---|
| NFR-1.1 | Loss of the control plane prevents new sessions from opening but does not interrupt collection already authorised and in flight. |
| NFR-1.2 | Loss of a single adapter affects only its own source. |
| NFR-1.3 | Loss of one estate degrades reads to explicitly reported partial results rather than to an error or to silence. |
| NFR-1.4 | Every failure mode resolves toward not collecting and not disclosing, rather than toward continuing. |

### 7.2 Scale

| ID | Requirement |
|---|---|
| NFR-2.1 | Ingest scales horizontally per source without coordination between sources. |
| NFR-2.2 | Control interactions and telemetry scale independently, reflecting their different volumes. |
| NFR-2.3 | Onboarding an additional source adds no load to existing sources. |
| NFR-2.4 | Read latency is bounded by an explicit deadline rather than by the slowest participant. |

### 7.3 Security

| ID | Requirement |
|---|---|
| NFR-3.1 | Encryption in transit and at rest throughout. |
| NFR-3.2 | Tenant isolation is structural, not a filter applied at query time. |
| NFR-3.3 | Customer environments require no inbound access in any deployment or migration topology. |
| NFR-3.4 | Administrative actions are attributable to an individual. |
| NFR-3.5 | Deployment credentials are short lived and federated. Long lived static credentials are prohibited. |

### 7.4 Compliance

| ID | Requirement |
|---|---|
| NFR-4.1 | Data residency is enforceable per tenant. |
| NFR-4.2 | Subject access and erasure are satisfiable across all sources and both estates. |
| NFR-4.3 | Retention is enforced at storage, with hold taking precedence. |
| NFR-4.4 | Jurisdiction policy is versioned, and every decision references the version applied. |
| NFR-4.5 | Access to collected data is itself auditable. |

### 7.5 Operability

| ID | Requirement |
|---|---|
| NFR-5.1 | The full path is exercisable locally without cloud infrastructure. |
| NFR-5.2 | Deployment is deliberate and manually initiated; teardown is a first class, supported operation. |
| NFR-5.3 | Known divergences between local and cloud behaviour are documented and covered by a pre release verification path. |
| NFR-5.4 | Infrastructure is composed of small independently destroyable units. |

### 7.6 Extensibility

| ID | Requirement |
|---|---|
| NFR-6.1 | Adding a source touches only the new adapter and the vocabulary. |
| NFR-6.2 | Components communicate only through published contracts, never through shared internal code. |
| NFR-6.3 | Substrate dependencies are on protocols with more than one viable implementation. |

---

## 8. Data requirements

### 8.1 Core entities

**Normalized signal record.** The universal unit. Carries identity, tenant, source provenance, resolved subject, occurrence and observation times, category, signal type, typed attributes, optional payload reference, authority reference, optional derived scoring with model version, and integrity fields.

**Authority decision.** Bounded permission to collect. Carries capture mode, grant or denial, legal basis, approving party role, jurisdiction, policy version, evaluation time, expiry, constraints, and denial reason where applicable.

**Payload reference.** Pointer to stored bytes. Carries location, content hash, media type, size, encryption key identity, retention class, hold status, and which estate can resolve it.

**Adapter manifest.** Declared capability of a source. Carries adapter identity and version, source system, delivery model, minimum interval, supported capture modes, emitted signal types with fidelity, and supplied identifier kinds.

**Subject.** Canonical principal. Carries subject identity, governing jurisdiction, and the identifier claims that resolve to it with confidence.

**Vocabulary.** The governed set of signal types, their categories, and their attribute definitions, versioned.

**Tenant.** Carries residency selection, pinned model version, estate assignment, retention configuration, and migration state.

### 8.2 Data lifecycle

Collection is gated by authority. Records enter the stream, are indexed for retrieval, and expire under retention unless held. Payloads follow the same lifecycle with storage layer enforcement. Deletion is complete across index, stream derived stores, and payloads, subject to hold.

### 8.3 Data quality

Records failing structural or vocabulary validation are diverted, never silently accepted or silently dropped. Diverted volume by adapter is a monitored quality signal.

---

## 9. Success metrics

### 9.1 Integration economics

| Metric | Definition |
|---|---|
| Time to first signal | Elapsed time from source selection to production signals |
| Adapter change ratio | Files changed outside the new adapter per integration. Target: zero |
| Vocabulary reuse | Proportion of a new adapter's signal types already present in the vocabulary |
| Cross source query share | Proportion of queries spanning two or more sources |

### 9.2 Governance

| Metric | Definition |
|---|---|
| Authority coverage | Proportion of records resolvable to a decision. Target: 100 percent |
| Unbounded grants | Count of granted decisions lacking expiry. Target: zero |
| Revocation latency | Interval from approval withdrawal to collection ceasing |
| Unexplained denials | Denials whose reason is insufficient to act on. Target: zero |

### 9.3 Migration

| Metric | Definition | Why it decides the programme |
|---|---|---|
| Cost per tenant migrated | Fully loaded engineering hours per completed migration | If this does not fall, the long tail is never reached |
| Tenants migrated per quarter | Completed migrations | The programme's actual rate |
| Rollback rate | Proportion reversed within the window | Health, not failure; a zero rate suggests reversal is impractical rather than unnecessary |
| Rollback success rate | Proportion of attempted rollbacks completing without loss | Reversibility is a claim only if demonstrated |
| Time to first value | Interval from start to the tenant using the managed interface | Read path first is justified by this being short |
| Hold lapse count | Legal holds not effective after migration. Target: zero | A single occurrence can end the programme |

### 9.4 Reliability

| Metric | Definition |
|---|---|
| Cross adapter interference | Correlation between one adapter's error rate and others'. Target: none |
| Partial result honesty | Proportion of degraded responses correctly labelled. Target: 100 percent |
| Dangling reference count | References to absent payloads. Target: zero |

---

## 10. Release plan

### Phase 1 — Contracts

Establish the normalized structure, governed vocabulary, shared construction library, and validation. Nothing else can be built stably first, because everything downstream is an implementation of these.

**Exit:** validation passes across all declared adapters; construction invariants are proven by test, including refusal without authority and refusal after expiry.

### Phase 2 — Governed collection

Authority evaluation against persisted jurisdictional policy, identity resolution, session lifecycle, and coverage discovery.

**Exit:** a subject in a restrictive jurisdiction is denied an impermissible capture mode with a reason; a permitted request is granted with a bounded expiry.

### Phase 3 — Ingest

Reference adapters, payload write ordering, isolation, and the estate ingest endpoint.

**Exit:** two adapters run concurrently under load without cross interference; an injected fault between payload write and reference publication produces an orphan, never a dangling reference.

### Phase 4 — Read

Index backed retrieval, federation across estates, partial result reporting, and structural scope enforcement.

**Exit:** with one estate unavailable, results are returned, labelled, and the unavailable estate named.

### Phase 5 — Migration tooling

Assessment, compatibility reporting, cutover state machine, backfill, rollback, and metrics.

**Exit:** a tenant is migrated and rolled back end to end without bespoke engineering.

### Phase 6 — Interface and deployment

Administrative and investigative interface; cloud deployment with verified independent teardown and a divergence smoke path.

**Exit:** a stage is deployed, exercised, and destroyed from automation alone.

---

## 11. Dependencies and assumptions

### 11.1 Assumptions

- Source systems expose an interface permitting extraction at useful fidelity.
- Customers can and will supply jurisdictional policy and approval records; the platform enforces them but cannot originate them.
- The self hosted estate can be modified to run an outbound transmission component.
- For most tenants, retention windows are shorter than the migration programme, making expiry a viable alternative to backfill.

### 11.2 External dependencies

- A managed event streaming service exposing a standard protocol.
- Object storage with retention lock semantics.
- A managed key service supporting customer supplied keys.
- Identity federation for administrative and deployment authentication.

### 11.3 Constraints

- Cloud managed services are the deployment target, but development must be possible locally at no cost, or the architecture will not be exercised.
- Substrate choices must have a viable local equivalent.

---

## 12. Risks

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | Vocabulary governance lapses and each adapter invents terms | The normalized layer stops normalizing; the central value is lost | Automated cross validation blocking release; additive only policy; recorded decision required for change |
| R2 | Authority checking is bypassed under delivery pressure | Unlawful collection; the outcome the product exists to prevent | Construction library is the only path to a record; refusal is proven by test; no override |
| R3 | Migration is coupled to a model version change | Tuned thresholds misfire on day one; migration is blamed and reversed | Version pinned per tenant; upgrade separately scheduled; compatibility report precedes cutover |
| R4 | Per tenant migration cost does not fall | The programme reaches only escalating customers and stalls | Cost per tenant is a tracked metric from the first migration; tooling is the deliverable |
| R5 | A legal hold lapses during migration | Regulatory exposure and loss of customer confidence; possibly terminal for the programme | Holds verified by asserting refusal of deletion; verification is a gated step |
| R6 | Partial results presented as complete | An investigator reaches a false conclusion | Estate status is part of the response contract; the interface must display it; covered by test |
| R7 | Identity resolution silently merges two individuals | Records attributed to the wrong person | Ambiguity resolves to no subject; merging requires confidence and is auditable and correctable |
| R8 | The control plane is drawn onto the telemetry path | It becomes the ingest ceiling, and its failure drops signals | Plane separation is architectural; decisions are cached for bounded session lifetimes |
| R9 | Local and cloud behaviour diverge undetected | Defects surface first in production | Divergences enumerated; smoke path mandatory before release |
| R10 | Payload volume overwhelms the event stream | Latency collapse; retention becomes unenforceable | Payloads by reference only; enforced structurally, not by convention |

---

## 13. Open questions

| # | Question | Needed by |
|---|---|---|
| Q1 | What is the acceptable upper bound on revocation latency, and does it vary by jurisdiction? | Phase 2 |
| Q2 | Is customer supplied key custody required at general availability or deferrable? | Phase 3 |
| Q3 | What confidence threshold governs automatic identity resolution, and who adjudicates below it? | Phase 2 |
| Q4 | How long is the standard rollback window, and does it vary by tenant size? | Phase 5 |
| Q5 | Where a subject's jurisdiction is genuinely unresolvable, is denial correct, or is a restricted default appropriate? | Phase 2 |
| Q6 | How many concurrent model versions are supportable before the deprecation burden exceeds the migration benefit? | Phase 5 |
| Q7 | Do any jurisdictions require prior approval that cannot be represented as a bounded decision at all? | Phase 2 |

---

## 14. Glossary

| Term | Definition |
|---|---|
| Adapter | An independently deployed component serving exactly one source system |
| Authority decision | Bounded, mode specific, jurisdiction aware permission to collect |
| Capture mode | A named level of collection intrusiveness determining the approving party |
| Coverage | Which sources can observe a given subject, at what fidelity |
| Estate | A deployment holding data: the managed plane, or a customer's self hosted deployment |
| Federated read | A retrieval resolving across more than one estate and merging results |
| Managed plane | The vendor operated deployment that is the migration target |
| Normalized record | The universal signal structure every source is mapped into |
| Payload reference | A pointer to stored bytes, carried in place of the bytes |
| Self hosted estate | Customer operated deployments constituting the installed base to be migrated |
| Signal type | A governed vocabulary entry naming a kind of observation |
| Subject | The canonical principal a record concerns |
| Vocabulary | The governed, versioned set of signal types and their attributes |
