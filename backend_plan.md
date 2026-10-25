# PRISM — Backend Implementation Plan
### Complete Specification (No Code) — Python Edition

> **Purpose:** This document is the single source of truth for building the PRISM backend in Python. Every developer or AI model reading this should be able to build the full, working, production-ready backend without needing any other reference. Follow parts in order. Do not skip sections.

---

## TABLE OF CONTENTS

- **Part 1:** System Overview & Tech Stack
- **Part 2:** Architecture & Data Flow
- **Part 3:** Folder Structure
- **Part 4:** Database Design
- **Part 5:** Redis Architecture
- **Part 6:** API Design Rules
- **Part 7:** Authentication & Session Management
- **Part 8:** Role-Based Access Control (RBAC)
- **Part 9:** All API Endpoints (Full Specification)
- **Part 10:** Cloud Connector Specifications
- **Part 11:** Background Job System
- **Part 12:** Alert & Notification System
- **Part 13:** WebSocket (Real-Time Events)
- **Part 14:** LLM Integration (OpenRouter)
- **Part 15:** Virtual Tag Engine
- **Part 16:** Spend Forecast Engine
- **Part 17:** FinOps Health Scorecard
- **Part 18:** Monthly Report System
- **Part 19:** Email System
- **Part 20:** Security Requirements
- **Part 21:** Error Handling
- **Part 22:** Logging & Observability
- **Part 23:** Edge Cases & Pitfalls
- **Part 24:** Testing Requirements
- **Part 25:** Implementation Order
- **Appendix A:** Project Setup, Scripts, DB Bootstrap, Graceful Shutdown
- **Appendix B:** Environment Variables Reference

---

## PART 1 — System Overview & Tech Stack

### 1.1 What PRISM Does

PRISM connects to AWS, Azure, and GCP. It pulls daily cost data from each cloud provider. It stores that data in a database. It shows a real-time dashboard, fires budget alerts, and sends monthly reports. It is a multi-tenant SaaS — one deployment serves many organizations, each with their own data fully isolated.

### 1.2 Backend Tech Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| Runtime | Python 3.12 | Mature, rich ecosystem, asyncio-native |
| HTTP Framework | FastAPI | Async, built-in Pydantic, WebSocket, auto OpenAPI |
| ASGI Server | Uvicorn (with Gunicorn in prod) | Production-grade ASGI, multi-worker |
| Primary DB | PostgreSQL 16 | Relational config/alert/user data |
| Time-series DB | TimescaleDB extension on PostgreSQL | Efficient queries over daily cost records |
| DB Driver | asyncpg | Fastest async PostgreSQL driver for Python |
| Cache | Redis 7 (via redis.asyncio) | Session storage, dashboard query cache, LLM cache |
| Job Queue | Celery + Redis broker | Reliable async background jobs with retry |
| Scheduler | Celery Beat | Periodic cron tasks (replaces node-cron) |
| Auth | python-jose[cryptography] (JWT) + passlib[bcrypt] | Stateless access tokens, hashed passwords |
| OAuth | Google OAuth 2.0 (via httpx + Google public keys) | Alternative to email/password |
| Email | boto3 (AWS SES) | Transactional email delivery |
| WebSocket | FastAPI built-in WebSocket support | Real-time dashboard updates |
| LLM | OpenRouter API (OpenAI-compatible REST via httpx) | Optional AI features |
| Encryption | Python `cryptography` library — AES-256-GCM | Credentials at rest |
| Validation | Pydantic v2 | Runtime schema validation for all request bodies |
| HTTP Client | httpx (async) | Cloud API calls, outbound webhooks, LLM |
| Retry | tenacity | Exponential backoff, retry-after, conditional retry |
| Rate Limiting | slowapi (Starlette/FastAPI native) | Per-IP and per-org rate limiting |
| Logging | structlog | Structured JSON logs |
| Config | pydantic-settings | Env var loading and validation |
| AWS SDK | boto3 | STS AssumeRole, Cost Explorer, SES, resource discovery |
| Azure SDK | azure-identity + azure-mgmt-costmanagement | Azure Cost Management API |
| GCP SDK | google-cloud-bigquery | BigQuery billing export |

### 1.3 What the Backend Must NOT Do

- Never store raw cloud API responses (only parsed daily aggregates)
- Never store per-hour cost breakdowns (daily is sufficient)
- Never store LLM conversations in the database (Redis cache only, 24h TTL)
- Never log or return credential values in error messages
- Never process cloud credentials synchronously in an HTTP request (always via Celery task)
- Never trust org_id from request body for multi-tenant scoping (only from JWT)

---

## PART 2 — Architecture & Data Flow

### 2.1 Component Map

```
Browser (React frontend)
    │
    ├── HTTPS REST API (/v1/*)  ──► FastAPI Router ──► Route Handler ──► DB / Redis
    │
    └── WebSocket (/ws?token=)  ──► WebSocketManager ──► org-scoped broadcast

Celery Workers (background)
    ├── prism-sync          ← triggered by Celery Beat (06:00 UTC) + manual trigger
    ├── prism-alerts        ← triggered after every sync + on cap create
    ├── prism-forecast      ← triggered daily (07:30 UTC)
    ├── prism-commitments   ← triggered daily (07:00 UTC)
    ├── prism-recommendations ← triggered daily (08:00 UTC)
    ├── prism-reports       ← triggered on org report day (09:00 UTC check)
    ├── prism-virtual-tags  ← triggered on rule save by user
    └── prism-dlq           ← receives tasks that failed 3 attempts

Data stores
    ├── PostgreSQL + TimescaleDB  ← all persistent data
    └── Redis                     ← sessions, cache, job queue, LLM cache
```

### 2.2 Request Lifecycle (Happy Path)

1. Browser sends `GET /v1/orgs/{org_id}/costs` with `Authorization: Bearer <jwt>`
2. `get_current_user` FastAPI dependency verifies JWT signature and expiry. Extracts `{ sub, org_id, role }`.
3. `get_org_access` dependency verifies `current_user.org_id == path_org_id`. Fetches org from DB. Returns `org`.
4. `slowapi` rate limit middleware checks request count per org in Redis. Returns 429 if over limit.
5. Route handler runs. Checks Redis cache first. On cache miss, queries PostgreSQL via asyncpg.
6. Response is cached in Redis with appropriate TTL.
7. Response sent to browser.

### 2.3 Sync Lifecycle (Daily Background Flow)

1. Celery Beat fires at 06:00 UTC. Periodic task fetches all active `cloud_accounts` from DB.
2. For each account, dispatches one Celery task to `prism-sync` queue with `{ account_id, org_id, backfill: False }`.
3. Worker picks up task. Decrypts credentials from `cloud_accounts.credentials_enc`.
4. Worker instantiates the correct connector (AWS / Azure / GCP). Calls provider API.
5. Received cost records are bulk-upserted into `cost_records` table (idempotent — ON CONFLICT DO UPDATE).
6. `cloud_accounts` row updated: `last_sync`, `last_sync_status`, `data_as_of`, `last_sync_records`.
7. `sync_logs` row written.
8. Redis dashboard cache for this org+provider invalidated.
9. WebSocket event `sync.complete` broadcast to all connected clients of this org.
10. New Celery task dispatched to `prism-alerts` queue.
11. If task fails 3 times, it moves to DLQ handler. DLQ logs failure and creates `sync_failure` alert in DB.

### 2.4 Alert Lifecycle

1. `prism-alerts` task runs for an org.
2. For each active `BudgetCap`: query `cost_records` for current month spend matching cap scope.
3. Compute `pct = (spent / cap_amount) * 100`.
4. For each threshold in [75, 90, 100, 125, 150]: if `pct >= threshold`, check DB for existing alert this month.
5. If no existing alert → insert `Alert` row → fire all notification channels concurrently (email, Teams, Slack, outbound webhook).
6. Update alert row with which channels succeeded.
7. Also check `spend_forecasts`: if any forecast has `will_breach = True`, fire `forecast_breach` alert.
8. WebSocket event `alert.fired` broadcast to org's connected clients instantly.

### 2.5 Multi-Tenancy Isolation

- Every DB table has an `org_id` column.
- Every query includes `WHERE org_id = $1` — never rely on joins alone.
- The `org_id` used in queries always comes from `current_user.org_id` (from JWT) — never from request body or URL parameters.
- The `get_org_access` dependency explicitly checks `current_user.org_id == path_org_id` and rejects mismatches with 403.
- Redis cache keys always start with `orgId` — no shared keys between orgs.
- WebSocket connections are tracked in a `dict[str, set[WebSocket]]` — broadcasts never cross org boundaries.

---

## PART 3 — Folder Structure

```
prism-backend/
├── src/
│   ├── main.py                  FastAPI app factory: create_app(), mount routers, middleware, exception handlers
│   ├── server.py                Uvicorn startup, graceful shutdown (SIGTERM/SIGINT handlers)
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py          pydantic-settings: all env vars with types + validation. Fail fast if missing.
│   │   ├── database.py          asyncpg Pool creation; get_db() async generator dependency
│   │   └── redis_client.py      redis.asyncio connection; get_redis() async generator dependency
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py              get_current_user(): verify JWT from Authorization header. Returns UserContext.
│   │   ├── org_scope.py         get_org_access(): verify path org_id matches JWT org_id. Fetch org from DB.
│   │   ├── rbac.py              require_role(min_role) factory — returns FastAPI Depends that rejects if role insufficient.
│   │   ├── hmac.py              validate_hmac(provider) factory — for Teams/Slack incoming webhook callbacks.
│   │   └── rate_limit.py        slowapi limiter instance + limit strings for each endpoint group.
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py              POST signup, verify-email, login, refresh, logout, forgot-password, reset-password, GET google, GET google/callback
│   │   ├── orgs.py              GET+PUT /v1/orgs/{org_id}
│   │   ├── accounts.py          CRUD + test + sync-trigger + sync-logs for cloud accounts
│   │   ├── costs.py             Cost aggregation queries (overall, by-service, by-day, by-tag, top-services, unit-economics)
│   │   ├── alerts.py            List + acknowledge + snooze alerts
│   │   ├── caps.py              CRUD for budget caps
│   │   ├── reports.py           GET+PUT report config, POST send-now
│   │   ├── team.py              List + invite + accept-invite + change-role + remove member
│   │   ├── recommendations.py   List + update status (implemented/rejected/archived)
│   │   ├── virtual_tags.py      CRUD + reorder + apply + audit-log for virtual tag rules
│   │   ├── forecasts.py         GET current forecast + GET history
│   │   ├── commitments.py       GET list + summary + expiring
│   │   ├── scorecard.py         GET scorecard + executive view
│   │   ├── notifications.py     GET+PUT notification settings + test endpoints
│   │   ├── webhooks.py          CRUD + test for outbound webhooks
│   │   ├── llm.py               GET+PUT+DELETE LLM config + POST natural language query
│   │   ├── business_metrics.py  CRUD metrics + ingest values + unit economics
│   │   ├── resources.py         List + idle list + get resource detail
│   │   ├── api_keys.py          CRUD for machine-to-machine API keys + API key auth dependency
│   │   ├── teams_actions.py     POST callback from Teams (HMAC validated, no JWT)
│   │   └── slack_actions.py     POST callback from Slack (HMAC validated, no JWT)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── connectors/
│   │   │   ├── __init__.py
│   │   │   ├── aws.py           AWSConnector: STS AssumeRole, Cost Explorer, EC2 describe, commitments
│   │   │   ├── azure.py         AzureConnector: azure-identity, Cost Management API (via httpx)
│   │   │   └── gcp.py           GCPConnector: BigQuery billing export (parameterized queries)
│   │   ├── alert_service.py     CapAlertService: check caps, dedup, fire all channels concurrently
│   │   ├── commitment_service.py CommitmentService: sync AWS/GCP, update expiry status, expiry alerts
│   │   ├── email_service.py     EmailService: all transactional emails via boto3 SES
│   │   ├── forecast_service.py  ForecastEngine: daily avg + rolling avg, breach calc, upsert
│   │   ├── fx_service.py        FXService: fetch USD conversion rate, 6h Redis cache
│   │   ├── llm_service.py       LLMService: OpenRouter via httpx, Redis cache, budget check, None fallback
│   │   ├── recommendation_service.py RecommendationEngine: idle + rightsizing heuristics + LLM
│   │   ├── report_service.py    ReportGenerator: gather sections, call LLM, send email, update next_send
│   │   ├── scorecard_service.py ScorecardEngine: compute 7 metrics, weighted overall score
│   │   ├── virtual_tag_service.py VirtualTagEngine: batched retroactive re-tag with WS progress
│   │   └── webhook_service.py   OutboundWebhookService: HMAC-sign + dispatch to customer URLs via httpx
│   │
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── celery_app.py        Celery app instance + Beat schedule (all cron timings defined here)
│   │   ├── sync_worker.py       Celery task: sync cost + resource data; invalidate cache; trigger alerts
│   │   ├── alerts_worker.py     Celery task: run CapAlertService for org
│   │   ├── forecast_worker.py   Celery task: run ForecastEngine for org
│   │   ├── commitments_worker.py Celery task: run CommitmentService for org
│   │   ├── recommendations_worker.py Celery task: run RecommendationEngine for org
│   │   ├── reports_worker.py    Celery task: run ReportGenerator for org
│   │   ├── virtual_tags_worker.py Celery task: run VirtualTagEngine for org (soft_time_limit=600)
│   │   └── dlq_worker.py        Celery task: log DLQ tasks, create sync_failure alert in DB
│   │
│   ├── ws/
│   │   ├── __init__.py
│   │   └── ws_manager.py        WebSocketManager: JWT auth on connect, per-org dict, ws_broadcast()
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py            structlog configuration; bind_logger() for per-request context
│   │   ├── encrypt.py           aes_encrypt() / aes_decrypt() using cryptography AES-256-GCM
│   │   ├── retry.py             with_retry() using tenacity: exponential backoff, retry-after, no retry on 401/403
│   │   ├── cache.py             invalidate_dashboard_cache(org_id, provider): delete Redis keys pattern
│   │   ├── validate_webhook_url.py SSRF guard: HTTPS-only, private IP blocklist, DNS re-check on dispatch
│   │   ├── regex_utils.py       safe_regex_test() + validate_regex_pattern() with ReDoS protection
│   │   ├── date_utils.py        current_month_start(), next_month_start(), days_remaining_in_month()
│   │   └── pagination.py        get_pagination(request), paginated_response(data, total, params)
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py              Pydantic models: SignupRequest, LoginRequest, TokenResponse, etc.
│   │   ├── orgs.py              OrgUpdateRequest, OrgResponse
│   │   ├── accounts.py          AccountCreateRequest, AccountResponse, SyncLogResponse
│   │   ├── costs.py             CostSummaryResponse, CostByServiceResponse, CostByDayResponse
│   │   ├── alerts.py            AlertResponse, SnoozeRequest
│   │   ├── caps.py              CapCreateRequest, CapResponse
│   │   ├── team.py              InviteRequest, ChangRoleRequest, MemberResponse
│   │   └── ... (one per domain — mirrors routers/ folder)
│   │
│   ├── types/
│   │   ├── __init__.py
│   │   └── models.py            Shared dataclasses + TypedDicts: UserContext, ConnectorResult, WSEvent, etc.
│   │
│   └── db/
│       └── schema.sql           Full DDL for all tables + indexes (run once on fresh DB)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              pytest fixtures: test DB, test Redis, authenticated client
│   ├── unit/                    Pure logic tests (no DB/Redis)
│   └── integration/             End-to-end flow tests with real DB
│
├── pyproject.toml               All dependencies + tool configs (pytest, mypy, ruff)
├── .env                         Local secrets (never commit)
├── .env.example                 Template for all required env vars
└── Makefile                     Dev shortcuts: make dev, make test, make db-migrate
```

---

## PART 4 — Database Design

### 4.1 Database: PostgreSQL 16 + TimescaleDB

- All tables are in one PostgreSQL instance with the TimescaleDB extension installed.
- `cost_records` is the only TimescaleDB hypertable (time-series, partitioned by month).
- All other tables are regular PostgreSQL tables.
- Connection pooling via asyncpg Pool (min 5, max 20 connections).
- All queries use asyncpg's `$1, $2, ...` parameterized syntax — never string interpolation.

### 4.2 Tables

#### Table: `organizations`
Stores each customer organization (tenant).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | auto-generated |
| name | TEXT NOT NULL | org display name |
| plan | TEXT | starter / professional / enterprise |
| billing_period_start | DATE | first day of org's billing cycle |
| currency | TEXT | USD/EUR/GBP/INR/AUD/CAD — default USD |
| timezone | TEXT | IANA tz string e.g. "America/New_York" |
| feature_flags | JSONB | {"virtual_tagging": true} — feature rollout |
| created_at | TIMESTAMPTZ | auto |

---

#### Table: `users`
Individual people who log in to PRISM.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| email | TEXT UNIQUE NOT NULL | lowercase |
| name | TEXT NOT NULL | |
| password_hash | TEXT | NULL if Google OAuth only |
| google_id | TEXT UNIQUE | NULL if email/password only |
| avatar_url | TEXT | |
| email_verified | BOOLEAN | default FALSE; required before login |
| email_verify_token | TEXT | bcrypt-hashed raw token; NULL after verification |
| email_verify_expires | TIMESTAMPTZ | 24h expiry |
| mfa_enabled | BOOLEAN | default FALSE (v1 stub) |
| last_login | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | auto |

---

#### Table: `refresh_tokens`
Tracks issued refresh tokens for invalidation on logout and rotation.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| token_hash | TEXT | bcrypt hash of raw token |
| revoked_at | TIMESTAMPTZ | NULL = active |
| expires_at | TIMESTAMPTZ | 30 days from issue |
| created_at | TIMESTAMPTZ | |

---

#### Table: `team_members`
Membership linking a user to an org with a role.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK → organizations | |
| user_id | UUID FK → users | |
| role | TEXT | owner / admin / editor / viewer |
| invite_accepted | BOOLEAN | default FALSE until accepted |
| invited_by | UUID FK → users | |
| created_at | TIMESTAMPTZ | |

Unique: `(org_id, user_id)`.

---

#### Table: `invites`
Pending email invitations before a user accepts and creates their account.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| email | TEXT | invited email address |
| role | TEXT | role they'll receive on accept |
| token_hash | TEXT | bcrypt hash of raw invite token |
| expires_at | TIMESTAMPTZ | 48h from creation |
| accepted_at | TIMESTAMPTZ | NULL until accepted |
| invited_by | UUID FK → users | |
| created_at | TIMESTAMPTZ | |

Unique: `(org_id, email)` where `accepted_at IS NULL` — only one active invite per email per org.

---

#### Table: `cloud_accounts`
Each connected cloud account/subscription/project.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| group_id | UUID FK → account_groups | |
| provider | TEXT | aws / azure / gcp |
| account_id | TEXT | AWS account ID, Azure subscription ID, GCP project ID |
| display_name | TEXT | user-assigned label |
| scope | TEXT | account / subscription / project |
| credentials_enc | TEXT | AES-256-GCM encrypted JSON credentials |
| last_sync | TIMESTAMPTZ | when last sync ran |
| last_sync_status | TEXT | never / running / success / failed |
| last_sync_error | TEXT | error message if last sync failed |
| last_sync_records | INTEGER | count of records upserted |
| data_as_of | DATE | latest date in synced cost data |
| is_active | BOOLEAN | default TRUE |
| created_at | TIMESTAMPTZ | |

Unique: `(org_id, provider, account_id)`.

---

#### Table: `account_groups`
Groups cloud accounts by provider for display (e.g. "All AWS Accounts").

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| provider | TEXT | aws / azure / gcp |
| name | TEXT | e.g. "AWS Production" |
| scope | TEXT | account / subscription / project |
| created_at | TIMESTAMPTZ | |

---

#### Table: `sync_logs`
One row per sync job run. Retained 90 days.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| account_id | UUID FK → cloud_accounts | |
| org_id | UUID | denormalized for easy queries |
| status | TEXT | running / success / failed |
| started_at | TIMESTAMPTZ | |
| finished_at | TIMESTAMPTZ | |
| records_synced | INTEGER | |
| error | TEXT | |

---

#### Table: `cost_records` — TimescaleDB Hypertable
The core time-series cost data. Partitioned by month.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | |
| org_id | UUID | |
| account_id | UUID FK → cloud_accounts | |
| provider | TEXT | aws / azure / gcp |
| time | TIMESTAMPTZ | daily (midnight UTC) |
| service | TEXT | e.g. "Amazon EC2", "Virtual Machines" |
| region | TEXT | e.g. "us-east-1" |
| cost_usd | NUMERIC(14,6) | primary cost field |
| cost_unblended_usd | NUMERIC(14,6) | AWS unblended / same as cost_usd for others |
| cost_amortized_usd | NUMERIC(14,6) | AWS amortized (RI/SP spread) / same for others |
| usage_quantity | NUMERIC | |
| usage_unit | TEXT | |
| tags | JSONB | cloud-provider tags + virtual_ tags |
| is_estimate | BOOLEAN | TRUE for current-month AWS data (re-synced daily) |

Hypertable partitioned by `time` (monthly chunks). Compressed after 3 months.

Unique constraint: `(account_id, time::date, service, region)` — enables ON CONFLICT DO UPDATE upsert.

---

#### Table: `resources`
Cloud resources discovered during sync (EC2 instances, VMs, GCE instances, etc.).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID | |
| account_id | UUID FK | |
| provider | TEXT | |
| resource_id | TEXT | provider's native resource ID |
| resource_type | TEXT | ec2_instance / vm / gce_instance / etc. |
| name | TEXT | |
| region | TEXT | |
| tags | JSONB | |
| last_cost_usd | NUMERIC | latest month cost |
| last_activity_at | TIMESTAMPTZ | |
| is_idle | BOOLEAN | TRUE if no activity for 7+ days |
| idle_since | DATE | |
| first_seen | DATE | |
| last_seen | DATE | |
| metadata | JSONB | instance type, size, etc. |

Unique: `(account_id, resource_id)`.

---

#### Table: `budget_caps`
Spend caps that trigger alerts at configured thresholds.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| name | TEXT | user label |
| scope | TEXT | platform / service / account |
| scope_value | TEXT | e.g. "aws" or "Amazon EC2" or account UUID |
| cap_amount | NUMERIC | spend limit in USD |
| period | TEXT | monthly (only option in v1) |
| is_active | BOOLEAN | |
| deleted_at | TIMESTAMPTZ | soft delete |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

---

#### Table: `alerts`
One row per triggered alert event. Never deleted automatically.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| cap_id | UUID FK → budget_caps ON DELETE SET NULL | NULL if cap deleted |
| type | TEXT | cap_threshold / forecast_breach / spend_acceleration / sync_failure / etc. |
| scope | TEXT | platform / service / account |
| scope_value | TEXT | |
| severity | TEXT | info / warning / critical |
| threshold_percent | NUMERIC | 75 / 90 / 100 / 125 / 150 for cap_threshold |
| message | TEXT | human-readable description |
| triggered_at | TIMESTAMPTZ | when fired |
| acknowledged_at | TIMESTAMPTZ | NULL until acknowledged |
| acknowledged_by | UUID FK → users | |
| snoozed_until | TIMESTAMPTZ | NULL if not snoozed |
| email_sent | BOOLEAN | |
| teams_sent | BOOLEAN | |
| slack_sent | BOOLEAN | |
| webhook_sent | BOOLEAN | |

Unique partial index: `(org_id, cap_id, threshold_percent, date_trunc('month', triggered_at)) WHERE type='cap_threshold'` — enforces one alert per cap per threshold per billing month.

---

#### Table: `notification_settings`
Per-org notification configuration.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID UNIQUE FK | one row per org |
| alert_emails | TEXT[] | list of email addresses to alert |
| teams_webhook_url | TEXT | incoming webhook URL |
| slack_webhook_url | TEXT | incoming webhook URL |
| teams_signing_secret_enc | TEXT | AES-encrypted signing secret |
| slack_signing_secret_enc | TEXT | AES-encrypted signing secret |
| alert_threshold_75 | BOOLEAN | enable 75% alerts |
| alert_threshold_90 | BOOLEAN | enable 90% alerts |
| alert_threshold_100 | BOOLEAN | enable 100% alerts |
| alert_threshold_125 | BOOLEAN | enable 125% alerts |
| alert_threshold_150 | BOOLEAN | enable 150% alerts |

---

#### Table: `monthly_reports`
Report schedule configuration per org.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID UNIQUE FK | one row per org |
| is_active | BOOLEAN | |
| recipient_emails | TEXT[] | |
| send_day | INTEGER | day of month (1–28; 28 is max to be safe) |
| next_send | TIMESTAMPTZ | computed: next matching date at 09:00 UTC |
| last_sent | TIMESTAMPTZ | |
| include_recommendations | BOOLEAN | |
| include_finops_scorecard | BOOLEAN | |
| include_commitments | BOOLEAN | |
| include_unit_economics | BOOLEAN | |

---

#### Table: `recommendations`
Cost optimization recommendations generated by the system.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| account_id | UUID FK | |
| resource_id | UUID FK → resources | nullable |
| type | TEXT | idle_resource / rightsizing / commitment_purchase / unused_commitment |
| title | TEXT | |
| description | TEXT | LLM-generated or template |
| savings_usd | NUMERIC | estimated monthly savings |
| confidence | TEXT | high / medium / low |
| status | TEXT | open / implemented / rejected / archived |
| metadata | JSONB | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

---

#### Table: `virtual_tag_rules`
Rules for the virtual tagging engine.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| name | TEXT | user label |
| tag_key | TEXT | output key (e.g. "virtual_team") |
| tag_value | TEXT | output value (e.g. "platform") |
| conditions | JSONB | array of {field, operator, value} |
| split_config | JSONB | null or {strategy: "equal"/"fixed_pct"/"usage_ratio", targets: [{tag, pct}]} |
| priority | INTEGER | lower = higher priority; first-match wins |
| is_active | BOOLEAN | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

---

#### Table: `virtual_tag_audit_log`
Records each retroactive re-tag run for auditability.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| rule_id | UUID FK → virtual_tag_rules | |
| triggered_by | UUID FK → users | |
| started_at | TIMESTAMPTZ | |
| finished_at | TIMESTAMPTZ | |
| rows_processed | INTEGER | |
| rows_updated | INTEGER | |
| status | TEXT | running / completed / failed |

---

#### Table: `spend_forecasts`
Monthly forecast per org per provider. Updated daily.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| provider | TEXT | aws / azure / gcp / all |
| forecast_month | DATE | first day of the month being forecast |
| daily_avg | NUMERIC | rolling average of daily spend |
| projected_total | NUMERIC | daily_avg × days_in_month |
| cap_amount | NUMERIC | relevant cap if any |
| will_breach | BOOLEAN | projected_total > cap_amount |
| days_elapsed | INTEGER | |
| days_with_data | INTEGER | non-zero-spend days |
| data_coverage | TEXT | sufficient / insufficient |
| actual_total | NUMERIC | filled at month-end by accuracy job |
| variance_pct | NUMERIC | filled at month-end |
| computed_at | TIMESTAMPTZ | |

Unique: `(org_id, provider, forecast_month)` — upsert on conflict.

---

#### Table: `commitment_records`
RI, Savings Plans, CUD commitments from cloud providers.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| account_id | UUID FK | |
| provider | TEXT | aws / gcp |
| commitment_type | TEXT | RI / SP / CUD |
| resource_type | TEXT | e.g. "EC2", "RDS" |
| arn_or_id | TEXT | provider's identifier |
| start_date | DATE | |
| end_date | DATE | |
| monthly_cost | NUMERIC | |
| utilization_pct | NUMERIC | 0–100 |
| coverage_pct | NUMERIC | 0–100 |
| status | TEXT | active / expired / expiring_soon |
| last_synced | TIMESTAMPTZ | |

---

#### Table: `outbound_webhooks`
Customer-configured URLs to receive PRISM events.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| url | TEXT | customer's HTTPS endpoint |
| signing_secret_enc | TEXT | AES-encrypted; raw shown once at creation |
| events | TEXT[] | subscribed events |
| is_active | BOOLEAN | |
| last_delivery_status | TEXT | |
| last_delivery_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |

---

#### Table: `llm_configs`
Per-org LLM configuration (user's own OpenRouter key).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID UNIQUE FK | |
| api_key_enc | TEXT | AES-encrypted OpenRouter API key |
| model | TEXT | e.g. "openai/gpt-4o-mini" |
| monthly_budget_usd | NUMERIC | spending cap |
| is_enabled | BOOLEAN | |
| created_at | TIMESTAMPTZ | |

---

#### Table: `business_metrics`
User-defined metrics for unit economics (cost per customer, cost per request).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| name | TEXT | e.g. "active_customers", "api_requests" |
| source | TEXT | manual / webhook / datadog / stripe / csv |
| unit | TEXT | e.g. "customers", "requests" |
| is_active | BOOLEAN | |
| created_at | TIMESTAMPTZ | |

Unique: `(org_id, name)`.

---

#### Table: `business_metric_values`
Daily values for each business metric.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| metric_id | UUID FK → business_metrics | |
| org_id | UUID | |
| date | DATE | |
| value | NUMERIC | |
| ingested_at | TIMESTAMPTZ | |

Unique: `(metric_id, date)` — idempotent upsert.

---

#### Table: `api_keys`
Machine-to-machine keys for CI/CD integrations.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| user_id | UUID FK | |
| key_hash | TEXT | bcrypt hash; raw key shown once |
| key_prefix | TEXT | first 8 chars; shown in UI for identification |
| name | TEXT | user-assigned label |
| scopes | TEXT[] | e.g. ['cost.read', 'alerts.read'] |
| expires_at | TIMESTAMPTZ | optional |
| last_used | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |
| revoked_at | TIMESTAMPTZ | NULL = active |

---

### 4.3 Critical Database Indexes

| Index | Table | Columns | Purpose |
|-------|-------|---------|---------|
| Idempotency | cost_records | (account_id, time::date, service, region) UNIQUE | Enables ON CONFLICT upsert |
| Time range | cost_records | (org_id, time DESC) | Dashboard time-range queries |
| Provider filter | cost_records | (org_id, provider, time DESC) | Per-platform queries |
| Tag search | cost_records | GIN(tags) | Tag-based allocation |
| Alert dedup | alerts | (org_id, cap_id, threshold_percent, date_trunc('month', triggered_at)) WHERE type='cap_threshold' | Unique partial — dedup |
| Resource upsert | resources | (account_id, resource_id) UNIQUE | Idempotent upsert |
| Idle resources | resources | (org_id, is_idle, idle_since) WHERE is_idle=true | Fast idle queries |
| Commitment expiry | commitment_records | (org_id, status, end_date) | Expiry calendar |
| Forecast lookup | spend_forecasts | (org_id, forecast_month DESC) | Dashboard forecast |
| Tag rule order | virtual_tag_rules | (org_id, priority) WHERE is_active=true | Rule evaluation |

### 4.4 Data Retention Policy

| Data | Retention | Action after |
|------|-----------|-------------|
| cost_records | 13 months (hot) | Archive to S3 Parquet |
| sync_logs | 90 days | Purge (DELETE) via daily Celery Beat task |
| alerts / recommendations | Indefinite | No action |
| LLM cache (Redis) | 24 hours per entry | Auto-expire (Redis TTL) |
| Refresh tokens (revoked) | 30 days | Purge expired |

---

## PART 5 — Redis Architecture

### 5.1 Purpose
Redis serves four roles: session token invalidation, dashboard query cache, job queue (via Celery), and LLM response cache.

### 5.2 Key Naming Convention

All keys are prefixed with the org's UUID or user's UUID to prevent cross-tenant data leakage.

| Key Pattern | Value | TTL | Purpose |
|-------------|-------|-----|---------|
| `dash:{orgId}:overall:{YYYY-MM}` | JSON cost aggregates | 5 min | Overall dashboard |
| `dash:{orgId}:{provider}:{YYYY-MM}` | JSON per-platform aggregates | 5 min | Per-platform dashboard |
| `dash:{orgId}:forecast:{YYYY-MM}` | JSON forecast rows | 1 hour | Forecast widget |
| `dash:{orgId}:commitments` | JSON commitment summary | 6 hours | Commitment tab |
| `dash:{orgId}:scorecard` | JSON scorecard result | 1 hour | Scorecard page |
| `unit:econ:{orgId}:{YYYY-MM}` | JSON unit economics result | 15 min | Unit economics tab |
| `llm:{base64_prompt_hash}` | LLM response string | 24 hours | Avoid repeat LLM calls |
| `llm:monthly_spent:{orgId}:{YYYY-MM}` | Decimal (string) | 33 days | Track LLM budget per org |
| `rl:auth:{ip}` | Request count | 15 min | Auth rate limit (slowapi) |
| `rl:api:{orgId}` | Request count | 1 min | API rate limit (slowapi) |
| `rl:llm:{userId}` | Request count | 1 hour | LLM query rate limit (slowapi) |
| `pwd:reset:{userId}` | bcrypt hash of reset token | 1 hour | Password reset |
| `fx:rate:{currency}` | Exchange rate (string) | 6 hours | FX conversion cache |

### 5.3 Cache Invalidation

When a sync job completes for an org+provider, the worker must delete:
- `dash:{orgId}:overall:{currentMonth}`
- `dash:{orgId}:{provider}:{currentMonth}`
- `dash:{orgId}:forecast:{currentMonth}`
- `dash:{orgId}:scorecard`

This ensures the next dashboard load hits PostgreSQL fresh and caches the new data.

---

## PART 6 — API Design Rules

### 6.1 URL Structure
All routes: `/v1/{resource-path}`. Breaking changes introduced under `/v2/` with 6-month deprecation on `/v1/`.

### 6.2 Request Rules
- All request bodies: `Content-Type: application/json`
- All authenticated requests: `Authorization: Bearer {jwt}`
- All org-scoped routes: `org_id` in URL must match `org_id` in JWT (enforced by `get_org_access`)

### 6.3 Response Rules
- Success responses: `200 OK` (or `201 Created` for creates)
- All successful list endpoints return an array or `{ data, pagination }` object
- All error responses: `{ "error": "Human-readable message" }` plus optional `"code"` field
- Validation errors (Pydantic): `{ "error": "Validation failed", "details": [{ "field": "...", "message": "..." }] }`

### 6.4 HTTP Status Codes

| Code | When |
|------|------|
| 200 | Success |
| 201 | Resource created |
| 400 | Bad request or validation failure |
| 401 | No/invalid/expired auth token |
| 403 | Authenticated but forbidden (wrong org or insufficient role) |
| 404 | Resource not found (always org-scoped — never reveal cross-org existence) |
| 409 | Conflict (duplicate email, already a member, etc.) |
| 429 | Rate limit exceeded |
| 500 | Unexpected server error (never leak internals in message) |

### 6.5 Pagination

All list endpoints that can grow unbounded accept:
- `?page=1` (default 1)
- `?limit=20` (default 20, max 100)

Paginated responses return: `{ data: [...], pagination: { total, page, limit, pages } }`

### 6.6 Filtering

Cost queries accept:
- `?month=YYYY-MM` (default: current month)
- `?provider=aws|azure|gcp` (optional)
- `?account_id=UUID` (optional)

---

## PART 7 — Authentication & Session Management

### 7.1 Primary Auth Flow (Email + Password)

**Signup:**
1. Receive `SignupRequest { email, name, password, org_name }`. Validated by Pydantic.
2. Normalize email to lowercase. Check no existing user (return 409 if exists).
3. Hash password with `passlib.context.CryptContext(schemes=["bcrypt"], deprecated="auto")` — bcrypt cost factor 12.
4. In a single asyncpg DB transaction: create `User`, create `Organization`, create `TeamMember` (role=owner, invite_accepted=True), create `NotificationSettings` (alert_emails=[email]).
5. Generate raw verification token (`secrets.token_hex(32)`). Hash with bcrypt. Store in `users.email_verify_token`. Set `email_verify_expires = NOW() + 24h`.
6. Send verification email with raw token.
7. Return `{ message, user_id, org_id }`. Do NOT issue JWT yet.

**Email Verification:**
1. Receive `{ user_id, token }`.
2. Fetch user. Check `email_verified = False` and `email_verify_expires > NOW()`.
3. Compare raw token against `email_verify_token` with `pwd_context.verify(token, stored_hash)`.
4. If valid: set `email_verified = True`, clear token fields.
5. Return success. User can now log in.

**Login:**
1. Receive `{ email, password }`.
2. Fetch user by email. Fetch their org membership from `team_members`.
3. Always call `pwd_context.verify` even if user not found (dummy hash) — prevents timing attacks.
4. If user not found OR password wrong → return 401 (same message for both).
5. If `email_verified = False` → return 403 with "Check your email to verify your account."
6. Call `issue_tokens(user_id, org_id, role, email)`:
   - Sign access JWT (7 days) using `python_jose.jwt.encode({ "sub": user_id, "org_id": org_id, "role": role, "email": email }, ACCESS_SECRET, algorithm="HS256")`.
   - Generate 64-byte raw refresh token (`secrets.token_hex(64)`). Hash with bcrypt (cost 10). Store in `refresh_tokens`.
   - Return `{ access_token, refresh_token }`.
7. Update `users.last_login = NOW()`.

**Token Refresh:**
1. Receive `{ refresh_token }`.
2. Verify JWT signature (refresh secret). Extract `sub`.
3. Find latest non-revoked `refresh_tokens` row for this user. Compare with `pwd_context.verify`.
4. If invalid → 401.
5. Revoke old token (`revoked_at = NOW()`). Issue new token pair. Return new tokens.

**Logout:**
1. Receive refresh token in body.
2. Mark that token row `revoked_at = NOW()`. Return 200.

**Forgot Password:**
1. Receive `{ email }`. Always return 200 (no user enumeration).
2. If user exists and email verified: generate raw reset token (`secrets.token_hex(32)`). Store bcrypt hash in Redis with key `pwd:reset:{user_id}` and 1h TTL.
3. Send password reset email with link: `{FRONTEND_URL}/reset-password?userId={id}&token={raw}`.

**Reset Password:**
1. Receive `{ user_id, token, new_password }`.
2. Fetch bcrypt hash from Redis at `pwd:reset:{user_id}`. Compare with raw token.
3. If valid: hash new password with bcrypt (factor 12). Update `users.password_hash`.
4. Delete Redis key. Revoke ALL refresh tokens for this user (all sessions invalidated).
5. Return success.

### 7.2 Google OAuth Flow

1. `GET /v1/auth/google` — build Google OAuth consent URL with `client_id`, `redirect_uri`, `scope=openid email profile`, `state=random_token`. Return 302 redirect.
2. Google redirects to `GET /v1/auth/google/callback?code=...&state=...`.
3. Exchange code for tokens: `POST https://oauth2.googleapis.com/token` via httpx.
4. Verify `id_token` with Google public keys (fetch from `https://www.googleapis.com/oauth2/v3/certs` and cache 1h).
5. Extract `email`, `name`, `sub` (google_id), `picture` from id_token payload.
6. If email matches existing user:
   - If `google_id` not set on user → link it (`UPDATE users SET google_id = $1`).
   - Issue tokens. Redirect to `{FRONTEND_URL}/auth/callback?accessToken=...&refreshToken=...`.
7. If no existing user → JIT provision: create User (password_hash=None, email_verified=True, google_id=sub) + Org + TeamMember (owner) in one transaction. Issue tokens. Redirect.
8. Edge case: Google returns error → redirect to `{FRONTEND_URL}/login?error=oauth_failed`.
9. Google env vars required: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`.

---

## PART 8 — Role-Based Access Control (RBAC)

### 8.1 Roles (Ordered by Permission Level, Lowest to Highest)

| Role | Rank | Permissions |
|------|------|-------------|
| viewer | 1 | GET all data endpoints |
| editor | 2 | viewer + create/edit caps, virtual tags, recommendations status |
| admin | 3 | editor + manage team members, connect/delete accounts, org settings |
| owner | 4 | admin + transfer ownership. One per org. Cannot be removed. |

### 8.2 Role Enforcement

FastAPI dependency factory pattern:
- `require_role("viewer")` — min rank 1 (all authenticated members)
- `require_role("editor")` — min rank 2
- `require_role("admin")` — min rank 3
- `require_role("owner")` — min rank 4 (owner only)

Implementation:
- `require_role(min_role)` returns a FastAPI `Depends` callable.
- The callable receives `current_user` from `get_current_user` and compares `ROLE_RANK[current_user.role] >= ROLE_RANK[min_role]`.
- If insufficient: raise `HTTPException(status_code=403, detail="Insufficient permissions")`.

### 8.3 Special RBAC Rules

- Owner cannot be demoted via team API. Returns 403 with explicit message.
- Owner can only be transferred: `PUT /team/{memberId}/role` with `{ role: "owner" }` — this promotes the target and demotes current owner to admin.
- Admin cannot change the role of the owner.
- Members cannot remove themselves if they are the owner.
- Members can remove themselves if editor/viewer.

---

## PART 9 — All API Endpoints (Full Specification)

> All authenticated routes require `Authorization: Bearer {access_token}`.
> All org-scoped routes require the path `org_id` to match the JWT's `org_id`.
> Role notation: (viewer) = minimum role required.

---

### 9.1 Auth (`/v1/auth`)

All auth endpoints are unauthenticated (no JWT required). Apply auth rate limit (10 req / 15 min / IP).

**POST /v1/auth/signup**
- Body: `{ email, name, password, org_name }`
- Password rules: min 8 chars, at least 1 number, 1 uppercase, 1 special char. Validated by Pydantic validator.
- Response: `{ message, user_id, org_id }`
- Errors: 409 if email already exists

**POST /v1/auth/verify-email**
- Body: `{ user_id, token }`
- Response: `{ message }`
- Errors: 400 if token invalid or expired

**POST /v1/auth/login**
- Body: `{ email, password }`
- Response: `{ access_token, refresh_token, user: { id, email, name, org_id, role } }`
- Errors: 401 wrong credentials, 403 email not verified

**POST /v1/auth/refresh**
- Body: `{ refresh_token }`
- Response: `{ access_token, refresh_token }`
- Errors: 401 if refresh token invalid/expired/revoked

**POST /v1/auth/logout**
- Body: `{ refresh_token }`
- Response: `{ message }`

**POST /v1/auth/forgot-password**
- Body: `{ email }`
- Response: `{ message }` (always 200 — no enumeration)

**POST /v1/auth/reset-password**
- Body: `{ user_id, token, new_password }`
- Response: `{ message }`
- Errors: 400 if token invalid or expired

**GET /v1/auth/google** — no auth
- Browser redirect to Google OAuth consent URL (302 response)

**GET /v1/auth/google/callback** — no auth
- Query: `?code=...&state=...`
- Exchanges code → verifies id_token → JIT provision or link → issues tokens
- Response: 302 redirect to `{FRONTEND_URL}/auth/callback?accessToken=...&refreshToken=...`
- On error: 302 redirect to `{FRONTEND_URL}/login?error=oauth_failed`

---

### 9.2 Organizations (`/v1/orgs/{org_id}`)

**GET /v1/orgs/{org_id}** — viewer
- Response: `{ id, name, plan, billing_period_start, currency, timezone, feature_flags, created_at }`

**PUT /v1/orgs/{org_id}** — admin
- Body: `{ name?, timezone?, currency?, billing_period_start? }`
- Response: updated org object

---

### 9.3 Cloud Accounts (`/v1/orgs/{org_id}/accounts`)

**GET /** — viewer
- Response: array of account objects (credentials_enc excluded)
- Fields: `{ id, provider, account_id, display_name, scope, last_sync, last_sync_status, last_sync_error, data_as_of, is_active, created_at }`
- **Sync status indicator rules** (backend returns the raw fields; frontend uses this logic):
  - 🟢 Green: `last_sync_status = 'success'` AND `data_as_of > NOW() - 24h`
  - 🟡 Yellow: `last_sync_status = 'success'` AND `data_as_of <= NOW() - 24h` (stale)
  - 🔴 Red: `last_sync_status = 'failed'` (show `last_sync_error` inline)
  - ⚪ Grey: `last_sync_status = 'never'` (never synced)

**POST /** — admin
- Body: `{ provider, display_name, scope, credentials }` where credentials is provider-specific JSON:
  - AWS: `{ role_arn, external_id, region }`
  - Azure: `{ tenant_id, client_id, client_secret, subscription_id }`
  - GCP: `{ project_id, dataset_id, table_prefix, service_account_json }`
- Encrypts credentials with AES-256-GCM before storing
- Creates `account_groups` row if no group exists for (org_id, provider, scope), otherwise reuses
- Creates `cloud_accounts` row
- Creates `notification_settings` row for org if not already exists
- Dispatches Celery task to `prism-sync` with `backfill=True` (13-month historical pull)
- Response `201`: `{ id, provider, account_id, display_name, last_sync_status, created_at }`
- Errors: 409 if duplicate (org_id, provider, account_id)

**GET /{account_id}** — viewer
- Response: single account object

**PUT /{account_id}** — admin
- Body: `{ display_name?, credentials? }`
- If credentials provided: re-encrypt and store. Mark `last_sync_status = 'never'` to trigger re-test.
- Response: updated account

**DELETE /{account_id}** — admin
- Soft delete: `is_active = False`
- Response: `{ message }`

**POST /{account_id}/test** — admin
- Decrypts credentials. Calls connector's `health_check()` method.
- Response: `{ ok: true/false, error?: string }`

**POST /{account_id}/sync** — admin
- Rate limited: 5 req / 1 hour / account
- Dispatches `prism-sync` task with `backfill=False` (last 3 days only)
- Response: `{ message, task_id }`

**GET /{account_id}/sync-logs** — viewer
- Query: `?page=1&limit=20`
- Response: paginated sync_logs for this account

---

### 9.4 Costs (`/v1/orgs/{org_id}/costs`)

All cost endpoints are read-only (viewer). All support `?month=YYYY-MM` (default: current month). Redis cache applies (5 min TTL per endpoint+org+month combination).

**Cost View Toggle (amortized / unblended):**
- All cost queries support `?view=unblended|amortized` param. Default: `unblended`.
- `unblended`: use `cost_unblended_usd` — standard AWS billing, no RI/SP spreading
- `amortized`: use `cost_amortized_usd` — RI/SP cost spread over commitment period
- Azure and GCP: `cost_unblended_usd = cost_amortized_usd = cost_usd` (no distinction)
- Backend always returns both columns in detail views so frontend can switch without re-fetching

**GET /** — Overall cost summary
- Response: `{ month, by_provider: [{ provider, total_usd, total_amortized_usd, account_count, service_count }], total_usd, total_amortized_usd, prev_month_total_usd }`

**GET /by-service** — Cost grouped by service
- Query: `?provider`, `?page`, `?limit`
- Response: paginated `[{ service, provider, total_usd, prev_month_usd, change_pct }]`

**GET /by-day** — Daily spend for trend chart
- Response: `[{ date: "YYYY-MM-DD", total_usd, by_provider: { aws, azure, gcp } }]`

**GET /by-tag** — Cost grouped by tag value
- Query: `?tag_key=virtual_team` (required)
- Response: `[{ tag_value, total_usd, pct_of_total }]`

**GET /top-services** — Top N most expensive services
- Query: `?limit=10` (default 10, max 50)
- Response: `[{ service, provider, total_usd, rank }]`

---

### 9.5 Budget Caps (`/v1/orgs/{org_id}/caps`)

**GET /** — viewer
- Response: all active caps for org with current month spend and percentage

**POST /** — editor
- Body: `{ name, scope, scope_value, cap_amount, period }`
- `scope`: platform / service / account
- `scope_value`: "aws" | "azure" | "gcp" | service name | account UUID
- After creating: immediately dispatch `prism-alerts` task to check the new cap
- Response `201`: created cap object

**GET /{cap_id}** — viewer
- Response: cap with current month spend, pct used, alert history

**PUT /{cap_id}** — editor
- Body: `{ name?, cap_amount?, is_active? }`
- Response: updated cap

**DELETE /{cap_id}** — admin
- Soft delete: set `deleted_at = NOW()`, `is_active = False`
- Response: `{ message }`

---

### 9.6 Alerts (`/v1/orgs/{org_id}/alerts`)

**GET /** — viewer
- Query: `?type`, `?severity`, `?acknowledged=false`, `?page`, `?limit`
- Response: paginated alerts sorted by `triggered_at DESC`

**POST /{alert_id}/acknowledge** — viewer (self-serve)
- Sets `acknowledged_at = NOW()`, `acknowledged_by = current_user.id`
- Response: updated alert

**POST /{alert_id}/snooze** — viewer
- Body: `{ snooze_until: ISO-8601 datetime }`
- Response: updated alert

---

### 9.7 Team Management (`/v1/orgs/{org_id}/team`)

**GET /** — viewer
- Response: `[{ id, user_id, email, name, role, invite_accepted, created_at }]`

**POST /invite** — admin
- Body: `{ email, role }`
- Checks: email not already a member (409). Role must not be 'owner' (400).
- Generates raw invite token (`secrets.token_hex(32)`). Bcrypt-hash. Store in `invites`.
- Sends invite email with link: `{FRONTEND_URL}/accept-invite?token={raw}&org_id={org_id}`.
- Response `201`: `{ message, invite_id }`

**POST /accept-invite** — no auth
- Body: `{ token, org_id, name, password }` (name+password for new users) OR `{ token, org_id }` (existing users)
- Find invite by `org_id`. Compare token against `token_hash`. Check `expires_at > NOW()` and `accepted_at IS NULL`.
- If new user: create `User` + `TeamMember`. Set `accepted_at`.
- If existing user: create `TeamMember`. Set `accepted_at`.
- Return `{ message, user_id }`. User must log in separately.
- Errors: 400 expired, 409 already accepted

**PUT /{member_id}/role** — admin (owner for owner transfer)
- Body: `{ role }`
- Cannot demote owner (403). Admin cannot change owner's role (403).
- Owner transfer: promote target to owner, demote current owner to admin (atomic transaction).
- Response: updated member

**DELETE /{member_id}** — admin
- Cannot remove owner (403). Can remove self if not owner.
- Response: `{ message }`

---

### 9.8 Reports (`/v1/orgs/{org_id}/reports`)

**GET /** — viewer
- Response: report config `{ is_active, recipient_emails, send_day, next_send, last_sent, include_* flags }`

**PUT /** — admin
- Body: `{ is_active?, recipient_emails?, send_day?, include_recommendations?, include_finops_scorecard?, include_commitments?, include_unit_economics? }`
- `send_day` must be 1–28 (enforced by Pydantic `ge=1, le=28`).
- After update: recompute `next_send` (next occurrence of `send_day` at 09:00 UTC).
- Response: updated config

**POST /send-now** — admin
- Dispatches `prism-reports` Celery task immediately without changing `next_send`.
- Response: `{ message, task_id }`

---

### 9.9 Recommendations (`/v1/orgs/{org_id}/recommendations`)

**GET /** — viewer
- Query: `?type`, `?status=open`, `?provider`, `?page`, `?limit`
- Response: paginated recommendations sorted by `savings_usd DESC`

**PUT /{rec_id}/status** — editor
- Body: `{ status }` where status ∈ `[implemented, rejected, archived]`
- Response: updated recommendation

---

### 9.10 Forecasts (`/v1/orgs/{org_id}/forecasts`)

**GET /** — viewer
- Query: `?month=YYYY-MM` (default: current month), `?provider=aws|azure|gcp|all`
- Response: `{ month, provider, daily_avg, projected_total, cap_amount, will_breach, days_elapsed, days_with_data, data_coverage, computed_at }`
- If `data_coverage = 'insufficient'`: return as-is with `{ projected_total: null }` — frontend shows placeholder

**GET /history** — viewer
- Response: last 12 months of org-level forecasts where `actual_total IS NOT NULL` (accuracy history)
- Response: `[{ month, projected_total, actual_total, variance_pct }]`

---

### 9.11 Commitments (`/v1/orgs/{org_id}/commitments`)

**GET /** — viewer
- Query: `?provider`, `?status=active`, `?page`, `?limit`
- Response: paginated commitment records

**GET /summary** — viewer
- Response: `{ total_monthly_cost, avg_utilization_pct, avg_coverage_pct, by_provider: [...] }`

**GET /expiring** — viewer
- Query: `?days=30` (commitments expiring within N days)
- Response: list sorted by `end_date ASC`

---

### 9.12 FinOps Scorecard (`/v1/orgs/{org_id}/scorecard`)

**GET /** — viewer
- Response: `{ overall_score, grade, computed_at, metrics: [{ name, score, weight, current_value, target_value, status }] }`

**GET /executive** — viewer
- Response: simplified view for C-suite — just `{ overall_score, grade, top_wins, top_risks }`

---

### 9.13 Notifications (`/v1/orgs/{org_id}/notifications`)

**GET /** — viewer
- Response: notification settings (webhook URLs shown as `***` after first 5 chars; signing secrets never returned)

**PUT /** — admin
- Body: `{ alert_emails?, teams_webhook_url?, slack_webhook_url?, alert_threshold_75?, alert_threshold_90?, alert_threshold_100?, alert_threshold_125?, alert_threshold_150? }`
- Webhook URLs: validated with SSRF guard (`validate_webhook_url()`) before storing
- Response: updated settings

**POST /test/email** — admin
- Sends a test email to `alert_emails`. Response: `{ message }`

**POST /test/teams** — admin
- Sends a test message to `teams_webhook_url`. Response: `{ ok, error? }`

**POST /test/slack** — admin
- Sends a test message to `slack_webhook_url`. Response: `{ ok, error? }`

---

### 9.14 Virtual Tags (`/v1/orgs/{org_id}/virtual-tags`)

**GET /** — viewer
- Response: all virtual tag rules for org sorted by `priority ASC`

**POST /** — editor
- Body: `{ name, tag_key, tag_value, conditions, split_config?, priority? }`
- Validates: `conditions` is non-empty array; `split_config.targets` pct sum = 100 if provided; regex values pass ReDoS safety check.
- Auto-assigns `priority = max(existing priorities) + 1` if not provided.
- Response `201`: created rule

**PUT /{rule_id}** — editor
- Body: `{ name?, tag_key?, tag_value?, conditions?, split_config?, is_active? }`
- Same validation as POST.
- Response: updated rule

**DELETE /{rule_id}** — editor
- Sets `is_active = False`
- Response: `{ message }`

**PUT /reorder** — editor
- Body: `{ order: [{ rule_id, priority }] }`
- Updates priority for all listed rules in one transaction
- Response: `{ message }`

**POST /{rule_id}/apply** — editor
- Dispatches `prism-virtual-tags` Celery task for retroactive re-tag
- Response: `{ message, task_id }`

**GET /audit-log** — viewer
- Response: paginated `virtual_tag_audit_log` entries

---

### 9.15 Outbound Webhooks (`/v1/orgs/{org_id}/webhooks`)

**GET /** — viewer
- Response: list of webhooks (signing_secret_enc never returned)

**POST /** — admin
- Body: `{ url, events }` where events ∈ `["alert.fired", "sync.complete", "forecast.updated", "report.sent"]`
- Validates URL with SSRF guard. Must be `https://`.
- Generates signing secret (`secrets.token_hex(32)`). Encrypts and stores.
- Response `201`: `{ id, url, events, signing_secret }` — `signing_secret` shown **once only**

**PUT /{webhook_id}** — admin
- Body: `{ url?, events?, is_active? }`
- Response: updated webhook

**DELETE /{webhook_id}** — admin
- Hard delete
- Response: `{ message }`

**POST /{webhook_id}/test** — admin
- Sends a test payload to the webhook URL
- Rate limited: 10 req / 1 hour / org
- Response: `{ ok, status_code?, error? }`

---

### 9.16 LLM (`/v1/orgs/{org_id}/llm`)

**GET /** — admin
- Response: `{ model, monthly_budget_usd, is_enabled, api_key_set: true/false }` — never return api_key_enc

**PUT /** — admin
- Body: `{ api_key?, model?, monthly_budget_usd?, is_enabled? }`
- If `api_key` provided: encrypt with AES-256-GCM before storing
- Response: updated config (without api_key)

**DELETE /** — admin
- Removes LLM config entirely. Sets all LLM features to disabled.
- Response: `{ message }`

**POST /query** — viewer
- Rate limited: 20 req / 1 hour / user
- Body: `{ question }` (natural language question about org's cost data)
- System builds context from cost data, calls LLMService
- If LLM not configured or returns None: `{ answer: null, used_llm: False, fallback_message: "LLM not configured." }`
- Response: `{ answer, used_llm, tokens_used? }`

---

### 9.17 Business Metrics (`/v1/orgs/{org_id}/metrics`)

**GET /** — viewer
- Response: active metrics for this org

**POST /** — admin
- Body: `{ name, source, unit }`
- Unique (org_id, name) — 409 on duplicate
- Response `201`: created metric

**DELETE /{metric_id}** — admin
- Soft delete: `is_active = False`
- Response: `{ message }`

**POST /{metric_id}/values** — editor
- Body: `{ values: [{ date: "YYYY-MM-DD", value: float }] }` (max 1000 entries per call)
- Upserts values (ON CONFLICT on (metric_id, date) → update value)
- Response: `{ message }`

**GET /{metric_id}/values** — viewer
- Query: `?days=30` (max 365)
- Response: `[{ date, value }]` sorted by date

**GET /unit-economics** — viewer
- Returns cost-per-metric ratios for the current (or `?month=YYYY-MM`) month
- Calculation per active metric:
  1. `metric_total = SUM(values.value)` for the month
  2. `cloud_total = SUM(cost_records.cost_usd)` for org+month
  3. If `metric_total > 0`: `cost_per_unit = cloud_total / metric_total`; else `cost_per_unit = None`
  4. Also compute 30-day and 90-day trends
- Response: `[{ metric_name, unit, metric_total, cloud_total, cost_per_unit, trend_30d, trend_90d }]`
- Cache: 15 min TTL (Redis key `unit:econ:{org_id}:{YYYY-MM}`)

---

### 9.18 Resources (`/v1/orgs/{org_id}/resources`)

**GET /** — viewer
- Query: `?provider`, `?idle=true`, `?page`, `?limit`
- Response: paginated resources sorted by `last_cost_usd DESC`

**GET /idle** — viewer
- Response: top 100 idle resources (`is_idle=True`) sorted by `idle_since ASC`, then `last_cost_usd DESC`

**GET /{resource_id}** — viewer
- Response: full resource object

---

### 9.19 API Keys (`/v1/orgs/{org_id}/api-keys`)

Machine-to-machine keys for CI/CD integrations (Terraform cost checks, custom dashboards).

**GET /** — admin
- Response: `[{ id, name, key_prefix, scopes, expires_at, last_used, created_at, revoked_at }]`
- Never return `key_hash`. `key_prefix` (first 8 chars) shown for identification only.

**POST /** — admin
- Body: `{ name, scopes, expires_at? }` where scopes ⊆ `["cost.read", "alerts.read", "reports.read", "webhooks.write"]`
- Generates `secrets.token_hex(32)` as raw key
- Stores `pwd_context.hash(raw_key)` in `api_keys.key_hash`
- Stores first 8 chars in `api_keys.key_prefix`
- Response `201`: `{ id, name, key_prefix, scopes, raw_key }` — raw_key shown **once only**

**DELETE /{key_id}** — admin
- Sets `revoked_at = NOW()`
- Response: `{ message }`

**API Key Auth FastAPI Dependency:**
- Requests with `Authorization: Bearer prism_...` (token starts with `prism_`) use API key auth path
- Dependency: find `api_keys` rows where `key_prefix = token[6:14]` for this org. `pwd_context.verify` each.
- If valid and not revoked and not expired → proceed with `{ org_id, scopes }` context
- API key requests: rate limited to 120 req/min per key
- On use: `UPDATE api_keys SET last_used = NOW()`
- Scope enforcement: a `cost.read`-only key cannot POST to `/caps`

---

### 9.20 Incoming Integration Callbacks

**POST /v1/integrations/teams** — no JWT auth; HMAC validated
- Validates Teams signature using `validate_hmac("teams")` dependency
- Processes button actions (acknowledge alert, snooze alert)
- Response: 200 (always respond quickly to Teams to avoid timeout)

**POST /v1/integrations/slack** — no JWT auth; HMAC validated
- Validates Slack signature using `validate_hmac("slack")` dependency
- Processes Slack interactive component payloads
- Response: 200

---

## PART 10 — Cloud Connector Specifications

### 10.1 General Rules for All Connectors

- Credentials decrypted just before use, never cached in memory between requests
- All API calls go through `with_retry(fn, max_retries=3)` from `utils/retry.py` (built with `tenacity`):
  - Do NOT retry on 401, 403, or credential errors (`retry_if_not_exception_type([AuthError, ForbiddenError])`)
  - On 429: read `retry-after` header, wait that many seconds (max 120s), then retry
  - On other errors: exponential backoff starting at 1 second, doubling each attempt, max 30 seconds
- Results bulk-upserted to `cost_records` using `ON CONFLICT DO UPDATE`
- Only cost > 0 rows are stored (skip zero-cost line items)
- Each connector must implement: `get_cost_and_usage(start_date, end_date)`, `get_resources()`, `get_commitments()`, `health_check()`

### 10.2 AWS Connector

**Authentication:**
- Use boto3 `sts.assume_role(RoleArn=..., RoleSessionName="prism", ExternalId=...)`
- Temporary credentials (AccessKeyId, SecretAccessKey, SessionToken) expire in 1 hour — re-assume before each task run
- `ExternalId` prevents confused deputy attacks — it is generated by PRISM and shown during account setup wizard

**Cost Data:**
- boto3 `ce.get_cost_and_usage()`
- Granularity: `DAILY`
- Metrics: `["UnblendedCost", "AmortizedCost", "UsageQuantity"]`
- GroupBy: `[SERVICE, REGION]`
- Date range: yesterday (daily) or 13 months back (backfill)

**Amortized vs Unblended:**
- Store both in `cost_amortized_usd` and `cost_unblended_usd` columns

**Resource Discovery:**
- boto3 `ec2.describe_instances()` per configured region
- Upsert to `resources` on `(account_id, resource_id)`
- Mark idle if `last_activity_at < NOW() - 7 days` and `last_cost_usd > 0`

**Commitments:**
- `ce.get_reservation_utilization()` for RI utilization
- `ce.get_reservation_coverage()` for RI coverage
- `ce.get_savings_plans_utilization_details()` for SP utilization
- `ce.get_savings_plans_coverage()` for SP coverage

**IAM Policy Required (read-only):**
```
ce:GetCostAndUsage
ce:GetReservationUtilization
ce:GetReservationCoverage
ce:GetSavingsPlansUtilizationDetails
ce:GetSavingsPlansCoverage
ec2:DescribeInstances
```

**Health Check:**
- Minimal CE call with 1-day window. Returns `{ ok, error? }`.

### 10.3 Azure Connector

**Authentication:**
- `azure.identity.ClientSecretCredential(tenant_id=..., client_id=..., client_secret=...)`
- Token acquired per request — `azure-identity` handles caching internally
- `fx_rate` fetched from `FXService` and passed at construction time — never `None`

**Cost Data:**
- `POST /subscriptions/{id}/providers/Microsoft.CostManagement/query` via httpx
- api-version: `2021-10-01`
- Granularity: `Daily`
- GroupBy: `ServiceName` + `ResourceGroup`
- Convert cost to USD at ingestion using fx_rate

**Health Check:**
- `GET /subscriptions/{id}` with api-version 2020-01-01

### 10.4 GCP Connector

**Authentication:**
- Service account JSON key (stored encrypted in `credentials_enc`)
- Passed to `google.cloud.bigquery.Client(credentials=service_account.Credentials.from_service_account_info(json_key))`

**Cost Data:**
- BigQuery billing export table: `{project_id}.{dataset_id}.{table_prefix}*`
- **Always use parameterized queries** (`@start_date`, `@end_date`) — never f-string or `.format()` interpolation
- Group by: `usage_date, service.description, location.region, currency`
- Filter: `cost > 0`

**Health Check:**
- Call `client.get_dataset(dataset_id)`. Returns `{ ok, error? }`.

### 10.5 Tag Normalization (Unified Schema)

Each cloud provider uses a different tagging model. All raw tags must be normalized to a single dict before storing in `cost_records.tags` (JSONB).

**AWS Tags:**
- Source: `Tags` list in CE response — `[{ "Key": "Environment", "Value": "prod" }]`
- Normalize: `{ key.lower().strip(): value.strip() for key, value in tags }`

**Azure Tags:**
- Source: `tags` object in Cost Management response — `{ "Environment": "prod" }`
- Normalize: same — lowercase all keys, strip values

**GCP Labels:**
- Source: `labels` repeated field in BigQuery billing export — `[{"key": "environment", "value": "prod"}]`
- Already lowercase by GCP convention; still strip whitespace
- GCP `system_labels` — **ignore** (PRISM only stores user-defined labels)

**Reserved PRISM Tag Keys:**
- `virtual_team`, `virtual_project`, etc. (prefixed with `virtual_`) — written only by VirtualTagEngine
- Cloud sync upsert: `tags = EXCLUDED.tags || cost_records.tags` (cloud-provided overwrites, but existing `virtual_*` keys are preserved via the merge order — set the merge so existing `virtual_*` wins)
- Sync must never overwrite keys prefixed with `virtual_`

**Cross-provider matching:**
- Virtual tag rule targeting `key = "environment"` matches AWS, Azure, and GCP tags after normalization

---

## PART 11 — Background Job System

### 11.1 Queue Architecture

All queues use Celery backed by Redis as broker AND result backend. Each queue has a dedicated worker concurrency config.

| Queue | Trigger | Concurrency | Typical Duration |
|-------|---------|-------------|-----------------|
| prism-sync | Celery Beat 06:00 UTC + manual | 5 | 2–10 min per account |
| prism-alerts | After each sync + on cap create | 10 | <1 min |
| prism-forecast | Celery Beat 07:30 UTC | 5 | <30 sec |
| prism-commitments | Celery Beat 07:00 UTC | 3 | 2–5 min |
| prism-recommendations | Celery Beat 08:00 UTC | 3 | 1–5 min |
| prism-reports | Celery Beat 09:00 UTC (daily check) | 2 | 30 sec – 2 min |
| prism-virtual-tags | On rule save by user | 1 (serialized) | 2 min per 1M rows |
| prism-dlq | Automatic (tasks that failed 3×) | 1 | <1 sec |

### 11.2 Idempotency Rules

- Every task has a deterministic `task_id` format: `{type}:{org_id_or_account_id}:{YYYY-MM-DD}`
- Celery `task_id` deduplication: use `apply_async(task_id=..., ignore_result=True)` — Celery deduplicates by task_id
- `cost_records` upsert with `ON CONFLICT DO UPDATE` ensures duplicate syncs are safe
- `resource` upserts with `ON CONFLICT (account_id, resource_id) DO UPDATE SET last_seen = NOW()` are safe
- Alert deduplication via unique partial index in DB (not application logic alone)

### 11.3 Retry Policy

- All queues: `max_retries=3`, backoff: exponential starting at 60 seconds (`countdown=60 * (2 ** self.request.retries)`)
- After 3 failures: task moves to `prism-dlq` (via `link_error` or dedicated error callback)
- DLQ task: log the failure at ERROR level, optionally create a `sync_failure` alert in DB, do NOT retry
- DLQ task result retained: 14 days

### 11.4 Scheduler (Celery Beat)

`celery_app.py` defines the `beat_schedule` dict. Each schedule entry:
1. Calls a periodic Celery task
2. That task queries DB for eligible orgs or accounts
3. For each: dispatches one task per org/account to the appropriate Celery queue
4. Does NOT do the actual work inline

Beat schedule (all UTC):
- `crontab(hour=6, minute=0)` → `prism-sync` (one task per active cloud_account)
- `crontab(hour=7, minute=0)` → `prism-commitments` (one task per org)
- `crontab(hour=7, minute=30)` → `prism-forecast` (one task per org)
- `crontab(hour=8, minute=0)` → `prism-recommendations` (one task per org)
- `crontab(hour=9, minute=0)` → `prism-reports` (one task per org where `next_send <= today`)
- `crontab(hour=10, minute=0, day_of_month=1)` → **forecast accuracy task** (once a month, 1st of month)
  - For each `spend_forecasts` row where `month = last month` and `actual_total IS NULL`:
    - Query `SUM(cost_usd)` from `cost_records` for that org+provider for the closed month
    - `UPDATE spend_forecasts SET actual_total = X, variance_pct = (X - projected_total) / projected_total * 100`
- `crontab(hour=2, minute=0)` → **purge task** (daily, lightweight)
  - `DELETE FROM sync_logs WHERE created_at < NOW() - INTERVAL '90 days'`
  - `DELETE FROM alerts WHERE created_at < NOW() - INTERVAL '180 days' AND acknowledged_at IS NOT NULL`
  - Log count of rows deleted

### 11.5 Sync Worker — Step by Step

1. Receive `{ account_id, org_id, backfill }` from Celery queue
2. Insert `sync_logs` row (`status='running'`)
3. Update `cloud_accounts.last_sync_status = 'running'`
4. Fetch account from DB; call `aes_decrypt(credentials_enc)` to get credentials JSON
5. Get FX rate from FXService (async — use `asyncio.run()` in Celery worker or run via event loop)
6. Determine date range: backfill → 13 months back; normal → last 3 days (re-sync recent estimates)
7. Call `connector.get_cost_and_usage(start_date, end_date)`
8. Normalize tags for all records (10.5)
9. Bulk upsert records in chunks of 500 using `asyncpg.executemany()` with `ON CONFLICT DO UPDATE`
10. Call `connector.get_resources()` and upsert resources
11. Update `cloud_accounts`: `last_sync, last_sync_status='success', data_as_of, last_sync_records`
12. Update `sync_logs`: `finished_at, status='success', records_synced`
13. Call `invalidate_dashboard_cache(org_id, provider)` (Redis key deletion)
14. Call `ws_broadcast(org_id, { event: "sync.complete", data: { provider, records } })`
15. Dispatch `prism-alerts` task for this org
16. On any exception: update account and sync_log to failed status, re-raise (Celery retries)

**Celery + asyncpg note:** Celery workers run synchronously by default. For DB access, either:
- Use `psycopg2` (sync) in workers exclusively, or
- Use `asyncio.run()` to run async asyncpg calls in each task (simpler, recommended)
- Use `gevent` or `eventlet` pool with `asyncio` bridge only if latency matters significantly

---

## PART 12 — Alert & Notification System

### 12.1 Alert Types and Triggers

| Type | Trigger | Severity | Dedup Rule |
|------|---------|---------|-----------|
| cap_threshold | Current month spend ≥ threshold % of cap | warning (75/90) / critical (100+) | Once per (cap, threshold, billing month) via unique DB index |
| forecast_breach | projected_total > cap_amount | warning | Once per (org, provider, billing month) |
| spend_acceleration | Daily avg this week > last week by 30%+ | warning | Once per (org, provider, week) |
| sync_failure | Sync task fails after 3 retries | critical | On every failure (no dedup — real errors always notify) |
| credential_expiry | Azure/GCP credential expires ≤ 14 days | warning | Once per (account, 30-day window) |
| commitment_expiry | RI/SP/CUD expires ≤ 30 days | warning | Once per (commitment, 30-day window) |
| unused_commitment | Commitment utilization < 80% | warning | Once per (commitment, billing month) |
| untagged_resource | New resource with no owner/team tag | info | Once per resource per discovery |
| idle_resource | Resource has 0 usage for 7+ days | info | Once per (resource, idle_since month) |

### 12.2 CapAlertService — Step by Step

For each active `budget_cap` in the org:
1. Query `cost_records` for current month, matching `scope_value` (provider/service/account)
2. `pct = (spent / cap_amount) * 100`
3. For each threshold `t` in `[75, 90, 100, 125, 150]` (if enabled in notification_settings):
   - Check if `pct >= t`
   - Query DB for existing alert: `SELECT 1 FROM alerts WHERE cap_id=$1 AND threshold_percent=$2 AND date_trunc('month', triggered_at) = date_trunc('month', NOW()) AND type='cap_threshold'`
   - If no existing alert: insert alert row, then fire all channels
4. Fire channels concurrently with `asyncio.gather(*[send_email(), send_teams(), send_slack(), send_webhooks()], return_exceptions=True)` — use `return_exceptions=True` so one failure doesn't block others
5. Update alert row: `email_sent`, `teams_sent`, `slack_sent`, `webhook_sent` based on results

### 12.3 Notification Channels

**Email:**
- Use `EmailService.send_alert_email(alert, org, cap)` via boto3 SES
- Subject: `"⚠️ {scope_value} at {pct}% — {org.name}"` (specific, never generic)

**Teams:**
- POST to `notification_settings.teams_webhook_url` via httpx with Adaptive Card JSON
- Validate Teams signature on incoming callbacks (HMAC-SHA256)

**Slack:**
- POST to `notification_settings.slack_webhook_url` via httpx with Block Kit JSON
- Validate Slack signature on incoming callbacks

**Outbound Webhooks:**
- For each active `outbound_webhooks` row subscribing to `"alert.fired"`:
  - Sign payload with HMAC-SHA256 using `signing_secret`
  - POST via httpx with `X-PRISM-Signature` header
  - Validate URL with SSRF guard at dispatch time (DNS rebinding protection)

---

## PART 13 — WebSocket (Real-Time Events)

### 13.1 Connection Lifecycle

1. Client connects to `wss://api.prism.io/ws?token={jwt}` (FastAPI WebSocket endpoint)
2. Server validates JWT from query string on connect — closes with code 4001 if invalid/expired
3. Server registers the connection: `org_connections: dict[str, set[WebSocket]]`; `org_connections[org_id].add(ws)`
4. Server sends `{ event: "connected", org_id, timestamp }` confirmation
5. Server starts a 30-second ping loop (`asyncio.create_task(ping_loop(ws))`)
6. On disconnect: remove from `org_connections[org_id]`; cancel ping task; clean up empty sets

### 13.2 Events Broadcast (Server → Client)

All events share this envelope:
```
{
  "event": string,
  "org_id": string,
  "timestamp": ISO-8601 string,
  "data": object
}
```

| Event | When fired | Data payload |
|-------|-----------|--------------|
| `sync.complete` | After sync task finishes | `{ provider, account_id, records }` |
| `alert.fired` | When new alert is inserted | `{ alert_id, type, scope, severity, threshold_percent }` |
| `forecast.updated` | After forecast recalculation | `{ provider, projected_total, will_breach, data_coverage }` |
| `recommendation.new` | When new recs are generated | `{ count, top_savings }` |
| `virtual_tags.progress` | During retroactive re-tag | `{ processed, updated }` (batched) |
| `connected` | Immediately after connect | `{}` — confirms connection |

### 13.3 Broadcast Rules

- `ws_broadcast(org_id, event_dict)` is called from workers and services
- Only sends to `WebSocket` instances in `org_connections.get(org_id, set())`
- Never broadcasts across org boundaries
- Skips clients whose `client_state != WebSocketState.CONNECTED`
- `ws_broadcast` from a Celery worker: use `httpx` to POST to an internal `/internal/ws-broadcast` endpoint on the API process (since workers are separate processes and don't share memory)

### 13.4 Multi-Instance Scaling (Redis Pub/Sub)

In a single-instance deployment, the in-memory `dict` works fine. For horizontal scaling (multiple pods), each pod has its own dict.

**How to implement (v2):**
1. Maintain two Redis connections: one for commands, one dedicated to Pub/Sub (`aioredis.create_redis_pool` with `SUBSCRIBE` only)
2. `ws_broadcast(org_id, event)`:
   - `PUBLISH prism:ws:{org_id}` with serialized JSON payload
3. At startup, each API instance subscribes to `prism:ws:*` via `psubscribe` (pattern subscribe)
4. On received Pub/Sub message: parse org_id from channel name, deliver to local `org_connections.get(org_id)`

**v1 default:** single instance only (no Redis Pub/Sub). Mark `org_connections` dict with a `# ponytail: in-memory only; upgrade to Redis Pub/Sub for multi-instance` comment.

---

## PART 14 — LLM Integration (OpenRouter)

### 14.1 Design Principles

- LLM is entirely optional — every feature works without it
- Every caller of `LLMService` checks for `None` return and has a non-LLM fallback
- LLM is never on the critical path for any user-facing action
- The user provides their own OpenRouter API key (PRISM never bills for LLM)
- API key stored AES-256-GCM encrypted in `llm_configs`

### 14.2 LLMService Behavior

1. `LLMService.for_org(org_id)` — classmethod factory. Loads config from DB. If no config or disabled → returns a disabled-mode instance.
2. `can_call()` → returns `False` if not enabled, OR if `spent_this_month >= monthly_budget_usd`
3. Monthly spend tracked in Redis (`llm:monthly_spent:{org_id}:{YYYY-MM}`), not DB
4. All prompts checked against Redis cache first (`llm:{base64_prompt_hash}`, 24h TTL)
5. On LLM error → `logger.warning` → return `None` (never raise)
6. All callers treat `None` as "use template fallback"
7. HTTP client: `httpx.AsyncClient` (async), base URL `https://openrouter.ai/api/v1`, OpenAI-compatible `/chat/completions` endpoint

### 14.3 LLM Surfaces

| Feature | LLM adds | Fallback when LLM off |
|---------|---------|----------------------|
| Monthly report | Executive narrative paragraph | Template: "Total spend: $X (+Y%)" |
| Recommendations | Explanation + risk note per rec | Show type + savings only |
| Alert context | Natural language summary | Show raw numbers |
| Q&A chat | `POST /v1/orgs/{org_id}/llm/query` | Static "LLM not configured" message |
| Untagged resource ownership | Ownership suggestion | Show resource name + cost only |

### 14.4 Prompt Safety Rules

- Prompts never include credential values, raw API keys, or PII beyond email
- Max prompt size: 4000 chars. Max response tokens: 400 (narrative) / 200 (Q&A) / 150 (explanations)
- Same prompt always returns same cached response (deterministic by hash)
- All prompts include org context but never raw credential data

---

## PART 15 — Virtual Tag Engine

### 15.1 What It Does

Retroactively applies user-defined tags to historical `cost_records.tags` (JSONB) based on matching conditions. Runs as a long Celery task with `soft_time_limit=600` (10-minute soft limit, 630 hard limit).

### 15.2 Condition Operators

| Operator | Applies to | Logic |
|----------|-----------|-------|
| `equals` | service, region, tag value | Exact string match |
| `contains` | service, resource name | `value in field` |
| `starts_with` | service | `field.startswith(value)` |
| `regex` | any string field | `re.search(pattern, field)` — only after ReDoS safety check |
| `greater_than` | cost_usd | Numeric comparison |
| `less_than` | cost_usd | Numeric comparison |
| `tag_exists` | tags | `key in record.tags` |
| `tag_equals` | tags | `record.tags.get(key) == value` |

### 15.3 Rule Evaluation Order

1. Rules are sorted by `priority ASC` (lower number = higher priority)
2. **First-match wins** — once a record matches a rule, no further rules are evaluated for that record
3. Split config: if rule has `split_config`, the tagged cost is split across multiple virtual tag values (creates multiple logical records in the report layer, does not duplicate DB rows)
4. Split pct validation: sum of all `targets[*].pct` must equal 100.0 — validated at rule save time

### 15.4 Retroactive Re-tag Process

1. Celery task `apply_virtual_tags_task(org_id, rule_id)` starts
2. Insert `virtual_tag_audit_log` row (status=running)
3. Fetch all active rules for org sorted by priority
4. Process `cost_records` in batches of 5000 rows (using `LIMIT 5000 OFFSET N` cursor)
5. For each batch: evaluate conditions, compute new tags dict, `UPDATE cost_records SET tags = $1 WHERE id = $2`
6. After every batch: broadcast `virtual_tags.progress` WebSocket event with `{ processed, updated }`
7. On completion: update `virtual_tag_audit_log` (status=completed, rows_processed, rows_updated, finished_at)
8. Task is idempotent — safe to restart (same output on same input)

### 15.5 ReDoS Protection

User-supplied regex patterns must pass validation before storing:
1. Compile pattern: `re.compile(pattern)` — reject with 400 if compilation fails
2. Max pattern length: 200 characters
3. Timing test: run `re.search(pattern, "a" * 1000)` in a thread with 50ms timeout using `concurrent.futures.ThreadPoolExecutor`
4. If timeout exceeded: reject with 400 "Regex pattern has catastrophic backtracking risk"

---

## PART 16 — Spend Forecast Engine

### 16.1 Algorithm

Runs daily per org per provider. Upserts one row to `spend_forecasts`.

1. Query `cost_records` for current month to date: `SELECT time::date, SUM(cost_usd) FROM cost_records WHERE org_id=$1 AND provider=$2 AND time >= $3 GROUP BY time::date ORDER BY time::date`
2. Count `days_with_data` (days where sum > 0)
3. If `days_with_data < 3` → set `data_coverage = 'insufficient'`, skip projection
4. Simple daily average: `daily_avg = total_spend / days_elapsed`
5. Rolling 7-day average: `rolling_avg = SUM(last 7 days) / 7`
6. If any day in last 7 had spend = 0 AND `rolling_avg` differs from `daily_avg` by > 20% → use `rolling_avg` as `daily_avg` (smoothes weekend zeros)
7. `projected_total = daily_avg × days_in_month`
8. `will_breach = projected_total > relevant_cap_amount` (query caps for this org+provider)
9. Upsert to `spend_forecasts` on `(org_id, provider, forecast_month)`

### 16.2 Edge Cases

| Situation | Handling |
|-----------|---------|
| First 1–2 days of month | `data_coverage = 'insufficient'` — frontend shows placeholder |
| Weekend zeros | Use rolling 7d average when it differs >20% from daily average |
| Provider not connected | Skip that provider — no forecast row |
| Month just closed | `actual_total` filled by forecast accuracy task (runs 1st of next month) |
| Retroactive re-tag changes cost data | Forecasts will be recomputed on next daily run |

### 16.3 Forecast Accuracy Computation

At month-end (when `actual_total` is available):
```
variance_pct = (actual_total - projected_total) / actual_total × 100
```
The projection used is the one made on day 15 of the month (mid-month snapshot). Stored in `spend_forecasts.variance_pct` for reporting.

---

## PART 17 — FinOps Health Scorecard

### 17.1 Seven Metrics

| Metric | Formula | Green | Yellow | Red | Weight |
|--------|---------|-------|--------|-----|--------|
| Tagging Coverage | % of cost_records with ≥1 non-virtual tag | ≥90% | 70–89% | <70% | 20% |
| Idle Resource Rate | (1 - idle_resource_count / total_resources) × 100 | ≥95% | 85–94% | <85% | 20% |
| Commitment Coverage | avg coverage_pct from commitment_records | ≥80% | 60–79% | <60% | 20% |
| Budget Cap Coverage | % of active cloud accounts with ≥1 cap | 100% | 75–99% | <75% | 15% |
| Forecast Accuracy | 100 - avg(ABS(variance_pct)) for last 3 months | ≥90% | 80–89% | <80% | 10% |
| Alert Response Time | avg hours from alert triggered to acknowledged | <4h | 4–24h | >24h | 10% |
| Recommendation Action Rate | % of recommendations as implemented/rejected (not open) | ≥80% | 50–79% | <50% | 5% |

### 17.2 Overall Score

`overall_score = SUM(metric_score × metric_weight)` where `metric_score` is 0–100 per metric.

Grades:
- A: 90–100
- B: 80–89
- C: 70–79
- D: 60–69
- F: <60

### 17.3 Caching

Scorecard cached in Redis (`dash:{orgId}:scorecard`, 1h TTL). Invalidated when sync completes or caps are created.

---

## PART 18 — Monthly Report System

### 18.1 Trigger Logic

1. Celery Beat fires at 09:00 UTC daily.
2. Query: `SELECT org_id FROM monthly_reports WHERE is_active=True AND date_trunc('day', next_send) <= date_trunc('day', NOW())`
3. For each matched org: dispatch `prism-reports` Celery task.
4. Task runs `ReportGenerator.generate(org_id)`.
5. After send: `last_sent = NOW()`, `next_send = next month same day at 09:00 UTC`.

### 18.2 Report Sections (in order)

1. **Header**: Org name, report month, generated date
2. **Executive Summary**: Total spend, delta from last month, LLM narrative (or template if LLM off)
3. **Spend by Platform**: Table: provider → this month → last month → change → cap → % of cap
4. **Top 10 Services**: Table: service → provider → this month → change
5. **Spend by Team (Tag)**: If team tags exist — allocate spend by virtual_team tag
6. **Budget Cap Status**: All active caps with spent/cap/% and status indicator
7. **Top 5 Recommendations**: If `include_recommendations = True`
8. **FinOps Health Score**: If `include_finops_scorecard = True`
9. **Commitment Summary**: If `include_commitments = True`
10. **Unit Economics**: If `include_unit_economics = True` and business metrics exist
11. **Forecast Accuracy (last 3 months)**: Forecast vs actual comparison

### 18.3 Test Report

`POST /reports/send-now` sends the report immediately without changing `next_send`. Useful for verifying email delivery and report content.

---

## PART 19 — Email System

### 19.1 Provider

boto3 AWS SES (primary). `send_email()` via `ses_client.send_email()`. SendGrid works as a drop-in via SMTP or API — configure via env vars. Both produce same interface in `EmailService`.

### 19.2 All Email Types

| Email | Trigger | Recipients |
|-------|---------|-----------|
| Email verification | Signup | Signing-up user only |
| Password reset | forgot-password | Requesting user only |
| Team invite | invite API | Invited email address |
| Cap alert (75%) | Alert engine | `notification_settings.alert_emails` |
| Cap alert (90%) | Alert engine | `notification_settings.alert_emails` |
| Cap alert (100%) | Alert engine | `notification_settings.alert_emails` |
| Cap alert (125%) | Alert engine | `notification_settings.alert_emails` |
| Cap alert (150%) | Alert engine | `notification_settings.alert_emails` |
| Forecast breach | Alert engine | `notification_settings.alert_emails` |
| Commitment expiry | Commitment service | `notification_settings.alert_emails` |
| Monthly report | Report generator | `monthly_reports.recipient_emails` |
| Sync failure | DLQ task | `notification_settings.alert_emails` |

### 19.3 Email Content Rules

- All emails must have both HTML and plain-text versions
- Every email includes: from address, org name in subject, link to dashboard, unsubscribe/manage link
- Cap alerts: include spend amount, cap amount, % used, forecast, next threshold, and action links
- Never include credentials or sensitive data in email body
- Email subject must be specific (not generic — "PRISM alert" is bad; "⚠️ AWS EC2 at 90% — Acme Corp" is good)

---

## PART 20 — Security Requirements

### 20.1 Authentication Security

- Passwords: `passlib.context.CryptContext(schemes=["bcrypt"])` with cost factor 12. Never store plaintext.
- JWT secrets: minimum 32 chars of random entropy. Stored in env (never in code or DB).
- Refresh tokens: stored as bcrypt hash in DB. Raw token shown only at issue time.
- Email verification tokens: 24h expiry. Single-use (cleared after verification).
- Invite tokens: 48h expiry. Bcrypt-hashed in DB. Raw token sent once via email.
- Password reset tokens: 1h expiry. Stored bcrypt-hashed in Redis. Deleted after use.
- Login errors: same 401 message for "wrong email" and "wrong password" — no enumeration.
- Login timing: always call `pwd_context.verify` even when user not found (dummy hash) — prevents timing attacks.
- On successful password reset: revoke ALL refresh tokens for that user (all sessions invalidated).

### 20.2 Authorization Security

- Every authenticated route applies `get_current_user` (JWT verify) then `get_org_access` (org_id match).
- `org_id` for DB queries: always from `current_user.org_id` (JWT) — never from request body.
- CSRF: state-changing endpoints (POST/PUT/PATCH/DELETE) require `Authorization: Bearer` header — cookie-only requests are rejected (FastAPI doesn't use cookies for auth by default, so this is naturally satisfied).
- Owner cannot be demoted via team API. Owner can only be transferred to another admin.

### 20.3 Data Security

- Cloud credentials: AES-256-GCM encrypted in DB. Key from env (`ENCRYPTION_KEY`). Never logged.
- LLM API key: AES-256-GCM encrypted.
- Webhook signing secrets: AES-256-GCM encrypted. Raw secret shown once at creation.
- All DB queries: asyncpg parameterized (`$1, $2`). Never Python f-strings or `.format()`.
- BigQuery queries: `@param` syntax — never f-string or `%s` interpolation.

### 20.4 Network Security

- All HTTPS. TLS 1.3 minimum (handled at load balancer / ingress level).
- CORS: locked to `FRONTEND_URL` env var. Configured via FastAPI `CORSMiddleware`.
- Security headers: `starlette.middleware.trustedhost`, custom headers middleware for `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`.
- Teams/Slack webhook validation: HMAC-SHA256 with `hmac.compare_digest()` — never `==`.

### 20.5 SSRF Protection (Outbound Webhooks)

When storing or dispatching a customer-supplied webhook URL:
1. Must be `https://` — reject `http://`, `ftp://`, `file://`, etc.
2. Must not resolve to private IP ranges: 127.x, 10.x, 192.168.x, 172.16–31.x, 169.254.x, ::1, 0.0.0.0
3. DNS re-check at dispatch time (DNS rebinding protection): `socket.getaddrinfo(hostname)` → verify resulting IPs are not private.
4. Reject if hostname cannot be resolved.

Implementation in `utils/validate_webhook_url.py`:
- `validate_webhook_url(url)` — called at save time. Raises `HTTPException(400)` if invalid.
- `verify_dispatch_url(url)` — called at dispatch time. Returns `False` if IP changed to private (DNS rebinding).

### 20.6 Input Validation

- All request bodies validated with Pydantic v2 models before reaching business logic.
- FastAPI raises `422 Unprocessable Entity` for Pydantic validation errors — convert to `400` with custom exception handler.
- Regex patterns: validated for compilation + ReDoS safety (max 50ms on 1000-char test string, max 200 chars).
- Split configs: pct values must sum to 100.0 (validated by Pydantic `@model_validator`).
- Pagination limits: capped at 100 via Pydantic `le=100`.
- Email addresses: Pydantic `EmailStr` type with DNS check.
- URL fields: `AnyHttpUrl` Pydantic type + additional SSRF checks.

### 20.7 Rate Limiting

slowapi (built on limits library) integrated with FastAPI. Uses Redis as backend.

| Endpoint Group | Limit | Window | Key |
|---------------|-------|--------|-----|
| Auth endpoints | 10 req | 15 min | per IP |
| All API endpoints | 300 req | 1 min | per org |
| LLM query | 20 req | 1 hour | per user |
| Manual sync trigger | 5 req | 1 hour | per account |
| Webhook test | 10 req | 1 hour | per org |

Rate limit headers returned on every response: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

---

## PART 21 — Error Handling

### 21.1 Custom Exception Class

`class AppError(Exception)` with `status_code: int` and optional `code: str`. All intentional errors are raised as `AppError`. Unexpected errors bubble to global handler.

### 21.2 FastAPI Exception Handlers

- `@app.exception_handler(AppError)` → respond with `{ "error": exc.detail, "code": exc.code }` at `exc.status_code`
- `@app.exception_handler(RequestValidationError)` → respond with `{ "error": "Validation failed", "details": [...] }` at 400
- `@app.exception_handler(Exception)` → log at `error` level → respond with `{ "error": "Internal server error" }` at 500
- Never include stack traces or DB error messages in 500 responses

### 21.3 Edge Cases That Must Be Handled Explicitly

| Situation | Handling |
|-----------|---------|
| Duplicate sync (task fires twice) | `ON CONFLICT DO UPDATE` — safe |
| Cap alert fires twice same month | Unique partial index in DB — second INSERT raises IntegrityError, caught and ignored |
| LLM call fails | Return `None`, caller uses template |
| LLM budget exceeded | `can_call()` returns `False`, caller uses template |
| Email send fails | Log error, do NOT raise — alert still created in DB |
| Teams/Slack notification fails | Log warn, other channels still fire (asyncio.gather with return_exceptions=True) |
| Webhook URL fails SSRF check | Log warn, skip dispatch, do not error the calling request |
| Retroactive re-tag cancelled/crashed | Task is idempotent — restart from beginning, same output |
| First 3 days of month (forecast) | `data_coverage = 'insufficient'` — frontend shows placeholder |
| Zero-spend weekends in forecast | Use rolling 7d avg |
| User accepts expired invite | 400 — ask inviter to resend |
| User tries to remove org owner | 403 — explicit message |
| Cross-org access attempt | 403 — same message as "org not found" (no information leakage) |
| BigQuery dataset not found | Connector `health_check` returns `{ ok: False, error: message }` |
| STS AssumeRole fails | Connector raises — sync task fails, retries, eventually DLQ |
| DB pool exhausted | asyncpg raises `TooManyConnectionsError` — global handler → 503 |
| Redis connection lost | redis.asyncio auto-reconnects; in-flight operations may fail → log warn |
| asyncpg IntegrityError on alert dedup | Catch `asyncpg.UniqueViolationError`, ignore silently |

---

## PART 22 — Logging & Observability

### 22.1 Logger

structlog at `INFO` level in production, `DEBUG` in development. JSON output in production. Pretty-printed in development.

`structlog.configure()` in `utils/logger.py` with processors: `TimeStamper(fmt="iso")`, `add_log_level`, `JSONRenderer` (production) / `ConsoleRenderer` (development).

Every log entry includes: `service="prism-backend"`, `env=NODE_ENV`, standard ISO-8601 timestamp.

Bind per-request context with `structlog.contextvars.bind_contextvars(org_id=..., user_id=...)` in request middleware.

### 22.2 What to Log

| Event | Level | Fields |
|-------|-------|--------|
| HTTP request | info | method, path, status, duration_ms, org_id |
| User login | info | user_id, org_id, email |
| Login failed | warn | email, ip |
| Sync started | info | account_id, org_id, provider, backfill |
| Sync completed | info | account_id, records, duration_ms |
| Sync failed | error | account_id, error message |
| Alert fired | info | alert_id, org_id, type, threshold |
| Email sent | info | to (list), subject |
| Email failed | error | to, error |
| LLM fallback | warn | org_id, reason |
| DLQ task received | error | task_id, task_name, data |
| Unhandled error | error | error, path, method |

### 22.3 Health Check

`GET /health` — no auth. Returns:
```json
{ "status": "ok" | "degraded", "db": true | false, "redis": true | false, "ts": "ISO-8601" }
```
Status 200 if both DB and Redis are healthy. Status 503 if either fails. Implementation: try a `SELECT 1` on asyncpg pool and a `PING` on redis client; set booleans accordingly.

---

## PART 23 — Edge Cases & Pitfalls

### 23.1 Multi-Tenancy Pitfalls

- Never use `account_id` alone as a query filter without also filtering by `org_id`.
- WebSocket: after lookup, broadcast ONLY to the specific org's connections — never iterate all.
- Cache: use `redis.scan_iter("dash:{org_id}:*")` in a cursor-based loop — never use `KEYS` pattern (blocks Redis).

### 23.2 Sync Pitfalls

- AWS Cost Explorer has a 24–48h data lag — today's data is not available. Always sync yesterday at minimum.
- The "current month" data from AWS is marked `is_estimate = True` — re-sync it daily until month closes.
- Azure Cost Management can return 500 errors during high load — `with_retry` handles this.
- GCP BigQuery billing export must be enabled by the customer before PRISM can pull data — if table doesn't exist, `health_check()` fails with a clear error.
- FX rate must be set before calling AzureConnector — passing `None` causes `NoneType` multiplication error producing NaN costs.

### 23.3 Alert Pitfalls

- The dedup unique index prevents duplicate `cap_threshold` alerts per cap per month. `forecast_breach` alerts use a separate query-based dedup check.
- Snoozed alerts are NOT re-fired when the snooze expires — they remain snoozed. Only new threshold crossings fire new alerts.
- When a cap is deleted (soft delete), existing alerts for that cap remain with `cap_id = NULL` (FK is `ON DELETE SET NULL`).

### 23.4 Background Job Pitfalls

- Celery task deduplication works by `task_id` per queue — same `task_id` in different queues is fine.
- The `prism-virtual-tags` worker must use `soft_time_limit=600` because retroactive re-tagging can take several minutes for large orgs — without this, Celery may kill the task mid-batch, causing partial updates.
- The monthly report Celery Beat fires daily at 09:00 UTC and checks `next_send <= today`. Ensure `next_send` is always in UTC (`TIMESTAMPTZ`), not local time.
- Celery workers are separate processes — they cannot share the FastAPI WebSocket manager's in-memory dict. Use the internal `/internal/ws-broadcast` HTTP endpoint pattern or Redis Pub/Sub.

### 23.5 WebSocket Pitfalls

- The `org_connections` dict is in-memory — in a multi-instance deployment, a WS broadcast from one process won't reach clients on other instances. Upgrade path: Redis Pub/Sub (Part 13.4).
- Always cancel the ping task in the disconnect handler — not doing so causes asyncio task leaks.
- JWT expiry during a long WS session: server does NOT re-validate JWT after connection. Client is responsible for reconnecting with a fresh token before expiry.

### 23.6 Python-Specific Pitfalls

- `asyncpg` is async-only — do not mix with synchronous psycopg2. Celery workers (which are sync by default) must use `asyncio.run()` to call async DB operations.
- Never use `datetime.datetime.now()` — always `datetime.datetime.now(tz=datetime.timezone.utc)` or `datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)`. Naive datetimes cause timezone bugs.
- Pydantic v2 is NOT backward compatible with Pydantic v1. Do not mix v1 and v2 syntax in the same codebase.
- `secrets.token_hex(32)` generates 64 hex characters. When the spec says "32-byte token", use `secrets.token_bytes(32)` or `secrets.token_hex(32)` (the hex string is 64 chars but represents 32 bytes of entropy).
- `hmac.compare_digest()` requires both arguments to be the same type (both `str` or both `bytes`). Encode both to bytes before comparing.

---

## PART 24 — Testing Requirements

### 24.1 What to Test

**Unit tests (pure logic, no DB/Redis) — `tests/unit/`:**
- `with_retry`: 429 respects retry-after header; 401 not retried; 3rd attempt success returns value (use `pytest-mock` to mock httpx)
- `aes_encrypt/aes_decrypt`: round-trip produces original string; wrong key raises `InvalidTag`
- Virtual tag engine: `matches_condition()` for each operator; split pct validation; first-match wins
- `safe_regex_test()`: catastrophic backtracking pattern completes in <500ms (uses thread timeout)
- Forecast: `data_coverage = 'insufficient'` when `days_with_data < 3`; rolling avg used when weekend zeros
- Scorecard: each metric formula matches spec

**Integration tests (with real test DB + real Redis) — `tests/integration/`:**
- Use `pytest-asyncio` and `httpx.AsyncClient` with `app` TestClient
- Test DB: a separate PostgreSQL DB or schema, seeded in `conftest.py`
- Signup → verify → login → issue tokens
- Token refresh: old token revoked; new pair issued
- Invite → accept → login as new user
- Create cap → trigger alert check → exactly one alert per threshold per month
- Sync upsert idempotency: running sync twice produces same result
- Cross-org access: user from org A cannot access org B's data
- Role enforcement: viewer cannot POST to /caps; editor cannot POST to /accounts

**Edge case tests:**
- Auth: wrong email → 401; wrong password → 401 (same message); unverified email → 403
- Role: viewer can GET /costs; viewer cannot POST /caps → 403
- Invite: expired token → 400; already accepted → 409
- Remove owner → 403; remove yourself as owner → 400
- Regex with ReDoS pattern → 400
- Webhook URL with private IP → 400
- Webhook URL with `http://` → 400
- Split config pct ≠ 100 → 400
- LLM query with LLM not configured → 200 with `used_llm: False`
- Sync with bad credentials → sync_status = failed; sync_failure alert created

### 24.2 Testing Tools

| Tool | Purpose |
|------|---------|
| pytest | Test runner |
| pytest-asyncio | Async test support |
| httpx | Async HTTP test client (FastAPI test client) |
| pytest-mock / unittest.mock | Mock external APIs (AWS, Azure, GCP, OpenRouter) |
| factory_boy | Test data factories (not fixtures) |
| freezegun | Freeze time for date-dependent tests |

---

## PART 25 — Implementation Order

Follow this order. Each milestone produces a working, testable system. Never skip ahead.

### Milestone 1 — Auth + DB (Days 1–5)
1. Create PostgreSQL DB. Run `CREATE EXTENSION IF NOT EXISTS timescaledb;`
2. Run `schema.sql` — all tables + indexes.
3. Implement `config/settings.py` — pydantic-settings with all env vars.
4. Implement `config/database.py` — asyncpg Pool + `get_db()` dependency.
5. Implement `config/redis_client.py` — redis.asyncio connection + `get_redis()` dependency.
6. Implement `utils/logger.py` — structlog config.
7. Implement `utils/encrypt.py` — AES-256-GCM encrypt/decrypt.
8. Implement `middleware/auth.py` — `get_current_user()` JWT dependency.
9. Implement `middleware/org_scope.py` — `get_org_access()` dependency.
10. Implement `middleware/rbac.py` — `require_role()` factory.
11. Implement `middleware/rate_limit.py` — slowapi limiter config.
12. Implement `routers/auth.py` — full signup/verify/login/refresh/logout/forgot-reset flow.
13. Implement `main.py` (without workers yet) + `server.py`.
14. Test: signup → verify → login → refresh → logout.

### Milestone 2 — Team + Org Settings (Days 6–8)
15. Implement `routers/orgs.py` — GET + PUT org.
16. Implement `routers/team.py` — all member management + invite/accept flow.
17. Implement `services/email_service.py` — verification, invite, password reset emails (boto3 SES).
18. Test: full invite flow end-to-end; role enforcement; owner protection.

### Milestone 3 — Cloud Connectors + Sync (Days 9–15)
19. Implement `utils/retry.py` — tenacity-based `with_retry()`.
20. Implement `services/fx_service.py`.
21. Implement `services/connectors/aws.py`, `azure.py`, `gcp.py`.
22. Implement `workers/celery_app.py` — Celery app + Beat schedule.
23. Implement `workers/sync_worker.py`.
24. Implement `utils/cache.py` — `invalidate_dashboard_cache()`.
25. Implement `routers/accounts.py` — CRUD + test + sync trigger + sync logs.
26. Implement `ws/ws_manager.py` — WebSocket manager + broadcast.
27. Test: connect AWS account → sync fires → cost_records populated → WS sync.complete received.

### Milestone 4 — Dashboard + Caps + Alerts (Days 16–22)
28. Implement `routers/costs.py` — all aggregation queries + Redis caching.
29. Implement `routers/caps.py`.
30. Implement `services/alert_service.py`.
31. Implement `workers/alerts_worker.py`.
32. Implement `routers/alerts.py` — list + acknowledge + snooze.
33. Add alert Celery Beat trigger.
34. Add cap alert emails to `email_service.py`.
35. Implement `utils/validate_webhook_url.py`.
36. Implement `services/webhook_service.py`.
37. Implement `routers/notifications.py`.
38. Test: create cap → sync fires → pct > 75% → alert created → email sent → WS alert.fired.

### Milestone 5 — Reports + Forecast + Recommendations (Days 23–30)
39. Implement `services/forecast_service.py` + `workers/forecast_worker.py`.
40. Implement `routers/forecasts.py`.
41. Implement `services/recommendation_service.py` + `workers/recommendations_worker.py`.
42. Implement `routers/recommendations.py`.
43. Implement `services/report_service.py` + `workers/reports_worker.py`.
44. Implement `routers/reports.py`.
45. Add all Celery Beat schedule entries.
46. Test: forecast computed after sync; monthly report sends on configured day.

### Milestone 6 — Advanced Features (Days 31–40)
47. Implement `utils/regex_utils.py`.
48. Implement `services/virtual_tag_service.py` + `workers/virtual_tags_worker.py`.
49. Implement `routers/virtual_tags.py`.
50. Implement `services/commitment_service.py` + `workers/commitments_worker.py`.
51. Implement `routers/commitments.py`.
52. Implement `services/scorecard_service.py`.
53. Implement `routers/scorecard.py`.
54. Implement `services/llm_service.py`.
55. Implement `routers/llm.py`.
56. Implement `routers/webhooks.py`.
57. Implement `routers/business_metrics.py`.
58. Implement `routers/resources.py`.
59. Implement `middleware/hmac.py` + `routers/teams_actions.py` + `routers/slack_actions.py`.
60. Implement `workers/dlq_worker.py`.
61. Implement `routers/api_keys.py` — API key CRUD + API key auth dependency.
62. Add forecast-accuracy Beat task and purge Beat task to `celery_app.py`.
63. Implement `types/models.py` — export all shared dataclasses/TypedDicts.
64. Verify graceful shutdown handles SIGTERM and SIGINT in `server.py`.
65. Run full end-to-end flow: signup → connect cloud → invite team → set cap → get alert → read report → API key auth.

---

## APPENDIX A — Project Setup & Startup

### A.1 Dependencies (pyproject.toml)

All production dependencies. Pinned to exact versions in `pyproject.toml` for reproducibility.

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | ≥0.111 | HTTP framework |
| uvicorn[standard] | ≥0.29 | ASGI server |
| gunicorn | ≥22 | Process manager for production |
| asyncpg | ≥0.29 | Async PostgreSQL driver |
| redis[asyncio] | ≥5.0 | Async Redis client |
| celery[redis] | ≥5.4 | Task queue + scheduler |
| pydantic | ≥2.7 | Validation |
| pydantic-settings | ≥2.3 | Env var config |
| python-jose[cryptography] | ≥3.3 | JWT encode/decode |
| passlib[bcrypt] | ≥1.7 | Password hashing |
| cryptography | ≥42 | AES-256-GCM encryption |
| httpx | ≥0.27 | Async HTTP client |
| tenacity | ≥8.3 | Retry logic |
| slowapi | ≥0.1 | Rate limiting for FastAPI |
| structlog | ≥24 | Structured logging |
| boto3 | ≥1.34 | AWS SDK (SES + STS + Cost Explorer) |
| azure-identity | ≥1.16 | Azure authentication |
| azure-mgmt-costmanagement | ≥4.0 | Azure cost management API |
| google-cloud-bigquery | ≥3.20 | GCP BigQuery client |
| python-multipart | ≥0.0.9 | Form data support |

Dev/test dependencies (separate group):
```
pytest, pytest-asyncio, pytest-mock, httpx, factory-boy, freezegun, ruff, mypy
```

### A.2 Makefile Commands

| Command | Action |
|---------|--------|
| `make dev` | `uvicorn src.main:app --reload --port 8000` |
| `make worker` | `celery -A src.workers.celery_app worker -l info` |
| `make beat` | `celery -A src.workers.celery_app beat -l info` |
| `make test` | `pytest -x tests/` |
| `make test-unit` | `pytest tests/unit/` |
| `make test-integration` | `pytest tests/integration/` |
| `make db-setup` | `psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"` |
| `make db-migrate` | `psql $DATABASE_URL -f src/db/schema.sql` |
| `make lint` | `ruff check src/` |
| `make typecheck` | `mypy src/ --strict` |

### A.3 DB Bootstrap Order (Fresh Install)

Run these in order, exactly once on a fresh server:
1. `make db-setup` — installs TimescaleDB extension
2. `make db-migrate` — creates all tables, indexes, hypertable
3. Start API: `make dev` (development) or `gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.main:app` (production)
4. Start Celery worker: `make worker`
5. Start Celery Beat: `make beat`

### A.4 Graceful Shutdown (server.py)

`server.py` must handle `SIGTERM` and `SIGINT` with this shutdown sequence:
1. Call `server.should_exit = True` to stop Uvicorn from accepting new requests
2. Wait for in-flight HTTP requests to complete (Uvicorn handles this with `--timeout-graceful-shutdown 30`)
3. Close all WebSocket connections gracefully
4. Call `celery_app.control.shutdown()` to stop workers after active tasks complete
5. Close `asyncpg` pool: `await pool.close()`
6. Close Redis connection: `await redis.aclose()`
7. `sys.exit(0)`

Timeout: 30 seconds. If shutdown exceeds 30 seconds, force `sys.exit(1)`.

### A.5 Production Deployment (Gunicorn + Uvicorn Workers)

```
gunicorn src.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 120 \
  --graceful-timeout 30 \
  --bind 0.0.0.0:8000 \
  --access-logfile -
```

Celery workers (separate process/container):
```
celery -A src.workers.celery_app worker \
  --concurrency 8 \
  --loglevel info \
  --queues prism-sync,prism-alerts,prism-forecast,prism-commitments,prism-recommendations,prism-reports,prism-virtual-tags,prism-dlq
```

Celery Beat (one instance only — never run multiple Beat instances):
```
celery -A src.workers.celery_app beat --loglevel info
```

---

## APPENDIX B — Environment Variables Reference

| Variable | Required | Description |
|----------|---------|---------|
| ENVIRONMENT | Yes | development / production / test |
| PORT | No | HTTP server port (default 8000) |
| DATABASE_URL | Yes | asyncpg DSN e.g. `postgresql://user:pass@host:5432/prism` |
| DATABASE_POOL_MIN | No | Min pool connections (default 5) |
| DATABASE_POOL_MAX | No | Max pool connections (default 20) |
| REDIS_URL | Yes | Redis DSN e.g. `redis://localhost:6379/0` |
| CELERY_BROKER_URL | Yes | Redis URL for Celery broker (can be same as REDIS_URL) |
| CELERY_RESULT_BACKEND | Yes | Redis URL for Celery results |
| JWT_ACCESS_SECRET | Yes | Min 32 chars random string |
| JWT_REFRESH_SECRET | Yes | Min 32 chars random string (different from access) |
| JWT_ACCESS_EXPIRY_DAYS | No | Default 7 |
| JWT_REFRESH_EXPIRY_DAYS | No | Default 30 |
| GOOGLE_CLIENT_ID | No | For Google OAuth |
| GOOGLE_CLIENT_SECRET | No | For Google OAuth |
| GOOGLE_REDIRECT_URI | No | For Google OAuth (e.g. `https://api.prism.io/v1/auth/google/callback`) |
| AWS_SES_REGION | Yes | e.g. "us-east-1" |
| AWS_SES_FROM | Yes | Verified sender email e.g. `noreply@prism.io` |
| AWS_ACCESS_KEY_ID | No | PRISM's own AWS creds (for SES + STS) |
| AWS_SECRET_ACCESS_KEY | No | PRISM's own AWS creds |
| ENCRYPTION_KEY | Yes | 64 hex chars (32 bytes) — AES key for credentials at rest |
| PRISM_AWS_ACCOUNT_ID | Yes | PRISM's own AWS account ID (for STS ExternalId) |
| TEAMS_SIGNING_SECRET | No | For validating Teams incoming webhook payloads |
| SLACK_SIGNING_SECRET | No | For validating Slack incoming webhook payloads |
| FRONTEND_URL | Yes | CORS origin e.g. `https://app.prism.io` |
| CRON_SYNC | No | Default `0 6 * * *` (UTC) |
| CRON_COMMITMENTS | No | Default `0 7 * * *` |
| CRON_FORECAST | No | Default `30 7 * * *` |
| CRON_RECOMMENDATIONS | No | Default `0 8 * * *` |
| CRON_REPORTS | No | Default `0 9 * * *` |
| WORKER_CONCURRENCY | No | Celery worker concurrency (default 8) |

---

*End of PRISM Backend Implementation Plan — Python Edition — backend_plan.md*
