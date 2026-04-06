from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.shortener import resolve_short_url
from app.services.analytics import record_click

router = APIRouter()


@router.get("/{short_code}")
async def redirect_to_url(
    short_code: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    url = await resolve_short_url(db, short_code)
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")

    now = datetime.now(timezone.utc)
    if url.expires_at and url.expires_at < now:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This URL has expired")

    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    referrer = request.headers.get("referer")

    background_tasks.add_task(record_click, db, url.id, ip, user_agent, referrer)

    return RedirectResponse(url=url.long_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
