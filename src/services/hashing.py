import hashlib
import json

from src.models.audit_event import AuditEvent


def calculate_event_hash(audit_event: AuditEvent) -> str:
    canonical_event = json.dumps(
        audit_event.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical_event.encode("utf-8")
    ).hexdigest()