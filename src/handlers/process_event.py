import json
import os
from typing import Any

from src.models.audit_event import AuditEvent
from src.repositories.audit_repository import save_audit_event


def lambda_handler(event: dict, context: Any) -> dict:
    table_name = os.getenv("AUDIT_TABLE_NAME")

    if not table_name:
        raise RuntimeError("AUDIT_TABLE_NAME is not configured")

    failed_messages = []

    for record in event.get("Records", []):
        message_id = record.get("messageId", "unknown")

        try:
            message_body = json.loads(record["body"])
            audit_event = AuditEvent.model_validate(message_body)

            save_audit_event(
                audit_event=audit_event,
                table_name=table_name,
            )

        except Exception:
            failed_messages.append(
                {
                    "itemIdentifier": message_id,
                }
            )

    return {
        "batchItemFailures": failed_messages,
    }