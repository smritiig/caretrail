import json

import boto3
from moto import mock_aws

from src.handlers.ingest_event import lambda_handler as ingest_handler
from src.handlers.process_event import lambda_handler as process_handler


TABLE_NAME = "caretrail-audit-events"
BUCKET_NAME = "caretrail-audit-archive-test"


def create_audit_event() -> dict:
    return {
        "event_id": "evt-1001",
        "actor_id": "doctor-27",
        "patient_id": "patient-104",
        "action": "PATIENT_RECORD_VIEWED",
        "outcome": "SUCCESS",
        "occurred_at": "2026-09-20T15:30:00Z",
    }


@mock_aws
def test_complete_audit_pipeline(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    sqs = boto3.client("sqs", region_name="us-east-1")
    s3 = boto3.client("s3", region_name="us-east-1")
    dynamodb = boto3.resource(
        "dynamodb",
        region_name="us-east-1",
    )

    queue = sqs.create_queue(
        QueueName="caretrail-audit-events",
    )
    queue_url = queue["QueueUrl"]

    s3.create_bucket(Bucket=BUCKET_NAME)
    s3.put_bucket_versioning(
        Bucket=BUCKET_NAME,
        VersioningConfiguration={
            "Status": "Enabled",
        },
    )

    table = dynamodb.create_table(
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

    monkeypatch.setenv("AUDIT_QUEUE_URL", queue_url)
    monkeypatch.setenv("AUDIT_TABLE_NAME", TABLE_NAME)
    monkeypatch.setenv("AUDIT_BUCKET_NAME", BUCKET_NAME)

    api_gateway_event = {
        "body": json.dumps(create_audit_event()),
    }

    ingest_response = ingest_handler(
        api_gateway_event,
        None,
    )

    assert ingest_response["statusCode"] == 202

    received = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
    )

    sqs_message = received["Messages"][0]

    lambda_sqs_event = {
        "Records": [
            {
                "messageId": sqs_message["MessageId"],
                "body": sqs_message["Body"],
            }
        ]
    }

    process_response = process_handler(
        lambda_sqs_event,
        None,
    )

    assert process_response == {
        "batchItemFailures": [],
    }

    stored_item = table.get_item(
        Key={
            "event_id": "evt-1001",
        }
    )["Item"]

    assert stored_item["event_id"] == "evt-1001"
    assert stored_item["actor_id"] == "doctor-27"
    assert stored_item["patient_id"] == "patient-104"
    assert stored_item["action"] == "PATIENT_RECORD_VIEWED"
    assert stored_item["outcome"] == "SUCCESS"

    assert stored_item["archive_key"] == (
        "audit-events/2026/09/20/evt-1001.json"
    )
    assert stored_item["archive_version_id"]

    archived_object = s3.get_object(
        Bucket=BUCKET_NAME,
        Key=stored_item["archive_key"],
        VersionId=stored_item["archive_version_id"],
    )

    archived_event = json.loads(
        archived_object["Body"].read()
    )

    assert archived_event["event_id"] == "evt-1001"
    assert archived_event["actor_id"] == "doctor-27"
    assert archived_event["event_hash"] == stored_item["event_hash"]