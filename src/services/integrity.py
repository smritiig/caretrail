import json
from typing import Any

import boto3

from src.models.audit_event import AuditEvent
from src.services.hashing import calculate_event_hash


def verify_audit_event(
    event_id: str,
    table_name: str,
    bucket_name: str,
    dynamodb_resource: Any = None,
    s3_client: Any = None,
) -> dict:
    dynamodb = dynamodb_resource or boto3.resource("dynamodb")
    s3 = s3_client or boto3.client("s3")

    table = dynamodb.Table(table_name)

    response = table.get_item(
        Key={
            "event_id": event_id,
        }
    )

    stored_item = response.get("Item")

    if not stored_item:
        return {
            "event_id": event_id,
            "status": "NOT_FOUND",
        }

    archive_key = stored_item["archive_key"]
    archive_version_id = stored_item["archive_version_id"]

    archived_object = s3.get_object(
        Bucket=bucket_name,
        Key=archive_key,
        VersionId=archive_version_id,
    )

    archived_data = json.loads(
        archived_object["Body"].read()
    )

    archived_hash = archived_data.pop("event_hash", None)
    archived_event = AuditEvent.model_validate(archived_data)

    stored_event_data = {
        field_name: stored_item.get(field_name)
        for field_name in AuditEvent.model_fields
    }
    stored_event = AuditEvent.model_validate(stored_event_data)

    calculated_archive_hash = calculate_event_hash(
        archived_event
    )
    calculated_stored_hash = calculate_event_hash(
        stored_event
    )
    stored_hash = stored_item.get("event_hash")

    is_verified = (
        archived_hash
        == calculated_archive_hash
        == calculated_stored_hash
        == stored_hash
    )

    return {
        "event_id": event_id,
        "status": "VERIFIED" if is_verified else "FAILED",
        "event_hash": stored_hash,
        "archive_key": archive_key,
        "archive_version_id": archive_version_id,
    }