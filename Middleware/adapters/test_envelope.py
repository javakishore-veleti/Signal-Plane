"""Contract tests. Every adapter's output is validated against the schema in CI,
which is what stops adapter N+1 from drifting away from the envelope (ADR-0003).
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from Middleware.adapters.common.envelope import (
    AdapterContext,
    AuthorityContext,
    deterministic_signal_id,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "Contracts" / "schemas" / "signal-envelope.schema.json").read_text())


def _validator():
    schema = dict(SCHEMA)
    # payload_ref resolves by $ref in production; drop it for isolated unit tests
    schema["properties"] = {k: v for k, v in schema["properties"].items() if k != "payload_ref"}
    return Draft202012Validator(schema)


def _ctx(expires_in_hours: float = 1.0) -> AdapterContext:
    exp = (datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")
    return AdapterContext(
        adapter_id="test_source",
        adapter_version="0.0.1",
        source_system="test",
        tenant_id="tenant-demo",
        authority=AuthorityContext("d-1", "notice", "p-1", "US-NC", exp),
    )


def _build(ctx, native_id="n-1", subject="subject-0001"):
    return ctx.build(
        subject_id=subject,
        signal_type="file_action.modify",
        category="file_action",
        occurred_at="2026-08-14T10:00:00.000Z",
        native_id=native_id,
        attributes={"path": "/tmp/a", "bytes": 12, "volume_kind": "local"},
    )


def test_envelope_matches_schema():
    _validator().validate(_build(_ctx()))


def test_signal_id_is_deterministic():
    a = deterministic_signal_id("t", "adapter", "native")
    b = deterministic_signal_id("t", "adapter", "native")
    assert a == b, "federated merge across estates depends on this"


def test_hash_chain_links_consecutive_signals():
    ctx = _ctx()
    first = _build(ctx, "n-1")
    second = _build(ctx, "n-2")
    assert second["integrity"]["prev_hash"] == first["integrity"]["content_hash"]


def test_chain_is_per_subject():
    ctx = _ctx()
    _build(ctx, "n-1", "subject-A")
    other = _build(ctx, "n-2", "subject-B")
    assert "prev_hash" not in other["integrity"]


def test_capture_refused_without_authority():
    ctx = _ctx()
    ctx.authority = None
    with pytest.raises(PermissionError):
        _build(ctx)


def test_capture_refused_after_expiry():
    with pytest.raises(PermissionError, match="expired"):
        _build(_ctx(expires_in_hours=-1))
