from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter(tags=["events"])


@router.get("/events/stream")
async def event_stream(request: Request):
    event_bus = request.app.state.event_bus

    async def generate():
        async for event in event_bus.stream():
            yield {
                "event": event.event_type.value,
                "data": event.model_dump_json(),
            }

    return EventSourceResponse(generate())
