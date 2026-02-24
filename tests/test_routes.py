import pytest

from tests.conftest import make_incident


@pytest.mark.asyncio
async def test_get_status(client):
    resp = await client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "mock"
    assert data["status"]["indicator"] == "none"
    assert data["component_count"] == 2


@pytest.mark.asyncio
async def test_get_components(client):
    resp = await client.get("/components")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["name"] == "Chat Completions"
    assert data[1]["name"] == "Embeddings"


@pytest.mark.asyncio
async def test_list_incidents_empty(client):
    resp = await client.get("/incidents")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_incidents_with_data(client, mock_provider):
    mock_provider.add_incident(make_incident())
    resp = await client.get("/incidents")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "inc-1"


@pytest.mark.asyncio
async def test_get_incident_by_id(client, mock_provider):
    mock_provider.add_incident(make_incident())
    resp = await client.get("/incidents/inc-1")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Elevated error rates"


@pytest.mark.asyncio
async def test_get_incident_not_found(client):
    resp = await client.get("/incidents/nonexistent")
    assert resp.status_code == 404
