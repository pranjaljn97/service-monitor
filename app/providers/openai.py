from __future__ import annotations

import httpx

from app.models.status import (
    Component,
    Incident,
    IncidentsResponse,
    OverallStatus,
    SummaryResponse,
)
from app.providers.base import StatusPageProvider


class OpenAIStatusProvider(StatusPageProvider):

    def __init__(self, base_url: str = "https://status.openai.com/api/v2"):
        self._base_url = base_url
        self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def name(self) -> str:
        return "openai"

    async def fetch_summary(self) -> tuple[OverallStatus, list[Component]]:
        resp = await self._client.get(f"{self._base_url}/summary.json")
        resp.raise_for_status()
        data = SummaryResponse.model_validate(resp.json())
        return data.status, data.components

    async def fetch_incidents(self) -> list[Incident]:
        resp = await self._client.get(f"{self._base_url}/incidents.json")
        resp.raise_for_status()
        data = IncidentsResponse.model_validate(resp.json())
        return data.incidents

    async def close(self):
        await self._client.aclose()
