import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_requests_under_limit_pass(client):
    response = await client.post("/shorten", json={"long_url": "https://example.com"})
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_requests_over_limit_return_429(client):
    import app.cache as cache_module

    # mock Redis pipeline to simulate 101 existing requests in window
    pipe = AsyncMock()
    pipe.zremrangebyscore = AsyncMock()
    pipe.zadd = AsyncMock()
    pipe.zcard = AsyncMock()
    pipe.expire = AsyncMock()
    pipe.execute = AsyncMock(return_value=[None, None, 101, None])

    throttled_redis = AsyncMock()
    throttled_redis.pipeline = MagicMock(return_value=pipe)
    throttled_redis.get = AsyncMock(return_value=None)
    throttled_redis.setex = AsyncMock()
    throttled_redis.delete = AsyncMock()
    throttled_redis.ping = AsyncMock(return_value=True)

    original = cache_module.get_redis

    async def _throttled():
        return throttled_redis

    import app.middleware.rate_limit as rl_module

    original_rl = rl_module.get_redis
    cache_module.get_redis = _throttled
    rl_module.get_redis = _throttled
    try:
        response = await client.post("/shorten", json={"long_url": "https://example.com"})
        assert response.status_code == 429
        assert "Retry-After" in response.headers
    finally:
        cache_module.get_redis = original
        rl_module.get_redis = original_rl
