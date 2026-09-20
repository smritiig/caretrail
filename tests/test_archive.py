import json

from src.models.audit_event import AuditEvent
from src.services.archive import archive_audit_event


class FakeS3Client:
    def __init__(self):
        self.request = None

    def put_object(self, **kwargs):
        self.request = kwargs
        return {
            "VersionId": "version-123",
        }


def test_event_is_archived_with_hash_and_version():
    audit_event = AuditEvent(
        event_id="evt-1001",
        actor_id="doctor-27",
        patient_id="patient-104",
        action="PATIENT_RECORD_VIEWED",
        outcome="SUCCESS",
        occurred_at="2026-09-20T15:30:00Z",
    )
    fake_s3 = FakeS3Client()

    result = archive_audit_event(
        audit_event=audit_event,
        bucket_name="test-audit-bucket",
        s3_client=fake_s3,
    )

    archived_event = json.loads(fake_s3.request["Body"])

    assert result.object_key == (
        "audit-events/2026/09/20/evt-1001.json"
    )
    assert result.version_id == "version-123"
    assert fake_s3.request["Bucket"] == "test-audit-bucket"
    assert fake_s3.request["Key"] == result.object_key
    assert fake_s3.request["ChecksumAlgorithm"] == "SHA256"
    assert archived_event["event_id"] == "evt-1001"
    assert len(archived_event["event_hash"]) == 64