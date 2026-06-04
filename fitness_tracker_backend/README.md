# Fitness Tracker Backend (FastAPI)

FastAPI backend providing:
- JWT authentication (email/password) with role support (`user`, `admin`)
- Onboarding/preferences + profile
- Goals CRUD
- Workout plan get/regenerate (rules-based)
- Workout logs CRUD (+ entries)
- Nutrition logs CRUD (optional)
- Progress summaries
- Admin content management (content pages)
- WebSocket endpoint for real-time notifications

## Environment variables

This service expects these environment variables (set in `.env`):

- `DATABASE_URL` (required): SQLAlchemy DSN for Postgres, e.g. `postgresql+asyncpg://user:pass@host:5432/db`
- `JWT_SECRET` (required): secret for signing JWTs
- `JWT_ALGORITHM` (optional): default `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES` (optional): default `10080` (7 days)
- `CORS_ORIGINS` (optional): comma-separated origins; use `*` for dev (not recommended for prod)
- `LOG_LEVEL` (optional): default `INFO`

A `.env.example` is provided.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

OpenAPI docs:
- http://localhost:8000/docs
- http://localhost:8000/openapi.json

## WebSocket

Connect to:

`ws://<host>:<port>/ws/notifications?token=<JWT>`

The backend will push events like:
- `notification.created`
- `progress.updated`
- `plan.regenerated`

You can also call `POST /notifications/test` to generate a test notification for the current user (useful for verifying WS from frontend).

## Notes

- The database schema is defined by the database container (`fitness_tracker_database/schema.sql`).
- Password hashing uses bcrypt.
- The ORM is SQLAlchemy 2.0 (async) with `asyncpg`.
- Role-based endpoints require `role=admin` in `app_user`.
