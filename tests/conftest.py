from datetime import datetime, timezone
from typing import Optional

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.models.status import (
    Component,
    ComponentStatus,
    Incident,
    IncidentImpact,
    IncidentStatus,
    IncidentUpdate,
    OverallStatus,
)
from app.providers.base import StatusPageProvider


class MockProvider(StatusPageProvider):
    """A mock provider returning canned data for tests."""

    def __init__(self):
        self._incidents: list[Incident] = []
        self._components: list[Component] = [
            Component(
                id="comp-1",
                name="Chat Completions",
                status=ComponentStatus.OPERATIONAL,
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                position=1,
                page_id="page-1",
            ),
            Component(
                id="comp-2",
                name="Embeddings",
                status=ComponentStatus.OPERATIONAL,
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                position=2,
                page_id="page-1",
            ),
        ]
        self._overall = OverallStatus(
            indicator="none",
            description="All Systems Operational",
        )

    @property
    def name(self) -> str:
        return "mock"

    async def fetch_summary(self) -> tuple[OverallStatus, list[Component]]:
        return self._overall, self._components

    async def fetch_incidents(self) -> list[Incident]:
        return self._incidents

    def add_incident(self, incident: Incident):
        self._incidents.append(incident)


def make_incident(
    incident_id: str = "inc-1",
    name: str = "Elevated error rates",
    status: IncidentStatus = IncidentStatus.INVESTIGATING,
    impact: IncidentImpact = IncidentImpact.MINOR,
    update_time: Optional[datetime] = None,
    update_body: str = "We are investigating elevated error rates.",
) -> Incident:
    """Helper to create test incidents with sensible defaults."""
    ts = update_time or datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    return Incident(
        id=incident_id,
        name=name,
        status=status,
        impact=impact,
        created_at=ts,
        updated_at=ts,
        page_id="page-1",
        incident_updates=[
            IncidentUpdate(
                id=f"{incident_id}-update-1",
                body=update_body,
                status=status,
                created_at=ts,
                updated_at=ts,
                display_at=ts,
                incident_id=incident_id,
            ),
        ],
    )


@pytest.fixture
def mock_provider():
    return MockProvider()


@pytest.fixture
def app_with_mock(mock_provider):
    """Create a FastAPI app wired with the mock provider (no polling)."""
    from fastapi import FastAPI

    from app.routes import events, incidents, status
    from app.services.event_bus import EventBus

    test_app = FastAPI()
    test_app.state.provider = mock_provider
    test_app.state.event_bus = EventBus()

    test_app.include_router(status.router)
    test_app.include_router(incidents.router)
    test_app.include_router(events.router)

    return test_app


@pytest_asyncio.fixture
async def client(app_with_mock):
    transport = ASGITransport(app=app_with_mock)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
