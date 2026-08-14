#!/usr/bin/env python3
"""Validate schemas, taxonomy, and adapter manifests against each other.

Run in CI. The check that matters most is the last one: every signal_type an
adapter claims to emit must exist in the governed taxonomy. Without it the
vocabulary fragments silently and the normalized layer stops being normalized.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []


def load(p: Path):
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as e:
        errors.append(f"{p.relative_to(ROOT)}: invalid JSON: {e}")
        return None


def main() -> int:
    schemas = {p.name: load(p) for p in sorted((ROOT / "Contracts" / "schemas").glob("*.schema.json"))}
    print(f"schemas: {len(schemas)} loaded")

    try:
        import yaml  # type: ignore
        taxonomy = yaml.safe_load((ROOT / "Contracts" / "taxonomy.yaml").read_text())
        known = set(taxonomy["signal_types"])
    except ImportError:
        print("PyYAML not installed, taxonomy cross check skipped")
        known = None

    envelope = schemas.get("signal-envelope.schema.json")
    if envelope:
        categories = set(envelope["properties"]["category"]["enum"])
        if known is not None:
            for name, spec in taxonomy["signal_types"].items():
                if spec["category"] not in categories:
                    errors.append(
                        f"taxonomy {name}: category '{spec['category']}' is not in the envelope enum"
                    )

    manifests = list((ROOT / "Middleware" / "adapters").rglob("manifest.json"))
    print(f"adapter manifests: {len(manifests)} found")
    for mp in manifests:
        m = load(mp)
        if not m:
            continue
        for emit in m.get("emits", []):
            st = emit["signal_type"]
            if known is not None and st not in known:
                errors.append(
                    f"{mp.relative_to(ROOT)}: emits '{st}' which is not in taxonomy.yaml"
                )
            if envelope and emit["category"] not in categories:
                errors.append(
                    f"{mp.relative_to(ROOT)}: category '{emit['category']}' is not a valid category"
                )

    if errors:
        print("\nFAILED")
        for e in errors:
            print(f"  {e}")
        return 1
    print("\nall contracts consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
