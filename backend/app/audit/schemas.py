import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    action: str
    before_state: dict | None
    after_state: dict | None
    related_record_type: str | None
    related_record_id: uuid.UUID | None
    created_at: datetime
