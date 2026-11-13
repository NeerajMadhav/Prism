# PRISM — Run Guide

Repo layout:

- `prism-backend/` — FastAPI API + WebSocket + workers
- `prism-frontend/` — Next.js app

Default local URLs:

| Service | URL |
|---------|-----|
| Backend API | http://127.0.0.1:8000 |
| Backend health | http://127.0.0.1:8000/health |
| Frontend | http://localhost:3000 (or 3001 if 3000 is busy) |
| WebSocket | ws://127.0.0.1:8000/ws |

---

## How to run (frontend + backend)

Use **two terminals**. Start the backend first, then the frontend.

### 1) Backend

```powershell
cd prism-backend

# Load env (PowerShell example if you use a .env file manually, or rely on pydantic .env)
# Ensure DATABASE_URL / REDIS_URL / JWT secrets match your running Postgres + Redis.

# Option A — Makefile (Git Bash / make available)
make dev

# Option B — direct
py -3 -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

Check it is up:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

You want something like: `status=ok`, `db=true`, `redis=true`.

Optional workers (sync / scheduled jobs — only if Redis + Celery are configured):

```powershell
cd prism-backend
make worker
# another terminal:
make beat
```

### 2) Frontend

```powershell
cd prism-frontend

# Ensure .env.local points at the API (see first-time setup below)
npm run dev
```

Open the printed URL (usually http://localhost:3000).

If port 3000 is taken:

```powershell
npx next dev -p 3001
```

And set `NEXT_PUBLIC_APP_URL=http://localhost:3001` in `.env.local`. Also set backend `FRONTEND_URL` to the same origin.

### 3) Quick sanity check

1. Backend health returns OK  
2. Frontend loads login/signup  
3. After signup, verify email in DB (dev often skips SES) then login  
4. Dashboard / Costs load against the API  

Useful frontend commands:

```powershell
cd prism-frontend
npm run typecheck
npm run test
npm run build
```

Useful backend commands:

```powershell
cd prism-backend
make test-unit
make test
make lint
```

---

## First-time setup

Do this once on a new machine before the “How to run” section.

### Prerequisites

- **Node.js** ≥ 20  
- **Python** ≥ 3.12 (`py -3` on Windows)  
- **Docker Desktop** (for Postgres/TimescaleDB + Redis)  
- **Git**

### A) Start databases (recommended local test stack)

From `prism-backend`:

```powershell
cd prism-backend
docker compose -f docker-compose.test.yml up -d
```

This starts:

- Postgres/TimescaleDB on host port **55432** → db `prism_test` / user `prism` / password `prism`  
- Redis on host port **6380**

Wait until healthy:

```powershell
docker compose -f docker-compose.test.yml ps
```

### B) Backend install + env + schema

```powershell
cd prism-backend

# 1. Copy env template
copy .env.example .env
```

Edit `.env` for the test compose ports (important on this machine):

```env
ENVIRONMENT=development
PORT=8000
DATABASE_URL=postgresql://prism:prism@127.0.0.1:55432/prism_test
REDIS_URL=redis://127.0.0.1:6380/0
CELERY_BROKER_URL=redis://127.0.0.1:6380/1
CELERY_RESULT_BACKEND=redis://127.0.0.1:6380/2
JWT_ACCESS_SECRET=change-me-access-secret-min-32-chars!!
JWT_REFRESH_SECRET=change-me-refresh-secret-min-32-chars!
ENCRYPTION_KEY=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
PRISM_INTERNAL_SECRET=change-me-internal-secret-not-jwt
FRONTEND_URL=http://localhost:3000
```

Install Python package (editable + dev tools):

```powershell
py -3 -m pip install -e ".[dev]"
```

Apply schema:

```powershell
# Requires psql, or run via docker exec:
docker exec -i prism-backend-postgres-1 psql -U prism -d prism_test < src/db/schema.sql
```

If Timescale extension is needed and not already applied, enable it in the DB, then re-run schema as needed.

### C) Frontend install + env

```powershell
cd prism-frontend
npm install --legacy-peer-deps
```

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_LLM_STREAMING=false
```

If you run the app on port 3001, set `NEXT_PUBLIC_APP_URL=http://localhost:3001` and match `FRONTEND_URL` in the backend `.env`.

### D) First login note (dev)

Signup creates a user with `email_verified=false`. Without SES, verification email is skipped in logs. For local testing you can verify the user in Postgres:

```powershell
docker exec -it prism-backend-postgres-1 psql -U prism -d prism_test -c "UPDATE users SET email_verified=TRUE WHERE email='you@example.com';"
```

Then log in with that email and password.

### E) Stop local infra

```powershell
cd prism-backend
docker compose -f docker-compose.test.yml down
```

Add `-v` only if you want to wipe database volumes.
