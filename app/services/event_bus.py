from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from app.models.events import StatusEvent


class EventBus:
    """In-process async event bus.

    Producers call emit(event). Consumers call stream() to get an async
    generator that yields events. Each consumer gets its own queue so a
    slow consumer cannot block others.
    """

    def __init__(self):
        self._subscribers: list[asyncio.Queue[StatusEvent]] = []

    async def emit(self, event: StatusEvent):
        for queue in self._subscribers:
            await queue.put(event)

    def subscribe(self) -> asyncio.Queue[StatusEvent]:
        queue: asyncio.Queue[StatusEvent] = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[StatusEvent]):
        self._subscribers.remove(queue)

    async def stream(self) -> AsyncGenerator[StatusEvent, None]:
        queue = self.subscribe()
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self.unsubscribe(queue)
