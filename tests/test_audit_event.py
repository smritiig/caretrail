from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models.audit_event import (
    AuditAction,
    AuditEvent,
    AuditOutcome,
)


def valid_event_data() -> dict:
    return {
        "event_id": "evt-1001",
        "actor_id": "doctor-27",
        "patient_id": "patient-104",
        "action": "PATIENT_RECORD_VIEWED",
        "outcome": "SUCCESS",
        "occurred_at": "2026-09-20T15:30:00Z",
    }


def test_valid_audit_event():
    event = AuditEvent.model_validate(valid_event_data())

    assert event.event_id == "evt-1001"
    assert event.actor_id == "doctor-27"
    assert event.action == AuditAction.PATIENT_RECORD_VIEWED
    assert event.outcome == AuditOutcome.SUCCESS
    assert isinstance(event.occurred_at, datetime)


def test_missing_actor_id_is_rejected():
    data = valid_event_data()
    del data["actor_id"]

    with pytest.raises(ValidationError):
        AuditEvent.model_validate(data)


def test_invalid_action_is_rejected():
    data = valid_event_data()
    data["action"] = "DELETE_HOSPITAL"

    with pytest.raises(ValidationError):
        AuditEvent.model_validate(data)


def test_invalid_timestamp_is_rejected():
    data = valid_event_data()
    data["occurred_at"] = "yesterday afternoon"

    with pytest.raises(ValidationError):
        AuditEvent.model_validate(data)


def test_unexpected_field_is_rejected():
    data = valid_event_data()
    data["password"] = "secret"

    with pytest.raises(ValidationError):
        AuditEvent.model_validate(data)