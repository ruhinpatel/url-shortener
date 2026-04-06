import time
from fastapi import APIRouter
from sqlalchemy import text

from app.database import engine
from app.cache import get_redis
from app.schemas import HealthResponse

router = APIRouter()
_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    redis_status = "disconnected"
    postgres_status = "disconnected"

    try:
        redis = await get_redis()
        await redis.ping()
        redis_status = "connected"
    except Exception:
        pass

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        postgres_status = "connected"
    except Exception:
        pass

    overall = (
        "healthy" if redis_status == "connected" and postgres_status == "connected" else "degraded"
    )

    return HealthResponse(
        status=overall,
        redis=redis_status,
        postgres=postgres_status,
        uptime_seconds=round(time.time() - _start_time, 2),
    )
