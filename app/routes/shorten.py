from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ShortenRequest, ShortenResponse
from app.services.shortener import create_short_url
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(payload: ShortenRequest, db: AsyncSession = Depends(get_db)):
    try:
        url = await create_short_url(
            db=db,
            long_url=payload.long_url,
            custom_code=payload.custom_code,
            expires_in_hours=payload.expires_in_hours,
        )
    except ValueError as exc:
        msg = str(exc)
        if "already taken" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return ShortenResponse(
        short_code=url.short_code,
        short_url=f"{settings.base_url}/{url.short_code}",
        long_url=url.long_url,
        created_at=url.created_at,
        expires_at=url.expires_at,
    )
