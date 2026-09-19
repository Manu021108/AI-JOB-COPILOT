# AI Job Copilot

A full-stack job-search copilot. Upload a resume to build a structured candidate profile, then track the jobs you're applying to — added manually, imported from a URL, or generated from a pasted job description — with automatic analysis of requirements, skills, and salary.

## Features

**Phase 1 — Accounts**
- JWT sign-up / sign-in, `GET /api/users/me`, CORS-enabled API.

**Phase 2 — Resume Intelligence**
- Upload a resume (`.pdf`, `.docx`) stored in Postgres with versioning.
- Text extraction and offline heuristic parsing into a structured candidate profile (skills, experience, projects, education, certifications).
- Profile completeness score and inline profile editor.
- LLM analysis (openai) with mock/offline fallback when no API key is configured.

**Phase 3 — Job Intelligence & Job Ingestion**
- Three ways to add a job: import from a public URL, paste a full job description, or manual entry.
- URL import is SSRF-guarded (http/https only, private/reserved IPs, `.local`/`.internal` hosts and DNS rebinding blocked; every redirect hop re-validated), respects `robots.txt`, enforces a response size limit, and never touches LinkedIn (users are told to paste the description instead).
- A per-user sliding-window rate limit on URL imports.
- Deterministic offline analyzer (mock provider) or the configured LLM extracts structured data: required/preferred/nice-to-have skills, responsibilities, qualifications, education, experience range, employment details, salary and currency, work mode, posting date and application URL.
- Anti-hallucination rules — nothing is invented; missing values are `null`/`[]`.
- Jobs, analyses and skills persisted in Postgres (`jobs`, `job_analysis`, `job_skills`).
- Duplicate detection by source URL / application URL / source job id and a normalized `company|title|location` key (per user).
- List with search, filters (status, work mode, company, location, source), pagination and sorting; edit, delete, and re-analysis (replaces the stored analysis without clobbering your edits).
- Frontend: Jobs dashboard (`/jobs`), Add-Job modal with all three input modes, and a job detail page (`/jobs/[id]`) with edit, delete and re-analyze actions.

## Stack

| Layer | Tech |
| --- | --- |
| API | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, psycopg3 |
| Database | PostgreSQL 16 |
| AI | httpx-based LLM client (OpenAI-compatible) with an offline `mock` provider as default |
| Web | Next.js 15 (App Router), React 19, TypeScript |
| Infra | Docker Compose |

## Repo layout

```
backend/
  app/
    api/            # FastAPI routers (auth, users, resumes, profile, jobs)
    ai/             # LLM client, openai provider, mock provider, analyzers
    core/           # settings, DB session, responses, rate limiting
    models/         # SQLAlchemy models (user, resume, profile, job, job_analysis, job_skills)
    schemas/        # Pydantic schemas incl. structured analyzer output
    services/       # parsers, normalizers, skill taxonomy, job sources, URL security
  alembic/          # migrations (001 auth, 002 resume tables, 003 job intelligence)
tests/
frontend/
  app/              # pages (/, /login, /register, /dashboard, /resume, /jobs, /jobs/[id])
  components/       # Navbar, Sidebar, ProtectedRoute, resume + job components
  lib/api.ts        # typed API client
  types/            # shared response types
docker-compose.yml
.env.example
```

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- API docs (Swagger): http://localhost:8000/docs
- Health check: `GET /api/health`

### Local development (backend)

Requires PostgreSQL running locally (or adjust `DATABASE_URL`).

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows (POSIX: source .venv/bin/activate)
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Running tests

```bash
cd backend
$env:DATABASE_URL="postgresql+psycopg://job_copilot:change_me@localhost:5432/job_copilot"
$env:JWT_SECRET="test-only-secret"
.venv\Scripts\python.exe -m pytest tests -q
```

Tests use the offline `mock` analyzer and fake HTTP fetches for URL imports — no API keys or network required.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | local Postgres | SQLAlchemy connection string |
| `JWT_SECRET` | — | Secret used to sign tokens |
| `LLM_PROVIDER` | `mock` | `mock` (offline heuristics) or `openai` (OpenAI-compatible API) |
| `LLM_API_KEY` / `LLM_MODEL` / `LLM_BASE_URL` | — | Required when `LLM_PROVIDER=openai` |
| `JOB_FETCH_CONNECT_TIMEOUT` | `5` | Connect timeout (seconds) for URL imports |
| `JOB_FETCH_TIMEOUT` | `20` | Overall request timeout (seconds) |
| `JOB_FETCH_MAX_SIZE` | `2000000` | Max response body size in bytes |
| `JOB_FETCH_MAX_REDIRECTS` | `5` | Max redirect hops followed per import |
| `JOB_IMPORT_RATE_LIMIT` / `JOB_IMPORT_RATE_WINDOW` | `20` / `60` | Per-user URL import rate limit (sliding window) |

## Job intelligence pipeline

1. **Ingest** — manual form, pasted description, or a fetched public job page.
   - URL fetch: scheme + DNS-rebinding check → `robots.txt` policy → size-limited, redirect-revalidated GET. LinkedIn, private/reserved hosts, unsupported schemes, unpublishable content and oversized pages are rejected with a specific error code.
2. **Clean** — the description is normalized line-by-line; navigation/boilerplate lines are dropped but the document structure is preserved.
3. **Analyze** — the LLM (or the deterministic mock parser) extracts structured data. The prompt treats the job description as untrusted input and instructs the model never to follow instructions inside it and never to invent facts. Output is validated by a Pydantic schema before anything is persisted.
4. **Persist** — one `jobs` row plus one `job_analysis` row (JSONB fields) and normalized `job_skills` rows.
5. **Deduplicate** — source URL, application URL, source job id, then a normalized key hash; duplicates return `409 DUPLICATE_JOB` and are never re-inserted.

## API overview (Phase 3)

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/jobs` | Create a job manually |
| `POST` | `/api/jobs/from-description` | Create + analyze from a pasted description |
| `POST` | `/api/jobs/import-url` | Fetch, clean and analyze a public job URL |
| `GET` | `/api/jobs` | List with `search`, `company`, `location`, `source`, `status`, `work_mode`, `sort`, `page`, `page_size` |
| `GET` / `PUT` / `DELETE` | `/api/jobs/{id}` | Read / update / delete a job |
| `POST` | `/api/jobs/{id}/analyze` | Run / re-run analysis |
| `GET` | `/api/jobs/{id}/analysis` | Read the stored analysis |

All endpoints require a bearer token and are scoped to the authenticated user. Errors follow the envelope `{"success": false, "error": {"code", "message"}}`.

## Known limitations

- The default `mock` analyzer is heuristic by design (works offline, deterministic tests). Use `LLM_PROVIDER=openai` for stronger extraction.
- LinkedIn pages are intentionally never fetched (anti-bot/paywall + terms). The UI directs users to paste the description instead.
- URL import is a simple fetch + HTML-to-text parse; job boards with heavy JavaScript rendering may yield little content (reported as `EMPTY_URL_CONTENT`).
- The URL import rate limiter is in-memory (per process). Swap `app/core/rate_limit.py` for Redis when running multiple instances.
- Job matching/shortlisting, cover letters, applications and interview prep are planned in follow-up phases.