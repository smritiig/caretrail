import json

import boto3
from moto import mock_aws

from src.models.audit_event import AuditEvent
from src.services.queue import send_audit_event


def valid_audit_event() -> AuditEvent:
    return AuditEvent.model_validate(
        {
            "event_id": "evt-1001",
            "actor_id": "doctor-27",
            "patient_id": "patient-104",
            "action": "PATIENT_RECORD_VIEWED",
            "outcome": "SUCCESS",
            "occurred_at": "2026-09-20T15:30:00Z",
        }
    )


@mock_aws
def test_send_audit_event_places_message_on_queue():
    sqs = boto3.client("sqs", region_name="us-east-1")

    queue = sqs.create_queue(QueueName="caretrail-audit-events")
    queue_url = queue["QueueUrl"]

    message_id = send_audit_event(
        audit_event=valid_audit_event(),
        queue_url=queue_url,
        sqs_client=sqs,
    )

    result = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
    )

    messages = result["Messages"]
    stored_event = json.loads(messages[0]["Body"])

    assert message_id
    assert len(messages) == 1
    assert stored_event["event_id"] == "evt-1001"
    assert stored_event["actor_id"] == "doctor-27"
    assert stored_event["action"] == "PATIENT_RECORD_VIEWED"