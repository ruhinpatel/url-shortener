import pytest


@pytest.mark.asyncio
async def test_create_short_url(client):
    response = await client.post("/shorten", json={"long_url": "https://example.com/path"})
    assert response.status_code == 201
    data = response.json()
    assert data["long_url"] == "https://example.com/path"
    assert "short_code" in data
    assert data["short_url"].endswith(data["short_code"])
    assert data["expires_at"] is None


@pytest.mark.asyncio
async def test_create_with_expiry(client):
    response = await client.post(
        "/shorten", json={"long_url": "https://example.com", "expires_in_hours": 72}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["expires_at"] is not None


@pytest.mark.asyncio
async def test_create_with_custom_code(client):
    response = await client.post(
        "/shorten", json={"long_url": "https://example.com", "custom_code": "mylink"}
    )
    assert response.status_code == 201
    assert response.json()["short_code"] == "mylink"


@pytest.mark.asyncio
async def test_custom_code_conflict(client):
    await client.post(
        "/shorten", json={"long_url": "https://example.com", "custom_code": "taken"}
    )
    response = await client.post(
        "/shorten", json={"long_url": "https://other.com", "custom_code": "taken"}
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_invalid_url_rejected(client):
    response = await client.post("/shorten", json={"long_url": "not-a-url"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_custom_code_rejected(client):
    response = await client.post(
        "/shorten", json={"long_url": "https://example.com", "custom_code": "a"}
    )
    assert response.status_code == 422
