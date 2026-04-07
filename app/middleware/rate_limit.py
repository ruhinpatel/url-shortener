import time

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.cache import get_redis
from app.config import get_settings

settings = get_settings()

_EXCLUDED = ("/health", "/docs", "/openapi", "/stats")


class RateLimitMiddleware:
    """
    Pure ASGI sliding-window rate limiter backed by Redis sorted sets.
    Avoids BaseHTTPMiddleware to prevent anyio task-group event-loop conflicts.
    - POST /shorten : 100 req/min per IP
    - GET /{code}   : 1000 req/min per IP
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        method: str = scope.get("method", "")

        if any(path.startswith(p) for p in _EXCLUDED):
            await self.app(scope, receive, send)
            return

        if method == "POST" and path == "/shorten":
            limit = settings.rate_limit_shorten_per_minute
            bucket = f"rl:shorten:{self._ip(scope)}"
        elif method == "GET":
            limit = settings.rate_limit_redirect_per_minute
            bucket = f"rl:redirect:{self._ip(scope)}"
        else:
            await self.app(scope, receive, send)
            return

        now = time.time()
        try:
            redis = await get_redis()
            pipe = redis.pipeline()
            pipe.zremrangebyscore(bucket, "-inf", now - 60.0)
            pipe.zadd(bucket, {str(now): now})
            pipe.zcard(bucket)
            pipe.expire(bucket, 60)
            results = await pipe.execute()
            count = results[2]
        except Exception:
            await self.app(scope, receive, send)
            return

        if count > limit:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": "60"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    @staticmethod
    def _ip(scope: Scope) -> str:
        client = scope.get("client")
        return client[0] if client else "unknown"
