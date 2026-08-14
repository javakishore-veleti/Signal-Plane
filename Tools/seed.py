#!/usr/bin/env python3
"""Seed the local policy store and register adapter manifests.

Idempotent: safe to run repeatedly.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def psql(sql: str) -> int:
    return subprocess.call([
        "docker", "compose", "exec", "-T", "policy-store",
        "psql", "-U", "signalplane", "-d", "signalplane", "-v", "ON_ERROR_STOP=1", "-c", sql,
    ], cwd=ROOT)


def main() -> int:
    manifests = list((ROOT / "adapters").rglob("manifest.json"))
    print(f"registering {len(manifests)} adapter manifest(s)")
    for mp in manifests:
        m = json.loads(mp.read_text())
        payload = json.dumps(m).replace("'", "''")
        rc = psql(
            "INSERT INTO adapter_registration (adapter_id, version, manifest) "
            f"VALUES ('{m['adapter_id']}', '{m['version']}', '{payload}'::jsonb) "
            "ON CONFLICT (adapter_id, version) DO UPDATE SET manifest = EXCLUDED.manifest;"
        )
        if rc != 0:
            print("policy store unreachable; run 'make up' first", file=sys.stderr)
            return rc
        print(f"  {m['adapter_id']} {m['version']}")

    psql("SELECT tenant_id, scoring_model_version FROM tenant;")
    psql("SELECT subject_id, jurisdiction FROM subject;")
    print("\nseed complete")
    print("note: subject-0002 is in DE, where only PASSIVE_METADATA is permitted")
    print("      and the approver is the works council. Try requesting")
    print("      CONTINUOUS_SCREEN for that subject to see the gate deny it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
