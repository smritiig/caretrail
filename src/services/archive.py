import json
from dataclasses import dataclass
from typing import Any

import boto3

from src.models.audit_event import AuditEvent
from src.services.hashing import calculate_event_hash


@dataclass(frozen=True)
class ArchiveResult:
    object_key: str
    version_id: str


def archive_audit_event(
    audit_event: AuditEvent,
    bucket_name: str,
    s3_client: Any = None,
) -> ArchiveResult:
    event_data = audit_event.model_dump(mode="json")
    event_data["event_hash"] = calculate_event_hash(audit_event)

    object_key = (
        f"audit-events/"
        f"{audit_event.occurred_at:%Y/%m/%d}/"
        f"{audit_event.event_id}.json"
    )

    object_body = json.dumps(
        event_data,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    client = s3_client or boto3.client("s3")

    response = client.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=object_body,
        ContentType="application/json",
        ServerSideEncryption="AES256",
        ChecksumAlgorithm="SHA256",
    )

    version_id = response.get("VersionId")

    if not version_id:
        raise RuntimeError("S3 did not return an object version ID")

    return ArchiveResult(
        object_key=object_key,
        version_id=version_id,
    )