from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class EventType(str, Enum):
    NEW_INCIDENT = "new_incident"
    INCIDENT_UPDATED = "incident_updated"
    COMPONENT_STATUS_CHANGED = "component_status_changed"


class StatusEvent(BaseModel):
    event_type: EventType
    provider: str
    timestamp: datetime
    incident_id: Optional[str] = None
    incident_name: Optional[str] = None
    component_name: Optional[str] = None
    old_status: Optional[str] = None
    new_status: str
    message: str
