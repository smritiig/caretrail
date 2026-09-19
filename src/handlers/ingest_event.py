import json
import os
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError
from pydantic import ValidationError

from src.models.audit_event import AuditEvent
from src.services.queue import send_audit_event


def create_response(status_code: int, body: dict[str, Any]) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(body),
    }


def lambda_handler(event: dict, context: Any) -> dict:
    try:
        request_body = json.loads(event.get("body") or "{}")
        audit_event = AuditEvent.model_validate(request_body)

    except (json.JSONDecodeError, ValidationError, TypeError):
        return create_response(
            400,
            {
                "error": "Invalid audit event",
            },
        )

    queue_url = os.getenv("AUDIT_QUEUE_URL")

    if not queue_url:
        return create_response(
            500,
            {
                "error": "Service configuration error",
            },
        )

    try:
        send_audit_event(
            audit_event=audit_event,
            queue_url=queue_url,
        )

    except (BotoCoreError, ClientError):
        return create_response(
            503,
            {
                "error": "Unable to accept audit event",
            },
        )

    return create_response(
        202,
        {
            "event_id": audit_event.event_id,
            "status": "accepted",
        },
    )