import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings
from app.providers.openai import OpenAIStatusProvider
from app.routes import events, incidents, status
from app.services.event_bus import EventBus
from app.services.poller import PollingService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    logging.basicConfig(level=settings.log_level)

    event_bus = EventBus()
    provider = OpenAIStatusProvider(base_url=settings.openai_status_url)
    poller = PollingService(event_bus=event_bus)

    app.state.event_bus = event_bus
    app.state.provider = provider
    app.state.settings = settings

    poller.start(provider, interval_seconds=settings.openai_poll_interval)

    yield

    await poller.stop()
    await provider.close()


app = FastAPI(title="Service Monitor", lifespan=lifespan)
app.include_router(status.router)
app.include_router(incidents.router)
app.include_router(events.router)
