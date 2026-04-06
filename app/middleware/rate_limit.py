import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.cache import get_redis
from app.config import get_settings

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter backed by Redis sorted sets.
    - POST /shorten : 100 req/min per IP
    - GET /{code}   : 1000 req/min per IP  (excludes /health and /stats)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        method = request.method
        ip = request.client.host if request.client else "unknown"

        if path.startswith("/health") or path.startswith("/stats") or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        if method == "POST" and path == "/shorten":
            limit = settings.rate_limit_shorten_per_minute
            bucket = f"rl:shorten:{ip}"
        elif method == "GET":
            limit = settings.rate_limit_redirect_per_minute
            bucket = f"rl:redirect:{ip}"
        else:
            return await call_next(request)

        now = time.time()
        window_start = now - 60.0

        try:
            redis = await get_redis()
            pipe = redis.pipeline()
            pipe.zremrangebyscore(bucket, "-inf", window_start)
            pipe.zadd(bucket, {str(now): now})
            pipe.zcard(bucket)
            pipe.expire(bucket, 60)
            results = await pipe.execute()
            count = results[2]
        except Exception:
            # if Redis is unavailable, let the request through
            return await call_next(request)

        if count > limit:
            retry_after = 60
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
