import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from unittest.mock import AsyncMock, MagicMock

from app.database import get_db
from app.main import app
from app.models import Base

TEST_DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/urlshortener_test"


@pytest_asyncio.fixture
async def db_session():
    # NullPool: no connection reuse across event loops — each test gets a fresh connection
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def mock_redis():
    store = {}

    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=lambda k: store.get(k))
    redis.setex = AsyncMock(side_effect=lambda k, ttl, v: store.update({k: v}))
    redis.delete = AsyncMock(side_effect=lambda k: store.pop(k, None))
    redis.ping = AsyncMock(return_value=True)

    pipe = AsyncMock()
    pipe.zremrangebyscore = AsyncMock()
    pipe.zadd = AsyncMock()
    pipe.zcard = AsyncMock()
    pipe.expire = AsyncMock()
    pipe.execute = AsyncMock(return_value=[None, None, 1, None])
    redis.pipeline = MagicMock(return_value=pipe)

    return redis


@pytest_asyncio.fixture
async def client(db_session, mock_redis):
    app.dependency_overrides[get_db] = lambda: db_session

    import app.cache as cache_module

    original_get_redis = cache_module.get_redis

    async def _mock_get_redis():
        return mock_redis

    cache_module.get_redis = _mock_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    cache_module.get_redis = original_get_redis
    # reset the Redis singleton so it doesn't leak across event loops
    cache_module._redis_client = None
