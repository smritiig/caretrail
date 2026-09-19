import json

import pytest

from src.handlers.ingest_event import lambda_handler


def valid_request_body() -> dict:
    return {
        "event_id": "evt-1001",
        "actor_id": "doctor-27",
        "patient_id": "patient-104",
        "action": "PATIENT_RECORD_VIEWED",
        "outcome": "SUCCESS",
        "occurred_at": "2026-09-20T15:30:00Z",
    }


def create_api_event(body: dict) -> dict:
    return {
        "body": json.dumps(body),
    }


@pytest.fixture(autouse=True)
def mock_queue(monkeypatch):
    monkeypatch.setenv(
        "AUDIT_QUEUE_URL",
        "https://sqs.us-east-1.amazonaws.com/123456789/test-queue",
    )

    monkeypatch.setattr(
        "src.handlers.ingest_event.send_audit_event",
        lambda audit_event, queue_url: "message-123",
    )


def test_valid_request_returns_202():
    api_event = create_api_event(valid_request_body())

    response = lambda_handler(api_event, None)
    response_body = json.loads(response["body"])

    assert response["statusCode"] == 202
    assert response_body["event_id"] == "evt-1001"
    assert response_body["status"] == "accepted"


def test_valid_request_is_sent_to_queue(monkeypatch):
    captured = {}

    def fake_send(audit_event, queue_url):
        captured["event"] = audit_event
        captured["queue_url"] = queue_url
        return "message-123"

    monkeypatch.setattr(
        "src.handlers.ingest_event.send_audit_event",
        fake_send,
    )

    response = lambda_handler(
        create_api_event(valid_request_body()),
        None,
    )

    assert response["statusCode"] == 202
    assert captured["event"].event_id == "evt-1001"
    assert captured["queue_url"].endswith("/test-queue")


def test_missing_actor_id_returns_400():
    body = valid_request_body()
    del body["actor_id"]

    response = lambda_handler(create_api_event(body), None)
    response_body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert response_body["error"] == "Invalid audit event"


def test_invalid_json_returns_400():
    api_event = {
        "body": "{not valid json}",
    }

    response = lambda_handler(api_event, None)

    assert response["statusCode"] == 400


def test_missing_body_returns_400():
    response = lambda_handler({}, None)

    assert response["statusCode"] == 400


def test_missing_queue_configuration_returns_500(monkeypatch):
    monkeypatch.delenv("AUDIT_QUEUE_URL")

    response = lambda_handler(
        create_api_event(valid_request_body()),
        None,
    )

    assert response["statusCode"] == 500


def test_response_is_json():
    response = lambda_handler(
        create_api_event(valid_request_body()),
        None,
    )

    assert response["headers"]["Content-Type"] == "application/json"