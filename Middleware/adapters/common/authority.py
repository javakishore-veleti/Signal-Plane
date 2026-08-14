"""Client for the control plane authority gate.

Adapters resolve a decision once per session and cache it for the session's bounded
lifetime, so the control plane never sits on the telemetry path (ADR-0005).
When the gate is unreachable and no unexpired decision is cached, capture stops.
Fail closed is the only correct behaviour here.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import requests

from .envelope import AuthorityContext


class AuthorityDenied(PermissionError):
    pass


def request_decision(
    *, tenant_id: str, subject_id: str, capture_mode: str, timeout: float = 3.0
) -> AuthorityContext:
    base = os.getenv("CONTROL_PLANE_URL")
    if not base:
        # Offline development path. Explicitly time bounded so that the local
        # behaviour still exercises expiry and fail closed handling.
        return AuthorityContext(
            decision_id="local-dev-decision",
            basis="legitimate_interest",
            policy_version="local-0",
            jurisdiction="US-NC",
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=1))
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
        )

    import requests  # imported lazily so the offline path needs no dependencies

    resp = requests.post(
        f"{base}/v1/authority/decisions",
        json={"tenant_id": tenant_id, "subject_id": subject_id, "capture_mode": capture_mode},
        timeout=timeout,
    )
    resp.raise_for_status()
    body = resp.json()
    if not body.get("granted"):
        raise AuthorityDenied(body.get("denial_reason", "capture not authorised"))

    return AuthorityContext(
        decision_id=body["decision_id"],
        basis=body["basis"],
        policy_version=body["policy_version"],
        jurisdiction=body.get("jurisdiction"),
        expires_at=body.get("expires_at"),
    )
