# Agent instructions

<!-- BEADS:START -->
## Work tracking

Work is tracked in beads. Do not keep plans in markdown scratch files or TODO comments; they do not survive a session.

```bash
bd ready --json              # the claimable frontier
bd update <id> --claim       # take work atomically
bd close <id> --reason "..."
bd dolt push                 # end of session, always
```

Always pass `--json` for programmatic use. Capture discovered work as you find it:

```bash
bd create "..." --deps discovered-from:<current-id> --json
```

`plan/backlog.yaml` is the source of truth for planned work. To add planned scope, edit that file and run `python3 tools/beads-sync.py`. Do not create planned epics or features directly with `bd create`, or the plan and the graph diverge.
<!-- BEADS:END -->

## Repository rules

**The schemas are the architecture.** Read `schemas/` and `docs/adr/` before changing behaviour. A change that contradicts an accepted ADR needs a new ADR superseding it, not a quiet edit.

**Do not hand construct envelopes.** Build them through `AdapterContext`. Identity, hashing, and the fail closed checks live in the shared library so adapters cannot drift from the contract.

**Fail closed on authority.** No code path may emit a signal without an unexpired decision. If a test is inconvenient because of this, the test is wrong.

**Taxonomy changes are additive only** within a `schema_version`. Removing or repurposing a `signal_type` is a breaking change requiring an ADR.

**Blobs are written before their reference is published.** Orphaned blobs are recoverable; dangling references are not.

**Never couple a migration change to a scoring model change.** They are separately scheduled by design.

## Before opening a PR

```bash
make validate          # contracts consistent
make test              # adapter and broker suites
bd lint                # beads missing required sections
bd dep cycles          # graph integrity
```
