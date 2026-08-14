"""Reference adapter: watches a directory and emits file_action signals.

Deliberately trivial as a source. It exists to demonstrate the adapter shape end to
end: request authority, map source events into the envelope, emit to the bus. A real
adapter differs only in the mapping function.

Local:  python3 -m Middleware.adapters.sources.directory_watch.handler --once
Lambda: handler(event, context)
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from Middleware.adapters.common.authority import request_decision
from Middleware.adapters.common.envelope import AdapterContext, Emitter

MANIFEST = json.loads((Path(__file__).parent / "manifest.json").read_text())
CAPTURE_MODE = "passive_metadata"
REMOVABLE_HINTS = ("/media/", "/mnt/removable", "/Volumes/")


def _classify(path: Path) -> tuple[str, str]:
    if any(h in str(path) for h in REMOVABLE_HINTS):
        return "file_action.copy_to_removable", "file_action"
    return "file_action.modify", "file_action"


def scan(root: Path, ctx: AdapterContext, subject_id: str) -> list[dict]:
    envelopes = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        stat = p.stat()
        signal_type, category = _classify(p)
        envelopes.append(
            ctx.build(
                subject_id=subject_id,
                signal_type=signal_type,
                category=category,
                occurred_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z"),
                native_id=f"{p}:{stat.st_mtime_ns}",
                attributes={
                    "path": str(p),
                    "bytes": stat.st_size,
                    "volume_kind": "removable"
                    if signal_type.endswith("copy_to_removable")
                    else "local",
                },
                raw_identifiers=[{"kind": "device_id", "value": os.uname().nodename}],
            )
        )
    return envelopes


def run(root: Path, tenant_id: str, subject_id: str) -> int:
    authority = request_decision(
        tenant_id=tenant_id, subject_id=subject_id, capture_mode=CAPTURE_MODE
    )
    ctx = AdapterContext(
        adapter_id=MANIFEST["adapter_id"],
        adapter_version=MANIFEST["version"],
        source_system=MANIFEST["source_system"],
        tenant_id=tenant_id,
        estate=os.getenv("ESTATE", "managed"),
        authority=authority,
    )
    envelopes = scan(root, ctx, subject_id)
    emitted = Emitter().emit(envelopes)
    print(f"emitted {emitted} signals from {root}", flush=True)
    return emitted


def handler(event, context):  # AWS Lambda entry point
    return {
        "emitted": run(
            Path(event.get("root", "/tmp/watch")),
            event["tenant_id"],
            event["subject_id"],
        )
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.getenv("WATCH_ROOT", "/tmp/watch"))
    ap.add_argument("--tenant", default=os.getenv("TENANT_ID", "tenant-demo"))
    ap.add_argument("--subject", default="subject-0001")
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    if not any(root.iterdir()):
        (root / "quarterly-forecast.xlsx").write_text("demo")
        (root / "client-list.csv").write_text("demo")
    run(root, args.tenant, args.subject)
