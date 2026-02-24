import asyncio
from datetime import datetime, timezone

import pytest

from app.models.events import StatusEvent
from app.services.event_bus import EventBus
from app.services.poller import PollingService
from tests.conftest import MockProvider, make_incident


@pytest.mark.asyncio
async def test_first_poll_sets_watermark_no_events():
    """First poll should set watermark silently without emitting events."""
    event_bus = EventBus()
    poller = PollingService(event_bus=event_bus)
    provider = MockProvider()

    provider.add_incident(make_incident(
        update_time=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
    ))

    collected: list[StatusEvent] = []
    queue = event_bus.subscribe()

    await poller._check_for_updates(provider)

    # Queue should be empty — first poll emits nothing
    assert queue.empty()
    # But watermark should be set
    assert provider.name in poller._last_seen


@pytest.mark.asyncio
async def test_new_update_emits_event():
    """A new incident update after watermark should emit exactly one event."""
    event_bus = EventBus()
    poller = PollingService(event_bus=event_bus)
    provider = MockProvider()

    provider.add_incident(make_incident(
        update_time=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
    ))

    queue = event_bus.subscribe()

    # First poll — sets watermark
    await poller._check_for_updates(provider)
    assert queue.empty()

    # Add a newer incident
    provider.add_incident(make_incident(
        incident_id="inc-2",
        name="API latency spike",
        update_time=datetime(2024, 6, 15, 13, 0, 0, tzinfo=timezone.utc),
        update_body="Latency increased for Chat Completions.",
    ))

    # Second poll — should detect the new update
    await poller._check_for_updates(provider)

    assert not queue.empty()
    event = await queue.get()
    assert event.incident_id == "inc-2"
    assert "API latency spike" in event.message


@pytest.mark.asyncio
async def test_no_change_emits_nothing():
    """Polling with no new updates should emit zero events."""
    event_bus = EventBus()
    poller = PollingService(event_bus=event_bus)
    provider = MockProvider()

    provider.add_incident(make_incident(
        update_time=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
    ))

    queue = event_bus.subscribe()

    # First poll — sets watermark
    await poller._check_for_updates(provider)

    # Second poll — same data, no changes
    await poller._check_for_updates(provider)

    assert queue.empty()
