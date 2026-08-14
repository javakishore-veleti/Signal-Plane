"""Envelope construction, hashing, and emission.

Every adapter builds signals through this module. Adapters own source specific
mapping and nothing else; identity, hashing, validation, and emission are shared
so that adapter N+1 cannot drift from the contract.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "1.0"
NAMESPACE = uuid.UUID("6f1c2a5e-0b4d-5f8a-9c3e-7d2b1a4f6e80")
REPO_ROOT = Path(__file__).resolve().parents[3]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def deterministic_signal_id(tenant_id: str, adapter_id: str, native_id: str) -> str:
    """Same source event always yields the same id.

    This is what makes replay idempotent and lets the query broker merge results
    from two estates without producing duplicates during migration.
    """
    return str(uuid.uuid5(NAMESPACE, f"{tenant_id}|{adapter_id}|{native_id}"))


def content_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


@dataclass
class AuthorityContext:
    """Cached for the bounded lifetime of a session. Adapters fail closed on expiry."""
    decision_id: str
    basis: str
    policy_version: str
    jurisdiction: str | None = None
    expires_at: str | None = None

    def is_expired(self, now: datetime | None = None) -> bool:
        if not self.expires_at:
            return False
        now = now or datetime.now(timezone.utc)
        return now >= datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))


@dataclass
class AdapterContext:
    adapter_id: str
    adapter_version: str
    source_system: str
    tenant_id: str
    estate: str = "managed"
    authority: AuthorityContext | None = None
    _chain: dict[str, str] = field(default_factory=dict)

    def build(
        self,
        *,
        subject_id: str,
        signal_type: str,
        category: str,
        occurred_at: str,
        native_id: str,
        attributes: dict[str, Any] | None = None,
        payload_ref: dict[str, Any] | None = None,
        raw_identifiers: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        if self.authority is None:
            raise PermissionError(
                f"no authority decision held for subject {subject_id}; capture refused"
            )
        if self.authority.is_expired():
            raise PermissionError(
                f"authority decision {self.authority.decision_id} expired; capture refused"
            )

        body = {
            "schema_version": SCHEMA_VERSION,
            "signal_id": deterministic_signal_id(self.tenant_id, self.adapter_id, native_id),
            "tenant_id": self.tenant_id,
            "source": {
                "adapter_id": self.adapter_id,
                "adapter_version": self.adapter_version,
                "source_system": self.source_system,
                "source_native_id": native_id,
                "estate": self.estate,
            },
            "subject": {
                "subject_id": subject_id,
                "raw_identifiers": raw_identifiers or [],
            },
            "occurred_at": occurred_at,
            "observed_at": _now(),
            "ingested_at": _now(),
            "category": category,
            "signal_type": signal_type,
            "attributes": attributes or {},
            "authority": {
                "decision_id": self.authority.decision_id,
                "basis": self.authority.basis,
                "jurisdiction": self.authority.jurisdiction,
                "policy_version": self.authority.policy_version,
            },
        }
        if payload_ref:
            body["payload_ref"] = payload_ref

        chain_key = f"{self.tenant_id}|{subject_id}"
        integrity: dict[str, str] = {"content_hash": content_hash(body)}
        prev = self._chain.get(chain_key)
        if prev:
            integrity["prev_hash"] = prev
        self._chain[chain_key] = integrity["content_hash"]

        body["integrity"] = integrity
        return body


def topic_for(category: str) -> str:
    return f"signals.{category}"


class Emitter:
    """Publishes envelopes to the bus. Falls back to stdout when no broker is present,
    so an adapter can be exercised without any infrastructure at all."""

    def __init__(self, bootstrap: str | None = None) -> None:
        self.bootstrap = bootstrap or os.getenv("BUS_BOOTSTRAP", "")
        self._producer = None
        if self.bootstrap:
            try:
                from confluent_kafka import Producer  # type: ignore
                self._producer = Producer({"bootstrap.servers": self.bootstrap})
            except Exception:
                self._producer = None

    def emit(self, envelopes: Iterable[dict[str, Any]]) -> int:
        count = 0
        for env in envelopes:
            payload = json.dumps(env).encode()
            key = f"{env['tenant_id']}|{env['subject']['subject_id']}".encode()
            if self._producer is not None:
                self._producer.produce(topic_for(env["category"]), key=key, value=payload)
            else:
                print(payload.decode())
            count += 1
        if self._producer is not None:
            self._producer.flush(10)
        return count
