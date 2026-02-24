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

    async def _log_status_summary(self, provider: StatusPageProvider):
        overall, components = await provider.fetch_summary()
        non_operational = [
            c for c in components if c.status.value != "operational"
        ]
        print(f"\n{'=' * 60}")
        print(f"[{provider.name.upper()}] Overall: {overall.description}")
        print(f"  Components: {len(components)} total, {len(components) - len(non_operational)} operational")
        if non_operational:
            for c in non_operational:
                print(f"  !! {c.name}: {c.status.value}")
        print(f"{'=' * 60}")

    async def _check_for_updates(self, provider: StatusPageProvider):
        incidents = await provider.fetch_incidents()

        all_update_times = [
            u.created_at
            for inc in incidents
            for u in inc.incident_updates
        ]

        last_seen = self._last_seen.get(provider.name)

        # First poll: log current status, set watermark
        if last_seen is None:
            await self._log_status_summary(provider)

            # Show recent unresolved incidents
            unresolved = [i for i in incidents if i.status.value != "resolved"]
            if unresolved:
                print(f"\n  Active incidents ({len(unresolved)}):")
                for inc in unresolved:
                    print(f"    - {inc.name} [{inc.impact.value}] ({inc.status.value})")
                    if inc.incident_updates:
                        latest = inc.incident_updates[0]
                        if latest.body:
                            print(f"      {latest.body}")
            else:
                print("  No active incidents.")
            print()

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

        # Emit in chronological order and print to console
        for event in sorted(new_events, key=lambda e: e.timestamp):
            await self._event_bus.emit(event)
            ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{ts}] Product: {provider.name.upper()} - {event.incident_name}")
            print(f"Status: {event.new_status}")
            if event.message:
                print(f"Detail: {event.message}")
            logger.info(event.message)

        # Update watermark
        if all_update_times:
            newest = max(all_update_times)
            if newest > last_seen:
                self._last_seen[provider.name] = newest
