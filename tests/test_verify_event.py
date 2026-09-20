import json

import pytest

from src.handlers.verify_event import lambda_handler


@pytest.fixture(autouse=True)
def configure_verifier(monkeypatch):
    monkeypatch.setenv(
        "AUDIT_TABLE_NAME",
        "caretrail-audit-events",
    )
    monkeypatch.setenv(
        "AUDIT_BUCKET_NAME",
        "caretrail-audit-archive",
    )


def create_request(event_id: str) -> dict:
    return {
        "pathParameters": {
            "event_id": event_id,
        }
    }


def test_verified_event_returns_200(monkeypatch):
    def fake_verify(event_id, table_name, bucket_name):
        return {
            "event_id": event_id,
            "status": "VERIFIED",
            "event_hash": "abc123",
            "archive_key": "audit-events/event.json",
            "archive_version_id": "version-123",
        }

    monkeypatch.setattr(
        "src.handlers.verify_event.verify_audit_event",
        fake_verify,
    )

    response = lambda_handler(
        create_request("evt-1001"),
        None,
    )
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["status"] == "VERIFIED"


def test_failed_verification_returns_409(monkeypatch):
    def fake_verify(event_id, table_name, bucket_name):
        return {
            "event_id": event_id,
            "status": "FAILED",
        }

    monkeypatch.setattr(
        "src.handlers.verify_event.verify_audit_event",
        fake_verify,
    )

    response = lambda_handler(
        create_request("evt-1001"),
        None,
    )

    assert response["statusCode"] == 409


def test_missing_event_returns_404(monkeypatch):
    def fake_verify(event_id, table_name, bucket_name):
        return {
            "event_id": event_id,
            "status": "NOT_FOUND",
        }

    monkeypatch.setattr(
        "src.handlers.verify_event.verify_audit_event",
        fake_verify,
    )

    response = lambda_handler(
        create_request("missing-event"),
        None,
    )

    assert response["statusCode"] == 404


def test_missing_event_id_returns_400():
    response = lambda_handler(
        {
            "pathParameters": None,
        },
        None,
    )

    assert response["statusCode"] == 400