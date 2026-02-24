from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from app.models.events import EventType, StatusEvent
from app.providers.base import StatusPageProvider
from app.services.event_bus import EventBus

logger = logging.getLogger(__name__)


class PollingService:

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._tasks: list[asyncio.Task] = []
        self._last_seen: dict[str, datetime] = {}

    def start(self, provider: StatusPageProvider, interval_seconds: int):
        task = asyncio.create_task(
            self._poll_loop(provider, interval_seconds),
            name=f"poll-{provider.name}",
        )
        self._tasks.append(task)

    async def stop(self):
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _poll_loop(self, provider: StatusPageProvider, interval: int):
        logger.info("Polling %s every %ds", provider.name, interval)
        while True:
            try:
                await self._check_for_updates(provider)
            except Exception:
                logger.exception("Error polling %s", provider.name)
            await asyncio.sleep(interval)

    async def _check_for_updates(self, provider: StatusPageProvider):
        incidents = await provider.fetch_incidents()

        all_update_times = [
            u.created_at
            for inc in incidents
            for u in inc.incident_updates
        ]

        last_seen = self._last_seen.get(provider.name)

        # First poll: set watermark silently, don't flood with historical data
        if last_seen is None:
            if all_update_times:
                self._last_seen[provider.name] = max(all_update_times)
            logger.info("Initial poll for %s complete, watermark set", provider.name)
            return

        # Subsequent polls: detect new updates
        new_events: list[StatusEvent] = []
        for incident in incidents:
            for update in incident.incident_updates:
                if update.created_at <= last_seen:
                    continue

                message = (
                    f"[{provider.name.upper()}] {incident.name} "
                    f"- Status: {update.status.value}"
                )
                if update.body:
                    message += f" - {update.body}"

                event = StatusEvent(
                    event_type=EventType.INCIDENT_UPDATED,
                    provider=provider.name,
                    timestamp=update.created_at,
                    incident_id=incident.id,
                    incident_name=incident.name,
                    new_status=update.status.value,
                    message=message,
                )
                new_events.append(event)

        # Emit in chronological order
        for event in sorted(new_events, key=lambda e: e.timestamp):
            await self._event_bus.emit(event)
            logger.info(event.message)

        # Update watermark
        if all_update_times:
            newest = max(all_update_times)
            if newest > last_seen:
                self._last_seen[provider.name] = newest
