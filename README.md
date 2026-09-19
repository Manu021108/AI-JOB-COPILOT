# AI Job Copilot

A full-stack job-search copilot. Upload a resume to build a structured candidate profile, then track the jobs you're applying to — added manually, imported from a URL, or generated from a pasted job description — with automatic analysis of requirements, skills, and salary, plus a hybrid AI match score that tells you how well every job fits your profile.

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

**Phase 4 — Hybrid Job Matching**
- Deterministic weighted matching engine, always computed locally in Python: skills (40%), role (20%), experience (15%), projects (10%), education (5%), location (5%) and semantic text similarity (5%).
- Rule-based scoring per component with transparent, human-readable alignment reasons: exact/related skill matching (with a conservative relationship map), role alias groups + keyword Jaccard, experience range fit, degree-level vs. field-of-study education fit, project tech-overlap, remote/hybrid/city-aware location, and cached semantic cosine similarity.
- The final score is never touched by the LLM — the LLM only writes an anti-hallucinated explanation (strengths, gaps); missing profile data is reported, never invented.
- `job_matches` persisted in Postgres with version fingerprints, lazy staleness detection, and cache reuse (skip embeddings + LLM when nothing changed).
- APIs: per-job match calculate/get (`/api/jobs/{id}/match`), and a matches collection (`/api/matches`) with sorting, category/score/company filters, recalculate-all and generate-missing.
- Category bands: STRONG_MATCH ≥85, GOOD_MATCH ≥70, REVIEW ≥55, LOW_MATCH <55.
- Offline-safe by default: `EMBEDDING_PROVIDER=deterministic` (hashed bag-of-tokens, stable across machines); set `sentence-transformers` for real semantic embeddings (`requirements-embeddings.txt`).
- Frontend: `/matches` ranking page, per-job Match Analysis panel on `/jobs/[id]`, and score rings on the Jobs dashboard.

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
    api/            # FastAPI routers (auth, users, resumes, profile, jobs, matches)
    ai/             # LLM client, openai provider, mock provider, analyzers, match explainer
    core/           # settings, DB session, responses, rate limiting
    models/         # SQLAlchemy models (user, resume, profile, job, job_analysis, job_skills, job_match)
    schemas/        # Pydantic schemas incl. structured analyzer output and match responses
    services/       # parsers, normalizers, skill taxonomy, job sources, URL security, matching engine
  alembic/          # migrations (001 auth, 002 resume tables, 003 job intelligence, 004 job matches)
tests/
frontend/
  app/              # pages (/, /login, /register, /dashboard, /resume, /jobs, /jobs/[id], /matches)
  components/       # Navbar, Sidebar, ProtectedRoute, resume + job + match components
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
| `EMBEDDING_PROVIDER` | `deterministic` | `deterministic` (offline, hash-based) or `sentence-transformers` (local semantic model) |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer model name used when `EMBEDDING_PROVIDER=sentence-transformers` |

## Job intelligence pipeline

1. **Ingest** — manual form, pasted description, or a fetched public job page.
   - URL fetch: scheme + DNS-rebinding check → `robots.txt` policy → size-limited, redirect-revalidated GET. LinkedIn, private/reserved hosts, unsupported schemes, unpublishable content and oversized pages are rejected with a specific error code.
2. **Clean** — the description is normalized line-by-line; navigation/boilerplate lines are dropped but the document structure is preserved.
3. **Analyze** — the LLM (or the deterministic mock parser) extracts structured data. The prompt treats the job description as untrusted input and instructs the model never to follow instructions inside it and never to invent facts. Output is validated by a Pydantic schema before anything is persisted.
4. **Persist** — one `jobs` row plus one `job_analysis` row (JSONB fields) and normalized `job_skills` rows.
5. **Deduplicate** — source URL, application URL, source job id, then a normalized key hash; duplicates return `409 DUPLICATE_JOB` and are never re-inserted.

## Matching engine

For each job you can compute a **match** against your candidate profile. The engine is hybrid: a deterministic weighted rule matcher produces the only score that matters, and embeddings/LLM are used only as inputs to specific components.

1. **Snapshot** — the current candidate profile and the job (content + stored analysis) are reduced to plain, versioned snapshots. The version fingerprint drives caching: if nothing changed, an existing match is returned without recomputing embeddings or calling the LLM.
2. **Components** — each component returns a `0..100` score plus an `applicable` flag and a human-readable reason:
   - *Skills* — exact matches score 1.0, explicitly related skills (conservative map: PostgreSQL↔SQL, Python↔FastAPI, JavaScript↔TypeScript, …) score 0.6; preferred skills tune the result by at most ±10. Only-preferred listings are treated as soft requirements.
   - *Role* — exact title → 100; normalized alias groups (backend/frontend/AI-ML/data/cloud/… ) → 85; otherwise token Jaccard → 40–80. Not applicable when the profile has no target roles.
   - *Experience* — fit within the job's range → 100; below range is proportional; extreme over-qualification is partially penalized. Falls back to `infer_experience_range` when the range wasn't stored.
   - *Education* — degree-level ladder (high school → PhD) vs the job's stated requirement; a CS-required job that needs a CS candidate loses 20 points when the candidate's field isn't CS-related.
   - *Projects* — technology overlap (tech ratio 60% + coverage 40%); projects are surfaced only above a relevance threshold.
   - *Location* — remote → 100; hybrid floors at 60 with city-aware matching; otherwise city-token equality.
   - *Semantic* — cosine similarity between the profile text and the job text (normalized `(cos+1)/2·100`), skipped when either text is too short.
3. **Combine** — weights are re-normalized over the applicable components, so a job without an analysis or a profile without a target role never distorts the overall score.
4. **Explain** — the LLM (or the offline mock explainer) gets the candidate snapshot, the job fields, the component scores and all reasons, and writes strengths/gaps plus a summary. It is instructed to never invent candidate facts; unknown information is reported as "Not identified in the candidate profile."
5. **Persist & refresh** — results are stored in `job_matches` keyed by `(user, job, profile, match_version)`. On reads, the profile/job fingerprints are compared lazily and stale matches are flagged (`is_stale`) so the UI can prompt a recalculate.

## API overview (Phase 3 & 4)

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/jobs` | Create a job manually |
| `POST` | `/api/jobs/from-description` | Create + analyze from a pasted description |
| `POST` | `/api/jobs/import-url` | Fetch, clean and analyze a public job URL |
| `GET` | `/api/jobs` | List with `search`, `company`, `location`, `source`, `status`, `work_mode`, `sort`, `page`, `page_size` |
| `GET` / `PUT` / `DELETE` | `/api/jobs/{id}` | Read / update / delete a job |
| `POST` | `/api/jobs/{id}/analyze` | Run / re-run analysis |
| `GET` | `/api/jobs/{id}/analysis` | Read the stored analysis |
| `POST` | `/api/jobs/{id}/match` | Calculate (or reuse a cached) match for a job |
| `GET` | `/api/jobs/{id}/match` | Read the latest match for a job (`404 MATCH_NOT_FOUND` if none yet) |
| `GET` | `/api/matches` | List matches with `sort` (match, newest, oldest, role, company, stale), `category`, `score_min`, `score_max`, `company`, `location`, `role`, `stale`, `page`, `page_size` |
| `GET` | `/api/matches/{id}` | Read a match by id |
| `POST` | `/api/matches/recalculate` | Recompute every existing match for the user |
| `POST` | `/api/matches/run` | Generate matches for ACTIVE jobs that don't have one yet |

All endpoints require a bearer token and are scoped to the authenticated user. Errors follow the envelope `{"success": false, "error": {"code", "message"}}`.

Match errors: `PROFILE_NOT_FOUND` (422) when no candidate profile exists yet, `MATCH_NOT_FOUND` (404) when no match has been computed.

## Known limitations

- The default `mock` analyzer is heuristic by design (works offline, deterministic tests). Use `LLM_PROVIDER=openai` for stronger extraction.
- LinkedIn pages are intentionally never fetched (anti-bot/paywall + terms). The UI directs users to paste the description instead.
- URL import is a simple fetch + HTML-to-text parse; job boards with heavy JavaScript rendering may yield little content (reported as `EMPTY_URL_CONTENT`).
- The URL import rate limiter is in-memory (per process). Swap `app/core/rate_limit.py` for Redis when running multiple instances.
- The default `deterministic` embedding provider measures token overlap, not true semantics. Install sentence-transformers (`pip install -r backend/requirements-embeddings.txt`) and set `EMBEDDING_PROVIDER=sentence-transformers` for semantic similarity.
- Match explanations need a profile to compare against; jobs matched without certain data (e.g. no target roles, no analysis) are scored only on the components that are applicable, which keeps scores meaningful but means a bare job can score highly on the few things it does specify.
- Cover letters, applications and interview prep are planned in follow-up phases.