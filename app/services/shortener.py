from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import URL
from app.services.hasher import encode, is_valid_custom_code
from app.cache import get_redis
from app.config import get_settings

settings = get_settings()


async def create_short_url(
    db: AsyncSession,
    long_url: str,
    custom_code: Optional[str] = None,
    expires_in_hours: Optional[int] = None,
) -> URL:
    expires_at = None
    if expires_in_hours is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

    if custom_code:
        if not is_valid_custom_code(custom_code):
            raise ValueError("Invalid custom code format")
        existing = await db.scalar(select(URL).where(URL.short_code == custom_code))
        if existing:
            raise ValueError("Custom code already taken")
        short_code = custom_code
    else:
        short_code = None  # assigned after insert

    url = URL(
        short_code=short_code or "__placeholder__",
        long_url=long_url,
        expires_at=expires_at,
        is_active=True,
        click_count=0,
    )
    db.add(url)
    await db.flush()  # get the auto-incremented id

    if not custom_code:
        url.short_code = encode(url.id)

    await db.commit()
    await db.refresh(url)

    # populate cache
    redis = await get_redis()
    ttl = (
        int((expires_at - datetime.now(timezone.utc)).total_seconds())
        if expires_at
        else settings.default_cache_ttl_seconds
    )
    if ttl > 0:
        await redis.setex(f"url:{url.short_code}", ttl, url.long_url)

    return url


async def resolve_short_url(db: AsyncSession, short_code: str) -> Optional[URL]:
    redis = await get_redis()
    cached = await redis.get(f"url:{short_code}")
    if cached:
        # still fetch the full row for expiry / active checks (lightweight)
        result = await db.scalar(
            select(URL).where(URL.short_code == short_code, URL.is_active)
        )
        return result

    result = await db.scalar(
        select(URL).where(URL.short_code == short_code, URL.is_active)
    )
    if result:
        # backfill cache
        now = datetime.now(timezone.utc)
        if result.expires_at and result.expires_at < now:
            return None  # expired
        ttl = (
            int((result.expires_at - now).total_seconds())
            if result.expires_at
            else settings.default_cache_ttl_seconds
        )
        if ttl > 0:
            await redis.setex(f"url:{short_code}", ttl, result.long_url)

    return result


async def deactivate_short_url(db: AsyncSession, short_code: str) -> bool:
    url = await db.scalar(select(URL).where(URL.short_code == short_code))
    if not url:
        return False
    url.is_active = False
    await db.commit()
    redis = await get_redis()
    await redis.delete(f"url:{short_code}")
    return True
