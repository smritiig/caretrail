from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class AuditAction(str, Enum):
    PATIENT_RECORD_VIEWED = "PATIENT_RECORD_VIEWED"


class AuditOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    DENIED = "DENIED"
    FAILURE = "FAILURE"


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    actor_id: str
    patient_id: str
    action: AuditAction
    outcome: AuditOutcome
    occurred_at: datetime