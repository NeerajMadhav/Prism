# PRISM — Backend Implementation Plan
### Complete Specification (No Code)

> **Purpose:** This document is the single source of truth for building the PRISM backend. Every developer or AI model reading this should be able to build the full, working, production-ready backend without needing any other reference. Follow parts in order. Do not skip sections.

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

---

## PART 1 — System Overview & Tech Stack

### 1.1 What PRISM Does

PRISM connects to AWS, Azure, and GCP. It pulls daily cost data from each cloud provider. It stores that data in a database. It shows a real-time dashboard, fires budget alerts, and sends monthly reports. It is a multi-tenant SaaS — one deployment serves many organizations, each with their own data fully isolated.

### 1.2 Backend Tech Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| Runtime | Node.js 20 + TypeScript | Typed, widely known, async-native |
| HTTP Framework | Express.js | Simple, battle-tested, large ecosystem |
| Primary DB | PostgreSQL 16 | Relational config/alert/user data |
| Time-series DB | TimescaleDB extension on PostgreSQL | Efficient queries over daily cost records |
| Cache | Redis 7 (via ioredis) | Session storage, dashboard query cache, LLM cache |
| Job Queue | BullMQ (backed by Redis) | Reliable async background jobs with retry |
| Scheduler | node-cron | Triggers daily sync jobs at fixed UTC times |
| Auth | JWT (jsonwebtoken) + bcrypt | Stateless access tokens, hashed passwords |
| OAuth | Google OAuth 2.0 (optional sign-in) | Alternative to email/password |
| Email | AWS SES (SendGrid as drop-in) | Transactional email delivery |
| WebSocket | ws library (on same HTTP server) | Real-time dashboard updates |
| LLM | OpenRouter API (OpenAI-compatible) | Optional AI features |
| Encryption | AES-256-GCM (Node.js crypto) | Credentials at rest |
| Validation | Zod | Runtime schema validation for all request bodies |
| Logging | pino | Structured JSON logs |

### 1.3 What the Backend Must NOT Do

- Never store raw cloud API responses (only parsed daily aggregates)
- Never store per-hour cost breakdowns (daily is sufficient)
- Never store LLM conversations in the database (Redis cache only, 24h TTL)
- Never log or return credential values in error messages
- Never process cloud credentials synchronously in an HTTP request (always via background job)
- Never trust org_id from request body for multi-tenant scoping (only from JWT)

---

## PART 2 — Architecture & Data Flow

### 2.1 Component Map

```
Browser (React frontend)
    │
    ├── HTTPS REST API (/v1/*)  ──► Express Router ──► Route Handler ──► DB / Redis
    │
    └── WebSocket (/ws?token=)  ──► WsServer ──► org-scoped broadcast

BullMQ Workers (background)
    ├── prism-sync          ← triggered by cron (06:00 UTC) + manual trigger
    ├── prism-alerts        ← triggered after every sync + on cap create
    ├── prism-forecast      ← triggered daily (07:30 UTC)
    ├── prism-commitments   ← triggered daily (07:00 UTC)
    ├── prism-recommendations ← triggered daily (08:00 UTC)
    ├── prism-reports       ← triggered on org report day (09:00 UTC check)
    ├── prism-virtual-tags  ← triggered on rule save by user
    └── prism-dlq           ← receives jobs that failed 3 attempts

Data stores
    ├── PostgreSQL + TimescaleDB  ← all persistent data
    └── Redis                     ← sessions, cache, job queue, LLM cache
```

### 2.2 Request Lifecycle (Happy Path)

1. Browser sends `GET /v1/orgs/:orgId/costs` with `Authorization: Bearer <jwt>`
2. `requireAuth` middleware verifies JWT signature and expiry. Extracts `{ sub, orgId, role }`.
3. `requireOrgAccess` middleware verifies `req.user.orgId === req.params.orgId`. Fetches org from DB. Attaches to `req.org`.
4. Rate limit middleware checks request count per org in Redis. Allows if under limit.
5. Route handler runs. Checks Redis cache first. On cache miss, queries PostgreSQL.
6. Response is cached in Redis with appropriate TTL.
7. Response sent to browser.

### 2.3 Sync Lifecycle (Daily Background Flow)

1. `node-cron` fires at 06:00 UTC. Fetches all active `cloud_accounts` from DB.
2. For each account, enqueues one job in `prism-sync` queue with `{ accountId, orgId, backfill: false }`.
3. BullMQ worker picks up job. Decrypts credentials from `cloud_accounts.credentials_enc`.
4. Worker instantiates the correct connector (AWS / Azure / GCP). Calls provider API.
5. Received cost records are bulk-upserted into `cost_records` table (idempotent — ON CONFLICT DO UPDATE).
6. `cloud_accounts` row is updated: `last_sync`, `last_sync_status`, `data_as_of`, `last_sync_records`.
7. `sync_logs` row is written.
8. Redis dashboard cache for this org+provider is invalidated.
9. WebSocket event `sync.complete` is broadcast to all connected clients of this org.
10. A new job is enqueued in `prism-alerts` to check all budget caps against fresh data.
11. If job fails 3 times, it moves to `prism-dlq`. DLQ worker logs the failure and creates a `sync_failure` alert in DB.

### 2.4 Alert Lifecycle

1. `prism-alerts` job runs for an org.
2. For each active `BudgetCap`: query `cost_records` for current month spend matching cap scope.
3. Compute `pct = (spent / cap_amount) * 100`.
4. For each threshold in [75, 90, 100, 125, 150]: if `pct >= threshold`, check DB for existing alert this month.
5. If no existing alert → insert `Alert` row → fire all notification channels concurrently (email, Teams, Slack, outbound webhook).
6. Update alert row with which channels succeeded.
7. Also check `spend_forecasts`: if any forecast has `will_breach = true`, fire `forecast_breach` alert (same dedup pattern).
8. WebSocket event `alert.fired` broadcast to org's connected clients instantly.

### 2.5 Multi-Tenancy Isolation

- Every DB table has an `org_id` column.
- Every query includes `WHERE org_id = $<param>` — never rely on joins alone.
- The `org_id` used in queries always comes from `req.user.orgId` (from JWT) — never from request body or URL parameters.
- The `requireOrgAccess` middleware explicitly checks `req.user.orgId === req.params.orgId` and rejects mismatches with 403.
- Redis cache keys always start with `orgId` — no shared keys between orgs.
- WebSocket connections are tracked in a `Map<orgId, Set<WebSocket>>` — broadcasts never cross org boundaries.

---

## PART 3 — Folder Structure

```
prism-backend/
├── src/
│   ├── index.ts                 Boot: connect DB+Redis, start workers+cron, start HTTP+WS server
│   ├── app.ts                   Express app factory: mounts all routes + middleware
│   │
│   ├── config/
│   │   ├── env.ts               Read + validate all env vars with Zod. Fail fast if any are missing.
│   │   ├── db.ts                PostgreSQL Pool (pg). Export `db` object used by all queries.
│   │   ├── redis.ts             ioredis client. Export `redis` used by cache + sessions.
│   │   └── queues.ts            BullMQ Queue objects: one per job type. Export each queue.
│   │
│   ├── middleware/
│   │   ├── auth.ts              Verify JWT from Authorization header. Attach req.user.
│   │   ├── orgScope.ts          Verify URL orgId matches JWT orgId. Fetch org from DB. Attach req.org.
│   │   ├── rbac.ts              requireRole(minRole) factory. Reject if user role < required.
│   │   ├── hmac.ts              validateHMAC(provider) factory for Teams/Slack incoming webhooks.
│   │   ├── validateBody.ts      validate(zodSchema) factory. Parse + replace req.body. Return 400 on fail.
│   │   ├── rateLimit.ts         express-rate-limit configs: auth (10/15min/IP), api (300/min/org), llm (20/hr/user).
│   │   ├── requestLogger.ts     Log every HTTP request with method, path, status, duration, orgId.
│   │   └── errorHandler.ts      Global error handler. AppError → status+message. Unexpected → 500.
│   │
│   ├── routes/
│   │   ├── auth.ts              POST signup, verify-email, login, refresh, logout, forgot-password, reset-password
│   │   ├── orgs.ts              GET+PUT /v1/orgs/:orgId
│   │   ├── accounts.ts          CRUD + test + sync-trigger + sync-logs for cloud accounts
│   │   ├── costs.ts             Cost aggregation queries (overall, by-service, by-day, by-tag, top-services)
│   │   ├── alerts.ts            List + acknowledge + snooze alerts
│   │   ├── caps.ts              CRUD for budget caps
│   │   ├── reports.ts           GET+PUT report config, POST send-now
│   │   ├── team.ts              List + invite + accept-invite + change-role + remove member
│   │   ├── recommendations.ts   List + update status (implemented/rejected/archived)
│   │   ├── virtualTags.ts       CRUD + reorder + apply + audit-log for virtual tag rules
│   │   ├── forecasts.ts         GET current forecast + GET history
│   │   ├── commitments.ts       GET list + summary + expiring
│   │   ├── scorecard.ts         GET scorecard + executive view
│   │   ├── notifications.ts     GET+PUT notification settings + test endpoints
│   │   ├── webhooks.ts          CRUD + test for outbound webhooks
│   │   ├── llm.ts               GET+PUT+DELETE LLM config + POST natural language query
│   │   ├── businessMetrics.ts   CRUD metrics + ingest values
│   │   ├── resources.ts         List + idle list + get resource detail
│   │   ├── teamsActions.ts      POST callback from Teams (HMAC validated, no JWT)
│   │   └── slackActions.ts      POST callback from Slack (HMAC validated, no JWT)
│   │
│   ├── services/
│   │   ├── connectors/
│   │   │   ├── aws.ts           AWSConnector: STS AssumeRole, Cost Explorer, EC2 describe, commitments
│   │   │   ├── azure.ts         AzureConnector: ClientSecretCredential, Cost Management API
│   │   │   └── gcp.ts           GCPConnector: BigQuery billing export (parameterized queries)
│   │   ├── alert.service.ts     CapAlertService: check caps, dedup, fire notifications
│   │   ├── commitment.service.ts CommitmentService: sync AWS/GCP, update expiry status, expiry alerts
│   │   ├── email.service.ts     EmailService: all transactional emails via SES
│   │   ├── forecast.service.ts  ForecastEngine: daily avg + rolling avg, breach calc, upsert
│   │   ├── fx.service.ts        FXService: fetch USD conversion rate, 6h Redis cache
│   │   ├── llm.service.ts       LLMService: OpenRouter, Redis cache, budget check, null fallback
│   │   ├── recommendation.service.ts RecommendationEngine: idle + rightsizing heuristics + LLM
│   │   ├── report.service.ts    ReportGenerator: gather sections, call LLM, send email, update next_send
│   │   ├── scorecard.service.ts ScorecardEngine: compute 7 metrics, weighted overall score
│   │   ├── virtualTag.service.ts VirtualTagEngine: batched retroactive re-tag with WS progress
│   │   └── webhook.service.ts   OutboundWebhookService: HMAC-sign + dispatch to customer URLs
│   │
│   ├── jobs/
│   │   ├── scheduler.ts         node-cron registrar: fire cron triggers, start all workers
│   │   ├── sync.worker.ts       Sync cost + resource data; invalidate cache; trigger alerts
│   │   ├── alerts.worker.ts     Run CapAlertService for org
│   │   ├── forecast.worker.ts   Run ForecastEngine for org
│   │   ├── commitments.worker.ts Run CommitmentService for org
│   │   ├── recommendations.worker.ts Run RecommendationEngine for org
│   │   ├── reports.worker.ts    Run ReportGenerator for org
│   │   ├── virtualTags.worker.ts Run VirtualTagEngine for org (concurrency: 1, long lock)
│   │   └── dlq.worker.ts        Log DLQ jobs, create sync_failure alert in DB
│   │
│   ├── ws/
│   │   └── wsServer.ts          WS server: JWT auth on connect, per-org connection map, wsBroadcast()
│   │
│   ├── utils/
│   │   ├── logger.ts            pino logger export
│   │   ├── encrypt.ts           AES-256-GCM encrypt/decrypt for credentials at rest
│   │   ├── withRetry.ts         Retry wrapper: exponential backoff, 429 retry-after, no retry on 401/403
│   │   ├── cache.ts             invalidateDashboardCache(orgId, provider): delete Redis keys
│   │   ├── validateWebhookUrl.ts SSRF guard: HTTPS-only, no private IPs, DNS re-check on dispatch
│   │   ├── regex.ts             safeRegexTest() + validateRegexPattern() with ReDoS protection
│   │   ├── date.ts              currentMonthStart(), nextMonthStart(), daysRemainingInMonth()
│   │   └── pagination.ts        getPagination(req), paginatedResponse(data, total, params)
│   │
│   ├── types/
│   │   └── index.ts             All TypeScript interfaces — Organization, CloudAccount, CostRecord,
│   │                            Alert, BudgetCap, TeamMember, User, Recommendation, VirtualTagRule,
│   │                            CommitmentRecord, SpendForecast, WSEvent, JWTPayload, ConnectorResult
│   │
│   └── db/
│       └── schema.sql           Full DDL for all tables + indexes (run once on fresh DB)
│
├── .env                         Local secrets (never commit)
├── .env.example                 Template for all required env vars
├── tsconfig.json
└── package.json
```

---

## PART 4 — Database Design

### 4.1 Database: PostgreSQL 16 + TimescaleDB

- All tables are in one PostgreSQL instance with the TimescaleDB extension installed.
- `cost_records` is the only TimescaleDB hypertable (time-series, partitioned by month).
- All other tables are regular PostgreSQL tables.
- Connection pooling via `pg` Pool (max 20 connections).

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
| expires_at | TIMESTAMPTZ | 30 days from issue |
| created_at | TIMESTAMPTZ | |
| revoked_at | TIMESTAMPTZ | NULL = valid; set on logout or rotation |

Index: `(user_id)`.

---

#### Table: `team_members`
Many-to-many: users inside organizations. One row per membership.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK → organizations | |
| user_id | UUID FK → users | NULL until invite accepted |
| email | TEXT NOT NULL | invite target email |
| role | TEXT | owner / admin / editor / viewer |
| invited_by | UUID FK → users | |
| invite_token_hash | TEXT | bcrypt-hashed; NULL after acceptance |
| invite_expires_at | TIMESTAMPTZ | 48h after invite sent |
| invite_accepted | BOOLEAN | default FALSE |
| invited_at | TIMESTAMPTZ | |
| joined_at | TIMESTAMPTZ | filled on acceptance |

Unique constraint: `(org_id, email)` — one membership per email per org.
Indexes: `(org_id)`, `(user_id)`.

---

#### Table: `account_groups`
Groups cloud accounts by provider + scope (single / multi / organization).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK → organizations | |
| provider | TEXT | aws / azure / gcp |
| scope | TEXT | single / multi / organization |
| display_name | TEXT | |
| root_account_id | TEXT | AWS Org management account ID (nullable) |
| created_at | TIMESTAMPTZ | |

---

#### Table: `cloud_accounts`
One row per connected cloud account (AWS account, Azure subscription, GCP project).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| group_id | UUID FK → account_groups | |
| org_id | UUID FK → organizations | |
| provider | TEXT | aws / azure / gcp |
| account_id | TEXT | AWS account ID / Azure subscription ID / GCP project ID |
| display_name | TEXT | user-assigned label |
| credentials_enc | TEXT | AES-256-GCM encrypted JSON blob |
| last_sync | TIMESTAMPTZ | |
| last_sync_status | TEXT | success / partial / failed / never |
| last_sync_error | TEXT | last error message if failed |
| last_sync_records | INT | number of records in last sync |
| data_as_of | TIMESTAMPTZ | most recent data timestamp from provider |
| is_active | BOOLEAN | soft delete |
| created_at | TIMESTAMPTZ | |

Unique: `(org_id, provider, account_id)` — prevent duplicate connections.

---

#### Table: `sync_logs`
One row per sync run. Retained 90 days, then purged.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| account_id | UUID FK → cloud_accounts | |
| started_at | TIMESTAMPTZ | |
| finished_at | TIMESTAMPTZ | NULL while running |
| status | TEXT | running / success / partial / failed |
| records_synced | INT | |
| error_message | TEXT | |
| backfill | BOOLEAN | true if first-time 13-month historical pull |

Index: `(account_id, started_at DESC)`.

---

#### Table: `cost_records` (TimescaleDB hypertable)
The largest table. One row per service per day per account. Partitioned monthly.

| Column | Type | Notes |
|--------|------|-------|
| time | TIMESTAMPTZ NOT NULL | the day this cost applies to (midnight UTC) |
| org_id | UUID NOT NULL | |
| account_id | UUID NOT NULL | |
| provider | TEXT | aws / azure / gcp |
| service | TEXT | e.g. "Amazon EC2", "Azure Virtual Machines" |
| region | TEXT | e.g. "us-east-1" (empty string if unknown) |
| cost_usd | NUMERIC(14,6) | always USD |
| cost_unblended_usd | NUMERIC(14,6) | AWS unblended / same as cost_usd for others |
| cost_amortized_usd | NUMERIC(14,6) | AWS amortized (RI/SP spread) / same for others |
| cost_original | NUMERIC(14,6) | amount in original currency |
| original_currency | TEXT | e.g. "EUR" |
| fx_rate | NUMERIC(10,6) | rate used to convert to USD |
| usage_value | NUMERIC(18,4) | quantity used |
| usage_unit | TEXT | e.g. "Hrs", "GB-Month" |
| tags | JSONB | provider-supplied tags {team, owner, environment} |
| virtual_tags | JSONB | tags computed by VirtualTagEngine |
| is_estimate | BOOLEAN | true if from current billing period (not finalized) |

**Unique constraint:** `(account_id, time::date, service, region)` — enables idempotent upserts.
**Compression:** Chunks older than 3 months are compressed automatically.
**Retention:** 13 months hot; then archived to S3 Parquet.

**TimescaleDB continuous aggregate (optional but recommended):**
A materialized monthly rollup view per (org, account, provider, service, region) — significantly speeds up dashboard queries for large orgs.

---

#### Table: `budget_caps`
Budget limits set by users. The alert engine checks against these daily.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| name | TEXT | user-assigned label |
| scope | TEXT | platform / service / account |
| provider | TEXT | aws / azure / gcp / NULL (all) |
| service_name | TEXT | NULL = all services |
| account_id | UUID FK → cloud_accounts | NULL = all accounts |
| cap_amount | NUMERIC(14,2) | in org currency |
| period | TEXT | always "monthly" in v1 |
| is_active | BOOLEAN | soft delete |
| created_by | UUID FK → users | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

Index: `(org_id)` where `is_active = true`.

---

#### Table: `notification_settings`
One row per org. Controls where alerts go.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID UNIQUE FK | one row per org |
| alert_emails | TEXT[] | list of email addresses for alerts |
| teams_webhook_url | TEXT | NULL = Teams disabled |
| slack_webhook_url | TEXT | NULL = Slack disabled |
| updated_at | TIMESTAMPTZ | |

---

#### Table: `alerts`
Every alert fired by the system. Append-only (no updates except ack/snooze).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| cap_id | UUID FK → budget_caps | NULL for non-cap alerts |
| type | TEXT | cap_threshold / forecast_breach / spend_acceleration / sync_failure / credential_expiry / commitment_expiry / unused_commitment / untagged_resource / idle_resource |
| scope_label | TEXT | human-readable: "AWS EC2", "Azure total" |
| threshold_percent | INT | 75/90/100/125/150 (cap_threshold only) |
| spend_at_trigger | NUMERIC | amount spent when alert fired |
| cap_amount | NUMERIC | cap value at time of alert |
| metadata | JSONB | extra context (commitment_id, resource_id, etc.) |
| severity | TEXT | info / warning / critical |
| triggered_at | TIMESTAMPTZ | |
| email_sent | BOOLEAN | |
| teams_sent | BOOLEAN | |
| slack_sent | BOOLEAN | |
| webhook_sent | BOOLEAN | |
| acknowledged_by | UUID FK → users | |
| acknowledged_at | TIMESTAMPTZ | |
| snoozed_until | TIMESTAMPTZ | |

**Unique partial index for deduplication:**
`(org_id, cap_id, threshold_percent, date_trunc('month', triggered_at))` where `type = 'cap_threshold' AND cap_id IS NOT NULL`.
This enforces database-level deduplication: only one cap threshold alert per cap per threshold per billing month.

---

#### Table: `resources`
Cloud resource inventory. Upserted on every sync.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| account_id | UUID FK | |
| provider | TEXT | |
| resource_id | TEXT | AWS ARN / Azure resource ID / GCP name |
| resource_name | TEXT | |
| service | TEXT | |
| region | TEXT | |
| instance_type | TEXT | |
| tags | JSONB | provider-supplied tags |
| virtual_tags | JSONB | computed by VirtualTagEngine |
| created_at_cloud | TIMESTAMPTZ | from CloudTrail / Activity Log |
| last_activity_at | TIMESTAMPTZ | last usage signal |
| created_by_user | TEXT | from CloudTrail |
| last_cost_usd | NUMERIC | most recent daily cost |
| is_idle | BOOLEAN | true if no usage for 7+ days |
| idle_since | TIMESTAMPTZ | when is_idle became true |
| first_seen | TIMESTAMPTZ | when Prism first discovered it |
| last_seen | TIMESTAMPTZ | updated on every sync |

Unique: `(account_id, resource_id)` — idempotent upsert.

---

#### Table: `recommendations`
Savings recommendations generated by the recommendation engine.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| account_id | UUID FK | |
| resource_id | TEXT | |
| resource_name | TEXT | |
| provider | TEXT | |
| service | TEXT | |
| type | TEXT | rightsizing / idle_termination / reserved_instance / storage_tiering / network_egress / commitment_renewal |
| estimated_monthly_savings | NUMERIC | |
| confidence | TEXT | high / medium / low |
| llm_explanation | TEXT | NULL if LLM not configured |
| llm_risk_note | TEXT | NULL if LLM not configured |
| status | TEXT | pending / implemented / rejected / archived |
| created_at | TIMESTAMPTZ | |
| implemented_at | TIMESTAMPTZ | filled when user marks implemented |
| actual_savings | NUMERIC | measured 30 days post-implementation |
| actual_savings_updated_at | TIMESTAMPTZ | |

---

#### Table: `virtual_tag_rules`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| priority | INT | lower = evaluated first; UNIQUE (org_id, priority) |
| condition_field | TEXT | resource_name / account_id / service / region / tag_value |
| condition_operator | TEXT | contains / equals / starts_with / ends_with / regex |
| condition_value | TEXT | the value to match against |
| action_type | TEXT | set_tag / split |
| tag_key | TEXT | e.g. "team", "environment" |
| tag_value | TEXT | NULL for split rules |
| split_config | JSONB | [{team:"eng",pct:60},{team:"data",pct:40}] — must sum to 100 |
| provider_scope | TEXT | aws / azure / gcp / all |
| is_active | BOOLEAN | |
| last_applied_at | TIMESTAMPTZ | |
| records_affected | INT | |
| created_by | UUID FK → users | |
| updated_by | UUID FK → users | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

#### Table: `virtual_tag_audit_log`
Immutable log of all changes to virtual tag rules.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID | |
| rule_id | UUID FK (nullable) | NULL if rule was deleted |
| changed_by | UUID FK → users | |
| change_type | TEXT | created / updated / deleted / reordered / applied |
| before_state | JSONB | |
| after_state | JSONB | |
| timestamp | TIMESTAMPTZ | |

---

#### Table: `commitment_records`
RI / Savings Plan / CUD data from AWS and GCP.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| account_id | UUID FK | |
| provider | TEXT | aws / gcp |
| commitment_type | TEXT | reserved_instance / savings_plan / committed_use_discount |
| external_id | TEXT | AWS RI ID / SP ARN / GCP CUD ID |
| instance_type | TEXT | |
| region | TEXT | |
| term_months | INT | 12 or 36 |
| start_date | DATE | |
| end_date | DATE | |
| hourly_commitment | NUMERIC | for Savings Plans |
| monthly_cost | NUMERIC | amortized |
| monthly_on_demand_equivalent | NUMERIC | what it would cost on-demand |
| monthly_savings | NUMERIC | |
| utilization_pct | NUMERIC | 0–100 |
| coverage_amount | NUMERIC | spend covered this month |
| status | TEXT | active / expiring_soon / expired |
| last_updated | TIMESTAMPTZ | |

Unique: `(account_id, external_id)`.

---

#### Table: `spend_forecasts`
One row per org per provider per month. Recalculated daily at 07:30 UTC.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| account_id | UUID FK | NULL = org-level |
| provider | TEXT | NULL = cross-platform |
| forecast_month | DATE | first day of the month being forecast |
| generated_at | TIMESTAMPTZ | |
| spend_to_date | NUMERIC | current month spend so far |
| daily_avg | NUMERIC | avg daily spend since month start |
| rolling_7d_avg | NUMERIC | last 7 days avg (smooths weekend zeros) |
| days_with_data | INT | actual days with cost data |
| days_remaining | INT | calendar days left in month |
| projected_total | NUMERIC | spend_to_date + (effective_avg × days_remaining) |
| cap_amount | NUMERIC | matched cap for this scope (nullable) |
| will_breach | BOOLEAN | projected_total > cap_amount |
| breach_date | DATE | estimated date when cap will be hit |
| data_coverage | TEXT | full / partial / insufficient (< 3 days data) |
| actual_total | NUMERIC | filled at month-end by comparison job |
| variance_pct | NUMERIC | filled at month-end |

---

#### Table: `monthly_reports`
One row per org. Controls report scheduling.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID UNIQUE FK | one row per org |
| send_day_of_month | INT | 1–28 |
| recipient_emails | TEXT[] | |
| include_recommendations | BOOLEAN | |
| include_per_account | BOOLEAN | |
| include_commitments | BOOLEAN | |
| include_unit_economics | BOOLEAN | |
| include_finops_scorecard | BOOLEAN | |
| last_sent | TIMESTAMPTZ | |
| next_send | TIMESTAMPTZ | computed: next occurrence of send_day |
| is_active | BOOLEAN | |

---

#### Table: `llm_configs`
One row per org if LLM is configured.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID UNIQUE FK | |
| openrouter_api_key | TEXT | AES-256-GCM encrypted |
| model | TEXT | e.g. "google/gemini-flash-1.5" |
| monthly_budget_usd | NUMERIC | default 10.00 |
| is_enabled | BOOLEAN | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

Monthly spend is tracked in Redis (`llm:monthly_spent:{orgId}:{YYYY-MM}`), not the DB, to avoid write amplification.

---

#### Table: `outbound_webhooks`
Customer-configured webhook endpoints.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| org_id | UUID FK | |
| url | TEXT | HTTPS only, no private IPs |
| signing_secret_enc | TEXT | AES-256-GCM encrypted; raw secret shown once at creation |
| description | TEXT | |
| events | TEXT[] | e.g. ['alert.fired', 'recommendation.new'] |
| is_active | BOOLEAN | |
| last_triggered_at | TIMESTAMPTZ | |
| last_status_code | INT | HTTP status of last dispatch |
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

### 4.3 Critical Database Indexes

These indexes are not optional — missing any of them causes full table scans at scale:

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
| sync_logs | 90 days | Purge (DELETE) |
| alerts / recommendations | Indefinite | No action |
| LLM cache (Redis) | 24 hours per entry | Auto-expire |
| Refresh tokens (revoked) | 30 days | Purge expired |

---

## PART 5 — Redis Architecture

### 5.1 Purpose
Redis serves four roles: session token invalidation, dashboard query cache, job queue (via BullMQ), and LLM response cache.

### 5.2 Key Naming Convention

All keys are prefixed with the org's UUID or user's UUID to prevent cross-tenant data leakage.

| Key Pattern | Value | TTL | Purpose |
|-------------|-------|-----|---------|
| `dash:{orgId}:overall:{YYYY-MM}` | JSON cost aggregates | 5 min | Overall dashboard |
| `dash:{orgId}:{provider}:{YYYY-MM}` | JSON per-platform aggregates | 5 min | Per-platform dashboard |
| `dash:{orgId}:forecast:{YYYY-MM}` | JSON forecast rows | 1 hour | Forecast widget |
| `dash:{orgId}:commitments` | JSON commitment summary | 6 hours | Commitment tab |
| `dash:{orgId}:scorecard` | JSON scorecard result | 1 hour | Scorecard page |
| `llm:{base64_prompt_hash}` | LLM response string | 24 hours | Avoid repeat LLM calls |
| `llm:monthly_spent:{orgId}:{YYYY-MM}` | Decimal (string) | 33 days | Track LLM budget per org |
| `rl:auth:{ip}` | Request count | 15 min | Auth rate limit |
| `rl:api:{orgId}` | Request count | 1 min | API rate limit |
| `rl:llm:{userId}` | Request count | 1 hour | LLM query rate limit |
| `pwd:reset:{userId}` | bcrypt hash of reset token | 1 hour | Password reset |
| `email:verify:{userId}` | bcrypt hash of verify token | 24 hours | Email verification |
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
All routes: `/v1/{resource-path}`. Breaking changes are introduced under `/v2/` with 6-month deprecation on `/v1/`.

### 6.2 Request Rules
- All request bodies: `Content-Type: application/json`
- All authenticated requests: `Authorization: Bearer {jwt}`
- All org-scoped routes: `:orgId` in URL must match `orgId` in JWT (enforced by `requireOrgAccess`)

### 6.3 Response Rules
- Success responses: `200 OK` (or `201 Created` for creates)
- All successful list endpoints return an array or `{ data, pagination }` object
- All error responses: `{ "error": "Human-readable message" }` plus optional `"code"` field
- Validation errors: `{ "error": "Validation failed", "details": [{ "field": "...", "message": "..." }] }`

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
1. Receive `{ email, name, password, orgName }`. Validate with Zod.
2. Check no existing user with same email (return 409 if exists).
3. Hash password with bcrypt (cost factor 12).
4. In a single DB transaction: create `User`, create `Organization`, create `TeamMember` (role=owner, invite_accepted=true), create `NotificationSettings` (alert_emails=[email]).
5. Generate raw verification token (32 random bytes hex). Bcrypt-hash and store in `users.email_verify_token`. Set `email_verify_expires = NOW() + 24h`.
6. Send verification email with raw token.
7. Return `{ message, userId, orgId }`. Do NOT issue JWT yet.

**Email Verification:**
1. Receive `{ userId, token }`.
2. Fetch user. Check `email_verified = false` and `email_verify_expires > NOW()`.
3. Compare raw token against `email_verify_token` with `bcrypt.compare`.
4. If valid: set `email_verified = true`, clear token fields.
5. Return success. User can now log in.

**Login:**
1. Receive `{ email, password }`.
2. Fetch user by email. Fetch their org membership from `team_members`.
3. Always call `bcrypt.compare` even if user not found (dummy hash) — prevents timing attacks.
4. If user not found OR password wrong → return 401 (same message for both — never reveal which).
5. If `email_verified = false` → return 403 with message to check email.
6. Call `issueTokens(userId, orgId, role, email)`:
   - Sign access JWT (7 days expiry) with `{ sub: userId, orgId, role, email }`.
   - Generate 64-byte random refresh token (hex). Bcrypt-hash. Store in `refresh_tokens`.
   - Return `{ accessToken, refreshToken }`.
7. Update `users.last_login = NOW()`.

**Token Refresh:**
1. Receive `{ refreshToken }`.
2. Verify JWT signature (refresh secret). Extract `sub`.
3. Find latest non-revoked `refresh_tokens` row for this user. Compare token with bcrypt.
4. If invalid → 401.
5. Revoke old token (`revoked_at = NOW()`). Issue new token pair. Return new tokens.

**Logout:**
1. Require valid JWT.
2. Revoke all non-revoked refresh tokens for this user.
3. Return success.

**Password Reset:**
1. `POST /v1/auth/forgot-password` with `{ email }`. Always return 200 regardless of whether email exists (prevent enumeration).
2. If user exists: generate reset token, store bcrypt hash in Redis (`pwd:reset:{userId}`, 1h TTL). Send email.
3. `POST /v1/auth/reset-password` with `{ userId, token, newPassword }`. Validate new password strength. Compare token. Update password hash. Delete Redis key. Revoke all refresh tokens.

### 7.2 Google OAuth Flow

1. User clicks "Sign in with Google" → redirect to Google consent page.
2. `GET /v1/auth/google/callback?code=...` → exchange code for `id_token` with Google.
3. Verify `id_token` with Google public keys. Extract `{ email, name, googleId, avatarUrl }`.
4. Look up user by `email`. If exists and has no `google_id` → link (set `google_id`). If exists with matching `google_id` → proceed. If not exists → JIT provision (create User).
5. Check `team_members` — if user has no org, this Google login is for a brand new user: create org + membership (same as signup flow but skip password).
6. Issue tokens. Return same response as email login.

### 7.3 JWT Structure

Access token payload: `{ sub: userId, orgId, role, email, iat, exp }`
Signed with `JWT_ACCESS_SECRET` (min 32 chars). Expires in 7 days.
Stored in HttpOnly, Secure, SameSite=Strict cookie by the frontend OR in Authorization header.

Refresh token: random 64-byte hex string. Not a JWT. Stored bcrypt-hashed in DB.

### 7.4 Session Rules
- Concurrent sessions allowed (mobile + desktop).
- Each device gets its own refresh token row.
- On logout: revoke ALL refresh tokens for the user (all sessions).
- JWT cannot be invalidated before expiry — keep expiry short (7 days).
- On refresh token rotation: immediately revoke the old one before issuing new one.

---

## PART 8 — Role-Based Access Control (RBAC)

### 8.1 Roles (in order of power)

`owner > admin > editor > viewer`

### 8.2 Permission Table

| Action | owner | admin | editor | viewer |
|--------|-------|-------|--------|--------|
| View dashboard, costs, reports, alerts | ✅ | ✅ | ✅ | ✅ |
| Acknowledge / snooze alerts | ✅ | ✅ | ✅ | ❌ |
| Implement / reject recommendations | ✅ | ✅ | ✅ | ❌ |
| Create / edit virtual tag rules | ✅ | ✅ | ✅ | ❌ |
| Trigger virtual tag re-apply | ✅ | ✅ | ✅ | ❌ |
| Connect / remove cloud accounts | ✅ | ✅ | ❌ | ❌ |
| Create / edit / delete budget caps | ✅ | ✅ | ❌ | ❌ |
| Configure monthly report | ✅ | ✅ | ❌ | ❌ |
| Configure notifications (email/Teams/Slack) | ✅ | ✅ | ❌ | ❌ |
| Invite / remove team members | ✅ | ✅ | ❌ | ❌ |
| Change member roles | ✅ | ✅ | ❌ | ❌ |
| Configure outbound webhooks | ✅ | ✅ | ❌ | ❌ |
| Configure LLM (OpenRouter) | ✅ | ✅ | ❌ | ❌ |
| Update org settings | ✅ | ✅ | ❌ | ❌ |
| Transfer ownership | ✅ only | ❌ | ❌ | ❌ |
| Delete org | ✅ only | ❌ | ❌ | ❌ |

### 8.3 Implementation

- `requireRole("admin")` middleware checks `ROLE_RANK[userRole] >= ROLE_RANK["admin"]`.
- Role rank: owner=4, admin=3, editor=2, viewer=1.
- Role is embedded in the JWT — no extra DB lookup per request.
- `owner` role cannot be changed or removed via the team API — only transferred via dedicated endpoint.
- A user can be Admin in one org and Viewer in another (separate `team_members` rows).

---

## PART 9 — All API Endpoints (Full Specification)

For each endpoint: **Method · Path · Min Role · Request · Response · Key Behavior**

---

### 9.1 Auth (`/v1/auth` — no org scope, no JWT required except logout)

**POST /v1/auth/signup**
- Body: `{ email, name, password, orgName }`
- Response: `{ message, userId, orgId }`
- Creates user + org + owner membership + notification settings in one transaction
- Rate limit: 10/15min per IP

**POST /v1/auth/verify-email**
- Body: `{ userId, token }`
- Response: `{ message }`
- Edge case: expired → 400; already verified → 400

**POST /v1/auth/login**
- Body: `{ email, password }`
- Response: `{ accessToken, refreshToken, user: { id, email, name, role, orgId } }`
- Same 401 for wrong email or wrong password (no enumeration)
- Rate limit: 10/15min per IP

**POST /v1/auth/refresh**
- Body: `{ refreshToken }`
- Response: `{ accessToken, refreshToken }` (new pair; old token revoked)

**POST /v1/auth/logout** — requires JWT
- Response: `{ message }`
- Revokes all refresh tokens for user

**POST /v1/auth/forgot-password**
- Body: `{ email }`
- Response: always `{ message }` (never confirm email existence)
- Rate limit: 10/15min per IP

**POST /v1/auth/reset-password**
- Body: `{ userId, token, newPassword }`
- Response: `{ message }`
- Validates password strength; revokes all sessions on success

**GET /v1/auth/google** — no auth
- Redirect to Google OAuth consent URL
- No body. Browser redirect only.

**GET /v1/auth/google/callback** — no auth
- Query: `?code=...&state=...` (from Google)
- Exchanges code for Google `id_token`. Verifies with Google public keys.
- If email matches existing user → link Google ID if not already linked → login
- If new user → JIT provision (create User + Org + TeamMember owner) → login
- Response: `{ accessToken, refreshToken, user }` (same shape as login)
- Edge case: Google returns error → redirect frontend to login page with `?error=oauth_failed`

---

### 9.2 Organizations (`/v1/orgs/:orgId`)

**GET /v1/orgs/:orgId** — viewer
- Response: org object (id, name, plan, currency, timezone, feature_flags, created_at)

**PUT /v1/orgs/:orgId** — admin
- Body: any subset of `{ name, currency, timezone }`
- Response: updated org object
- Edge case: currency change does not retroactively convert stored cost records

---

### 9.3 Cloud Accounts (`/v1/orgs/:orgId/accounts`)

**GET /** — viewer
- Response: array of account objects (excludes credentials_enc)
- Fields: id, provider, account_id, display_name, last_sync, last_sync_status, last_sync_error, data_as_of, is_active
- **Sync status indicator rules** (for frontend but backend must return the right data):
  - 🟢 Green: `last_sync_status = 'success'` AND `data_as_of > NOW() - 24h`
  - 🟡 Yellow: `last_sync_status = 'success'` AND `data_as_of <= NOW() - 24h` (data is stale)
  - 🔴 Red: `last_sync_status = 'failed'` (show `last_sync_error` inline)
  - ⚪ Grey: `last_sync_status = 'never'` (never synced yet)
- Frontend must show `data_as_of` timestamp prominently when data is stale

**POST /** — admin
- Body: `{ provider, display_name, scope, credentials }` where credentials is provider-specific JSON
- Credentials shape per provider:
  - AWS: `{ roleArn, externalId, region }` — ExternalId is generated by Prism and shown in the setup wizard
  - Azure: `{ tenantId, clientId, clientSecret, subscriptionId }`
  - GCP: `{ projectId, datasetId, tablePrefix, serviceAccountJson }`
- Encrypts credentials with AES-256-GCM before storing
- Creates `account_groups` row if no group exists for (org_id, provider, scope) — otherwise reuses existing group
- Creates `cloud_accounts` row
- Creates `notification_settings` row for org if not exists yet
- Enqueues `prism-sync` job with `backfill: true` (13-month historical pull)
- Response: `{ id, provider, account_id, display_name, last_sync_status, created_at }`
- Edge case: duplicate (org_id, provider, account_id) → 409

**GET /:accountId** — viewer
- Response: full account detail (no credentials)

**PUT /:accountId** — admin
- Body: `{ display_name }` (only label can be changed post-creation)
- Response: updated account

**DELETE /:accountId** — admin
- Soft delete (`is_active = false`). Does not delete cost_records.
- Response: `{ message }`

**POST /:accountId/test** — admin
- No body. Decrypts credentials, calls provider health check API.
- Response: `{ ok: boolean, error?: string }`
- Updates `last_sync_status` on failure.

**POST /:accountId/sync** — admin
- No body. Enqueues manual sync job (non-backfill).
- Response: `{ message }`
- Rate limit: 5 manual syncs per account per hour

**GET /:accountId/sync-logs** — admin
- Response: paginated list of sync_logs for this account (started_at, finished_at, status, records_synced, error_message, backfill)
- Sorted: newest first

---

### 9.4 Costs (`/v1/orgs/:orgId/costs`)

All cost endpoints are read-only (viewer). All support `?month=YYYY-MM` query param (default: current month). Redis cache applies (5 min TTL).

**Cost View Toggle (amortized / unblended / blended):**
- All cost queries support `?view=unblended|amortized` query param. Default: `unblended`.
- `unblended`: use `cost_unblended_usd` column — standard AWS billing, no RI/SP spreading
- `amortized`: use `cost_amortized_usd` column — RI/SP cost spread over the commitment period (smoother month-to-month)
- For Azure and GCP: `cost_unblended_usd = cost_amortized_usd = cost_usd` (no distinction)
- The user's preference is stored on the frontend (Zustand state), not in the DB
- The backend always returns both columns in detail views so frontend can switch without re-fetching

**GET /** — Overall cost summary
- Response: `{ month, byProvider: [{provider, total_usd, total_amortized_usd, account_count, service_count}], totalUsd, totalAmortizedUsd, prevMonthTotalUsd }`

**GET /by-service** — Cost grouped by service
- Query: `?month`, `?provider`, `?limit` (max 100, default 20)
- Response: array of `{ service, provider, total_usd }` sorted by total_usd DESC

**GET /by-account** — Cost grouped by account
- Response: array of `{ account_id, display_name, provider, total_usd }`

**GET /by-tag** — Cost grouped by tag key/value
- Query: `?tag_key=team` (required)
- Response: array of `{ tag_value, total_usd }` for the given tag key
- Uses JSONB tag fields (both `tags` and `virtual_tags`)

**GET /by-day** — Daily cost trend
- Query: `?month`, `?provider`
- Response: array of `{ date, total_usd }` for each day in the month

**GET /top-services** — Top N services by spend
- Query: `?month`, `?limit=10`
- Response: array of `{ service, provider, total_usd, pct_of_total }`

**GET /untagged** — Untagged spend
- Response: `{ total_untagged_usd, pct_untagged, by_provider: [...] }`
- Untagged = no `team` tag in either `tags` or `virtual_tags`

---

### 9.5 Budget Caps (`/v1/orgs/:orgId/caps`)

**GET /** — viewer
- Response: array of caps with `current_spend` (computed from cost_records for current month)

**POST /** — admin
- Body: `{ name, scope, provider?, service_name?, account_id?, cap_amount }`
- Validates: scope=platform requires provider; scope=service requires service_name; scope=account requires account_id
- Enqueues immediate alert check after creation
- Response: created cap object
- Edge case: `cap_amount` must be positive number

**GET /:capId** — viewer
- Response: cap object with current_spend

**PUT /:capId** — admin
- Body: any subset of cap fields
- Response: updated cap
- Note: updating cap_amount does NOT retroactively change already-fired alerts

**DELETE /:capId** — admin
- Soft delete. Existing alerts referencing this cap remain.
- Response: `{ message }`

---

### 9.6 Alerts (`/v1/orgs/:orgId/alerts`)

**GET /** — viewer
- Query: `?type=cap_threshold`, `?unacknowledged=true`, `?page`, `?limit`
- Response: paginated alerts, newest first

**GET /:alertId** — viewer
- Response: full alert object

**POST /:alertId/acknowledge** — editor
- No body. Sets `acknowledged_by = current user`, `acknowledged_at = NOW()`.
- Response: updated alert

**POST /:alertId/snooze** — editor
- Body: `{ days: 1–90 }`
- Sets `snoozed_until = NOW() + days`.
- Snoozed alerts are not shown in the active alert list until snooze expires.
- Response: updated alert

---

### 9.7 Reports (`/v1/orgs/:orgId/reports`)

**GET /config** — viewer
- Response: monthly_reports config row for this org (or null if not set up)

**PUT /config** — admin
- Body: `{ send_day_of_month, recipient_emails, include_recommendations, include_per_account, include_commitments, include_unit_economics, include_finops_scorecard }`
- Computes and saves `next_send = next occurrence of send_day_of_month`
- Creates or updates the `monthly_reports` row (upsert on org_id)
- Response: updated config

**POST /send-now** — admin
- No body. Generates and sends a report immediately using current month's data.
- Does NOT change `next_send` or `last_sent`.
- Response: `{ message }`
- Edge case: if no recipients configured → 400

---

### 9.8 Team (`/v1/orgs/:orgId/team`)

**GET /** — viewer
- Response: all members including pending invites (with user name, email, role, invite status, joined_at)

**POST /invite** — admin
- Body: `{ email, role }` (role cannot be "owner")
- If email already a member (invite_accepted=true) → 409
- If pending invite exists: re-send (update token + expiry)
- Generates raw 32-byte token. Stores bcrypt hash + expiry (48h). Sends invite email.
- Response: `{ message, email, role, expires_at }`

**POST /accept-invite** — no auth (uses invite token)
- Body: `{ orgId, token, name?, password? }`
- Validates token not expired. Bcrypt-compare against stored hash.
- If user already exists (by email) → link to org. If new → create User with given name+password.
- Response: `{ message }` — user must then log in normally.

**POST /resend-invite** — admin
- Body: `{ memberId }`
- Regenerates token, resets expiry, resends email.

**PUT /:memberId/role** — admin
- Body: `{ role }` — must be admin/editor/viewer (cannot set "owner")
- Cannot change the current owner's role.
- Response: `{ message }`

**DELETE /:memberId** — admin
- Cannot remove the org owner. Cannot remove yourself.
- Deletes the `team_members` row entirely (hard delete).
- Response: `{ message }`

---

### 9.9 Recommendations (`/v1/orgs/:orgId/recommendations`)

**GET /** — viewer
- Query: `?status=pending|implemented|rejected|archived`, `?page`, `?limit`
- Default status: pending
- Sorted: estimated_monthly_savings DESC

**PUT /:recId/status** — editor
- Body: `{ status }` — implemented / rejected / archived
- Sets `implemented_at = NOW()` when status = implemented
- Response: updated recommendation

---

### 9.10 Virtual Tags (`/v1/orgs/:orgId/virtual-tags`)

**GET /** — viewer
- Response: all active rules for this org, sorted by priority

**POST /** — editor
- Body: `{ priority, condition_field, condition_operator, condition_value, action_type, tag_key, tag_value?, split_config?, provider_scope }`
- Validates: regex operator → test for ReDoS; split rules → pct sums to 100; set_tag → tag_value required
- Response: created rule

**PUT /:ruleId** — editor
- Body: any subset of rule fields
- Same validations as create
- Updates `updated_at`, `updated_by`
- Response: updated rule

**DELETE /:ruleId** — editor
- Soft delete (`is_active = false`)
- Response: `{ message }`

**POST /reorder** — editor
- Body: `{ orderedRuleIds: UUID[] }` — full ordered list of rule IDs
- Sets `priority = index + 1` for each rule in the list
- Response: `{ message }`

**POST /apply** — editor
- No body. Enqueues `prism-virtual-tags` job for this org.
- Response: `{ message }` explaining job is running in background

**GET /audit-log** — viewer
- Response: last 100 audit log entries for this org's tag rules

---

### 9.11 Forecasts (`/v1/orgs/:orgId/forecasts`)

**GET /** — viewer
- Query: `?month=YYYY-MM` (default: current)
- Response: array of forecast rows (one per scope: overall + per-provider)
- If `data_coverage = 'insufficient'` → frontend should show "Need more data" placeholder

**GET /history** — viewer
- Response: last 12 months of org-level forecasts where `actual_total IS NOT NULL` (accuracy history)

---

### 9.12 Commitments (`/v1/orgs/:orgId/commitments`)

**GET /** — viewer (Redis cached 6h)
- Response: all commitment records for this org, sorted by status then end_date

**GET /summary** — viewer
- Response: `{ total_count, active_count, expiring_count, avg_utilization, total_monthly_savings, total_coverage }`

**GET /expiring** — viewer
- Query: `?days=90` (default 90, max 365)
- Response: commitments expiring within N days, sorted by end_date

---

### 9.13 Scorecard (`/v1/orgs/:orgId/scorecard`)

**GET /** — viewer (Redis cached 1h)
- Response: `{ overall: 0-100, metrics: { tagCoverage, commitmentCoverage, ... }, generatedAt }`
- Each metric has `{ value, color: red|yellow|green, label }`

**GET /executive** — viewer
- Response: `{ overall, color, topIssues: [top 3 red metrics], generatedAt }`

---

### 9.14 Notifications (`/v1/orgs/:orgId/notifications`)

**GET /** — viewer
- Response: notification settings (never expose webhook URLs in full — show masked version for viewer; admin sees full URL)

**PUT /** — admin
- Body: `{ alert_emails?, teams_webhook_url?, slack_webhook_url? }`
- Upserts notification_settings row
- Response: `{ message }`

**POST /test-email** — admin
- Sends a test cap alert email to configured recipients
- Returns 400 if no recipients configured

**POST /test-teams** — admin
- Sends test message to Teams webhook
- Returns 400 if no Teams URL configured

**POST /test-slack** — admin
- Sends test message to Slack webhook
- Returns 400 if no Slack URL configured

---

### 9.15 Outbound Webhooks (`/v1/orgs/:orgId/webhooks`)

**GET /** — viewer
- Response: list of webhooks (URL, description, events, last_triggered_at, last_status_code) — signing_secret never returned

**POST /** — admin
- Body: `{ url, description, events }` — url must be HTTPS and not private IP
- Generates raw signing secret (32 bytes hex). Encrypts + stores. Returns raw secret **once** in response — cannot be retrieved again.
- Response: `{ ...webhook, signing_secret: "raw-secret" }`

**PUT /:webhookId** — admin
- Body: any subset of `{ url, description, events, is_active }`
- Re-validates URL if changed
- Response: updated webhook (no secret)

**DELETE /:webhookId** — admin
- Soft delete
- Response: `{ message }`

**POST /:webhookId/test** — admin
- Dispatches a test `alert.fired` event with `{ test: true }` payload
- Response: `{ message }`

---

### 9.16 LLM (`/v1/orgs/:orgId/llm`)

**GET /config** — admin
- Response: `{ model, monthly_budget_usd, is_enabled, api_key_configured: true/false }` — never returns the key itself

**PUT /config** — admin
- Body: `{ openrouter_api_key, model, monthly_budget_usd, is_enabled }`
- Encrypts and stores the API key
- Response: `{ message }`

**DELETE /config** — admin
- Sets `is_enabled = false`
- Response: `{ message }`

**POST /query** — viewer (rate limited: 20/hr per user)
- Body: `{ question }` (max 500 chars)
- Gathers current month cost context from DB. Calls LLMService.
- Response: `{ answer: string | null, used_llm: boolean }` — if LLM unavailable, answer is a template fallback string (never null in response)
- Edge case: LLM budget exceeded → template response, `used_llm: false`

---

### 9.17 Business Metrics (`/v1/orgs/:orgId/metrics`)

**GET /** — viewer
- Response: active metrics for this org

**POST /** — admin
- Body: `{ name, source, unit }`
- Unique (org_id, name) — 409 on duplicate
- Response: created metric

**POST /:metricId/values** — editor
- Body: `{ values: [{ date: "YYYY-MM-DD", value: number }] }` (max 1000 entries per call)
- Upserts values (ON CONFLICT on (metric_id, date) → update value)
- Response: `{ message }`

**GET /:metricId/values** — viewer
- Query: `?days=30` (max 365)
- Response: array of `{ date, value }` sorted by date

---

### 9.18 Resources (`/v1/orgs/:orgId/resources`)

**GET /** — viewer
- Query: `?provider`, `?idle=true`, `?page`, `?limit`
- Response: paginated resources sorted by last_cost_usd DESC

**GET /idle** — viewer
- Response: top 100 idle resources (is_idle=true) sorted by idle_since, then last_cost_usd DESC

**GET /:resourceId** — viewer
- Response: full resource object

---

### 9.19 API Keys (`/v1/orgs/:orgId/api-keys`)

Machine-to-machine API keys for CI/CD integrations (e.g. Terraform cost checks, custom dashboards).

**GET /** — admin
- Response: list of keys — `{ id, name, key_prefix, scopes, expires_at, last_used, created_at, revoked_at }`
- Never return `key_hash`. `key_prefix` (first 8 chars) is shown for identification only.

**POST /** — admin
- Body: `{ name, scopes, expires_at? }` where scopes is subset of `["cost.read","alerts.read","reports.read","webhooks.write"]`
- Generates `crypto.randomBytes(32).toString("hex")` as raw key
- Stores `bcrypt.hash(rawKey, 10)` in `api_keys.key_hash`
- Stores first 8 chars in `api_keys.key_prefix`
- Response: `{ id, name, key_prefix, scopes, raw_key }` — raw_key shown **once only**; tell user to copy it now

**DELETE /:keyId** — admin
- Sets `revoked_at = NOW()`
- Response: `{ message }`

**API Key Auth Middleware:**
- Requests with `Authorization: Bearer prism_...` where token starts with "prism_" are treated as API key auth
- Middleware: find `api_keys` where `key_prefix = token.slice(6,14)`. Load candidate keys for this org. `bcrypt.compare` each.
- If valid and not revoked and not expired → proceed with `{ orgId, scopes }` context
- API key requests are rate limited to 120 req/min per key
- On use: update `api_keys.last_used = NOW()`
- Scopes are enforced: e.g. a `cost.read`-only key cannot POST to `/caps`

---

### 9.20 Incoming Integration Callbacks

**POST /integrations/teams-actions** — no JWT; HMAC validated
- Teams adaptive card button callbacks
- Validates `x-ms-teams-signature` header
- Handles: alert acknowledgement
- Response: `{ type: "message", text: "Action received" }`

**POST /integrations/slack-actions** — no JWT; HMAC validated
- Slack interactive component payloads
- Validates `x-slack-signature` header
- Handles: alert acknowledgement
- Response: `{ response_type: "ephemeral", text: "Action received" }`

---

## PART 10 — Cloud Connector Specifications

### 10.1 General Rules for All Connectors

- Credentials are decrypted just before use, never cached in memory between requests
- All API calls go through `withRetry(fn, maxRetries=3)`:
  - Do not retry on 401, 403, or credential errors (fail fast)
  - On 429: read `retry-after` header, wait that many seconds (max 2 min), then retry
  - On other errors: exponential backoff starting at 1 second, doubling each attempt, max 30 seconds
- Results are bulk-upserted to `cost_records` using `ON CONFLICT DO UPDATE`
- Only cost > 0 rows are stored (skip zero-cost line items)

### 10.2 AWS Connector

**Authentication:**
- Use AWS STS `AssumeRole` with the customer's `roleArn` and Prism's `externalId`
- Temporary credentials expire in 1 hour — re-assume before each job
- ExternalId prevents confused deputy attacks

**Cost Data:**
- API: `ce:GetCostAndUsage`
- Granularity: DAILY
- Metrics: UnblendedCost + AmortizedCost + UsageQuantity
- GroupBy: SERVICE + REGION
- Date range: yesterday (daily) or 13 months back (backfill)

**Amortized vs Unblended:**
- Store both in `cost_amortized_usd` and `cost_unblended_usd`
- Dashboard lets user toggle between views (stored preference in Redux/Zustand on frontend)

**Resource Discovery:**
- `ec2:DescribeInstances` per configured region
- Map to `resources` table, upsert on `(account_id, resource_id)`
- Mark idle if `last_activity_at < NOW() - 7 days` and `last_cost_usd > 0`

**Commitments:**
- `ce:GetReservationUtilizationSummary` for RI utilization
- `ce:GetReservationCoverage` for coverage rate
- `ce:GetSavingsPlansUtilizationDetails` for SP utilization
- `ce:GetSavingsPlansCoverage` for SP coverage

**Health Check:**
- Minimal CE call with 1-day window. Returns `{ ok, error? }`.

### 10.3 Azure Connector

**Authentication:**
- `ClientSecretCredential` from `@azure/identity` (tenantId + clientId + clientSecret)
- Token fetched on each request via axios interceptor
- `fxRate` passed at construction time from FXService — never undefined

**Cost Data:**
- API: `POST /subscriptions/{id}/providers/Microsoft.CostManagement/query`
- api-version: `2021-10-01`
- Granularity: Daily
- GroupBy: ServiceName + ResourceGroup
- Convert cost to USD at ingestion using fxRate

**Health Check:**
- `GET /subscriptions/{id}` with api-version 2020-01-01

### 10.4 GCP Connector

**Authentication:**
- Service account JSON key (stored encrypted in `credentials_enc`)
- Passed to `@google-cloud/bigquery` as `credentials` object

**Cost Data:**
- BigQuery billing export table: `{projectId}.{datasetId}.{tablePrefix}*`
- **Always use parameterized queries** (`@startDate`, `@endDate`) — never string interpolation
- Group by: usage_date, service.description, location.region, currency
- Filter: `cost > 0`

**Health Check:**
- Call `bigquery.dataset(datasetId).get()`. Returns `{ ok, error? }`.

### 10.5 Tag Normalization (Unified Schema)

Each cloud provider uses a different tagging model. All raw tags must be normalized to a single unified map before storing in `cost_records.tags` (JSONB).

**AWS Tags:**
- Source: `Tags` array in CE response, e.g. `[{ Key: "Environment", Value: "prod" }]`
- Normalize: lowercase the Key, trim whitespace, convert to `{ environment: "prod" }`
- AWS tag keys are case-sensitive internally but PRISM normalizes all to lowercase for cross-provider matching

**Azure Tags:**
- Source: `tags` object in Cost Management response, e.g. `{ "Environment": "prod" }`
- Normalize: same — lowercase all keys, trim values

**GCP Labels:**
- Source: `labels` repeated field in BigQuery billing export, e.g. `[{key: "environment", value: "prod"}]`
- Normalize: already lowercase by GCP convention; still trim whitespace
- GCP also has `system_labels` — ignore these (Prism only stores user-defined labels)

**Reserved PRISM Tag Keys:**
- `virtual_team` — written by VirtualTagEngine, never from cloud provider sync
- `virtual_project` — written by VirtualTagEngine
- Cloud sync must never overwrite keys prefixed with `virtual_`
- Use `ON CONFLICT DO UPDATE SET tags = excluded.tags || existing.tags` (cloud-provided tags win for overlaps, but `virtual_*` keys from existing row are preserved via the merge)

**Cross-provider tag matching:**
- When a virtual tag rule targets `key = "environment"`, it matches regardless of whether source was AWS, Azure, or GCP
- Match logic uses normalized (lowercased) key names

---

## PART 11 — Background Job System

### 11.1 Queue Architecture

All queues use BullMQ backed by Redis. Each queue has a corresponding worker process.

| Queue | Trigger | Concurrency | Typical Duration |
|-------|---------|-------------|-----------------|
| prism-sync | Cron 06:00 UTC + manual | 5 | 2–10 min per account |
| prism-alerts | After each sync + on cap create | 10 | <1 min |
| prism-forecast | Cron 07:30 UTC | 5 | <30 sec |
| prism-commitments | Cron 07:00 UTC | 3 | 2–5 min |
| prism-recommendations | Cron 08:00 UTC | 3 | 1–5 min |
| prism-reports | Cron 09:00 UTC (daily check) | 2 | 30 sec – 2 min |
| prism-virtual-tags | On rule save by user | 1 (serialized) | 2 min per 1M rows |
| prism-dlq | Automatic (jobs that failed 3×) | 1 | <1 sec |

### 11.2 Idempotency Rules

- Every job has a deterministic `jobId` format: `{type}:{orgId/accountId}:{YYYY-MM-DD}`
- BullMQ `jobId` deduplication prevents duplicate jobs in the queue
- `cost_records` upsert with `ON CONFLICT DO UPDATE` ensures duplicate syncs are safe
- `resource` upserts with `ON CONFLICT (account_id, resource_id) DO UPDATE SET last_seen = NOW()` are safe
- Alert deduplication via unique partial index in DB (not application logic alone)

### 11.3 Retry Policy

- All queues: `attempts: 3`, backoff: exponential starting at 60 seconds
- After 3 failures: job moves to `prism-dlq`
- DLQ worker: log the failure, optionally create a `sync_failure` alert, do NOT retry
- DLQ retention: 14 days

### 11.4 Scheduler (Cron)

`node-cron` runs in the same process as the app. Each cron trigger:
1. Queries DB for eligible orgs or accounts
2. Enqueues one job per org/account into the appropriate BullMQ queue
3. Does NOT do the actual work inline

Cron schedules (all UTC):
- 06:00 → prism-sync (one job per active cloud_account)
- 07:00 → prism-commitments (one job per org)
- 07:30 → prism-forecast (one job per org)
- 08:00 → prism-recommendations (one job per org)
- 09:00 → prism-reports (one job per org where `next_send <= today`)

### 11.5 Sync Worker — Step by Step

1. Receive `{ accountId, orgId, backfill }` from queue
2. Create `sync_logs` row (status=running)
3. Update `cloud_accounts.last_sync_status = 'running'`
4. Fetch account from DB; decrypt credentials
5. Get FX rate from FXService
6. Determine date range: backfill → 13 months back; normal → last 3 days (re-sync recent estimates)
7. Call connector's `getCostAndUsage(startDate, endDate)`
8. Bulk upsert records in chunks of 500
9. Call connector's `getResources()` and upsert resources
10. Update `cloud_accounts`: `last_sync, last_sync_status=success, data_as_of, last_sync_records`
11. Update `sync_logs`: `finished_at, status=success, records_synced`
12. Invalidate Redis dashboard cache for this org+provider
13. Broadcast `sync.complete` WebSocket event to org's connected clients
14. Enqueue `prism-alerts` job for this org
15. On any error: update account and sync_log to failed status, throw (BullMQ retries)

---

## PART 12 — Alert & Notification System

### 12.1 Alert Types and Triggers

| Type | Trigger | Severity | Dedup Rule |
|------|---------|---------|-----------|
| cap_threshold | Current month spend ≥ threshold % of cap | warning (75/90) / critical (100+) | Once per (cap, threshold, billing month) via unique index |
| forecast_breach | projected_total > cap_amount | warning | Once per (org, provider, billing month) |
| spend_acceleration | Daily avg this week > last week by 30%+ | warning | Once per (org, provider, week) |
| sync_failure | Sync job fails after 3 retries | critical | On every failure (no dedup — real errors always notify) |
| credential_expiry | Azure/GCP credential expires ≤ 14 days | warning | Once per (account, 30-day window) |
| commitment_expiry | RI/SP/CUD expires ≤ 30 days | warning | Once per (commitment, 30-day window) |
| unused_commitment | Commitment utilization < 80% | warning | Once per (commitment, billing month) |
| untagged_resource | New resource with no owner/team tag | info | Once per resource per discovery |
| idle_resource | Resource has 0 usage for 7+ days | info | Once per (resource, idle_since month) |

### 12.2 Cap Alert Check Logic

1. For each active budget cap of the org:
2. Query `cost_records` WHERE `org_id + time range + scope filter`. SUM `cost_usd`.
3. `pct = (spent / cap.cap_amount) * 100`
4. For each threshold in [75, 90, 100, 125, 150]: if `pct >= threshold`:
5. Check DB: does an alert exist for this (org_id, cap_id, threshold, current billing month)?
6. If yes → skip (already fired this month for this threshold)
7. If no → insert Alert row → fire all notification channels concurrently

### 12.3 Notification Channels

All channels are fired concurrently using `Promise.allSettled` (failure in one never blocks others).

| Channel | When active | Payload |
|---------|------------|---------|
| Email | Always (if alert_emails configured) | HTML email via SES |
| Teams | If teams_webhook_url configured | Adaptive card via HTTP POST |
| Slack | If slack_webhook_url configured | Block kit JSON via HTTP POST |
| Outbound webhook | If org has active webhooks with `alert.fired` event | HMAC-signed JSON |
| WebSocket | Always (if any clients connected) | Immediate — no configuration needed |

### 12.4 Alert Insert + Channel Update Pattern

1. Insert Alert row with all `*_sent = false`
2. Run all channels with `Promise.allSettled`
3. Collect which channels succeeded
4. `UPDATE alerts SET email_sent=true, teams_sent=true, ...` for channels that succeeded
5. Failed channels: log at warn level — do not retry — do not throw

### 12.5 Teams & Slack Validation (Incoming)

Incoming action callbacks from Teams and Slack buttons must be HMAC-validated before processing.

- Teams: validate `x-ms-teams-signature` header against HMAC-SHA256 of body using `TEAMS_SIGNING_SECRET`
- Slack: validate `x-slack-signature` header using `SLACK_SIGNING_SECRET`
- Use `crypto.timingSafeEqual` for comparison — never `===`
- Invalid signature → 401 immediately

---

## PART 13 — WebSocket (Real-Time Events)

### 13.1 Connection Lifecycle

1. Client connects to `wss://api.prism.io/ws?token={jwt}`
2. Server validates JWT from query string on connect — rejects with close code 4001 if invalid/expired
3. Server registers the connection under the user's `orgId` in an in-memory Map: `Map<orgId, Set<WebSocket>>`
4. Server starts a 30-second ping interval to keep connection alive
5. Client must reconnect on close code 4001 — refresh access token first via `/v1/auth/refresh`
6. On disconnect: remove client from the Map; clear ping interval

### 13.2 Events Broadcast (Server → Client)

All events share this envelope:
```
{
  event: string,
  org_id: string,
  timestamp: ISO-8601 string,
  data: object
}
```

| Event | When fired | Data payload |
|-------|-----------|--------------|
| `sync.complete` | After sync worker finishes | `{ provider, account_id, records }` |
| `alert.fired` | When new alert is inserted | `{ alert_id, type, scope, severity, threshold_percent }` |
| `forecast.updated` | After forecast recalculation | `{ provider, projected_total, will_breach, data_coverage }` |
| `recommendation.new` | When new recs are generated | `{ count, top_savings }` |
| `virtual_tags.progress` | During retroactive re-tag | `{ processed, updated }` (batched) |
| `connected` | Immediately after connect | `{}` — confirms connection |

### 13.3 Broadcast Rules

- `wsBroadcast(orgId, event)` is called from workers and services
- Only sends to clients in the `Map.get(orgId)` set
- Never broadcasts across org boundaries
- Skips clients whose `readyState !== OPEN`

---

## PART 14 — LLM Integration (OpenRouter)

### 14.1 Design Principles

- LLM is entirely optional — every feature works without it
- Every caller of LLMService checks for `null` return and has a non-LLM fallback
- LLM is never on the critical path for any user-facing action
- The user provides their own OpenRouter API key (Prism never bills for LLM)
- API key is stored AES-256 encrypted in `llm_configs`

### 14.2 LLMService Behavior

1. `LLMService.forOrg(orgId)` — static factory. Loads config from DB. If no config or disabled → returns a disabled service instance.
2. `canCall()` — returns false if: not enabled, OR `spentThisMonth >= monthlyBudgetUSD`
3. Monthly spend tracked in Redis (`llm:monthly_spent:{orgId}:{YYYY-MM}`), not DB
4. All prompts checked against Redis cache first (`llm:{base64_prompt_hash}`, 24h TTL)
5. On LLM error → log warn → return `null` (never throw)
6. All callers treat `null` as "use template fallback"

### 14.3 LLM Surfaces

| Feature | LLM adds | Fallback when LLM off |
|---------|---------|----------------------|
| Monthly report | Executive narrative paragraph | Template: "Total spend: $X (+Y%)" |
| Recommendations | Explanation + risk note per rec | Show type + savings only |
| Alert context | Natural language summary | Show raw numbers |
| Q&A chat | `POST /v1/orgs/:orgId/llm/query` | Static "LLM not configured" message |
| Untagged resource ownership | Ownership suggestion | Show resource name + cost only |

### 14.4 Prompt Safety Rules

- Prompts never include credential values, raw API keys, or PII beyond email
- All prompts include org_id for audit purposes but not in the prompt text itself
- Max prompt size: 4000 chars. Max response tokens: 400 (narrative) / 200 (Q&A) / 150 (explanations)
- Same prompt always returns same cached response (deterministic by hash)

---

## PART 15 — Virtual Tag Engine

### 15.1 Purpose

Users define tag rules inside Prism to allocate cost records to teams/environments without modifying cloud provider tags.

### 15.2 Rule Evaluation Logic

1. Load all active rules for the org, ordered by `priority ASC`
2. For each `cost_records` row: iterate rules in priority order
3. For each rule: check if the record matches the condition
4. First matching rule wins for `set_tag` rules (stop evaluating for that tag key)
5. `split` rules always run (not first-match)
6. Write computed tags to `virtual_tags` JSONB column

### 15.3 Condition Matching

| Operator | Behavior |
|----------|---------|
| contains | case-insensitive substring match |
| equals | case-insensitive exact match |
| starts_with | case-insensitive prefix match |
| ends_with | case-insensitive suffix match |
| regex | safeRegexTest() — must complete in <50ms on 1000-char test string (ReDoS guard) |

Fields available for matching: `resource_name`, `account_id`, `service`, `region`, `tag_value` (JSON of provider tags).

### 15.4 Retroactive Re-tagging

- Always runs as a background job (`prism-virtual-tags` queue) — never synchronously
- Worker processes `cost_records` in batches of 5000 rows
- Sends `virtual_tags.progress` WebSocket events every batch
- Job is idempotent — safe to restart
- Concurrency: 1 (serialized per org to avoid concurrent writes)
- BullMQ lock duration: 10 minutes (retroactive tagging can take a while for large orgs)

### 15.5 Validation at Save Time

- Regex patterns: must compile, must execute in <50ms on test string, max 200 chars
- Split config: pct values must sum exactly to 100 (±0.01 tolerance)
- Priority must be unique per org (UNIQUE DB constraint)

---

## PART 16 — Spend Forecast Engine

### 16.1 Algorithm

```
spend_to_date = SUM of cost_records this month so far
days_with_data = count of calendar days that have at least one cost record
daily_avg = spend_to_date / days_with_data

rolling_7d_avg = avg daily spend for the last 7 calendar days

effective_avg = IF ABS(rolling_7d_avg - daily_avg) / daily_avg > 20%
                THEN rolling_7d_avg   ← use rolling (weekend effect)
                ELSE daily_avg

projected_total = spend_to_date + (effective_avg × days_remaining)
```

### 16.2 Edge Case Handling

| Situation | Behavior |
|-----------|---------|
| `days_with_data < 3` | Set `data_coverage = 'insufficient'`. Still compute forecast but mark as unreliable. |
| Org connected mid-month | Use days-since-connection, not days-since-month-start |
| Zero-spend days (weekends) | Rolling 7d avg smooths this out |
| Month just closed | `actual_total` is filled; widget shows "Final: $X" |
| No cap set for this scope | `cap_amount = null`; `will_breach = false` |
| Sync failed recently | Forecast uses last successful sync data. Frontend note: "Based on data as of [date]" |

### 16.3 Breach Date Calculation

```
days_until_breach = (cap_amount - spend_to_date) / effective_avg
breach_date = NOW() + days_until_breach days
```

Only computed when `will_breach = true`.

### 16.4 Accuracy Tracking

At month-end (when `actual_total` is available):
```
variance_pct = (actual_total - projected_total) / actual_total × 100
```
The projection used is the one made on day 15 of the month (mid-month snapshot). Stored in `spend_forecasts.variance_pct` for reporting.

---

## PART 17 — FinOps Health Scorecard

### 17.1 Metric Definitions

| Metric | Formula | Green | Yellow | Red | Weight |
|--------|---------|-------|--------|-----|--------|
| Tag Coverage | % of this month's cost_records with a `team` tag (provider or virtual) | ≥90% | 60–89% | <60% | 20% |
| Commitment Coverage | avg(utilization_pct) of active commitment_records | ≥60% | 30–59% | <30% | 20% |
| Commitment Utilization | avg(utilization_pct) of active commitments | ≥95% | 85–94% | <85% | 10% |
| Idle Resource Rate | idle resources / total resources × 100 | <5% | 5–10% | >10% | 10% |
| Recs Acted On | (implemented + rejected) / total recommendations × 100 | ≥60% | 30–59% | <30% | 10% |
| Forecast Accuracy | 100 - avg(ABS(variance_pct)) for last 3 months | ≥90% | 80–89% | <80% | 10% |
| Cap Breaches | count of cap_threshold alerts ≥100% this billing month | 0 | 1–2 | >2 | 20% |

### 17.2 Overall Score

`overall = SUM( metric_score × weight / 100 )` — rounds to nearest integer (0–100).

### 17.3 Caching

Scorecard is cached in Redis for 1 hour (`dash:{orgId}:scorecard`). Invalidated when any metric's inputs change (sync complete, cap alert, recommendation status change).

---

## PART 18 — Monthly Report System

### 18.1 Scheduling

1. Cron fires at 09:00 UTC daily.
2. Query: `SELECT org_id FROM monthly_reports WHERE is_active=true AND date_trunc('day', next_send) <= date_trunc('day', NOW())`
3. For each matched org: enqueue `prism-reports` job.
4. Worker runs `ReportGenerator.generate(orgId)`.
5. After send: `last_sent = NOW()`, `next_send = next month same day at 09:00 UTC`.

### 18.2 Report Sections (in order)

1. **Header**: Org name, report month, generated date
2. **Executive Summary**: Total spend, delta from last month, LLM narrative (or template if LLM off)
3. **Spend by Platform**: Table: provider → this month → last month → change → cap → % of cap
4. **Top 10 Services**: Table: service → provider → this month → change
5. **Spend by Team (Tag)**: If team tags exist — allocate spend by team/virtual_team tag
6. **Budget Cap Status**: All active caps with spent/cap/% and status indicator
7. **Top 5 Recommendations**: If `include_recommendations = true`
8. **FinOps Health Score**: If `include_finops_scorecard = true`
9. **Commitment Summary**: If `include_commitments = true`
10. **Unit Economics**: If `include_unit_economics = true` and business metrics exist
11. **Forecast Accuracy (last 3 months)**: Forecast vs actual comparison

### 18.3 Test Report

`POST /reports/send-now` sends the report immediately without changing `next_send`. Useful for verifying email delivery and report content.

---

## PART 19 — Email System

### 19.1 Provider

AWS SES (primary). SendGrid works as a drop-in replacement — same API shape (SMTP or REST). Configure via env vars.

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
| Sync failure | DLQ worker | `notification_settings.alert_emails` |

### 19.3 Email Content Rules

- All emails must have both HTML and plain-text versions
- Every email includes: from address, org name in subject, link to dashboard, unsubscribe/manage link
- Cap alerts: include spend amount, cap amount, % used, forecast, next threshold, and action links
- Never include credentials or sensitive data in email body
- Email subject must be specific (not generic — "PRISM alert" is bad; "⚠️ AWS EC2 at 90% — Acme Corp" is good)

---

## PART 20 — Security Requirements

### 20.1 Authentication Security

- Passwords: bcrypt cost factor 12. Never store plaintext.
- JWT secrets: minimum 32 chars of random entropy. Stored in env (never in code or DB).
- Refresh tokens: stored as bcrypt hash in DB. Raw token shown only at issue time.
- Email verification tokens: 24h expiry. Single-use (cleared after verification).
- Invite tokens: 48h expiry. Bcrypt-hashed in DB. Raw token sent once via email.
- Password reset tokens: 1h expiry. Stored bcrypt-hashed in Redis. Deleted after use.
- Login errors: same 401 message for "wrong email" and "wrong password" — no enumeration.
- Login timing: always call `bcrypt.compare` even when user not found (dummy hash) — prevents timing attacks.
- On successful password reset: revoke ALL refresh tokens for that user (all sessions invalidated).

### 20.2 Authorization Security

- Every authenticated route applies `requireAuth` (JWT verify) then `requireOrgAccess` (orgId match).
- org_id for DB queries: always from `req.user.orgId` (JWT) — never from request body.
- CSRF: state-changing endpoints (POST/PUT/PATCH/DELETE) require `Authorization: Bearer` header — cookie-only requests are rejected.
- Owner cannot be demoted via team API. Owner can only be transferred to another admin.

### 20.3 Data Security

- Cloud credentials: AES-256-GCM encrypted in DB. Key from env. Never logged.
- LLM API key: AES-256-GCM encrypted.
- Webhook signing secrets: AES-256-GCM encrypted. Raw secret shown once at creation.
- All DB queries: parameterized (pg library's `$1, $2` syntax). Never string concatenation.
- BigQuery queries: `@param` syntax — never `${variable}` interpolation.

### 20.4 Network Security

- All HTTPS. TLS 1.3 minimum.
- CORS: locked to frontend origin (configurable via env var).
- Helmet.js: sets all standard security headers.
- Teams/Slack webhook validation: HMAC-SHA256 with `crypto.timingSafeEqual` — never `===`.

### 20.5 SSRF Protection (Outbound Webhooks)

When storing or dispatching a customer-supplied webhook URL:
1. Must be `https://` — reject `http://`, `ftp://`, `file://`, etc.
2. Must not resolve to private IP ranges: 127.x, 10.x, 192.168.x, 172.16–31.x, 169.254.x, ::1, 0.0.0.0
3. DNS re-check at dispatch time (DNS rebinding protection): resolve hostname → verify resulting IP is not private.
4. Reject if hostname cannot be resolved.

### 20.6 Input Validation

- All request bodies validated with Zod schemas before reaching business logic.
- Regex patterns: validated for compilation + ReDoS safety (max 50ms on 1000-char test string, max 200 chars).
- Split configs: pct values must sum to 100.
- Pagination limits: capped at 100.
- Email addresses: RFC-format validated before storing.
- URL fields: `new URL()` parse + additional checks.

### 20.7 Rate Limiting

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

### 21.1 Error Class

A single `AppError` class extends `Error` and carries `statusCode` and optional `code`. All intentional errors are thrown as `AppError`. Unexpected errors bubble up to the global handler.

### 21.2 Global Error Handler

- `AppError` → respond with `{ error: message, code? }` at `statusCode`
- Any other error → log as `error` level → respond with `{ error: "Internal server error" }` at 500
- Never include stack traces or DB error messages in 500 responses

### 21.3 Edge Cases That Must Be Handled Explicitly

| Situation | Handling |
|-----------|---------|
| Duplicate sync (job fires twice) | `ON CONFLICT DO UPDATE` — safe |
| Cap alert fires twice same month | Unique partial index in DB — second insert fails silently |
| LLM call fails | Return `null`, caller uses template |
| LLM budget exceeded | `canCall()` returns false, caller uses template |
| Email send fails | Log error, do NOT throw — alert still created in DB |
| Teams/Slack notification fails | Log warn, other channels still fire (Promise.allSettled) |
| Webhook URL fails SSRF check | Log warn, skip dispatch, do not error the calling request |
| Retroactive re-tag cancelled/crashed | Job is idempotent — restart from beginning, same output |
| First 3 days of month (forecast) | `data_coverage = 'insufficient'` — frontend shows placeholder |
| Zero-spend weekends in forecast | Use rolling 7d avg |
| User accepts expired invite | 400 — ask inviter to resend |
| User tries to remove org owner | 403 — explicit message |
| Cross-org access attempt | 403 — same message as "org not found" (no information leakage) |
| BigQuery dataset not found | Connector healthCheck returns `{ ok: false, error: message }` |
| STS AssumeRole fails | Connector throws — sync job fails, retries, eventually DLQ |
| DB pool exhausted | pg Pool throws — unhandled error hits global handler → 500 |
| Redis connection lost | ioredis auto-reconnects; in-flight operations may fail → log |

---

## PART 22 — Logging & Observability

### 22.1 Logger

pino at `info` level in production, `debug` in development. Structured JSON output in production. Pretty-printed in development.

Every log entry includes: `service: "prism-backend"`, `env: NODE_ENV`, `timestamp: ISO-8601`.

### 22.2 What to Log

| Event | Level | Fields |
|-------|-------|--------|
| HTTP request | info | method, path, status, duration_ms, org_id |
| User login | info | userId, orgId, email |
| Login failed | warn | email, ip |
| Sync started | info | accountId, orgId, provider, backfill |
| Sync completed | info | accountId, records, duration_ms |
| Sync failed | error | accountId, error message |
| Alert fired | info | alertId, orgId, type, threshold |
| Email sent | info | to (list), subject |
| Email failed | error | to, error |
| LLM fallback | warn | orgId, reason |
| DLQ job received | error | jobId, jobName, data |
| Unhandled error | error | error, path, method |

### 22.3 Health Check

`GET /health` — no auth. Returns:
```json
{ "status": "ok" | "degraded", "db": true | false, "redis": true | false, "ts": "ISO-8601" }
```
Status 200 if both DB and Redis are healthy. 503 if either fails.

---

## PART 23 — Edge Cases & Pitfalls

### 23.1 Multi-Tenancy Pitfalls

- Never use `account_id` alone as a query filter without also filtering by `org_id` — account IDs are UUID internal IDs but multi-org scenarios could theoretically share providers.
- WebSocket: after lookup, broadcast ONLY to the specific org's connections — never iterate all connections.
- Cache: Redis scan by pattern for `dash:{orgId}:*` — ensure scan loop is complete before returning (cursor-based scan, not KEYS which blocks Redis).

### 23.2 Sync Pitfalls

- AWS Cost Explorer has a 24–48h data lag — today's data is not yet available. Always sync yesterday at minimum.
- The "current month" data from AWS is marked `is_estimate = true` — re-sync it daily until the month closes.
- Azure Cost Management can return 500 errors during high load — withRetry handles this.
- GCP BigQuery billing export must be enabled by the customer before Prism can pull data — if table doesn't exist, healthCheck fails with a clear error.
- FX rate must be set before calling AzureConnector — passing undefined causes NaN costs in DB.

### 23.3 Alert Pitfalls

- The dedup unique index only prevents duplicate cap_threshold alerts per cap per month. forecast_breach alerts use a separate query-based dedup check.
- Snoozed alerts are NOT re-fired when the snooze expires — they remain snoozed. Only new threshold crossings fire new alerts.
- When a cap is deleted (soft delete), existing alerts for that cap remain. The FK is set to NULL via `ON DELETE SET NULL`.

### 23.4 Background Job Pitfalls

- BullMQ `jobId` deduplication works per queue — the same jobId in different queues is fine.
- The `prism-virtual-tags` worker must use a long lock duration (10 min) because retroactive re-tagging can take several minutes for large orgs — without this, BullMQ may consider the job stalled and re-queue it, causing duplicate processing.
- The monthly report cron fires daily at 09:00 UTC and checks `next_send <= today`. Ensure `next_send` is always in UTC, not local time.

### 23.5 WebSocket Pitfalls

- The `orgConnections` Map is in-memory — in a multi-instance deployment, a WS broadcast from one instance won't reach clients on other instances. Solution for scale: publish WS events to Redis Pub/Sub; each instance subscribes and broadcasts to its own connected clients.
- Always clear the ping interval in `ws.on("close")` — not doing so causes memory leak.
- JWT expiry during a long WS session: server does NOT re-validate JWT after connection. Client is responsible for reconnecting with a fresh token before expiry.

---

## PART 24 — Testing Requirements

### 24.1 What to Test

**Unit tests (pure logic, no DB/Redis):**
- `withRetry`: 429 respects retry-after header; 401 is not retried; 3rd attempt success returns value
- `encrypt/decrypt`: round-trip produces original string; wrong key throws
- Virtual tag engine: `matchesCondition()` for each operator; split pct; first-match wins
- `safeRegexTest()`: catastrophic backtracking pattern completes in <500ms
- Forecast: `data_coverage = 'insufficient'` when `days_with_data < 3`; rolling avg used when weekend zeros
- Scorecard: each metric formula matches spec

**Integration tests (with real DB, test org):**
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
- Remove owner → 403; remove yourself → 400
- Regex with ReDoS pattern saved → 400
- Webhook URL with private IP → 400
- Webhook URL with http:// → 400
- Split config pct ≠ 100 → 400
- LLM query with LLM not configured → 200 with `used_llm: false`
- Sync with bad credentials → sync_status = failed; sync_failure alert created

---

## PART 25 — Implementation Order

Follow this order. Each milestone produces a working, testable system. Never skip ahead.

### Milestone 1 — Auth + DB (Days 1–5)
1. Create PostgreSQL DB. Run TimescaleDB extension.
2. Run `schema.sql` — all tables + indexes.
3. Implement `config/env.ts`, `config/db.ts`, `config/redis.ts`.
4. Implement `utils/logger.ts`, `utils/encrypt.ts`.
5. Implement all middleware: auth, orgScope, rbac, validateBody, errorHandler, requestLogger, rateLimit.
6. Implement `routes/auth.ts` — full signup/verify/login/refresh/logout/forgot-reset flow.
7. Implement `app.ts` + `index.ts` (without workers yet).
8. Test: signup → verify → login → refresh → logout.

### Milestone 2 — Team + Org Settings (Days 6–8)
9. Implement `routes/orgs.ts` — GET + PUT org.
10. Implement `routes/team.ts` — all member management + invite/accept flow.
11. Implement `services/email.service.ts` — verification, invite, password reset emails.
12. Test: full invite flow end-to-end; role enforcement; owner protection.

### Milestone 3 — Cloud Connectors + Sync (Days 9–15)
13. Implement `utils/withRetry.ts`.
14. Implement `services/fx.service.ts`.
15. Implement `services/connectors/aws.ts`, `azure.ts`, `gcp.ts`.
16. Implement `config/queues.ts`.
17. Implement `jobs/sync.worker.ts`.
18. Implement `jobs/scheduler.ts` (sync cron only).
19. Implement `utils/cache.ts`.
20. Implement `routes/accounts.ts` — CRUD + test + sync trigger + sync logs.
21. Implement `ws/wsServer.ts`.
22. Test: connect AWS account → sync fires → cost_records populated → WS sync.complete received.

### Milestone 4 — Dashboard + Caps + Alerts (Days 16–22)
23. Implement `routes/costs.ts` — all aggregation queries + Redis caching.
24. Implement `routes/caps.ts`.
25. Implement `services/alert.service.ts`.
26. Implement `jobs/alerts.worker.ts`.
27. Implement `routes/alerts.ts` — list + acknowledge + snooze.
28. Add alert cron trigger to scheduler.
29. Add cap alert emails to `email.service.ts`.
30. Implement `utils/validateWebhookUrl.ts`.
31. Implement `services/webhook.service.ts`.
32. Implement `routes/notifications.ts`.
33. Test: create cap → sync fires → pct > 75% → alert created → email sent → WS alert.fired.

### Milestone 5 — Reports + Forecast + Recommendations (Days 23–30)
34. Implement `services/forecast.service.ts` + `jobs/forecast.worker.ts`.
35. Implement `routes/forecasts.ts`.
36. Implement `services/recommendation.service.ts` + `jobs/recommendations.worker.ts`.
37. Implement `routes/recommendations.ts`.
38. Implement `services/report.service.ts` + `jobs/reports.worker.ts`.
39. Implement `routes/reports.ts`.
40. Add all cron entries to scheduler.
41. Test: forecast computed after sync; monthly report sends on configured day.

### Milestone 6 — Advanced Features (Days 31–40)
42. Implement `utils/regex.ts`.
43. Implement `services/virtualTag.service.ts` + `jobs/virtualTags.worker.ts`.
44. Implement `routes/virtualTags.ts`.
45. Implement `services/commitment.service.ts` + `jobs/commitments.worker.ts`.
46. Implement `routes/commitments.ts`.
47. Implement `services/scorecard.service.ts`.
48. Implement `routes/scorecard.ts`.
49. Implement `services/llm.service.ts`.
50. Implement `routes/llm.ts`.
51. Implement `routes/webhooks.ts`.
52. Implement `routes/businessMetrics.ts`.
53. Implement `routes/resources.ts`.
54. Implement `middleware/hmac.ts` + `routes/teamsActions.ts` + `routes/slackActions.ts`.
55. Implement `jobs/dlq.worker.ts`.
56. Run full end-to-end flow: signup → connect cloud → invite team → set cap → get alert → read report.

---

## APPENDIX — Environment Variables Reference

| Variable | Required | Description |
|----------|---------|-------------|
| NODE_ENV | Yes | development / production / test |
| PORT | Yes | HTTP server port |
| DATABASE_URL | Yes | PostgreSQL connection string |
| DATABASE_POOL_MAX | No | Default 20 |
| REDIS_URL | Yes | Redis connection string |
| JWT_ACCESS_SECRET | Yes | Min 32 chars random string |
| JWT_REFRESH_SECRET | Yes | Min 32 chars random string (different from access) |
| JWT_ACCESS_EXPIRY | No | Default "7d" |
| JWT_REFRESH_EXPIRY | No | Default "30d" |
| GOOGLE_CLIENT_ID | No | For Google OAuth |
| GOOGLE_CLIENT_SECRET | No | For Google OAuth |
| GOOGLE_REDIRECT_URI | No | For Google OAuth |
| AWS_SES_REGION | Yes | e.g. "us-east-1" |
| AWS_SES_FROM | Yes | Verified sender email |
| AWS_ACCESS_KEY_ID | No | Prism's own AWS creds (for SES + STS) |
| AWS_SECRET_ACCESS_KEY | No | Prism's own AWS creds |
| ENCRYPTION_KEY | Yes | 64 hex chars (32 bytes) — AES key for credentials |
| PRISM_AWS_ACCOUNT_ID | Yes | Prism's own AWS account ID (for STS ExternalId) |
| TEAMS_SIGNING_SECRET | No | For validating Teams incoming webhooks |
| SLACK_SIGNING_SECRET | No | For validating Slack incoming webhooks |
| FRONTEND_URL | Yes | CORS origin e.g. "https://app.prism.io" |
| CRON_SYNC | No | Default "0 6 * * *" |
| CRON_COMMITMENTS | No | Default "0 7 * * *" |
| CRON_FORECAST | No | Default "30 7 * * *" |
| CRON_RECOMMENDATIONS | No | Default "0 8 * * *" |
| CRON_REPORTS | No | Default "0 9 * * *" |
| WORKER_CONCURRENCY | No | Default 5 |

---

*End of PRISM Backend Implementation Plan — backend_plan.md*
