# GitHub Copilot Instructions

This repository uses **Beads (bd)** for issue tracking.

## Core Workflow

- Use `bd ready` to find unblocked work
- Use `bd create` to track new work
- Use `bd update <id> --claim` before starting
- Use `bd close <id>` when work is complete
- Treat commit, push, and Dolt remote sync as policy-controlled handoff actions
- Do not commit, push, or run Dolt remote sync unless explicitly authorized

## Context Loading

Run `bd prime` for the full workflow context.

If the Beads Copilot plugin is installed, Copilot CLI will automatically run
`bd prime` on session start and before compaction.

## Issue Tracking

This project uses **bd (beads)** for issue tracking.
Run `bd prime` for workflow context, or install hooks (`bd hooks install`) for auto-injection.

**Quick reference:**
- `bd ready` - Find unblocked work
- `bd create "Title" --type task --priority 2` - Create issue
- `bd close <id>` - Complete work
- `bd dolt push` - Push beads to remote

For full workflow details: `bd prime`