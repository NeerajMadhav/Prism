# PRISM

Multi-cloud FinOps platform: connect AWS / Azure / GCP billing, explore day-wise costs, caps & alerts, forecasts, recommendations, and team settings — with realtime sync updates over WebSocket.

## Repository

| Path | Role | Stack |
|------|------|--------|
| [`prism-backend/`](./prism-backend) | API, auth, sync, analytics, WebSocket | FastAPI · asyncpg · TimescaleDB · Redis (optional) · Celery (optional) |
| [`prism-frontend/`](./prism-frontend) | Web app | Next.js · React · TanStack Query · Axios · Tailwind |
| [`Guide.md`](./Guide.md) | Day-to-day run + first-time setup | — |
| [`PRISM_PRODUCT_DOCUMENT.md`](./PRISM_PRODUCT_DOCUMENT.md) | Product / domain reference | — |
| [`prism-backend/backend.md`](./prism-backend/backend.md) | Backend API & inventory | — |

## Local URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://127.0.0.1:8000 |
| Health | http://127.0.0.1:8000/health |
| WebSocket | `ws://127.0.0.1:8000/ws` (auth via `Sec-WebSocket-Protocol`) |

## How to run

Start **backend first**, then **frontend** (two terminals). Full commands and env details: **[Guide.md](./Guide.md)**.

### Backend (short)

```powershell
cd prism-backend
# .env configured + Postgres/Redis running (see Guide.md)
py -3 -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
# or: make dev
```

### Frontend (short)

```powershell
cd prism-frontend
# .env.local points at the API
npm run dev
```

### Sanity check

1. `GET /health` → `status` ok (or degraded if Redis off), DB up  
2. Open the frontend → signup / login  
3. Dashboard & Costs load against the live API  

## What’s included

**Backend**

- Auth (email/password, refresh rotation, Google OAuth, API keys)
- Org / team RBAC (owner, admin, editor, viewer)
- Cloud accounts + sync → `cost_records` (UTC day grain)
- Costs: summary, by-day, by-service, by-tag, top services
- Caps, alerts, forecasts, commitments, recommendations, scorecard
- Virtual tags, reports, notifications, LLM assist, business metrics
- Realtime: WebSocket `connected` / `ping` / `sync.complete`

**Frontend**

- Auth + session bootstrap, org-scoped app shell
- Dashboard, accounts, costs (day-wise by provider), alerts, caps, forecasts, and related screens
- TanStack Query caching + WS-driven invalidation on sync complete
- API adapters aligned to live FastAPI response shapes

## First-time setup

One-time machine setup (Docker Timescale/Redis, Python package, schema, npm install, env files) is documented at the **end** of **[Guide.md](./Guide.md)**.

Minimum prerequisites: Node.js ≥ 20, Python ≥ 3.12, Docker Desktop.

## Tests

```powershell
# Frontend
cd prism-frontend
npm run test
npm run typecheck

# Backend
cd prism-backend
make test-unit
# full suite needs docker-compose.test.yml databases
make test
```

## Docs map

- Run / setup → [`Guide.md`](./Guide.md)
- Product → [`PRISM_PRODUCT_DOCUMENT.md`](./PRISM_PRODUCT_DOCUMENT.md)
- Backend catalog → [`prism-backend/backend.md`](./prism-backend/backend.md)
- Frontend plan (deep) → [`prism-frontend/docs/frontend-plan.md`](./prism-frontend/docs/frontend-plan.md)
