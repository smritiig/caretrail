import json
from typing import Any

import boto3

from src.models.audit_event import AuditEvent


def send_audit_event(
    audit_event: AuditEvent,
    queue_url: str,
    sqs_client: Any = None,
) -> str:
    client = sqs_client or boto3.client("sqs")

    message_body = audit_event.model_dump_json()

    response = client.send_message(
        QueueUrl=queue_url,
        MessageBody=message_body,
    )

    return response["MessageId"]