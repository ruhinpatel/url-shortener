from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import URL, Click


async def record_click(
    db: AsyncSession,
    url_id: int,
    ip_address: Optional[str],
    user_agent: Optional[str],
    referrer: Optional[str],
) -> None:
    click = Click(
        url_id=url_id,
        ip_address=ip_address,
        user_agent=user_agent,
        referrer=referrer or "direct",
    )
    db.add(click)

    # increment denormalized counter
    url = await db.get(URL, url_id)
    if url:
        url.click_count = (url.click_count or 0) + 1

    await db.commit()


def _window_start(window: str) -> Optional[datetime]:
    now = datetime.now(timezone.utc)
    mapping = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}
    delta = mapping.get(window)
    return now - delta if delta else None


async def get_stats(db: AsyncSession, short_code: str, window: str = "all") -> Optional[dict]:
    url = await db.scalar(select(URL).where(URL.short_code == short_code))
    if not url:
        return None

    start = _window_start(window)

    # clicks in window
    q = select(func.count(Click.id)).where(Click.url_id == url.id)
    if start:
        q = q.where(Click.clicked_at >= start)
    clicks_in_window = await db.scalar(q) or 0

    # top referrers in window
    ref_q = (
        select(Click.referrer, func.count(Click.id).label("cnt"))
        .where(Click.url_id == url.id)
        .group_by(Click.referrer)
        .order_by(func.count(Click.id).desc())
        .limit(10)
    )
    if start:
        ref_q = ref_q.where(Click.clicked_at >= start)
    referrer_rows = (await db.execute(ref_q)).fetchall()
    top_referrers = [{"referrer": r or "direct", "count": c} for r, c in referrer_rows]

    # clicks by day in window
    day_q = (
        select(
            func.date_trunc("day", Click.clicked_at).label("day"),
            func.count(Click.id).label("cnt"),
        )
        .where(Click.url_id == url.id)
        .group_by(func.date_trunc("day", Click.clicked_at))
        .order_by(func.date_trunc("day", Click.clicked_at))
    )
    if start:
        day_q = day_q.where(Click.clicked_at >= start)
    day_rows = (await db.execute(day_q)).fetchall()
    clicks_by_day = [
        {"date": str(d.date()), "count": c} for d, c in day_rows
    ]

    return {
        "short_code": url.short_code,
        "long_url": url.long_url,
        "created_at": url.created_at,
        "total_clicks": url.click_count,
        "clicks_in_window": clicks_in_window,
        "top_referrers": top_referrers,
        "clicks_by_day": clicks_by_day,
    }
