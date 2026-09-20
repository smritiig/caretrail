import boto3
from moto import mock_aws

from src.models.audit_event import AuditEvent
from src.repositories.audit_repository import save_audit_event
from src.services.archive import archive_audit_event
from src.services.integrity import verify_audit_event


TABLE_NAME = "caretrail-audit-events"
BUCKET_NAME = "caretrail-audit-archive-test"


def create_event() -> AuditEvent:
    return AuditEvent(
        event_id="evt-1001",
        actor_id="doctor-27",
        patient_id="patient-104",
        action="PATIENT_RECORD_VIEWED",
        outcome="SUCCESS",
        occurred_at="2026-09-20T15:30:00Z",
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


def prepare_event(dynamodb, s3):
    table = create_table(dynamodb)

    s3.create_bucket(Bucket=BUCKET_NAME)
    s3.put_bucket_versioning(
        Bucket=BUCKET_NAME,
        VersioningConfiguration={
            "Status": "Enabled",
        },
    )

    event = create_event()

    archive_result = archive_audit_event(
        audit_event=event,
        bucket_name=BUCKET_NAME,
        s3_client=s3,
    )

    save_audit_event(
        audit_event=event,
        table_name=TABLE_NAME,
        archive_key=archive_result.object_key,
        archive_version_id=archive_result.version_id,
        dynamodb_resource=dynamodb,
    )

    return table


@mock_aws
def test_untampered_event_is_verified():
    dynamodb = boto3.resource(
        "dynamodb",
        region_name="us-east-1",
    )
    s3 = boto3.client("s3", region_name="us-east-1")

    prepare_event(dynamodb, s3)

    result = verify_audit_event(
        event_id="evt-1001",
        table_name=TABLE_NAME,
        bucket_name=BUCKET_NAME,
        dynamodb_resource=dynamodb,
        s3_client=s3,
    )

    assert result["status"] == "VERIFIED"
    assert result["event_id"] == "evt-1001"
    assert result["archive_version_id"]


@mock_aws
def test_modified_database_event_fails_verification():
    dynamodb = boto3.resource(
        "dynamodb",
        region_name="us-east-1",
    )
    s3 = boto3.client("s3", region_name="us-east-1")

    table = prepare_event(dynamodb, s3)

    table.update_item(
        Key={
            "event_id": "evt-1001",
        },
        UpdateExpression="SET patient_id = :patient",
        ExpressionAttributeValues={
            ":patient": "tampered-patient",
        },
    )

    result = verify_audit_event(
        event_id="evt-1001",
        table_name=TABLE_NAME,
        bucket_name=BUCKET_NAME,
        dynamodb_resource=dynamodb,
        s3_client=s3,
    )

    assert result["status"] == "FAILED"


@mock_aws
def test_missing_event_returns_not_found():
    dynamodb = boto3.resource(
        "dynamodb",
        region_name="us-east-1",
    )
    s3 = boto3.client("s3", region_name="us-east-1")

    create_table(dynamodb)
    s3.create_bucket(Bucket=BUCKET_NAME)

    result = verify_audit_event(
        event_id="missing-event",
        table_name=TABLE_NAME,
        bucket_name=BUCKET_NAME,
        dynamodb_resource=dynamodb,
        s3_client=s3,
    )

    assert result == {
        "event_id": "missing-event",
        "status": "NOT_FOUND",
    }