from __future__ import annotations

from fastapi import APIRouter, Request

from app.models.status import Component, OverallStatus

router = APIRouter(tags=["status"])


@router.get("/status")
async def get_status(request: Request) -> dict:
    provider = request.app.state.provider
    overall, components = await provider.fetch_summary()
    return {
        "provider": provider.name,
        "status": overall.model_dump(),
        "component_count": len(components),
    }


@router.get("/components")
async def get_components(request: Request) -> list[Component]:
    provider = request.app.state.provider
    _, components = await provider.fetch_summary()
    return components
