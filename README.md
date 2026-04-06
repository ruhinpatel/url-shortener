# URL Shortener

A production-grade URL shortening service with click analytics, rate limiting, and TTL support.

---

## Architecture

```
Client
  │
  ▼
FastAPI (app)
  ├── Redis  ← hot-path cache, rate limiting, TTL
  └── PostgreSQL  ← durable storage, click events, analytics
```

---

## Features

- Shorten any HTTP/HTTPS URL with an auto-generated or custom code
- 307 redirect with async click tracking (zero latency impact)
- Per-IP sliding-window rate limiting via Redis
- Optional TTL / link expiration
- Click analytics with time-window filtering and referrer breakdown
- Health check endpoint for monitoring
- Auto-generated OpenAPI docs at `/docs`

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + uvicorn |
| Cache | Redis 7 |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2 (async) + Alembic |
| Testing | pytest + httpx |
| Containers | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Linting | ruff |

---

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env

# 2. Start all services
docker compose up --build

# 3. Run migrations
docker compose exec app alembic upgrade head

# API is now live at http://localhost:8000
# Interactive docs: http://localhost:8000/docs
```

---

## API

### POST /shorten
```bash
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"long_url": "https://example.com/very/long/path", "expires_in_hours": 72}'
```

### GET /{short_code}
Redirects (307) to the original URL. Click is recorded asynchronously.

### GET /stats/{short_code}?window=7d
Returns click analytics. `window` options: `24h`, `7d`, `30d`, `all`.

### GET /health
Returns status of Redis and PostgreSQL connections.

---

## Design Decisions

**Base62 over random hashes**
Using the PostgreSQL auto-increment ID as the input to base62 encoding guarantees uniqueness without any collision checks or retry loops. A 6-character base62 code handles 56+ billion URLs. Random hashes require a uniqueness check on every write.

**Redis + PostgreSQL instead of Redis-only**
Redis provides sub-millisecond reads on hot URLs and handles TTL expiry natively. PostgreSQL provides durability — if Redis is flushed, the data survives and the cache is repopulated on the next read (cache-aside pattern). Redis-only would risk data loss on restart.

**Async click tracking via BackgroundTasks**
Recording a click requires a database write. Doing this synchronously on the redirect path would add latency to every redirect. Using FastAPI's `BackgroundTasks` defers the write until after the 307 response is sent, keeping redirects fast.

**Sliding window over fixed window rate limiting**
A fixed window counter resets on the clock boundary, allowing a burst of 2× the limit at the boundary edge (end of one window + start of next). A sliding window (implemented with a Redis sorted set keyed by timestamp) provides smoother, consistent throttling.

---

## Testing

```bash
# Run unit + integration tests with coverage
pytest --cov=app --cov-report=term-missing

# Coverage target: 85%+
```

Tests use a real PostgreSQL test database and mock Redis. The CI pipeline spins up both as service containers.

---

## Future Improvements

- **Authentication** — API keys or OAuth for private links and dashboards
- **Link management dashboard** — UI for viewing, editing, and deactivating links
- **Geographic analytics** — IP geolocation (e.g. MaxMind) for country-level click breakdowns
- **Horizontal scaling** — Redis Cluster for distributed rate limiting across multiple app instances
- **QR code generation** — return a QR code alongside the short URL on creation
