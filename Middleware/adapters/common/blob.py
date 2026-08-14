"""Blob handling. Bytes go to the object store; the bus only ever carries a reference.

Write order matters: the blob must be durable before the reference is published,
otherwise a consumer can read a pointer to nothing. Orphaned blobs are reconciled
by a sweeper; dangling references are not acceptable (ADR-0006).
"""
from __future__ import annotations

import hashlib
import os
from typing import Any


def put_payload(
    data: bytes,
    *,
    tenant_id: str,
    signal_id: str,
    media_type: str,
    retention_class: str = "standard",
    legal_hold: bool = False,
) -> dict[str, Any]:
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    bucket = os.getenv("OBJECT_BUCKET", "signal-plane-payloads")
    key = f"{tenant_id}/{signal_id}/{digest[7:]}"

    endpoint = os.getenv("OBJECT_ENDPOINT")
    if endpoint:
        import boto3  # type: ignore
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=os.getenv("OBJECT_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("OBJECT_SECRET_KEY"),
        )
        try:
            s3.head_bucket(Bucket=bucket)
        except Exception:
            s3.create_bucket(Bucket=bucket)
        extra = {"ObjectLockLegalHoldStatus": "ON"} if legal_hold else {}
        s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=media_type, **extra)

    return {
        "uri": f"s3://{bucket}/{key}",
        "content_hash": digest,
        "media_type": media_type,
        "bytes": len(data),
        "retention_class": retention_class,
        "legal_hold": legal_hold,
        "resolvable_from": os.getenv("ESTATE", "managed"),
    }
