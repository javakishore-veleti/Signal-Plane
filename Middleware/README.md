# Middleware

All backend services, grouped by role rather than by language. Languages differ
because the components have genuinely different profiles; they communicate only
through the contracts in `Contracts/`, never through shared code.

| Path | Role | Language | Why this language |
|---|---|---|---|
| `control-plane/` | Identity resolution, authority gate, session lifecycle, adapter registry | Java, Spring Boot | Transactional policy logic, rich validation, long lived with connection pools |
| `query-broker/` | Federated read across estates, merge, deadline, partial results | Go | Concurrent fan out under strict deadlines, small footprint |
| `edge-shipper/` | Outbound only transmission from a self hosted estate | Go | Single static binary into a customer environment, no runtime to install |
| `adapters/` | One per source: map source events into the normalized record | Python | Mapping code changes often, deploys as ephemeral compute |
| `consumers/` | Read from the bus and write derived state | Go, Python | Profile depends on the consumer |
| `etls/` | Batch jobs: estate backfill, compatibility reporting | Python | Batch analysis over stored state |

## Boundaries

**Adapters own source specifics and nothing else.** All knowledge of a source's
schema, delivery model, authentication, and identifier conventions stops at the
adapter. Nothing inward learns it.

**Never construct a record by hand.** Build through `adapters/common`. Identity
derivation, integrity hashing, and the fail closed authority checks live there so
that adapter N+1 cannot drift from the contract, and so that no emission path
exists that skips authority.

**The control plane is not on the telemetry path.** Adapters consult it once when
opening a session and cache the decision for that session's bounded lifetime.
Telemetry flows adapter to bus directly. A control plane outage stops new
sessions from opening; it does not drop signals already in flight.

## Adding a source

Map the source vocabulary onto `Contracts/taxonomy.yaml`, declare capability in a
manifest, confirm identity resolution, implement the mapping through the shared
library, prove fail closed behaviour by test, register in the ingest stack.
Nothing that already exists should change. If it does, the normalized layer is
leaking.
