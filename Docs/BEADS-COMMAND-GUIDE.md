# Beads Command Guide

**Purpose:** A working reference for using `bd` to track a project from installation through delivery.
**Reference version:** Documentation for bd 1.2.1; the published CLI reference covers 108 top level commands.
**Date:** 14 August 2026

---

## How to read this guide

Commands are grouped by the phase of work in which you reach for them, not alphabetically, because the useful question is usually "what do I run now" rather than "what does this command do".

**Verification status matters.** Sections marked **[verified]** were taken from the published command reference including exact flags. Sections marked **[from index]** name commands that appear in the official command list, but whose flags I have not read; treat the flags shown as likely rather than certain and confirm with `bd help --doc <command>`. Nothing here should be run blind in a repository that matters.

The single most reliable thing you can do is:

```
bd help --list                 # every command
bd help --doc <command>        # exact flags for one command
bd human                       # short menu of the common ones
bd quickstart                  # worked patterns
bd prime                       # workflow context written for agents
```

`bd prime` is worth running at the start of any Claude Code or Cursor session. It emits the workflow context in a form agents consume well.

---

## Signal-Plane: from empty graph to ready queue

This repository does **not** seed work by hand. `Plan/backlog.yaml` is the source of truth (format v2: 18 epics, stories under features). `Tools/render-product-map.py` regenerates that file; `Tools/beads-sync.py` projects it into beads and never reads back. Creating planned epics, features, or stories with `bd create` makes the plan and the graph diverge.

`bd init` leaves the graph empty. Until the sync runs, `bd ready` is a truthful empty list, not a missing installation.

### First-time setup (canonical clone)

```
git config beads.role maintainer
bd init --quiet --role maintainer     # already done in this clone
python3 Tools/beads-sync.py --dry-run
python3 Tools/beads-sync.py
bd ready --type task --explain
```

Role must be **maintainer** in this repo. `contributor` routes `bd create` to `~/.beads-planning`. If that workspace has no Dolt database, `bd ready` and `bd list` fail with `failed to open routed store` even when the in-repo graph is healthy.

Do not add `repos.additional` unless every listed path is itself a `bd init`'d workspace. An empty `~/.beads-planning/.beads/` directory is enough to take down the ready queue. Remove a bad entry with `bd repo remove <path>`.

The sync writes `Plan/.bead-ids.json`, mapping stable plan keys (`E2.F1.S1.T1`) to hash IDs. Commit that file. Re-running the sync is idempotent: existing keys are left alone, new plan items are created, `status: closed` items are closed, and `status: deferred` items are iced so they do not appear in `bd ready`.

The plan is four levels: epic → feature → story → task. Stories are persona plus outcome. Phase 1–2 (E1–E5) is the open frontier; phase 3–4 (E6–E18) is deferred so those leaves do not flood `bd ready`.

After a successful sync, unfiltered `bd ready` includes epics, features, and stories that have no blockers. For implementation work, filter to tasks:

```
bd ready --type task --explain
bd update <id> --claim
```

Discovered work (bugs found while implementing) is the exception: create those directly with `bd create` and `--deps discovered-from:<id>`. Do not put them in `backlog.yaml`.

See also `Docs/development-workflow.md`.

---

## 1. Installation and verification **[verified]**

```
# Homebrew, macOS and Linux
brew install beads

# Install script, macOS, Linux, FreeBSD
curl -fsSL https://raw.githubusercontent.com/gastownhall/beads/main/scripts/install.sh | bash

# Node
npm install -g @beads/bd

# Go
go install github.com/gastownhall/beads/cmd/bd@latest
```

Verify:

```
bd --help
bd version                     # binary is on PATH, correct version
bd doctor                      # diagnostic suite: storage, config, environment
bd ping                        # can bd reach its database
bd info                        # database information
bd info --schema --json        # schema and config, machine readable
bd where                       # active database location, including redirects
bd context                     # effective backend identity and repository paths
```

Run `bd doctor` before assuming anything else is wrong. It catches most environment problems directly.

---

## 2. Initialization **[verified]**

```
bd init                        # interactive; prompts for role
bd init --quiet                # non interactive, for agents
bd init --contributor          # fork workflow, separate planning repo
bd init --team                 # branch workflow for collaboration
bd init --server               # connect to an external dolt sql-server
bd init --from-jsonl           # import from an older installation
bd init --skip-hooks           # do not install git hooks
bd init --force                # override safety guards on existing data
bd init --stealth              # no git operations at all
```

`bd init` creates `.beads/`, initialises an embedded Dolt database, imports existing issues if present, and installs git hooks.

Working outside a git repository:

```
export BEADS_DIR=/path/to/project/.beads
bd init --quiet --stealth
```

Role configuration determines where issues are routed:

```
git config beads.role maintainer     # repo owner or push access, issues in-repo
git config beads.role contributor    # fork contributor, separate planning repo
git config --get beads.role
bd context                           # shows role, beads dir, and database
bd doctor                            # confirms role is configured
```

In Signal-Plane the canonical clone is a maintainer workspace. Contributor role plus an uninitialized `~/.beads-planning` is what produced an empty, unlistable ready queue after `bd init`. `bd context` is the check: `beads dir` must be this repo's `.beads/`, and `role` must be `maintainer`.

Recovery and fresh clones:

```
bd bootstrap                   # non destructive setup in a fresh clone
bd init-safety                 # the init flag safety contract
```

`bd bootstrap` auto detects an existing database on the Dolt ref, clones it, and wires the remote. It is what a teammate runs after cloning, not `bd init`.

---

## 3. Agent and IDE integration **[verified]**

```
bd setup claude                # Claude Code: hooks, skill, session lifecycle
bd setup codex                 # Codex: skill, AGENTS.md section, hooks
bd setup cursor                # Cursor: always applied project rules file
bd setup gemini                # Gemini CLI: SessionStart hooks, GEMINI.md
bd setup copilot               # GitHub Copilot
bd setup windsurf
bd setup kilocode
bd setup cody
bd setup junie
bd setup mux
bd setup opencode
bd setup factory
bd setup kiro
bd onboard                     # snippet to paste into your agent instructions file
bd rules                       # audit and compact Claude rules
```

For Claude Code and Cursor specifically, run `bd setup claude` and `bd setup cursor`. Both install instruction files so the agent reaches for `bd ready` instead of inventing a markdown to-do list, which is the entire point of adopting this.

---

## 4. Global flags **[verified]**

These are inherited by every command.

| Flag | Purpose |
|---|---|
| `--json` | Machine readable output. Use for anything programmatic. |
| `--db <path>` | Explicit database path |
| `--actor <name>` | Override actor name in the audit trail |
| `--repo <name>` | Override target repository or rig |
| `--verbose` | Verbose logging |
| `--quiet` | Suppress non essential output |
| `--no-color` | Disable colour |
| `--sandbox` | Sandbox mode, for testing |
| `--global` | Operate on the global database |
| `--server` | Connect to a Dolt SQL server |
| `--proxied-server` | Connect to a proxied Dolt SQL server |
| `--readonly` | Open read only |
| `--ignore-schema-skew` | Proceed despite forward schema drift |
| `--dolt-auto-commit <mode>` | Auto commit policy |

---

## 5. Planning: epics, features, stories, tasks **[verified]**

### 5.1 Types and priorities

Valid types: `bug`, `feature`, `task`, `epic`, `chore`, `decision`, `story`, `spike`, `milestone`. Aliases: `enhancement` and `feat` map to `feature`; `dec` and `adr` map to `decision`. Custom types require `types.custom` in configuration.

This plan uses four levels: epic → feature → story → task. `story` is built-in in bd 1.2.1 (persona plus outcome). Do not invent a custom type for it.

Priority is 0 to 4 or P0 to P4, where 0 is highest. Default is 2.

```
bd types                       # list valid types
bd statuses                    # list valid statuses and categories
```

### 5.2 Creating with specification content

Planned work is created by the sync, not by this command. Use `bd create` for **discovered** work (bugs, follow-ups) and put `--deps discovered-from:<id>` on it.

These flags put the spec on the bead:

```
bd create "Authority gate JDBC repository" \
  --type task \
  --priority 0 \
  --parent bd-a3f8e9 \
  --spec-id docs/adr/0004-authority-gate-precedes-capture.md \
  --design "Back the interface with the policy tables. Tenant scoped queries only." \
  --acceptance "Integration test seeds both demo subjects and asserts grant and denial paths." \
  --labels control-plane,java \
  --estimate 240 \
  --assignee kishore \
  --validate
```

Full flag set for `bd create`:

| Flag | Purpose |
|---|---|
| `-t, --type` | Issue type |
| `-p, --priority` | 0 to 4 or P0 to P4 |
| `-d, --description` | Description |
| `--design` | Design notes |
| `--design-file` | Read design from file, `-` for stdin |
| `--acceptance` | Acceptance criteria |
| `--context` | Additional context |
| `--notes` | Notes |
| `--append-notes` | Append to existing notes |
| `--spec-id` | Link to a specification document |
| `--parent` | Parent issue for hierarchical child |
| `--deps` | Dependencies as `type:id` or `id`, comma separated |
| `-l, --labels` | Comma separated labels |
| `--no-inherit-labels` | Do not inherit parent labels |
| `-a, --assignee` | Assignee |
| `-e, --estimate` | Estimate in minutes |
| `--due` | `+6h`, `+1d`, `+2w`, `tomorrow`, `next monday`, `2026-01-15` |
| `--defer` | Hide from ready until this date |
| `--metadata` | Custom JSON, or `@file.json` |
| `--external-ref` | External reference such as `gh-9` or a Jira key |
| `--skills` | Required skills |
| `--id` | Explicit ID, for partitioning |
| `--silent` | Output only the ID, for scripting |
| `--dry-run` | Preview without creating |
| `--validate` | Require sections appropriate to the type |
| `--body-file` / `--stdin` | Read description from file or stdin |
| `-f, --file` | Batch create from a markdown file |
| `--graph` | Batch create a dependency graph from a JSON plan file |
| `--ephemeral` | Ephemeral, subject to TTL compaction |
| `--wisp-type` | `heartbeat`, `ping`, `patrol`, `gc_report`, `recovery`, `error`, `escalation` |
| `--mol-type` | `swarm`, `patrol`, `work` |
| `--waits-for` | Spawner issue for a fanout gate |
| `--waits-for-gate` | `all-children` or `any-children` |
| `--force` | Create despite prefix mismatch |

### 5.3 Batch creation

```
bd create --file plan.md                # multiple issues from markdown
bd create --graph plan.json             # a dependency graph from a JSON plan
bd create --graph plan.json --dry-run   # preview first
```

`--graph` is the generic tool for seeding a backlog from JSON. **This repository does not use it.** Planned work is projected from `Plan/backlog.yaml` with `python3 Tools/beads-sync.py`. Use `--graph` only if you are following upstream beads examples outside this project.

### 5.4 Hierarchy

```
bd create "Estate migration tooling" -t epic -p 0        # returns bd-a3f8e9
bd create "Compatibility report" -t feature --parent bd-a3f8e9   # bd-a3f8e9.1
bd create "Static rule analysis" -t task --parent bd-a3f8e9.1    # bd-a3f8e9.1.1

bd dep tree bd-a3f8e9
bd children bd-a3f8e9
bd epic                        # epic management commands
```

Children inherit parent labels by default. Suppress with `--no-inherit-labels`, which matters when the parent carries a size or effort label.

### 5.5 Quick capture

```
bd q "Sweeper misses multipart uploads"    # creates and prints only the ID
bd todo add "Update the runbook"
bd todo list
bd todo done <id>
bd create-form                              # interactive terminal form
```

---

## 6. Dependencies **[verified]**

### 6.1 Creating and removing

```
bd dep add issue-2 issue-1              # issue-2 depends on issue-1
bd dep issue-1 --blocks issue-2         # same, stated the other way
bd dep add issue-2 --blocked-by issue-1
bd dep add issue-2 --depends-on issue-1
bd dep add issue-2 issue-1 --type tracks
bd dep remove issue-2 issue-1
bd dep rm issue-2 issue-1
bd link <a> <b>                          # link two issues with a dependency
```

### 6.2 Types

Blocking, affecting `bd ready`:

| Type | Meaning |
|---|---|
| `blocks` | Default. B cannot start until A closes |
| `parent-child` | Children blocked when parent is blocked |
| `conditional-blocks` | B runs only if A fails |
| `waits-for` | B waits for all of A's children |

Non blocking, graph annotation only:

| Type | Meaning |
|---|---|
| `related` | Informational link |
| `tracks` | Tracks another issue's progress |
| `discovered-from` | Found while working on another issue |
| `caused-by` | Root cause link |
| `validates` | Test or verification link |
| `supersedes` | Replaced by a newer issue |

Use `related` to attach a feature to the decision record that governs it: the reasoning shows in the tree without the decision blocking the work.

### 6.3 Inspecting

```
bd dep tree <id>
bd dep tree <id> --direction=up          # what depends on this
bd dep tree <id> --direction=both
bd dep tree <id> --status=open
bd dep tree <id> --max-depth=3
bd dep tree <id> --format=mermaid
bd dep list <id>
bd dep list <id> --direction=up
bd dep list <id> --type=tracks
bd dep blocks <id>                       # what is blocking this
bd dep cycles                            # detect cycles
```

`bd dep add` rejects cycles at write time, so `bd dep cycles` is a safety net rather than the primary defence.

### 6.4 Visualisation

```
bd graph <id>
bd graph --all
bd graph --compact <id>
bd graph --box <id>
bd graph --dot <id> | dot -Tsvg > graph.svg
bd graph --html <id> > graph.html
```

Layer 0 has no dependencies and can start immediately; higher layers depend on lower ones; items in the same layer can run in parallel.

### 6.5 Cross repository

```
bd dep add local-issue external:other-project:remote-issue
```

External dependencies always block, and are evaluated at query time.

---

## 7. The daily loop **[verified]**

```
bd ready                                 # unblocked work (epics, features, stories, tasks)
bd ready --type task                     # implementation frontier in this repo
bd ready --explain                       # and why, including what is blocked
bd ready --json                          # machine readable
bd ready --explain --json
bd ready --claim --json                  # atomically claim the first match
bd ready --priority 1
bd ready --label backend
bd ready --assignee alice
bd ready --unassigned
bd ready --sort oldest

bd update <id> --claim                   # assign to self, set in_progress
bd update <id> --status=in_progress
bd update <id> --set-metadata '{"pr":"142"}'
bd assign <id> <person>
bd priority <id> 1
bd tag <id> <label>
bd note <id> "Observation worth keeping"
bd comment <id> "Context for the next session"
bd comments <id>
bd edit <id> <field>                     # opens $EDITOR

bd close <id> --reason "..."
bd close <id> --suggest-next             # what just unblocked
bd done <id>                             # alias for close
bd reopen <id>
```

`bd ready` is not `bd list --status open`. The first computes the dependency graph and returns only genuinely workable items; the second returns everything open regardless of blockers. Using `list` where you meant `ready` is the most common way to waste an agent's session.

### 7.1 Capturing discovered work

```
bd create "Found a bug in the sweeper" \
  --description "..." \
  --deps discovered-from:bd-100 \
  --json
```

`discovered-from` is non blocking, so provenance is recorded without stalling the frontier. Do this the moment you notice something, rather than at the end of a session.

### 7.2 Session boundaries

```
bd prime                                 # start of session: workflow context
bd ready --type task --json              # sitting-sized work to claim
# ... work ...
bd dolt push                             # end of session, always
```

Losing a session without `bd dolt push` loses the tracking, which defeats the reason for using this at all.

---

## 8. Querying and reporting **[verified]**

```
bd list
bd list --status open
bd list --json
bd list --tree                           # hierarchical parent-child view
bd list --ready                          # only unblocked
bd list --pretty

bd show <id>
bd show <id> --json
bd show <id> --children
bd show <id> --refs                      # all dependency links
bd show <id> --thread                    # message threads

bd search <term>                         # title and ID, excludes closed
bd query "<expression>"                  # compound filter query language
bd count --status open
bd blocked                               # everything blocked, and by what
bd stats
bd status                                # database snapshot
bd stale                                 # not updated recently
bd orphans                               # referenced in commits but still open
bd lint                                  # missing recommended sections by type
bd duplicates                            # identical content
bd find-duplicates                       # semantically similar
bd diff <a> <b>                          # differences between commits or branches
bd history <id>                          # full version history
bd children <id>
bd audit                                 # audit log entries
```

Two of these are worth running before every pull request. `bd lint` catches beads that were created without the specification content that makes them actionable. `bd orphans` catches work that was mentioned in a commit message but never closed.

---

## 9. Workflows: formulas, protos, molecules, wisps **[verified]**

The pipeline is: a formula is a file, cooking it produces a proto, pouring the proto produces a molecule of real beads.

```
bd formula list
bd formula                               # manage formulas
bd cook <formula-file>                   # formula -> proto
bd mol pour <proto-id> --var key=value   # proto -> molecule
bd mol pour <proto-id> --dry-run
bd mol                                   # molecule management
bd mol wisp <proto-id>                   # ephemeral molecule
bd mol bond                              # link molecules
bd mol squash                            # compact completed molecules
bd promote <wisp-id>                     # wisp -> permanent bead
bd purge                                 # delete closed ephemeral beads
```

Formulas live in `.beads/formulas/` at project level or `~/.beads/formulas/` at user level, searched in that order.

Formula file structure, TOML preferred over JSON:

- `formula`, `description`, `version`, `type` at the top. Type is `workflow`, `expansion`, or `aspect`.
- `[vars.name]` blocks with `description`, `required`, `default`, `pattern`, `enum`.
- `[[steps]]` blocks with `id`, `title`, `description`, `type`, and `needs` as an array of step ids.
- `[steps.gate]` blocks for async waits.
- `[[advice]]` blocks with `target` and `[advice.before]` for aspect formulas.

A step's `type` sets the issue type of the bead it creates. Human sign offs and async waits use a `[steps.gate]` block, not a step type.

Use formulas for anything you will do more than twice: onboarding a component, recording a decision, running a release, migrating a tenant.

---

## 10. Gates **[verified]**

Gates park work until the outside world catches up. They matter here because issue state and code state are decoupled: closing a bead means the work is done, not that the code is on the main branch.

```
bd create --type=gate --title="Wait for PR #42" --await-type=gh:pr --await-id=42
bd create --type=gate --title="Wait for CI" --await-type=gh:run --await-id=12345
bd create --type=gate --title="Cooldown" --await-type=timer --await-id=30m
bd create --type=gate --title="Wait for upstream" --await-type=bead --await-id=other-rig:issue-id
bd create --type=gate --title="Deploy approval"          # human gate

bd dep add <next-issue> <gate-id>        # wire it in

bd gate check
bd gate check --type=gh:pr
bd gate check --type=gh:run
bd gate check --type=timer
bd gate check --dry-run
bd gate check --escalate
bd gate discover                         # match gates to CI runs
bd gate discover --dry-run
bd gate discover --branch main
bd gate list
bd gate list --all
bd gate show <gate-id>
bd gate resolve <gate-id> --reason "Approved by team lead"
bd merge-slot                            # serialize conflict prone work
```

Gate types and their resolution:

| Type | Condition | Auto resolution |
|---|---|---|
| `gh:pr` | PR merged | `gh pr view` returns MERGED |
| `gh:run` | CI passes | `gh run view` returns completed and success |
| `timer` | Time elapsed | Current time exceeds timeout |
| `bead` | Cross rig issue closed | Remote bead status checked |
| `human` | Manual approval | `bd gate resolve <id>` |

Automate the check with a CI step, a cron entry every five minutes, or an agent hook at session start.

---

## 11. Synchronisation **[verified]**

Beads stores issues in Dolt, a version controlled SQL database. Data lives under `refs/dolt/data` on the same git remote, separate from ordinary git refs. There is no protected branch problem and no server to run.

```
bd dolt remote list
bd dolt remote add origin git+ssh://git@github.com/org/repo.git
bd dolt push
bd dolt pull
bd dolt commit
bd dolt start                            # server mode: start dolt sql-server
bd dolt stop
bd dolt status
bd vc                                    # version control operations
bd branch                                # list or create branches
bd sql "<query>"                         # raw SQL against the database
```

Import, export, and backup:

```
bd export                                # to JSONL
bd export --scrub                        # remove sensitive content
bd import <file.jsonl>
bd backup init
bd backup sync
bd backup restore
```

`.beads/issues.jsonl` is a passive export for viewers and interchange. It is **not** the database, not the sync protocol, and not a backup. Older articles describe a JSONL plus SQLite storage model; that is out of date, and treating the JSONL as your issue store will eventually lose work.

---

## 12. Multi agent and multi repository **[from index]**

```
bd swarm                                 # coordinate parallel work on an epic
bd repo                                  # configure multi repository support
bd federation                            # peer to peer sync across workspaces
bd ship                                  # satisfy cross project dependencies
bd worktree                              # manage git worktrees with beads config
bd mail                                  # mail operations via a provider
```

Worktrees share one `.beads` workspace. Hash based IDs are what make concurrent creation across agents and branches safe: two agents cannot mint the same ID, so merges never renumber work.

`repos.additional` hydrates extra workspaces into the same ready query. Every additional path must contain a real embedded Dolt database (`.beads/embeddeddolt/`). A git repo with an empty `.beads/` directory fails the whole query:

```
failed to open routed store at /Users/.../.beads-planning: embeddeddolt: no embedded database
```

Fix: `bd repo remove <path>`, or `bd init --quiet --role maintainer` inside that path, then `bd ready` again. Signal-Plane's ready queue should come from this repo; do not attach a personal planning repo unless you intend those issues to appear here.

---

## 13. Memory **[from index]**

```
bd remember "Insight worth keeping across sessions"
bd recall <key>
bd memories
bd memories <keyword>
bd forget <key>
```

Use this rather than creating a MEMORY.md file. The point of adopting beads is that context survives the session; a markdown file does not.

---

## 14. External tracker synchronisation **[from index]**

```
bd github sync
bd gitlab sync
bd jira sync
bd linear sync
bd ado sync                              # Azure DevOps
bd notion sync
bd notion sync --dry-run
bd notion sync --pull
bd notion sync --push
bd notion init --parent <page-id>
bd notion connect --url <url>
bd notion status
bd notion status --json
bd config set notion.token <token>
```

Confirm flags with `bd help --doc <command>` before wiring any of these into automation. Bidirectional sync with an external tracker is the place where a wrong flag does visible damage.

---

## 15. Maintenance **[verified where noted]**

```
bd doctor                                # full diagnostic suite
bd doctor --check-health
bd migrate --inspect --json              # analyse migration safety first
bd migrate --dry-run
bd migrate
bd migrate --yes                         # migrate and clean up old files
bd upgrade                               # check versions, review changes
bd hooks                                 # install, uninstall, list git hooks
bd config set <key> <value>
bd config get <key>
bd config list
bd config validate
bd kv                                    # key-value store
bd metrics                               # anonymous usage metrics status
bd preflight                             # pre PR checklist
bd recompute-blocked                     # rebuild the denormalized blocked flag
```

Database size management:

```
bd admin compact --stats
bd admin compact --analyze --json        # candidates, 30+ days closed
bd admin compact --apply --id <id> --summary summary.txt
bd compact                               # squash Dolt commits older than N days
bd restore <id>                          # restore pre compaction content
bd gc                                    # lifecycle garbage collection
bd prune                                 # delete closed non ephemeral beads
bd purge                                 # delete closed ephemeral beads
bd flatten                               # squash all Dolt history. Nuclear.
bd admin cleanup --force                 # immediate permanent deletion
bd admin reset                           # remove beads from a repository
```

Compact when the database exceeds roughly 10MB with many old closed issues, after a milestone, or before archiving a phase. Compaction is permanent decay: original content is discarded but recoverable via `bd restore` from the pre compaction snapshot, with Dolt history as fallback.

`bd flatten` and `bd admin cleanup --force` are destructive and unrecoverable. Back up first.

---

## 16. Lifecycle and issue management **[verified]**

```
bd defer <id> --until 2026-09-01         # hide from ready until a date
bd undefer <id>
bd delete <id>
bd delete <id> --cascade                 # including children
bd delete <id> --force
bd delete <id> --dry-run
bd duplicate <id> --of <canonical>
bd supersede <old> --with <new>
bd rename <old-id> <new-id>
bd rename-prefix <old> <new>
bd batch                                 # multiple writes in one transaction
bd set-state <id> <dimension> <value>
bd state <id> <dimension>
bd label                                 # manage labels
```

Prefer `bd defer` over closing something you intend to return to. A deferred item leaves the ready queue without pretending it was done.

---

## 17. A worked sequence for a project

**Set up once.**

```
git config beads.role maintainer
bd init --quiet --role maintainer
bd setup claude
bd setup cursor
bd context                       # beads dir is this repo; role is maintainer
bd doctor
bd dolt remote list
```

**Seed the plan from the spec, not by hand.** Edit `Tools/render-product-map.py` (or `Plan/backlog.yaml` directly). Every epic, feature, and story needs `spec`, `design`, and `acceptance`; tasks inherit the parent's intent. Then project:

```
python3 Tools/render-product-map.py      # regenerate Plan/backlog.yaml
python3 Tools/beads-sync.py --dry-run
python3 Tools/beads-sync.py
```

The sync creates decisions, epics, features, stories, and tasks; wires sequential task edges and the `dependencies:` block; attaches ADRs with `--type related`; closes `status: closed`; and defers `status: deferred` so later phases stay off the ready queue. Do not `bd create` planned epics, features, or stories. `Plan/.bead-ids.json` is the idempotency map; commit it. Do not renumber keys.

**Verify the plan holds together.**

```
bd ready --type task --explain   # implementation frontier, not the epics
bd blocked                       # is anything blocked that should not be
bd dep cycles
bd lint                          # any bead missing its specification content
bd stats
```

**Work it, each session.**

```
bd prime
bd ready --type task --explain
bd update <id> --claim
# ... implement ...
bd create "..." --deps discovered-from:<id>     # as you find things
bd close <id> --reason "..." --suggest-next
bd dolt push
```

**Coordinate with code state.** Open the PR, gate the dependent work on the merge rather than on the bead closing.

```
bd create --type=gate --title="Wait for PR #N" --await-type=gh:pr --await-id=N
bd dep add <next> <gate-id>
bd gate check
```

**Before every pull request.**

```
bd preflight
bd lint
bd dep cycles
bd orphans
```

**Periodically.**

```
bd stale                         # what has gone quiet
bd stats
bd admin compact --stats
bd backup sync
```

---

## 18. Practices worth adopting

**Always `--json` for anything programmatic.** The human output format is not a contract; the JSON output is, and it carries a schema version envelope.

**`bd ready`, never `bd list`, when deciding what to do next.** The distinction is the reason for using beads at all.

**Capture discovered work immediately, with `discovered-from`.** Work noticed and not recorded is work lost at the session boundary, which is the failure beads exists to prevent.

**Push at every session end.** `bd dolt push` is the commit. Skipping it discards the session's tracking.

**Never renumber or delete plan items.** Supersede or defer instead. Hash IDs are stable and other things reference them.

**Gate on external state, not on bead closure.** A closed bead means work is done, not that code is on main. This gap is exactly what gates exist to bridge.

**Run `bd lint` before pushing.** A bead without acceptance criteria will be interpreted differently by the agent that picks it up than by the person who wrote it.

**Treat `bd flatten`, `bd admin cleanup --force`, and `bd admin reset` as irreversible.** Because they are.

---

## 19. Verifying anything in this guide

```
bd help --list
bd help --doc <command>
bd <command> --help
bd quickstart
bd human
bd prime
```

The official documentation is at `https://beads.gascity.com`, with a machine readable index at `https://beads.gascity.com/llms.txt` that lists every documentation page including one per command. If a flag here does not match what `bd help --doc` reports, the CLI is authoritative and this guide is stale.
