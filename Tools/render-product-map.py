#!/usr/bin/env python3
"""Render Plan/backlog.yaml for the 18-epic product map.

Run once (or after editing the data below):
    python3 Tools/render-product-map.py

The YAML is the source of truth afterwards. This script exists so the map can
be regenerated without hand-editing a several-thousand-line file.
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Plan" / "backlog.yaml"

PRD = "docs/PRD.md"
TSA = "docs/TARGET-STATE-ARCHITECTURE.md"
ENV = "schemas/signal-envelope.schema.json"
AUTH = "schemas/authority-decision.schema.json"
BLOB = "schemas/blob-reference.schema.json"
MAN = "schemas/adapter-manifest.schema.json"
TAX = "taxonomy.yaml"


def T(title: str, status: str | None = None, **more) -> dict:
    item = {"title": title, **more}
    if status:
        item["status"] = status
    return item


def S(title: str, spec: str, design: str, acceptance: str, tasks: list[str] | list[dict],
      status: str | None = None, **more) -> dict:
    out: dict = {
        "title": title,
        "spec": spec,
        "design": " ".join(design.split()),
        "acceptance": " ".join(acceptance.split()),
        "tasks": [
            t if isinstance(t, dict) else T(t)
            for t in tasks
        ],
        **more,
    }
    if status:
        out["status"] = status
    return out


def F(title: str, spec: str, design: str, acceptance: str, stories: list[dict],
      implements: list[str] | None = None, status: str | None = None,
      priority: int | None = None, **more) -> dict:
    out: dict = {
        "title": title,
        "spec": spec,
        "design": " ".join(design.split()),
        "acceptance": " ".join(acceptance.split()),
        "stories": stories,
        **more,
    }
    if implements:
        out["implements"] = implements
    if status:
        out["status"] = status
    if priority is not None:
        out["priority"] = priority
    return out


def E(title: str, spec: str, design: str, acceptance: str, features: list[dict],
      priority: int = 2, labels: list[str] | None = None,
      status: str | None = None, phase: int = 2) -> dict:
    out: dict = {
        "title": title,
        "priority": priority,
        "phase": phase,
        "spec": spec,
        "design": " ".join(design.split()),
        "acceptance": " ".join(acceptance.split()),
        "features": features,
    }
    if labels:
        out["labels"] = labels
    if status:
        out["status"] = status
    return out


# ---------------------------------------------------------------------------
# Product map. Stories are persona + outcome. Tasks are one sitting of work.
# Phase 1–2 stay open (except delivered items). Phase 3–4 are deferred.
# ---------------------------------------------------------------------------

EPICS = [
    E(
        "Contracts and vocabulary",
        ENV,
        "The five contracts plus taxonomy.yaml are the published language. Everything downstream is an implementation of them.",
        "make validate passes; every adapter manifest cross-checks the taxonomy; contract tests cover determinism, hash chaining, and fail closed.",
        priority=0, labels=["contracts"], phase=1,
        features=[
            F("Normalized envelope and shared construction library", ENV,
              "Adapters build records only through AdapterContext so identity, hashing, and authority checks cannot drift.",
              "No adapter can emit a record without an unexpired decision; signal_id is deterministic; hash chain is per subject.",
              implements=["ADR-0002"],
              stories=[
                  S("Integrator emits only the normalized envelope", ENV,
                    "Heterogeneity stops at the adapter. Consumers never see a source-specific shape.",
                    "A directory_watch event validates against signal-envelope.schema.json with no additional properties.",
                    [T("Define signal envelope schema", "closed"),
                     T("Implement AdapterContext build and hashing", "closed"),
                     T("Reject additional properties and unknown signal types at validation", "closed")],
                    status="closed"),
                  S("Replay of the same source event collapses to one record", ENV,
                    "signal_id is uuid5 of tenant|adapter|native_id so overlap during migration does not double count.",
                    "Two builds with the same native_id produce the same signal_id.",
                    [T("Deterministic v5 signal_id over tenant, adapter, native id", "closed"),
                     T("Contract test for id determinism", "closed")],
                    status="closed"),
                  S("Investigator can detect omitted records without trusting the store", ENV,
                    "Per-subject content hash chain. Integrity is evidential, not decorative.",
                    "Consecutive signals for one subject link; a second subject starts a new chain.",
                    [T("Per subject hash chain in AdapterContext", "closed"),
                     T("Contract test for chain linkage and per-subject isolation", "closed")],
                    status="closed"),
                  S("Capture is refused without an unexpired authority decision", ENV,
                    "Fail closed. Missing or expired authority is a defect, not a configuration choice.",
                    "build() raises PermissionError when authority is absent or expired.",
                    [T("Refuse emit without authority", "closed"),
                     T("Refuse emit after expiry", "closed"),
                     T("Treat missing expires_at as expired in is_expired")],
                    status=None),
              ]),
            F("Governed vocabulary", TAX,
              "Additive only within a schema_version. An unmapped event is a decision, not an unclassified record.",
              "A manifest with an unknown signal_type or invalid category fails CI; a taxonomy addition alone does not.",
              implements=["ADR-0002"],
              stories=[
                  S("Release is blocked when an adapter invents a signal type", TAX,
                    "Vocabulary governance is mechanical. AR-04 / R1.",
                    "validate.py exits non-zero on an unknown signal_type.",
                    [T("Cross check manifests against taxonomy", "closed"),
                     T("Fail validation when PyYAML is absent rather than skipping")]),
                  S("Integrator cannot emit an unclassified record", TAX,
                    "FR-1.8. Gap is declared; the event is diverted or rejected, never stored as other.",
                    "Handler that cannot map an event records a declared gap and does not call build().",
                    [T("Unmapped event path in shared library"),
                     T("Contract test that unclassified emit is impossible")]),
                  S("Removing a signal type requires a new schema_version and an ADR", TAX,
                    "FR-1.3. Repurposing a key is a breaking change.",
                    "docs/ describes the bump procedure with a worked example.",
                    [T("Schema version bump procedure")]),
              ]),
            F("Authority decision contract", AUTH,
              "Bounded permission. Capture mode names the approver. Jurisdiction follows the subject. Unbounded grants are invalid.",
              "Schema requires expires_at; capture_mode and approver.role enums match persisted policy values.",
              implements=["ADR-0004"],
              stories=[
                  S("A decision without expiry cannot be issued", AUTH,
                    "ADR-0004. expires_at is required, including on denials, so caches always have a bound.",
                    "JSON Schema validation fails when expires_at is absent.",
                    [T("Require expires_at in authority-decision.schema.json", "closed"),
                     T("Control plane deny path always stamps expires_at")]),
                  S("Persisted capture modes match the contract enums", AUTH,
                    "Uppercase seed values would fail runtime validation and block the gate.",
                    "Seed data and schema both use passive_metadata and friends.",
                    [T("Align SQL seed capture_mode with schema", "closed")]),
                  S("Persisted approver roles match the contract enums", AUTH,
                    "Approver mapping is the gate. Case mismatch is a silent deny-all or deny-none.",
                    "Seed approvals use subject, employer, works_council.",
                    [T("Align SQL seed approver with schema", "closed")]),
              ]),
            F("Payload reference contract", BLOB,
              "Bulk never rides the bus. Write bytes first, publish the reference second.",
              "blob-reference.schema.json is complete; envelope payload_ref $ref resolves.",
              implements=["ADR-0006"],
              stories=[
                  S("A record carries a reference, never the bytes", BLOB,
                    "FR-5.2. Retention has one enforcement point.",
                    "Envelope with inline bytes fails schema validation.",
                    [T("Blob reference schema fields: uri, hash, media_type, bytes, retention, hold, key, estate"),
                     T("Envelope payload_ref uses the blob schema")]),
                  S("A reference to absent content cannot be published", BLOB,
                    "Orphans are recoverable; dangling refs are not.",
                    "Shared library refuses to attach payload_ref before the write ack.",
                    [T("Adapter blob helper writes then returns the reference"),
                     T("Test: no payload_ref if write fails")]),
              ]),
            F("Adapter manifest contract", MAN,
              "Coverage is derived from manifests. An inaccurate manifest produces confidently wrong coverage.",
              "Manifest schema requires emits, capture_modes, delivery, identifier kinds; CI validates it.",
              implements=["ADR-0003"],
              stories=[
                  S("Integrator declares capability before shipping", MAN,
                    "FR-2.2. Coverage discovery reads this, not tribal knowledge.",
                    "A manifest missing capture_modes or emits fails validate.",
                    [T("Manifest required fields and enums"),
                     T("directory_watch manifest validates")]),
                  S("Identifier kinds on the manifest drive subject resolution", MAN,
                    "The control plane must not guess which identifiers an adapter will send.",
                    "Coverage for a subject includes only adapters whose identifier kinds can bind.",
                    [T("identifier_kinds on manifest schema"),
                     T("Registry rejects a manifest with empty identifier_kinds")]),
              ]),
            F("Generated contract models for portals", "Portals/README.md",
              "Types are generated from Contracts/schemas so a contract change is a compile error, not a runtime surprise.",
              "Fresh clone of admin-portal and client-portal builds without a codegen step; generated output is committed.",
              stories=[
                  S("Portal compile fails when the envelope schema changes incompatibly", "Portals/README.md",
                    "Shared library owns generation. Hand-written TS models are prohibited.",
                    "Changing a required envelope field breaks portal CI.",
                    [T("Codegen from JSON Schema into Portals/shared"),
                     T("Commit generated models"),
                     T("CI check that generated output is not stale")]),
              ]),
        ],
    ),
    E(
        "Collection authority",
        AUTH,
        "Deny by default. Mode determines the approver. Jurisdiction follows the subject. Every grant is bounded. Every denial is actionable.",
        "subject-0002 in DE is denied continuous_screen with a reason naming the jurisdiction; subject-0001 in US-NC is granted with expires_at.",
        priority=0, labels=["control-plane", "java", "governance"], phase=2,
        features=[
            F("Persisted jurisdictional policy", "DevOps/Local/Postgres/init/01-schema.sql",
              "Policy lives in the store, not in code. JDBC repository is tenant-scoped; a query without tenant does not compile.",
              "Integration test seeds both demo subjects and asserts grant and denial against a real database.",
              implements=["ADR-0004"],
              stories=[
                  S("Administrator's grant is evaluated against stored policy, not a stub", PRD,
                    "UC3 / FR-4.1. E2.F1.T2 of the old plan: JDBC PolicyRepository.",
                    "AuthorityGate.evaluate reads jurisdiction_policy, subject, and approval tables.",
                    [T("JDBC PolicyRepository implementation"),
                     T("Tenant predicate required on every query"),
                     T("Integration test against local Postgres seed")]),
                  S("Policy version on the decision is the version that was applied", AUTH,
                    "FR-4.2, NFR-4.4. Retroactive policy change does not rewrite history.",
                    "Granted decision.policy_version equals jurisdiction_policy.policy_version at evaluation time.",
                    [T("Stamp policy_version from the row used"),
                     T("Changing policy does not alter previously issued decision rows")]),
              ]),
            F("Capture mode and subject jurisdiction", AUTH,
              "Approver is a function of mode and optional jurisdiction override. Tenant HQ is irrelevant.",
              "DE subject cannot use a US-NC employer grant; works_council override is honoured.",
              implements=["ADR-0004"],
              stories=[
                  S("Investigator in DE is not captured at continuous_screen without works-council approval", PRD,
                    "UC3. Governing rule follows the subject.",
                    "evaluate(tenant-demo, subject-0002, continuous_screen) returns granted=false and names DE.",
                    [T("Load subject.jurisdiction, not tenant country"),
                     T("Denial reason includes jurisdiction and mode")]),
                  S("Works-council override replaces the mode default approver", AUTH,
                    "DE permitted_modes is passive_metadata only; approver_override is works_council.",
                    "Approval from employer is ignored when override is works_council.",
                    [T("JurisdictionPolicy.approverFor uses override when set"),
                     T("Test: employer approval does not satisfy DE override")]),
              ]),
            F("Bounded grant", AUTH,
              "Every granted decision has expires_at. max_lifetime_seconds on the policy is the bound.",
              "No granted decision lacks expiry. Cache lifetime cannot exceed the decision.",
              implements=["ADR-0004"],
              stories=[
                  S("Administrator receives a time-bounded grant for a permitted mode", PRD,
                    "FR-4.5. US-NC subject-0001 passive_metadata with employer approval.",
                    "granted=true and expires_at = evaluated_at + max_lifetime_seconds.",
                    [T("Compute expires_at from policy max_lifetime_seconds"),
                     T("Reject granted && expires_at == null in AuthorityDecision constructor")]),
                  S("Adapter stops emitting when the cached grant expires", "Middleware/adapters/common/authority.py",
                    "NFR-1.1 converse: in-flight collection continues only while the decision is unexpired.",
                    "After expiry, the next build() raises and no envelope is produced.",
                    [T("Adapter session cache stores expires_at"),
                     T("is_expired fail-closed when expires_at missing")]),
              ]),
            F("Actionable denial", AUTH,
              "A denial nobody can explain is indistinguishable from a bug and gets worked around.",
              "Every denial has denial_reason an administrator can act on; HTTP 200 with granted=false.",
              implements=["ADR-0004"],
              stories=[
                  S("Administrator can act on a denial without reading source code", PRD,
                    "FR-4.6. Reasons name missing approval, missing jurisdiction, or mode not permitted.",
                    "Each deny branch in AuthorityGate has a distinct reason string covering the cause.",
                    [T("Denial for unresolved jurisdiction"),
                     T("Denial for no policy on file"),
                     T("Denial for no approval on record")]),
                  S("Caller does not retry a denial as if it were a 5xx", "Middleware/control-plane/src/main/java/io/signalplane/controlplane/authority/AuthorityController.java",
                    "A denial is a well-formed answer.",
                    "POST /v1/authority/decisions returns 200 and granted=false.",
                    [T("Controller returns 200 for denials"),
                     T("Adapter raises AuthorityDenied and does not retry")]),
              ]),
            F("Decision constraints", AUTH,
              "Schedule windows, excluded categories, excluded destinations, redaction profile travel with the grant.",
              "A grant outside a window is unusable; excluded destinations are never captured.",
              implements=["ADR-0004"],
              stories=[
                  S("Collection is closed outside the permitted schedule window", PRD,
                    "FR-4.7, UC4. Session termination is rule driven.",
                    "A decision with weekday windows refuses emit on Sunday.",
                    [T("Stamp schedule_windows from policy onto the decision"),
                     T("Adapter refuses emit outside the window")]),
                  S("Banking and health destinations are never captured regardless of tenant config", AUTH,
                    "FR-4.12. Jurisdictional never-collect list.",
                    "Payload or metadata destined to *.bank.example is dropped even with a grant.",
                    [T("Stamp excluded_destinations from jurisdiction_policy"),
                     T("Adapter filters excluded destinations before build")]),
              ]),
            F("Revocation within the decision lifetime", AUTH,
              "Withdrawal takes effect within the cached TTL. Shortening TTL increases control-plane load. This is a designed bound.",
              "Revoking approval stops capture within max_lifetime_seconds.",
              implements=["ADR-0004"],
              stories=[
                  S("Works council withdraws approval and capture stops before the next TTL", PRD,
                    "FR-4.10. Adapters do not refresh a revoked decision.",
                    "After approval row is deleted, a new evaluate returns denied; in-flight session dies at expiry.",
                    [T("Delete approval invalidates new evaluates immediately"),
                     T("Document revocation latency as the decision lifetime")]),
              ]),
            F("Decision audit trail", AUTH,
              "Every decision, granted or denied, is persisted with its inputs.",
              "A decision_id resolves to policy version, approver, inputs, and outcome.",
              implements=["ADR-0004"],
              stories=[
                  S("Compliance owner traces a stored record to the decision that permitted it", PRD,
                    "UC6, FR-4.8, FR-4.11.",
                    "GET /v1/authority/decisions/{id} returns the full decision including inputs.",
                    [T("Persist every evaluate result"),
                     T("Lookup API by decision_id")]),
              ]),
        ],
    ),
    E(
        "Subject identity",
        ENV,
        "Raw identifiers resolve to a canonical subject with confidence. Ambiguity resolves to no subject. Correction is auditable and retroactive. Erasure spans estates.",
        "Conflicting claims produce unresolved + diagnostic, never a silent merge. SAR retrieve and erase work across managed and self-hosted estates subject to hold.",
        priority=0, labels=["control-plane", "java", "governance"], phase=2,
        features=[
            F("Identifier to canonical subject", ENV,
              "UPN, email, device id, account SID, employee number are claims, not the subject.",
              "A known mapping returns subject_id and confidence; unknown returns unresolved, not a new person guessed from email.",
              stories=[
                  S("Investigator's query by email finds the same subject as a query by device id", PRD,
                    "UC2, FR-3.1.",
                    "Two identifier kinds for subject-0001 resolve to the same subject_id.",
                    [T("subject_identifier table lookup"),
                     T("Confidence scored mapping API")]),
                  S("Ambiguous claims do not invent a person", PRD,
                    "FR-3.2, AR-08. Silent merge is the identity failure that matters.",
                    "Email mapped to two subject_ids returns unresolved and a diagnostic event.",
                    [T("Conflict detection across identifier rows"),
                     T("Diagnostic on unresolved, no subject_id issued")]),
              ]),
            F("Auditable correction", PRD,
              "Mappings are correctable. Correction reapplies across stored records.",
              "An administrator can split a merged identity; subsequent reads use the corrected subject.",
              stories=[
                  S("Administrator splits a wrong merge and history follows", PRD,
                    "FR-3.3.",
                    "After correction, records previously under subject A for identifier X appear under subject B.",
                    [T("Correction ledger with actor and reason"),
                     T("Reindex affected signal_id subject pointers")]),
              ]),
            F("Subject access and erasure", PRD,
              "Retrievable and deletable by canonical subject across sources and estates, hold taking precedence.",
              "SAR export contains all estates; erase is refused while held and completes when hold lifts.",
              stories=[
                  S("Subject receives everything the platform holds about them", PRD,
                    "NFR-4.2, FR-3.4.",
                    "Export job returns index rows and payload refs for one subject_id from every estate.",
                    [T("SAR export job across federated read"),
                     T("Include authority provenance in the export")]),
                  S("Subject erasure is refused while a legal hold applies", PRD,
                    "Hold is storage-layer enforcement.",
                    "DELETE subject is 409 while hold is on; after hold release, index and blobs are gone.",
                    [T("Hold check before erase"),
                     T("Erase across index, blobs, and identifier maps")]),
              ]),
        ],
    ),
    E(
        "Sessions and coverage",
        "docs/architecture.md",
        "Coverage is derived from registered manifests. Sessions terminate on a rule: schedule, expiry, retention, or case closure. Explicit close is the exception.",
        "Coverage for a subject lists adapters, fidelity, and modes. A session outside its window is closed without an operator.",
        priority=0, labels=["control-plane", "java"], phase=2,
        features=[
            F("Adapter registry", MAN,
              "Registration is how coverage becomes a derived answer.",
              "Registered manifests are queryable by adapter_id and version; seed.py is idempotent.",
              implements=["ADR-0003"],
              stories=[
                  S("Integrator registers a manifest and it becomes visible to coverage", PRD,
                    "FR-2.3.",
                    "POST /v1/adapters then GET coverage includes the new adapter.",
                    [T("Adapter registration API and store"),
                     T("Idempotent upsert on adapter_id+version")]),
              ]),
            F("Coverage discovery", PRD,
              "Which sources can observe this subject, at what fidelity, under which modes — from manifests, not tribal knowledge.",
              "Given an identifier, coverage lists adapters whose identifier_kinds and capture_modes apply.",
              stories=[
                  S("Administrator sees which sources can observe a subject before opening a session", PRD,
                    "UC2.",
                    "GET /v1/subjects/{id}/coverage names adapters, fidelity, and modes; ambiguity returns 409 with diagnostic.",
                    [T("Coverage endpoint from registry + identity"),
                     T("Ambiguous identifier does not guess coverage")]),
              ]),
            F("Rule-driven session lifecycle", PRD,
              "UC4. Sessions die on schedule boundary, decision expiry, retention clock, or case closure.",
              "A session past expiry is closed; explicit termination exists and is logged as exceptional.",
              implements=["ADR-0005"],
              stories=[
                  S("Collection stops at the schedule window without an operator", PRD,
                    "FR-4.7, UC4.",
                    "Clock past window.end closes the session and adapters fail closed.",
                    [T("Session record with window and decision_id"),
                     T("Terminator loop on schedule and expiry")]),
                  S("Administrator can explicitly close a session", PRD,
                    "Exception path, auditable.",
                    "POST close records actor and reason; subsequent emit is refused.",
                    [T("Explicit close API"),
                     T("Audit actor on explicit close")]),
                  S("Case closure terminates every session on that case", PRD,
                    "UC4 case closure rule.",
                    "Closing a case closes child sessions within the terminator interval.",
                    [T("Session to case foreign key"),
                     T("Cascade close on case closure")]),
              ]),
        ],
    ),
    E(
        "Adapter paved road",
        "docs/adr/0003-adapter-per-source-not-shared-ingest.md",
        "The Nth source is a mapping exercise. The paved road is map, declare, resolve identity, build via the shared library, prove fail closed, register.",
        "Adding an adapter changes no existing adapter, consumer, or shared runtime. Adapter change ratio is zero.",
        priority=0, labels=["adapters", "python"], phase=2,
        features=[
            F("Shared library is the only emit path", "Middleware/adapters/common/envelope.py",
              "Record construction, identity, integrity, authority live here. Adapter N+1 cannot drift.",
              "No public constructor for envelopes outside AdapterContext.build.",
              implements=["ADR-0002", "ADR-0003"],
              stories=[
                  S("Integrator cannot ship an adapter that bypasses authority", PRD,
                    "AR-01. No override path.",
                    "Grep/CI fails if an adapter imports json and writes an envelope by hand.",
                    [T("Lint: adapters must call AdapterContext.build"),
                     T("CI grep for hand-rolled schema_version keys")]),
              ]),
            F("Paved-road formula", ".beads/formulas",
              "add-adapter formula: map vocabulary, declare capability, identity, implement, fail-closed test, register, review.",
              "Pouring add-adapter for a named source produces the molecule; departing from it requires ARB.",
              implements=["ADR-0003"],
              stories=[
                  S("Integrator adds a source without a bespoke checklist", TSA,
                    "§13.3. Conformant path is the fastest path.",
                    "bd mol pour add-adapter --var adapter_id=... creates the task graph.",
                    [T("add-adapter formula covers the paved sequence"),
                     T("Worked example for a second source")]),
              ]),
            F("Isolation and failure channel", "DevOps/Cloud/cdk/lib/ingest-stack.ts",
              "Saturation in one adapter must not move another adapter's error rate. Each has a DLQ and redrive.",
              "Load on adapter A does not raise errors on adapter B. Redrive is operator initiated.",
              implements=["ADR-0003"],
              stories=[
                  S("A saturated source does not degrade any other source", PRD,
                    "FR-2.4, NFR-1.2, NFR-2.3.",
                    "Chaos test: throttle A, B's error rate and latency stay within baseline.",
                    [T("Per source concurrency limits"),
                     T("Cross-adapter interference metric")]),
                  S("Operator redrives records that could not be processed", PRD,
                    "FR-2.5. Diverted volume is a quality signal.",
                    "DLQ for adapter A is isolated; redrive republishes valid records only.",
                    [T("Per adapter DLQ"),
                     T("Redrive API scoped to one adapter")]),
              ]),
            F("Absence detection", TSA,
              "A source that stops emitting looks like a subject who did nothing. AR-11.",
              "Alert when volume is below the declared minimum interval multiple.",
              stories=[
                  S("Reliability engineer is told when a source goes silent", TSA,
                    "NFR observability. Silent failures rate above loud ones.",
                    "No events from directory_watch for 3× min_interval pages an owner.",
                    [T("Per-adapter expected volume baseline"),
                     T("Absence alert from min_interval")]),
              ]),
        ],
    ),
    E(
        "Source adapters",
        "Middleware/adapters",
        "One adapter per source, independently deployed. The estate is a source, not a peer. directory_watch is the reference shape.",
        "Two adapters run concurrently without cross interference. Estate ingest is just another adapter.",
        priority=1, labels=["adapters", "python"], phase=3,
        status="deferred",
        features=[
            F("Reference directory watch adapter", "Middleware/adapters/sources/directory_watch",
              "Demonstrates the full shape: manifest, authority, envelope, optional blob, emit.",
              "Runs with or without a broker; output validates against the schema.",
              implements=["ADR-0003"],
              stories=[
                  S("Integrator can exercise an adapter with no infrastructure", "Docs/local-development.md",
                    "Stdout fallback when Kafka is absent.",
                    "handler.py emits valid envelopes to stdout in local mode.",
                    [T("Directory watch adapter", "closed"),
                     T("Kafka emission with stdout fallback", "closed")],
                    status="closed"),
              ]),
            F("Estate ingest adapter", "Middleware/adapters",
              "Self-hosted estate integrates through the same contract. Batches are idempotent on signal_id.",
              "Submitting the same batch twice stores one set of records. Auth is bearer, rate-limited per tenant.",
              implements=["ADR-0007"],
              stories=[
                  S("Edge shipper batch is absorbed on replay", PRD,
                    "FR-8.1, FR-8.4.",
                    "Two POSTs of the same signal_ids do not duplicate the index.",
                    [T("estate_ingest handler"),
                     T("Idempotency by signal_id")]),
                  S("Customer security function sees no inbound listener on the estate", PRD,
                    "FR-8.2. The ingest endpoint lives on the managed plane.",
                    "Estate opens outbound only; managed plane authenticates the tenant.",
                    [T("Bearer authentication"),
                     T("Per tenant rate limit")]),
              ]),
            F("Nth source on the paved road", PRD,
              "G1. Each new source is a poured formula, not a new architecture.",
              "Adapter change ratio remains zero when the third source ships.",
              stories=[
                  S("Platform integrator ships a third source without touching consumers", PRD,
                    "FR-2.6, NFR-6.1.",
                    "PR for source C changes only adapters/sources/C and optionally taxonomy.yaml.",
                    [T("Paved-road checklist as CI"),
                     T("Measure adapter change ratio in CI")]),
              ]),
        ],
    ),
    E(
        "Transport and quality",
        "Docs/architecture.md",
        "Records on an event stream partitioned so subject order is preserved. Invalid records divert, never silently drop or accept.",
        "Topic per category; partition key tenant|subject; diverted volume by adapter is a monitored quality signal.",
        priority=1, labels=["ingest"], phase=3, status="deferred",
        features=[
            F("Ordered record transport", PRD,
              "FR-5.1. Category topics so consumers subscribe to what concerns them.",
              "Two records for one subject keep order; different subjects may interleave.",
              implements=["ADR-0002"],
              stories=[
                  S("Investigator sees file_action events in occurrence order for one subject", PRD,
                    "Partitioning is a contract, not a tuning knob.",
                    "Produce two envelopes for subject-0001; consume in the same order.",
                    [T("Partition key tenant|subject_id"),
                     T("Category topic mapping")]),
              ]),
            F("Structural and vocabulary diversion", PRD,
              "Failing records go to an isolated channel per adapter. Diverted volume is quality, not just errors.",
              "A bad record never lands on the main topic and never disappears.",
              stories=[
                  S("A malformed record is inspectable, not lost", PRD,
                    "§8.3 data quality.",
                    "Invalid envelope appears on adapter A's divert topic with the validation error.",
                    [T("Validation consumer before index write"),
                     T("Per-adapter divert topic and metric")]),
              ]),
        ],
    ),
    E(
        "Persistence",
        TSA,
        "Index for retrieval by subject and time, tenant-first partitioned. Object store for bytes with retention lock and hold. Residency is topology. Keys may be customer held.",
        "Cross-tenant read is inexpressible. Hold refuses deletion at the store. Dangling reference count is zero.",
        priority=1, labels=["storage"], phase=3, status="deferred",
        features=[
            F("Blob write-then-publish", BLOB,
              "Bytes durable before reference publication. Sweeper reclaims orphans.",
              "Fault between write and publish leaves an orphan, never a dangling ref.",
              implements=["ADR-0006"],
              stories=[
                  S("A crash after S3 PUT and before Kafka produce is recoverable", PRD,
                    "FR-5.3, AR-10.",
                    "Injected fault leaves an unreferenced object; sweeper deletes or republishes it; no envelope points at missing bytes.",
                    [T("Enforce write then publish ordering"),
                     T("Orphan sweeper"),
                     T("Dangling-ref metric stays zero")]),
              ]),
            F("Retention and legal hold at the store", PRD,
              "FR-5.5, FR-5.6. Application-level refusal is one bug away from a lapse.",
              "Held object delete is refused by the store. Expiry is suspended while held.",
              implements=["ADR-0006"],
              stories=[
                  S("Compliance officer's hold survives a delete API call", PRD,
                    "AR-02. Verify by asserting refusal, not by reading a flag.",
                    "DeleteObject on a held key returns an error from the store.",
                    [T("Object lock on legal hold"),
                     T("Hold verification probe used at cutover")]),
                  S("Unheld content expires without an application job", PRD,
                    "Retention class on the blob reference is enforced by the bucket lifecycle.",
                    "After retention, the object is gone and the index row is gone.",
                    [T("Retention class → lifecycle mapping"),
                     T("Index expiry aligned to occurrence time")]),
              ]),
            F("Tenant-first index", PRD,
              "FR-6.5, P9. A filter can be omitted; a partition key cannot.",
              "Query type requires tenant_id; missing tenant does not compile or is a 400 before execution.",
              implements=["ADR-0008"],
              stories=[
                  S("An out-of-scope query cannot be expressed", PRD,
                    "Structural isolation.",
                    "Broker Estate.Query includes tenant in the key; tests omit it and fail to compile or 400.",
                    [T("Index partition tenant, subject, time"),
                     T("API rejects missing tenant_id")]),
              ]),
            F("Residency and customer keys", PRD,
              "FR-5.7, FR-5.8. Residency is a deployment property. CMK is Should, may trail GA.",
              "Records for a residency=eu tenant never land in us buckets.",
              stories=[
                  S("Administrator selects EU residency and data does not leave the region", PRD,
                    "NFR-4.1.",
                    "Topology test: eu tenant produce/consume stays on eu resources.",
                    [T("Per-tenant residency on tenant record"),
                     T("Stack routing by residency")]),
                  S("Tenant requiring key custody holds the encryption keys", PRD,
                    "Q2 in PRD. Should.",
                    "Envelope payload_ref.encryption_key_id is the customer CMK; platform cannot decrypt without it.",
                    [T("CMK envelope encryption path"),
                     T("Document deferral if not GA")]),
              ]),
        ],
    ),
    E(
        "Federated read",
        "Middleware/query-broker",
        "One read interface across estates. Fan-out with a deadline. Merge on signal_id. Partial results named. Reads themselves are audited.",
        "With one estate down, results return, labelled partial, naming the estate. Duplicates collapse. Read audit records who/what/when/case.",
        priority=1, labels=["read-path", "go"], phase=3, status="deferred",
        features=[
            F("Federation, merge, honest partials", "Middleware/query-broker",
              "Concurrent fan-out, deadline, merge on signal_id, managed plane wins ties.",
              "Duplicate merge and partial result behaviour are covered by tests.",
              implements=["ADR-0008"],
              stories=[
                  S("Investigator gets one row when both estates hold the same signal", PRD,
                    "FR-6.2, UC5.",
                    "Same signal_id from managed and self_hosted collapses to one result.",
                    [T("Broker fan out and merge", "closed"),
                     T("Managed plane wins ties", "closed")],
                    status="closed"),
                  S("Investigator can tell nothing happened from we could not see", PRD,
                    "FR-6.3, FR-6.4, AR-07.",
                    "When stub estate times out, response is 200, partial=true, estate named.",
                    [T("Partial result reporting", "closed"),
                     T("Deadline so a slow estate cannot stall")],
                    status="closed"),
              ]),
            F("Index-backed managed estate", "DevOps/Cloud/cdk/lib/core-stack.ts",
              "Replace StubEstate with the signal index.",
              "Broker tests pass unchanged against the real implementation.",
              implements=["ADR-0008"],
              stories=[
                  S("Investigator query hits the index, not a stub", PRD,
                    "FR-6.1.",
                    "Signals written from the bus are returned by the broker for the managed estate.",
                    [T("Signal index writer from the bus"),
                     T("Index backed Estate implementation"),
                     T("Tenant scoping enforced structurally")]),
              ]),
            F("Blob handles across estates", BLOB,
              "Bytes may remain self-hosted during migration. Broker mints time-bounded references, does not proxy bytes.",
              "resolvable_from=self_hosted returns a short-lived signed handle.",
              implements=["ADR-0006", "ADR-0008"],
              stories=[
                  S("Investigator opens a self-hosted screenshot without inbound access to the estate", PRD,
                    "FR-6.6.",
                    "Handle expires; the estate serves bytes outbound or via pre-signed local store.",
                    [T("Signed handle broker for estate resident blobs"),
                     T("Handle TTL and single-use option")]),
              ]),
            F("Read audit", PRD,
              "FR-6.7. In an evidentiary context the reading is as significant as the collecting.",
              "Every query stores actor, subject scope, time, case_id, estates contacted, partial flag.",
              stories=[
                  S("Compliance owner sees who read a subject's history", PRD,
                    "UC6 companion.",
                    "Read audit log for subject-0001 lists investigator, case, and timestamp.",
                    [T("Read audit record on every broker query"),
                     T("Query API for audit by subject and by actor")]),
              ]),
        ],
    ),
    E(
        "Scoring and tenant rules",
        "docs/adr/0009-pinned-scoring-model-version-per-tenant.md",
        "Derived values carry model_version. Version is pinned per tenant. Platform migration never coincides with a model change. Rules cannot be authored unbounded or against missing vocab.",
        "A tenant with model 1.4.0 never sees 1.5.0 scores until a separate upgrade with a comparison period.",
        priority=1, labels=["scoring"], phase=4, status="deferred",
        features=[
            F("Pinned model version", "docs/adr/0009-pinned-scoring-model-version-per-tenant.md",
              "Tenant.scoring_model_version is the pin. Derived.risk_score.model_version must match.",
              "Mixing migration and model upgrade is refused by policy.",
              implements=["ADR-0009"],
              stories=[
                  S("Migration operator cannot cut over and bump the model in one change", PRD,
                    "FR-7.2, FR-7.3, AR-05.",
                    "Cutover API rejects a request that also changes scoring_model_version.",
                    [T("Pin stored on tenant"),
                     T("Cutover refuses combined model change")]),
                  S("Investigator can tell a score from an observed fact", PRD,
                    "FR-7.7. derived.* vs observed types.",
                    "UI and API mark derived.risk_score as inferred; file_action.modify is observed.",
                    [T("Stamp model_version on derived attributes"),
                     T("Presentation flag derived vs observed")]),
              ]),
            F("Rule authoring validation", PRD,
              "FR-7.5, FR-7.6. Unbounded or unknown-vocab rules are rejected at authoring time.",
              "A rule against signal_type=made_up is 400. A rule with no bound is 400.",
              stories=[
                  S("Administrator cannot save a rule that refers to a retired signal type", PRD,
                    "Vocabulary is executable language.",
                    "PUT rule with unknown type fails with the missing key named.",
                    [T("Rule schema validates signal_type against taxonomy"),
                     T("Reject unbounded window or threshold")]),
              ]),
            F("Dual-run comparison before upgrade", PRD,
              "FR-7.4 Should. Both versions computed; divergence reported.",
              "Comparison report exists before pin moves.",
              implements=["ADR-0009"],
              stories=[
                  S("Product owner sees score divergence before promoting 1.5.0", PRD,
                    "Prevents the false-positive wave blamed on migration.",
                    "Report names percent of subjects whose band changed.",
                    [T("Shadow-run second model version"),
                     T("Divergence report")]),
              ]),
        ],
    ),
    E(
        "Outbound estate shipper",
        "Middleware/edge-shipper",
        "Deployed in the customer estate. Outbound only. Checkpoint advances only after ack. Health is self-reported on the same channel.",
        "Restart resumes from checkpoint; replay is absorbed; skip is impossible. No listening port.",
        priority=1, labels=["migration", "go"], phase=4, status="deferred",
        features=[
            F("Outbound checkpointed transmission", "Middleware/edge-shipper",
              "Position durable before a batch is complete. Ack then checkpoint. Replay on gap.",
              "Kill -9 after send and before checkpoint; restart resends; managed plane idempotency absorbs.",
              implements=["ADR-0007"],
              stories=[
                  S("Customer security function permits the component because it dials out only", PRD,
                    "FR-8.2. The gate that precedes technical merit.",
                    "Binary has no listen socket; tests assert no bind.",
                    [T("Outbound shipper with atomic checkpoint", "closed"),
                     T("No-listen assertion in tests")]),
                  S("An interrupted send never skips a record", PRD,
                    "FR-8.3, FR-8.4.",
                    "Fault injection: replay duplicates, zero gaps.",
                    [T("Checkpoint file format and fsync"),
                     T("Restart resumes from checkpoint")]),
              ]),
            F("Self-reported health", PRD,
              "FR-8.5. Cannot be probed inbound.",
              "Health frames on the outbound channel include last checkpoint and lag.",
              implements=["ADR-0007"],
              stories=[
                  S("Migration operator sees estate lag without opening a port", PRD,
                    "UC8 observability.",
                    "Managed plane displays last_seen and checkpoint age from self-reports.",
                    [T("Self reported health over the outbound channel"),
                     T("Lag metric from checkpoint age")]),
              ]),
        ],
    ),
    E(
        "Migration programme",
        TSA,
        "Assessment, compatibility, read-path first, collection switch, history, rollback, decommission. Tooling is the product. Cost per tenant and rollback rate are first-class metrics.",
        "A tenant is assessed, cut over, and rolled back without a bespoke runbook. Changed compatibility cannot cut over without recorded acknowledgement.",
        priority=1, labels=["migration"], phase=4, status="deferred",
        features=[
            F("Exposure-scored assessment", TSA,
              "UC7. Volume, retention, holds, investigations, jurisdiction spread, customisation depth.",
              "Assessment artefact exists per tenant and ranks exposure vs cost.",
              implements=["ADR-0008"],
              stories=[
                  S("Migration operator gets an assessment rather than a spreadsheet", PRD,
                    "§12.4 legacy exposure index.",
                    "POST assess returns the six dimensions and a recommended sequence.",
                    [T("Assessment job: volume, holds, jurisdictions, rules"),
                     T("Exposure score persisted on tenant")]),
                  S("Jurisdiction check happens before any other migration step", TSA,
                    "Discovering unlawfulness late invalidates the rest.",
                    "Assessment fails closed if managed plane may not hold the subject mix.",
                    [T("Jurisdiction distribution on the assessment"),
                     T("Block assessment pass when residency cannot host")]),
              ]),
            F("Rule and threshold compatibility report", "docs/adr/0009-pinned-scoring-model-version-per-tenant.md",
              "Classify every tenant rule as identical, changed, or dependent on a retired type. Changed requires acknowledgement.",
              "Report names each rule and class; cutover refuses changed without ack.",
              implements=["ADR-0009"],
              stories=[
                  S("Cutover is a reviewable decision, not an act of faith", PRD,
                    "FR-8.11, FR-8.12, UC7.",
                    "A tenant with one changed rule cannot enter cutover without an ack record.",
                    [T("Static analysis of tenant rules against the taxonomy"),
                     T("Threshold drift estimate under the pinned model"),
                     T("Report generation and cutover gate")]),
              ]),
            F("Read path first", TSA,
              "FR-8.6. Value before irreversibility. If the programme stops here the tenant is still better off.",
              "Tenant uses the managed interface while data remains in the estate.",
              implements=["ADR-0008"],
              stories=[
                  S("Investigator uses one UI while bytes still live in the estate", PRD,
                    "UC8 first step.",
                    "Federation returns estate data; no data copy has occurred; rollback is DNS/config.",
                    [T("Migration state: read_path_managed"),
                     T("Console pointed at broker only")]),
              ]),
            F("Collection switch", TSA,
              "FR-8.7. New collection to managed plane; estate stops growing. Reversible by redirect.",
              "After switch, new envelopes have estate=managed. Redirect restores estate=self_hosted.",
              stories=[
                  S("Administrator redirects new capture without moving history", PRD,
                    "Independently reversible.",
                    "State machine transition new_collection_managed is reversible within the window.",
                    [T("Collection target on tenant migration state"),
                     T("Adapters honour the target estate")]),
              ]),
            F("History: backfill or expire", TSA,
              "FR-8.8. Index and metadata first. Bytes backfill or age out. Cost of each presented.",
              "Recommendation names cheaper option; holds never age out.",
              implements=["ADR-0008"],
              stories=[
                  S("Migration operator chooses expire when retention is shorter than the programme", PRD,
                    "Most tenants. Bulk bytes have no cheap option.",
                    "Tool shows backfill $X vs expire $Y; holds listed as must-move.",
                    [T("Metadata and index backfill job"),
                     T("Backfill versus age out cost model"),
                     T("Legal hold carries across the boundary")]),
              ]),
            F("Cutover, rollback, decommission", "Docs/deployment.md",
              "FR-8.9–8.14, UC8–UC10. Persisted state machine. Rollback is a supported operation. Decommission needs human approval after the window.",
              "Rollback within window: no data loss, no hold lapse. Cost per tenant and rollback rate are emitted.",
              implements=["ADR-0008"],
              stories=[
                  S("Migration operator rolls back without opening an incident", PRD,
                    "UC9. Zero rollback rate would mean rollback is impractical.",
                    "POST rollback restores prior state; holds still refuse delete.",
                    [T("Per tenant cutover state machine"),
                     T("Rollback within window"),
                     T("Hold verification by delete-refusal after rollback")]),
                  S("Self-hosted deployment is retired only with explicit approval after the window", PRD,
                    "UC10.",
                    "Decommission is blocked until window elapsed and an approver is recorded.",
                    [T("Decommission gate and approver"),
                     T("Cost per tenant and rollback rate metrics")]),
              ]),
        ],
    ),
    E(
        "Admin portal",
        "Portals/admin-portal",
        "Administrators configure policy, scope, retention, adapters, sessions, and migration. Unsafe states are hard to express. Consequence of widening collection is shown.",
        "Admin can set policy and see the capture-mode consequence. Scope pickers only list held scope. Migration state is visible.",
        priority=2, labels=["ui", "angular"], phase=4, status="deferred",
        features=[
            F("Admin scaffold and contract client", "Portals/README.md",
              "Angular + proxy to control plane and broker. Shared generated models.",
              "ng serve reaches /v1/authority and /v1/adapters without CORS hacks.",
              stories=[
                  S("Administrator loads the portal against local middleware", "Portals/README.md",
                    "Local-first.",
                    "ng serve --proxy-config reaches control plane.",
                    [T("Angular admin scaffold and proxy config"),
                     T("Shared generated API client")]),
              ]),
            F("Policy administration with consequences", PRD,
              "FR-9.6. Widening collection is obvious.",
              "Toggling continuous_screen shows who must approve in each jurisdiction before save.",
              stories=[
                  S("Administrator sees who must approve before enabling a more intrusive mode", PRD,
                    "Unsafe states hard to express.",
                    "UI lists approver role per jurisdiction for the selected mode; save is blocked without required approvals existing.",
                    [T("Policy editor bound to jurisdiction_policy"),
                     T("Consequence panel: mode → approver → missing approvals")]),
              ]),
            F("Approvals, sessions, adapter registry", PRD,
              "Admin records approvals, opens/closes sessions, sees registered adapters.",
              "Cannot open a session the gate would deny; denial reason is shown in the UI.",
              stories=[
                  S("Administrator records a works-council approval with evidence", PRD,
                    "UC3 input.",
                    "Approval row has role, recorded_at, evidence_ref.",
                    [T("Approval form and API client"),
                     T("Evidence ref required for consent basis")]),
                  S("Administrator is shown the denial instead of a spinner", PRD,
                    "FR-4.6 in the UI.",
                    "Opening continuous_screen for DE subject renders the gate reason.",
                    [T("Session open form calls /v1/authority/decisions"),
                     T("Render denial_reason")]),
                  S("Administrator sees registered adapters and their declared modes", PRD,
                    "Coverage starts with the registry.",
                    "Adapter list shows capture_modes and emits from manifests.",
                    [T("Adapter registry view")]),
              ]),
            F("Migration state for operators", PRD,
              "UC7–UC10 in the admin UI.",
              "Tenant page shows state machine, assessment, compatibility class, cost so far.",
              stories=[
                  S("Migration operator drives cutover from the portal, not a runbook", PRD,
                    "Tooling is the product.",
                    "Each legal transition is a button; illegal ones are absent, not disabled-and-callable.",
                    [T("Tenant migration panel"),
                     T("Only legal state transitions offered")]),
              ]),
        ],
    ),
    E(
        "Client portal",
        "Portals/client-portal",
        "Investigators and compliance owners. Timelines, case views, provenance, export. Degradation is displayed. Scope is reflected, not enforced here.",
        "With one estate down the banner names it and counts are qualified. Timeline shows decision_id. Export is a documented format.",
        priority=2, labels=["ui", "angular"], phase=4, status="deferred",
        features=[
            F("Client scaffold", "Portals/README.md",
              "Same proxy and shared models as admin. Different audience, different obligations.",
              "ng serve reaches /v1/signals.",
              stories=[
                  S("Investigator loads the client portal against local broker", "Portals/README.md",
                    "Local-first.",
                    "Proxy /v1/signals → :8081.",
                    [T("Angular client scaffold and proxy config")]),
              ]),
            F("Honest partial results", "Portals/README.md",
              "Architectural, not cosmetic. Silent half-data is worse than an error.",
              "Estate status banner; qualified counts.",
              implements=["ADR-0008"],
              stories=[
                  S("Investigator sees which estate failed", PRD,
                    "FR-9.2, UC5.",
                    "Fixture with self_hosted timeout shows banner and '12 results, 1 estate unavailable'.",
                    [T("Estate status banner"),
                     T("Qualify counts when results are partial")]),
              ]),
            F("Case-bounded timeline with provenance", PRD,
              "UC5, FR-9.4. Every row traces to adapter and decision.",
              "Timeline for a case lists signals with adapter_id, decision_id, derived vs observed.",
              stories=[
                  S("Investigator reviews a subject across sources in one view", PRD,
                    "G2 cross-source questions.",
                    "Filter by subject; rows from two adapters interleave by occurred_at.",
                    [T("Signal timeline view"),
                     T("Case scope required on the query")]),
                  S("Compliance owner opens a record and sees the authority that permitted it", PRD,
                    "UC6.",
                    "Record drawer shows basis, approver role, jurisdiction, policy_version, expires_at.",
                    [T("Provenance drawer from decision_id"),
                     T("Link to hold and retention class")]),
              ]),
            F("Scope reflected from the data layer", PRD,
              "FR-9.3. The UI never offers a scope the caller does not hold.",
              "Scope dropdown is the intersection of token grants and data-layer partitions.",
              stories=[
                  S("Investigator cannot pick a team they do not belong to", PRD,
                    "Presentational scope is not a control.",
                    "Token without team X omits X from the picker; crafting X in the query 400s.",
                    [T("Scope aware filters"),
                     T("Do not render ungranted scopes")]),
              ]),
            F("Bulk export", PRD,
              "FR-9.5. Documented stable format.",
              "Export of a case is JSONL of envelopes plus an authority sidecar.",
              stories=[
                  S("Compliance owner exports a case in a stable format", PRD,
                    "N5: export to their tooling, do not compete with it.",
                    "Download matches the published export schema version.",
                    [T("Export job and format doc"),
                     T("Include estate status in the export manifest")]),
              ]),
        ],
    ),
    E(
        "Observability and SLOs",
        TSA,
        "Authority coverage, dangling refs, cross-adapter interference, volume baselines, cost per tenant, conformance score. Silent failures rate above loud ones.",
        "Dashboards exist for the standing architecture measures in TSA §16.3. Authority coverage below 100% pages.",
        priority=2, labels=["observability"], phase=4, status="deferred",
        features=[
            F("Architectural measures", TSA,
              "These detect failures nothing else surfaces.",
              "Metrics exported: authority_coverage, dangling_refs, interference_correlation, adapter_change_ratio.",
              stories=[
                  S("Platform lead is paged when authority coverage is not complete", TSA,
                    "AR-01 trigger.",
                    "A record without decision_id increments a counter and fires.",
                    [T("Authority coverage metric from index"),
                     T("Alert below 100 percent")]),
                  S("Platform lead is paged when a dangling blob reference exists", TSA,
                    "AR-10 / quality.",
                    "Any count > 0 is an incident class evidentiary loss.",
                    [T("Dangling ref checker"),
                     T("Alert on count > 0")]),
                  S("Platform lead sees whether isolation has failed", TSA,
                    "Cross adapter interference correlation.",
                    "Dashboard of error-rate correlation across adapters; any persistent correlation is a defect.",
                    [T("Per-adapter error and latency series"),
                     T("Correlation measure")]),
              ]),
            F("Service levels and incident classes", TSA,
              "§13.4–13.5. Governance breach vs evidentiary loss vs silent degradation vs availability vs quality.",
              "Runbook maps each class to the designed failure behaviour.",
              stories=[
                  S("On-call treats a silent source as severe despite no red dashboard", TSA,
                    "A down component is known; a quiet source looks like innocence.",
                    "Page class Silent degradation is documented and tested.",
                    [T("SLO docs per component"),
                     T("Incident class runbooks")]),
              ]),
        ],
    ),
    E(
        "Deploy and local-first",
        "docs/adr/0010-local-first-development-cdk-for-cloud.md",
        "Full path locally against protocol substitutes. Cloud is small separable CDK stacks, manual dispatch, destroy as a first-class operation. Known divergences are smoked before release.",
        "A stage is brought up, smoked, and destroyed from the workflow alone. Local green is not claimed as cloud green.",
        priority=2, labels=["infra", "cdk"], phase=4, status="deferred",
        features=[
            F("Local protocol substitutes", "Docs/local-development.md",
              "Redpanda, MinIO, Postgres, no vendor SDK feature without a local equivalent.",
              "make up && make test exercises the path without AWS.",
              implements=["ADR-0010"],
              stories=[
                  S("Contributor runs the path without a cloud account", PRD,
                    "NFR-5.1. Unexercised architecture decays.",
                    "Documented make up brings bus, store, policy DB, and one adapter.",
                    [T("Compose files for Kafka, MinIO, Postgres, Redis"),
                     T("Local development doc matches make targets")]),
              ]),
            F("Separable cloud stacks", "DevOps/Cloud/cdk",
              "Core, Ingest, ControlPlane. Destroying control plane loses no data. Ingest redeploy does not touch Core.",
              "Independent destroy verified per stack.",
              implements=["ADR-0005", "ADR-0010"],
              stories=[
                  S("Platform engineer destroys ControlPlane and data remains", PRD,
                    "NFR-5.2, NFR-5.4.",
                    "After destroy, index and objects still queryable.",
                    [T("First deploy of the dev stage"),
                     T("OIDC deploy role and least privilege policy"),
                     T("Independent destroy verified per stack")]),
              ]),
            F("Cloud divergence smoke", "Docs/local-development.md",
              "IAM, MSK auth, partition skew, object lock, cold starts.",
              "Smoke path exercises all five before any release.",
              implements=["ADR-0010"],
              stories=[
                  S("A release cannot ship on local green alone", PRD,
                    "NFR-5.3, AR-12.",
                    "Pipeline requires the five-divergence smoke.",
                    [T("Smoke test covering the known divergences"),
                     T("Cost guardrail alarm on the dev stage")]),
              ]),
        ],
    ),
    E(
        "Platform governance",
        TSA,
        "Policy as code for mechanically checkable rules. Exceptions are owned, time-bounded, and expire. Decision records cover structural change. Paved road is faster than review.",
        "Pipeline blocks unknown signal types, missing authority, missing spec on planned work, and cyclic deps. Exception count and age are reported.",
        priority=2, labels=["governance"], phase=4, status="deferred",
        features=[
            F("Policy as code in CI", TSA,
              "§14.3. The mechanically checked policies are the ones that hold.",
              "make validate and bd lint/bd dep cycles are required checks.",
              stories=[
                  S("A PR that emits an unknown signal type cannot merge", TSA,
                    "AR-04.",
                    "CI job validate.py is required and blocking.",
                    [T("Required status check for make validate"),
                     T("Required bd lint and bd dep cycles")]),
                  S("A planned bead without acceptance cannot merge", TSA,
                    "Plan validation, blocking.",
                    "bd lint fails the PR.",
                    [T("CI bd lint"),
                     T("CI beads-sync --prune drift check")]),
              ]),
            F("Exceptions and decision coverage", TSA,
              "Exception without expiry is a change to the standard and must be processed as one. AR-13.",
              "Structural PRs reference an ADR; exceptions have owner and expiry.",
              stories=[
                  S("An architecture exception expires or becomes a standard", TSA,
                    "§14.4.",
                    "Exception register lists owner, compensating control, expiry; CI warns on overdue.",
                    [T("Exception record schema"),
                     T("Overdue exception report")]),
              ]),
        ],
    ),
    E(
        "Tenant lifecycle",
        PRD,
        "Tenant carries residency, pinned model, estate assignment, retention, migration state. Onboarding does not collect anything until policy and approvals exist.",
        "A new tenant cannot open a session until jurisdiction policy and at least the required approver records exist.",
        priority=2, labels=["control-plane"], phase=4, status="deferred",
        features=[
            F("Tenant onboarding", PRD,
              "Create tenant, pin model, select residency, assign estate, set retention classes. Fail closed until policy exists.",
              "POST /v1/tenants succeeds; first authority evaluate fails closed until policy rows exist.",
              stories=[
                  S("Administrator onboards a tenant without enabling capture by accident", PRD,
                    "Anti-goal: do not make unauthorised collection easy.",
                    "New tenant has no permitted_modes until policy is attached.",
                    [T("Tenant record: residency, model pin, estate, retention"),
                     T("Evaluate fail-closed with no policy")]),
                  S("Scoring model pin is set at onboard and not silently defaulted later", PRD,
                    "FR-7.2.",
                    "Missing pin is 400 on tenant create.",
                    [T("Require scoring_model_version on create"),
                     T("Pin visible on tenant GET")]),
              ]),
            F("Retention and hold configuration", PRD,
              "Retention classes per tenant. Hold is per record/case, not a tenant-wide mute.",
              "Admin can set default class; hold is applied to records and verified at the store.",
              stories=[
                  S("Administrator sets a retention class without being able to disable hold", PRD,
                    "Hold takes precedence.",
                    "UI has no control that turns off store-level hold enforcement.",
                    [T("Retention class on tenant"),
                     T("Hold API cannot be overridden by retention settings")]),
              ]),
        ],
    ),
]


DEPENDENCIES = [
    # Authority before estate ingest and sessions
    {"blocked": "E6.F2", "blocker": "E2.F1"},
    {"blocked": "E4.F3", "blocker": "E2.F1"},
    {"blocked": "E4.F2", "blocker": "E5.F1"},
    # Blobs need envelope
    {"blocked": "E8.F1", "blocker": "E1.F4"},
    # Index needs signals
    {"blocked": "E9.F2", "blocker": "E6.F1"},
    # Blob handles need write ordering
    {"blocked": "E9.F3", "blocker": "E8.F1"},
    # Compatibility needs vocabulary
    {"blocked": "E12.F2", "blocker": "E1.F2"},
    # Backfill needs index
    {"blocked": "E12.F5", "blocker": "E9.F2"},
    # Cutover needs compatibility and history decision
    {"blocked": "E12.F6", "blocker": "E12.F2"},
    {"blocked": "E12.F6", "blocker": "E12.F5"},
    # Portals need federation and identity
    {"blocked": "E14.F2", "blocker": "E9.F1"},
    {"blocked": "E14.F3", "blocker": "E2.F7"},
    {"blocked": "E13.F2", "blocker": "E2.F1"},
    {"blocked": "E14.F4", "blocker": "E3.F1"},
    # Cloud smoke after stacks
    {"blocked": "E16.F3", "blocker": "E16.F2"},
    # Scoring cutover coupling
    {"blocked": "E10.F1", "blocker": "E18.F1"},
    # Shipper before estate ingest
    {"blocked": "E6.F2", "blocker": "E11.F1"},
]


DECISIONS = [
    ("ADR-0002", "One normalized envelope is the integration contract", "docs/adr/0002-normalized-envelope-as-integration-contract.md"),
    ("ADR-0003", "One adapter per source", "docs/adr/0003-adapter-per-source-not-shared-ingest.md"),
    ("ADR-0004", "Authority gate precedes capture", "docs/adr/0004-authority-gate-precedes-capture.md"),
    ("ADR-0005", "Control plane stays off the telemetry hot path", "docs/adr/0005-control-plane-off-the-telemetry-hot-path.md"),
    ("ADR-0006", "Large payloads travel by reference", "docs/adr/0006-blobs-by-reference-never-on-the-bus.md"),
    ("ADR-0007", "Self hosted estate ships outbound only", "docs/adr/0007-outbound-only-edge-shipper.md"),
    ("ADR-0008", "Federated read path, no cutover", "docs/adr/0008-federated-read-path-during-migration.md"),
    ("ADR-0009", "Scoring model version pinned per tenant", "docs/adr/0009-pinned-scoring-model-version-per-tenant.md"),
    ("ADR-0010", "Local first development, CDK only for cloud", "docs/adr/0010-local-first-development-cdk-for-cloud.md"),
]


def assign_keys(epics: list[dict]) -> None:
    for ei, epic in enumerate(epics, 1):
        epic["key"] = f"E{ei}"
        for fi, feat in enumerate(epic["features"], 1):
            feat["key"] = f"E{ei}.F{fi}"
            for si, story in enumerate(feat["stories"], 1):
                story["key"] = f"E{ei}.F{fi}.S{si}"
                for ti, task in enumerate(story["tasks"], 1):
                    task["key"] = f"E{ei}.F{fi}.S{si}.T{ti}"
        if epic.get("status") == "deferred":
            _inherit_deferred(epic)


def _inherit_deferred(epic: dict) -> None:
    for feat in epic["features"]:
        if feat.get("status") not in ("closed", "deferred"):
            feat["status"] = "deferred"
        for story in feat["stories"]:
            if story.get("status") not in ("closed", "deferred"):
                story["status"] = "deferred"
            for task in story["tasks"]:
                if task.get("status") not in ("closed", "deferred"):
                    task["status"] = "deferred"


def _fold(text: str, indent: str) -> str:
    return f"{indent}{text}"


def emit_item(lines: list[str], item: dict, indent: str, extra: tuple[str, ...] = ()) -> None:
    lines.append(f"{indent}- key: {item['key']}")
    lines.append(f"{indent}  title: {yaml_str(item['title'])}")
    if item.get("status"):
        lines.append(f"{indent}  status: {item['status']}")
    if item.get("priority") is not None and extra:
        pass
    for k in extra:
        if k == "priority" and "priority" in item:
            lines.append(f"{indent}  priority: {item['priority']}")
        elif k == "phase" and "phase" in item:
            lines.append(f"{indent}  phase: {item['phase']}")
        elif k == "labels" and item.get("labels"):
            lines.append(f"{indent}  labels: [{', '.join(item['labels'])}]")
        elif k == "implements" and item.get("implements"):
            lines.append(f"{indent}  implements: [{', '.join(item['implements'])}]")
    if item.get("spec"):
        lines.append(f"{indent}  spec: {yaml_str(item['spec'])}")
    if item.get("design"):
        lines.append(f"{indent}  design: {yaml_str(item['design'])}")
    if item.get("acceptance"):
        lines.append(f"{indent}  acceptance: {yaml_str(item['acceptance'])}")


def yaml_str(value: str) -> str:
    if any(c in value for c in ":#{}[],&*?|>!%@`'\"\n"):
        return json_dumps(value)
    return value


def json_dumps(value: str) -> str:
    import json
    return json.dumps(value)


def render() -> str:
    assign_keys(EPICS)
    lines: list[str] = []
    lines.append(dedent("""\
        # Specification driven backlog. Plan format v2.
        #
        # This file is the source of truth for what gets built. Tools/beads-sync.py
        # projects it into the beads graph; it never reads back from beads.
        #
        # Levels: epic -> feature -> story -> task.
        # story is a built-in beads type (persona + outcome).
        # feature is a shippable capability. task is one sitting of work.
        #
        # Every epic, feature, and story carries spec, design, and acceptance.
        # Phase 1–2 items are the open frontier. Phase 3–4 items are deferred
        # so bd ready stays a real queue.
        #
        # key is stable. Do not renumber. Retire with status: retired.
        # v1 keys E2–E7 (control-plane-shaped engineering spine) were closed as
        # superseded by this product map; ADR-* keys are unchanged.

        prefix: sp
        """).rstrip())
    lines.append("")
    lines.append("decisions:")
    for key, title, spec in DECISIONS:
        lines.append(f"  - key: {key}")
        lines.append(f"    title: {yaml_str(title)}")
        lines.append(f"    spec: {spec}")
        lines.append("    status: closed")
    lines.append("")
    lines.append("epics:")
    lines.append("")
    for epic in EPICS:
        lines.append(f"  - key: {epic['key']}")
        lines.append(f"    title: {yaml_str(epic['title'])}")
        lines.append(f"    priority: {epic['priority']}")
        lines.append(f"    phase: {epic['phase']}")
        if epic.get("status"):
            lines.append(f"    status: {epic['status']}")
        if epic.get("labels"):
            lines.append(f"    labels: [{', '.join(epic['labels'])}]")
        lines.append(f"    spec: {yaml_str(epic['spec'])}")
        lines.append(f"    design: {yaml_str(epic['design'])}")
        lines.append(f"    acceptance: {yaml_str(epic['acceptance'])}")
        lines.append("    features:")
        for feat in epic["features"]:
            lines.append(f"      - key: {feat['key']}")
            lines.append(f"        title: {yaml_str(feat['title'])}")
            if feat.get("status"):
                lines.append(f"        status: {feat['status']}")
            if feat.get("implements"):
                lines.append(f"        implements: [{', '.join(feat['implements'])}]")
            lines.append(f"        spec: {yaml_str(feat['spec'])}")
            lines.append(f"        design: {yaml_str(feat['design'])}")
            lines.append(f"        acceptance: {yaml_str(feat['acceptance'])}")
            lines.append("        stories:")
            for story in feat["stories"]:
                lines.append(f"          - key: {story['key']}")
                lines.append(f"            title: {yaml_str(story['title'])}")
                if story.get("status"):
                    lines.append(f"            status: {story['status']}")
                lines.append(f"            spec: {yaml_str(story['spec'])}")
                lines.append(f"            design: {yaml_str(story['design'])}")
                lines.append(f"            acceptance: {yaml_str(story['acceptance'])}")
                lines.append("            tasks:")
                for task in story["tasks"]:
                    status = f", status: {task['status']}" if task.get("status") else ""
                    lines.append(
                        f"              - {{ key: {task['key']}, title: {yaml_str(task['title'])}{status} }}"
                    )
        lines.append("")
    lines.append("# Cross cutting ordering. Tasks within a story are sequential.")
    lines.append("# Stories in a feature are parallel. These edges are extra.")
    lines.append("dependencies:")
    for edge in DEPENDENCIES:
        lines.append(f"  - {{ blocked: {edge['blocked']}, blocker: {edge['blocker']} }}")
    lines.append("")

    n_e = len(EPICS)
    n_f = sum(len(e["features"]) for e in EPICS)
    n_s = sum(len(f["stories"]) for e in EPICS for f in e["features"])
    n_t = sum(len(s["tasks"]) for e in EPICS for f in e["features"] for s in f["stories"])
    lines.append(f"# counts: epics={n_e} features={n_f} stories={n_s} tasks={n_t} "
                 f"total_work={n_e + n_f + n_s + n_t + len(DECISIONS)}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    text = render()
    OUT.write_text(text)
    print(f"wrote {OUT} ({len(text.splitlines())} lines)")
    print(text.splitlines()[-2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
