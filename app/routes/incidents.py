from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.models.status import Incident

router = APIRouter(tags=["incidents"])


@router.get("/incidents")
async def list_incidents(request: Request) -> list[Incident]:
    provider = request.app.state.provider
    return await provider.fetch_incidents()


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str, request: Request) -> Incident:
    provider = request.app.state.provider
    incidents = await provider.fetch_incidents()
    for inc in incidents:
        if inc.id == incident_id:
            return inc
    raise HTTPException(status_code=404, detail="Incident not found")
