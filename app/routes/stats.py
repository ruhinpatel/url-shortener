from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import StatsResponse
from app.services.analytics import get_stats

router = APIRouter()

VALID_WINDOWS = {"24h", "7d", "30d", "all"}


@router.get("/stats/{short_code}", response_model=StatsResponse)
async def get_url_stats(
    short_code: str,
    window: str = Query(default="all", pattern="^(24h|7d|30d|all)$"),
    db: AsyncSession = Depends(get_db),
):
    data = await get_stats(db, short_code, window)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")
    return StatsResponse(**data)
