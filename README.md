# Service Monitor API

A FastAPI service that tracks the OpenAI Status Page for incidents, outages, and degradations in real time. Uses smart polling with change detection on ingestion and exposes an SSE endpoint for event-driven push to consumers.

## Architecture

```
OpenAI Status API  --(poll every 60s)-->  PollingService
                                              |
                                       (detect changes via
                                        timestamp watermark)
                                              |
                                         emit StatusEvent
                                              |
                                           EventBus
                                          /        \
                                         v          v
                                Console Logger   SSE /events/stream

GET /status, /incidents, /components --> Provider (direct fetch)
```

### Key Components

| Component | Description |
|---|---|
| **StatusPageProvider** (ABC) | Abstract base with 3 methods (`name`, `fetch_summary`, `fetch_incidents`). New providers implement this interface. |
| **OpenAIStatusProvider** | Concrete provider hitting `status.openai.com/api/v2` JSON APIs via `httpx.AsyncClient`. |
| **PollingService** | Background `asyncio.Task` per provider. Uses a timestamp watermark to detect new incident updates. First poll sets the watermark silently to avoid flooding with historical data. |
| **EventBus** | In-process async pub/sub. Each SSE subscriber gets its own `asyncio.Queue` so a slow client cannot block others. |
| **SSE Endpoint** | `/events/stream` pushes `StatusEvent` objects to connected clients via `sse-starlette`. |

### Project Structure

```
service-monitor/
├── app/
│   ├── main.py              # FastAPI app, lifespan, router mounting
│   ├── config.py            # pydantic-settings (SM_ env prefix)
│   ├── models/
│   │   ├── status.py        # Component, Incident, IncidentUpdate, OverallStatus
│   │   └── events.py        # StatusEvent envelope
│   ├── providers/
│   │   ├── base.py          # StatusPageProvider ABC
│   │   └── openai.py        # OpenAI implementation
│   ├── services/
│   │   ├── poller.py        # Background polling with change detection
│   │   └── event_bus.py     # Async pub/sub
│   └── routes/
│       ├── status.py        # GET /status, GET /components
│       ├── incidents.py     # GET /incidents, GET /incidents/{id}
│       └── events.py        # GET /events/stream (SSE)
├── tests/
│   ├── conftest.py          # Mock provider, test fixtures
│   ├── test_poller.py       # Change detection unit tests
│   └── test_routes.py       # API endpoint integration tests
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/status` | Current overall status (indicator + component count) |
| `GET` | `/components` | List all tracked components with their status |
| `GET` | `/incidents` | List recent incidents |
| `GET` | `/incidents/{id}` | Single incident detail |
| `GET` | `/events/stream` | SSE stream of real-time status change events |

## Getting Started

### Prerequisites

- Python 3.9+
- Docker (optional, for containerized deployment)

### Run Locally

```bash
# Install dependencies
pip install .

# Copy and configure environment
cp .env.example .env

# Start the server
uvicorn app.main:app --reload
```

### Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

The server starts on `http://localhost:8000`.

### Run Tests

```bash
pip install ".[dev]"
pytest tests/ -v
```

## Configuration

All settings use the `SM_` environment variable prefix. See `.env.example` for defaults.

| Variable | Default | Description |
|---|---|---|
| `SM_OPENAI_STATUS_URL` | `https://status.openai.com/api/v2` | OpenAI status API base URL |
| `SM_OPENAI_POLL_INTERVAL` | `60` | Polling interval in seconds |
| `SM_HOST` | `0.0.0.0` | Server bind host |
| `SM_PORT` | `8000` | Server bind port |
| `SM_LOG_LEVEL` | `INFO` | Logging level |

## Adding a New Provider

1. Create `app/providers/<name>.py` implementing `StatusPageProvider`
2. Add URL + poll interval to `app/config.py`
3. Instantiate the provider and call `poller.start()` in the lifespan (`app/main.py`)
