import json

import pytest

from src.handlers.process_event import lambda_handler


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
def configure_table(monkeypatch):
    monkeypatch.setenv(
        "AUDIT_TABLE_NAME",
        "caretrail-audit-events",
    )


def test_valid_message_is_processed(monkeypatch):
    captured = {}

    def fake_save(audit_event, table_name):
        captured["event"] = audit_event
        captured["table_name"] = table_name
        return True

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
    def fake_save(audit_event, table_name):
        return True

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