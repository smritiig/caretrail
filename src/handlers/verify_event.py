import json
import os
from typing import Any

from src.services.integrity import verify_audit_event


def create_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(body),
    }


def lambda_handler(event: dict, context: Any) -> dict:
    table_name = os.getenv("AUDIT_TABLE_NAME")
    bucket_name = os.getenv("AUDIT_BUCKET_NAME")

    if not table_name:
        raise RuntimeError("AUDIT_TABLE_NAME is not configured")

    if not bucket_name:
        raise RuntimeError("AUDIT_BUCKET_NAME is not configured")

    path_parameters = event.get("pathParameters") or {}
    event_id = path_parameters.get("event_id")

    if not event_id:
        return create_response(
            400,
            {
                "error": "event_id is required",
            },
        )

    result = verify_audit_event(
        event_id=event_id,
        table_name=table_name,
        bucket_name=bucket_name,
    )

    if result["status"] == "NOT_FOUND":
        return create_response(404, result)

    if result["status"] == "FAILED":
        return create_response(409, result)

    return create_response(200, result)