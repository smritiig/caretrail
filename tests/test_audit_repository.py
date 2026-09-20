import boto3
from moto import mock_aws

from src.models.audit_event import AuditEvent
from src.repositories.audit_repository import save_audit_event
from src.services.hashing import calculate_event_hash

TABLE_NAME = "caretrail-audit-events"


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


def create_table(dynamodb):
    return dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {
                "AttributeName": "event_id",
                "KeyType": "HASH",
            }
        ],
        AttributeDefinitions=[
            {
                "AttributeName": "event_id",
                "AttributeType": "S",
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )


@mock_aws
def test_save_audit_event():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = create_table(dynamodb)

    inserted = save_audit_event(
        audit_event=valid_audit_event(),
        table_name=TABLE_NAME,
        dynamodb_resource=dynamodb,
    )

    stored_item = table.get_item(
        Key={"event_id": "evt-1001"}
    )["Item"]

    assert inserted is True
    assert stored_item["actor_id"] == "doctor-27"
    assert stored_item["patient_id"] == "patient-104"
    assert stored_item["outcome"] == "SUCCESS"
    assert stored_item["event_hash"] == calculate_event_hash(
    valid_audit_event()
)


@mock_aws
def test_duplicate_event_is_not_inserted_twice():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = create_table(dynamodb)
    event = valid_audit_event()

    first_result = save_audit_event(
        audit_event=event,
        table_name=TABLE_NAME,
        dynamodb_resource=dynamodb,
    )

    second_result = save_audit_event(
        audit_event=event,
        table_name=TABLE_NAME,
        dynamodb_resource=dynamodb,
    )

    stored_items = table.scan()["Items"]

    assert first_result is True
    assert second_result is False
    assert len(stored_items) == 1