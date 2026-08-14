# Development workflow

Work is tracked in [beads](https://beads.gascity.com), a dependency-aware issue graph. The reason for using it here rather than a flat tracker is specific: this architecture has a real build order. The index cannot be built before signals arrive, cutover cannot happen before the compatibility report exists, and blob resolution cannot be tested before write ordering is enforced. A flat list of open issues invites picking the wrong one; `bd ready` computes the frontier that is actually workable.

## The spec is the source of truth

`plan/backlog.yaml` defines every epic, feature, and task. It is the file that gets edited. `tools/beads-sync.py` projects it into the graph and never reads back, so the plan cannot silently drift into being a stale summary of the tracker.

Every item carries three fields that turn a title into a specification:

| Field | Flag | What it answers |
|---|---|---|
| `spec` | `--spec-id` | Which document this implements |
| `design` | `--design` | How, and which constraint shapes it |
| `acceptance` | `--acceptance` | How we know it is done |

A bead without a spec reference is a guess. `bd lint` flags items missing recommended sections; run it before pushing.

The ten ADRs are beads too, created with `--type=decision` (`adr` is an alias). Features link to the decisions they implement with a non-blocking `related` edge, so `bd dep tree` on a feature shows the reasoning it inherits without the decision gating the work.

## Levels

Beads ships `bug | feature | task | epic | chore | decision`. There is no `story` type; a fourth level needs `types.custom` configured. The mapping used here:

```
epic      E1        a coherent area of the system
feature   E1.F1     a shippable capability, what most teams call a story
task      E1.F1.T1  one sitting of work
decision  ADR-0004  an architecture decision, linked from the features it governs
```

Hierarchical child IDs (`bd-a3f8e9.1`) come from `--parent`, so the tree is navigable with `bd dep tree`.

## Daily loop

```bash
bd ready --explain          # what is workable and why
bd update <id> --claim      # take it
# ... work ...
bd close <id> --reason "..."
bd dolt push                # end of session
```

Work discovered mid-task gets captured rather than dropped:

```bash
bd create "Orphan sweeper misses multipart uploads" \
  --deps discovered-from:<current-id> \
  --spec-id docs/adr/0006-blobs-by-reference-never-on-the-bus.md \
  --design "..." --acceptance "..."
```

`discovered-from` is non-blocking, so it records provenance without stalling the frontier.

## Ordering rules encoded in the graph

Within a feature, tasks are sequential by default. Parallelism is opt in, because two agents claiming adjacent tasks in the same file is the common failure mode, not a throughput win.

The cross-cutting edges live in the `dependencies` block of `backlog.yaml`. The ones worth knowing:

- **Estate ingest waits on the authority gate.** Accepting batches from a customer estate before authority is real means collecting data you cannot justify.
- **Cutover waits on both the compatibility report and the backfill decision.** This is the ordering that keeps migration from being a leap of faith.
- **The console banner waits on partial result reporting.** The UI cannot honestly report a degraded estate before the broker tells it which one failed.

Check the graph holds together:

```bash
bd dep cycles
bd graph --all
bd blocked
```

## Formulas

Three repeatable workflows live in `.beads/formulas/`.

| Formula | Poured when |
|---|---|
| `add-adapter` | A new signal source is integrated. The workflow the architecture exists to make cheap. |
| `adr` | A structural decision needs recording, with the trade-off analysis enforced as steps. |
| `tenant-cutover` | One tenant migrates. Poured once per tenant, with timer gates for the soak and rollback windows. |

```bash
bd cook .beads/formulas/add-adapter.formula.toml
bd mol pour <proto-id> --var source_name=collaboration_suite --var adapter_id=collab_suite
bd mol pour <proto-id> --dry-run    # preview first
```

`tenant-cutover` is the one that matters commercially. The measure of the migration programme is cost per tenant migrated and rollback rate; pouring a molecule per tenant is what makes those numbers exist at all.

## Gates

Steps that wait on the outside world are gates, not blocked tasks.

```bash
# Downstream work waits for the PR to actually merge, not for the bead to close
bd create --type=gate --title="Wait for PR #42" --await-type=gh:pr --await-id=42
bd dep add <next-issue> <gate-id>
bd gate check
```

This matters more here than in a typical repo. Issue state and code state are decoupled: closing a bead means the work is done, not that the code is on main. The `tenant-cutover` formula uses timer gates for the soak and rollback windows for the same reason, since those are wall-clock waits that no amount of engineering shortens.

## First-time setup

```bash
git config beads.role maintainer    # canonical clone; see Docs/BEADS-COMMAND-GUIDE.md
bd init --quiet --role maintainer
python3 Tools/beads-sync.py --dry-run     # inspect
python3 Tools/beads-sync.py               # apply
bd ready --type task --explain
bd dolt push
```

The sync closes items already delivered before beads adoption, so the first `bd ready` shows the genuine frontier rather than work that is finished.

## Amending the plan

Edit `plan/backlog.yaml`, then re-run the sync. Existing beads are recognised by their stable plan key in `plan/.bead-ids.json` and left alone; only new items are created.

Never renumber a key. Retire an item instead of deleting it, so the mapping stays valid and history stays readable.
