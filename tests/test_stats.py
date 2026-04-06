import pytest


@pytest.mark.asyncio
async def test_stats_returns_data(client):
    create_resp = await client.post(
        "/shorten", json={"long_url": "https://example.com/stats-test"}
    )
    short_code = create_resp.json()["short_code"]

    response = await client.get(f"/stats/{short_code}")
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == short_code
    assert data["long_url"] == "https://example.com/stats-test"
    assert "total_clicks" in data
    assert "clicks_in_window" in data
    assert isinstance(data["top_referrers"], list)
    assert isinstance(data["clicks_by_day"], list)


@pytest.mark.asyncio
async def test_stats_unknown_code_returns_404(client):
    response = await client.get("/stats/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stats_window_param(client):
    create_resp = await client.post(
        "/shorten", json={"long_url": "https://example.com/window-test"}
    )
    short_code = create_resp.json()["short_code"]

    for window in ("24h", "7d", "30d", "all"):
        response = await client.get(f"/stats/{short_code}?window={window}")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_stats_invalid_window_rejected(client):
    create_resp = await client.post(
        "/shorten", json={"long_url": "https://example.com/w-invalid"}
    )
    short_code = create_resp.json()["short_code"]
    response = await client.get(f"/stats/{short_code}?window=bogus")
    assert response.status_code == 422
