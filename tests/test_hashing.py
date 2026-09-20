from src.models.audit_event import AuditEvent
from src.services.hashing import calculate_event_hash


def create_event() -> AuditEvent:
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


def test_same_event_produces_same_hash():
    first_hash = calculate_event_hash(create_event())
    second_hash = calculate_event_hash(create_event())

    assert first_hash == second_hash
    assert len(first_hash) == 64


def test_changed_event_produces_different_hash():
    original = create_event()

    changed = original.model_copy(
        update={
            "patient_id": "patient-999",
        }
    )

    assert calculate_event_hash(original) != calculate_event_hash(changed)