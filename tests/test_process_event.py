import json

import pytest

from src.handlers.process_event import lambda_handler
from src.services.archive import ArchiveResult


def valid_message_body() -> dict:
    return {
        "event_id": "evt-1001",
        "actor_id": "doctor-27",
        "patient_id": "patient-104",
        "action": "PATIENT_RECORD_VIEWED",
        "outcome": "SUCCESS",
        "occurred_at": "2026-09-20T15:30:00Z",
    }


def create_sqs_record(message_id: str, body: dict) -> dict:
    return {
        "messageId": message_id,
        "body": json.dumps(body),
    }


@pytest.fixture(autouse=True)
def configure_worker(monkeypatch):
    monkeypatch.setenv(
        "AUDIT_TABLE_NAME",
        "caretrail-audit-events",
    )
    monkeypatch.setenv(
        "AUDIT_BUCKET_NAME",
        "caretrail-audit-archive",
    )


def test_valid_message_is_processed(monkeypatch):
    captured = {}

    def fake_archive(audit_event, bucket_name):
        captured["bucket_name"] = bucket_name
        return ArchiveResult(
            object_key="audit-events/2026/09/20/evt-1001.json",
            version_id="version-123",
        )

    def fake_save(
        audit_event,
        table_name,
        archive_key,
        archive_version_id,
    ):
        captured["event"] = audit_event
        captured["table_name"] = table_name
        captured["archive_key"] = archive_key
        captured["archive_version_id"] = archive_version_id
        return True

    monkeypatch.setattr(
        "src.handlers.process_event.archive_audit_event",
        fake_archive,
    )
    monkeypatch.setattr(
        "src.handlers.process_event.save_audit_event",
        fake_save,
    )

    sqs_event = {
        "Records": [
            create_sqs_record(
                "message-1",
                valid_message_body(),
            )
        ]
    }

    response = lambda_handler(sqs_event, None)

    assert response == {"batchItemFailures": []}
    assert captured["event"].event_id == "evt-1001"
    assert captured["table_name"] == "caretrail-audit-events"
    assert captured["bucket_name"] == "caretrail-audit-archive"
    assert captured["archive_key"] == (
        "audit-events/2026/09/20/evt-1001.json"
    )
    assert captured["archive_version_id"] == "version-123"


def test_invalid_message_is_reported_as_failed():
    invalid_body = valid_message_body()
    del invalid_body["actor_id"]

    sqs_event = {
        "Records": [
            create_sqs_record(
                "message-2",
                invalid_body,
            )
        ]
    }

    response = lambda_handler(sqs_event, None)

    assert response == {
        "batchItemFailures": [
            {
                "itemIdentifier": "message-2",
            }
        ]
    }


def test_only_failed_message_is_retried(monkeypatch):
    def fake_archive(audit_event, bucket_name):
        return ArchiveResult(
            object_key="audit-events/2026/09/20/evt-1001.json",
            version_id="version-123",
        )

    def fake_save(
        audit_event,
        table_name,
        archive_key,
        archive_version_id,
    ):
        return True

    monkeypatch.setattr(
        "src.handlers.process_event.archive_audit_event",
        fake_archive,
    )
    monkeypatch.setattr(
        "src.handlers.process_event.save_audit_event",
        fake_save,
    )

    invalid_body = valid_message_body()
    invalid_body["action"] = "INVALID_ACTION"

    sqs_event = {
        "Records": [
            create_sqs_record(
                "message-1",
                valid_message_body(),
            ),
            create_sqs_record(
                "message-2",
                invalid_body,
            ),
        ]
    }

    response = lambda_handler(sqs_event, None)

    assert response == {
        "batchItemFailures": [
            {
                "itemIdentifier": "message-2",
            }
        ]
    }


def test_missing_table_configuration_raises_error(monkeypatch):
    monkeypatch.delenv("AUDIT_TABLE_NAME")

    with pytest.raises(RuntimeError):
        lambda_handler({"Records": []}, None)


def test_missing_bucket_configuration_raises_error(monkeypatch):
    monkeypatch.delenv("AUDIT_BUCKET_NAME")

    with pytest.raises(RuntimeError):
        lambda_handler({"Records": []}, None)