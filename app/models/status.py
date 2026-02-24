from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ComponentStatus(str, Enum):
    OPERATIONAL = "operational"
    DEGRADED_PERFORMANCE = "degraded_performance"
    PARTIAL_OUTAGE = "partial_outage"
    MAJOR_OUTAGE = "major_outage"
    UNDER_MAINTENANCE = "under_maintenance"


class IncidentStatus(str, Enum):
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class IncidentImpact(str, Enum):
    NONE = "none"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class Component(BaseModel):
    id: str
    name: str
    status: ComponentStatus
    created_at: datetime
    updated_at: datetime
    position: int
    page_id: str


class IncidentUpdate(BaseModel):
    id: str
    body: str
    status: IncidentStatus
    created_at: datetime
    updated_at: datetime
    display_at: datetime
    incident_id: str


class Incident(BaseModel):
    id: str
    name: str
    status: IncidentStatus
    impact: IncidentImpact
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    page_id: str
    incident_updates: List[IncidentUpdate] = Field(default_factory=list)


class PageInfo(BaseModel):
    id: str
    name: str
    url: str
    updated_at: datetime


class OverallStatus(BaseModel):
    indicator: str
    description: str


class SummaryResponse(BaseModel):
    page: PageInfo
    status: OverallStatus
    components: List[Component]


class IncidentsResponse(BaseModel):
    incidents: List[Incident]


class ComponentsResponse(BaseModel):
    components: List[Component]
