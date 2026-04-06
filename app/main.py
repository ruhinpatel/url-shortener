from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.cache import close_redis
from app.middleware.rate_limit import RateLimitMiddleware
from app.routes import shorten, redirect, stats, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(
    title="URL Shortener",
    description="Production-grade URL shortening service with analytics and rate limiting.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware)

app.include_router(shorten.router)
app.include_router(redirect.router)
app.include_router(stats.router)
app.include_router(health.router)
