# AI Job Application Copilot — Phase 1

A production-oriented foundation for an AI-assisted job application workspace. Phase 1 provides account management, authentication, a protected dashboard, database migrations, and a Docker-based local environment. It intentionally does **not** include resume parsing, AI, job discovery, matching, or application automation.

## Architecture and stack

- `frontend/`: Next.js 15, TypeScript, App Router, React Hook Form
- `backend/`: FastAPI, SQLAlchemy 2.x, Pydantic, Alembic, JWT, Argon2 password hashing
- `postgres`: PostgreSQL 16

The browser calls the FastAPI API using `NEXT_PUBLIC_API_URL`. The API persists users in PostgreSQL and issues short-lived configurable JWTs.

## Quick start with Docker

```bash
git clone <your-repository-url> ai-job-copilot
cd ai-job-copilot
cp .env.example .env
# Set JWT_SECRET to a long random value before use.
docker compose up --build
```

Open `http://localhost:3000`; API documentation is at `http://localhost:8000/docs`.

The backend runs `alembic upgrade head` before Uvicorn starts. To apply migrations manually:

```bash
docker compose exec backend alembic upgrade head
```

## Environment variables

Copy `.env.example` to `.env`. Required values are `DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `BACKEND_PORT`, `FRONTEND_PORT`, and `NEXT_PUBLIC_API_URL`. Do not use the example password or JWT secret outside local development.

## Local development

Start PostgreSQL with Compose, then in separate shells:

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

For host-local backend development set `DATABASE_URL=postgresql+psycopg://job_copilot:change_me@localhost:5432/job_copilot` and `NEXT_PUBLIC_API_URL=http://localhost:8000`.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Verifies API and database connectivity |
| POST | `/api/auth/register` | Creates a user account |
| POST | `/api/auth/login` | Returns a bearer JWT |
| GET | `/api/users/me` | Returns the authenticated user |

Passwords are Argon2-hashed; email is normalized to lowercase; `password_hash` is never returned. The frontend stores the JWT in `sessionStorage`, limiting it to the current browser session, attaches it as a bearer token, and redirects unauthenticated users to `/login`.

## Tests and verification

With the Compose stack running and migrations applied:

```bash
docker compose exec backend pytest
docker compose exec frontend npm run lint
curl http://localhost:8000/api/health
```

The backend suite checks health, registration, duplicate registration, valid/invalid login, and protected `/api/users/me` access.

## Phase 1 limitations and Phase 2

Phase 1 only establishes authentication and the dashboard shell. Phase 2 should introduce secure resume upload/storage and parsing, then build the candidate-profile workflow—without adding job scraping, browser automation, or submission automation until those are separately designed and authorized.
