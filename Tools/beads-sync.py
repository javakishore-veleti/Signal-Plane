#!/usr/bin/env python3
"""Project plan/backlog.yaml into the beads graph.

The plan file is the source of truth. This script never reads back from beads to
amend the plan; it only pushes the plan forward. Change the spec, re-run, and the
graph follows.

Idempotency comes from plan/.bead-ids.json, which maps stable plan keys to the
hash IDs beads mints. Beads IDs are content derived and include creation time, so
re-creating an item would mint a new ID; the map is what prevents that.

    python3 tools/beads-sync.py --dry-run     # show what would change
    python3 tools/beads-sync.py               # apply
    python3 tools/beads-sync.py --prune       # report plan items with no bead and vice versa
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "Plan" / "backlog.yaml"
IDMAP = ROOT / "Plan" / ".bead-ids.json"

PRIORITY_DEFAULT = {"epic": "1", "feature": "2", "story": "2", "task": "2", "decision": "2"}


class Sync:
    def __init__(self, dry_run: bool) -> None:
        self.dry_run = dry_run
        self.ids: dict[str, str] = json.loads(IDMAP.read_text()) if IDMAP.exists() else {}
        self.created = 0
        self.linked = 0
        self.skipped = 0

    def bd(self, args: list[str], capture: bool = True, ok_stderr: tuple[str, ...] = ()) -> str:
        if self.dry_run:
            print("  bd " + " ".join(args))
            return f"dry-{len(self.ids) + self.created}"
        out = subprocess.run(["bd", *args], capture_output=capture, text=True)
        if out.returncode != 0:
            err = (out.stderr or out.stdout or "").strip()
            lowered = err.lower()
            if any(needle in lowered for needle in ok_stderr):
                return out.stdout.strip()
            raise RuntimeError(f"bd {' '.join(args)} failed: {err}")
        return out.stdout.strip()

    def create(self, key: str, item: dict, kind: str, parent: str | None = None) -> str:
        if key in self.ids:
            self.skipped += 1
            return self.ids[key]

        args = [
            "--dolt-auto-commit", "batch",
            "create", item["title"],
            "--type", kind,
            "--priority", str(item.get("priority", PRIORITY_DEFAULT.get(kind, "2"))),
            "--silent",
        ]
        if parent:
            args += ["--parent", parent]
        if item.get("spec"):
            # Links the bead to the document it implements. This is the hinge of
            # spec driven development here: a bead with no spec is a guess.
            args += ["--spec-id", item["spec"]]
        if item.get("design"):
            args += ["--design", " ".join(item["design"].split())]
        if item.get("acceptance"):
            args += ["--acceptance", " ".join(item["acceptance"].split())]
        if item.get("labels"):
            args += ["--labels", ",".join(item["labels"])]
        args += ["--metadata", json.dumps({"plan_key": key})]

        bead_id = self.bd(args)
        self.ids[key] = bead_id
        self.created += 1
        print(f"  + {kind:<8} {key:<12} {bead_id:<12} {item['title'][:52]}")
        return bead_id

    def dep(self, blocked_key: str, blocker_key: str, dep_type: str | None = None) -> None:
        blocked, blocker = self.ids.get(blocked_key), self.ids.get(blocker_key)
        if not blocked or not blocker:
            print(f"  ! skipping dep {blocked_key} <- {blocker_key}: unknown key")
            return
        args = ["--dolt-auto-commit", "batch", "dep", "add", blocked, blocker]
        if dep_type:
            args += ["--type", dep_type]
        self.bd(args, ok_stderr=("already exists", "duplicate", "already has"))
        self.linked += 1

    def close_if_done(self, key: str, item: dict) -> None:
        if item.get("status") != "closed" or self.dry_run or key not in self.ids:
            return
        try:
            self.bd(
                ["--dolt-auto-commit", "batch", "close", self.ids[key],
                 "--reason", "delivered before beads adoption"],
                ok_stderr=("already closed", "is closed"),
            )
        except RuntimeError as exc:
            if "open child" in str(exc).lower():
                try:
                    self.bd(
                        ["--dolt-auto-commit", "batch", "update", self.ids[key],
                         "--status", "closed", "--force"],
                        ok_stderr=("already closed", "is closed"),
                    )
                    return
                except RuntimeError:
                    print(f"  ! not closing {key} ({self.ids[key]}): open children remain")
                    return
            raise

    def defer_if_later(self, key: str, item: dict) -> None:
        if item.get("status") != "deferred" or self.dry_run or key not in self.ids:
            return
        self.bd(
            ["--dolt-auto-commit", "batch", "defer", self.ids[key],
             "--reason", "later phase; not on the ready queue"],
            ok_stderr=("already deferred", "is deferred", "not open"),
        )

    def walk_close_and_defer(self, plan: dict) -> None:
        for d in plan.get("decisions", []):
            self.close_if_done(d["key"], d)
        for epic in plan["epics"]:
            for feat in epic.get("features", []):
                for story in feat.get("stories", []):
                    for task in story.get("tasks", []):
                        self.close_if_done(task["key"], task)
                        self.defer_if_later(task["key"], task)
                    self.close_if_done(story["key"], story)
                    self.defer_if_later(story["key"], story)
                for task in feat.get("tasks", []):
                    self.close_if_done(task["key"], task)
                    self.defer_if_later(task["key"], task)
                self.close_if_done(feat["key"], feat)
                self.defer_if_later(feat["key"], feat)
            self.close_if_done(epic["key"], epic)
            self.defer_if_later(epic["key"], epic)

    def save(self) -> None:
        if not self.dry_run:
            IDMAP.write_text(json.dumps(self.ids, indent=2, sort_keys=True) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--prune", action="store_true", help="report drift, do not delete")
    args = ap.parse_args()

    if not args.dry_run and not shutil.which("bd"):
        print("bd not found on PATH. Install it, or run with --dry-run.", file=sys.stderr)
        return 1

    try:
        import yaml
    except ImportError:
        print("PyYAML required: pip install PyYAML", file=sys.stderr)
        return 1

    plan = yaml.safe_load(PLAN.read_text())
    s = Sync(args.dry_run)

    print("decisions")
    for d in plan.get("decisions", []):
        s.create(d["key"], d, "decision")

    for epic in plan["epics"]:
        print(f"\n{epic['key']} {epic['title']}")
        epic_id = s.create(epic["key"], epic, "epic")

        for feat in epic.get("features", []):
            feat_id = s.create(feat["key"], feat, "feature", parent=epic_id)

            for story in feat.get("stories", []):
                story_id = s.create(story["key"], story, "story", parent=feat_id)
                prev_task_key = None
                for task in story.get("tasks", []):
                    s.create(task["key"], task, "task", parent=story_id)
                    if prev_task_key:
                        s.dep(task["key"], prev_task_key)
                    prev_task_key = task["key"]

            # v1 leftover: tasks hanging directly under a feature
            prev_task_key = None
            for task in feat.get("tasks", []):
                s.create(task["key"], task, "task", parent=feat_id)
                if prev_task_key:
                    s.dep(task["key"], prev_task_key)
                prev_task_key = task["key"]

            for adr in feat.get("implements", []):
                s.dep(feat["key"], adr, dep_type="related")

    print("\ncross cutting dependencies")
    for edge in plan.get("dependencies", []):
        s.dep(edge["blocked"], edge["blocker"])

    s.save()

    print("\nclosing already delivered items and deferring later phases")
    s.walk_close_and_defer(plan)

    s.save()
    if not args.dry_run:
        try:
            s.bd(["dolt", "commit", "--message", "beads-sync product map"], ok_stderr=("nothing to commit", "no changes"))
        except RuntimeError as exc:
            print(f"  ! dolt commit: {exc}")
    print(f"\ncreated {s.created}, existing {s.skipped}, dependencies {s.linked}")

    if args.prune:
        planned = set(s.ids)
        print(f"\nplan keys tracked: {len(planned)}")
        print("run 'bd list --json' and compare metadata.plan_key to find orphans")

    if not args.dry_run:
        print("\nnext: bd ready --explain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
