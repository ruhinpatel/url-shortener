import pytest


@pytest.mark.asyncio
async def test_redirect_follows_to_long_url(client):
    # create
    create_resp = await client.post(
        "/shorten", json={"long_url": "https://example.com/target"}
    )
    short_code = create_resp.json()["short_code"]

    # redirect (don't follow to avoid hitting external URL)
    response = await client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/target"


@pytest.mark.asyncio
async def test_redirect_unknown_code_returns_404(client):
    response = await client.get("/doesnotexist99", follow_redirects=False)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_records_click(client, db_session):
    from app.models import Click
    from sqlalchemy import select

    create_resp = await client.post(
        "/shorten", json={"long_url": "https://example.com/click-test"}
    )
    short_code = create_resp.json()["short_code"]

    # trigger redirect — background task runs synchronously in test client
    await client.get(f"/{short_code}", follow_redirects=False)

    # allow background task to execute
    import asyncio
    await asyncio.sleep(0.1)

    clicks = (
        await db_session.execute(
            select(Click).join(Click.url).where(Click.url.has(short_code=short_code))
        )
    ).scalars().all()
    assert len(clicks) >= 1
