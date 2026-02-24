from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.status import Component, Incident, OverallStatus


class StatusPageProvider(ABC):
    """Base class for status page providers.

    Each provider knows how to fetch data from one specific status page
    platform (incident.io, Atlassian Statuspage, Cachet, etc.).
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def fetch_summary(self) -> tuple[OverallStatus, list[Component]]: ...

    @abstractmethod
    async def fetch_incidents(self) -> list[Incident]: ...
