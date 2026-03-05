# Docker Deployment

This project now supports Docker-based local and production deployment for:
- API service (`FastAPI`)
- MySQL
- Redis

## Local deployment

1. Review/edit [.env.local](/c:/Users/Lenovo/Work%20Place/Lakshman/copytrade/.env.local).
2. Start all services:

```bash
docker compose --env-file .env.local -f deploy/docker-compose.local.yml up --build
```

Local stack behavior:
- API available on `http://localhost:${API_PORT}` (default `8000`)
- Hot reload enabled (`uvicorn --reload`)
- MySQL and Redis ports exposed for local tools

## Production deployment

1. Update secrets in [.env.production](/c:/Users/Lenovo/Work%20Place/Lakshman/copytrade/.env.production).
2. Start production stack:

```bash
docker compose --env-file .env.production -f deploy/docker-compose.prod.yml up --build -d
```

Production stack behavior:
- No code bind-mount
- No reload mode
- Restart policy `always`

## Notes

- API container runs migrations automatically on startup:
  - `alembic upgrade head`
- Internal postback auth is controlled by:
  - `INTERNAL_POSTBACK_TOKEN`
- DB URL and Redis URL are injected by compose:
  - `DATABASE_URL=mysql+aiomysql://...@mysql:3306/...`
  - `REDIS_URL=redis://redis:6379/0`
