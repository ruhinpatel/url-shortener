from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, field_validator
import re


class ShortenRequest(BaseModel):
    long_url: str
    custom_code: Optional[str] = None
    expires_in_hours: Optional[int] = None

    @field_validator("long_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not re.match(r"^https?://", v):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("custom_code")
    @classmethod
    def validate_custom_code(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^[a-zA-Z0-9]{3,20}$", v):
            raise ValueError("Custom code must be 3-20 alphanumeric characters")
        return v


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    long_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ClicksByDay(BaseModel):
    date: str
    count: int


class TopReferrer(BaseModel):
    referrer: str
    count: int


class StatsResponse(BaseModel):
    short_code: str
    long_url: str
    created_at: datetime
    total_clicks: int
    clicks_in_window: int
    top_referrers: List[TopReferrer]
    clicks_by_day: List[ClicksByDay]

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str
    redis: str
    postgres: str
    uptime_seconds: float
