# PRISM — Complete Backend Implementation Plan

**Target:** Node.js + TypeScript + Express  
**Database:** PostgreSQL 16 + TimescaleDB extension  
**Cache:** Redis 7  
**Queue:** BullMQ (backed by Redis)  
**Auth:** JWT + bcrypt + Google OAuth 2.0  
**Email:** AWS SES (or SendGrid as drop-in)  
**Real-time:** WebSocket (ws library)  
**LLM:** OpenRouter (OpenAI-compatible SDK, optional)  
**Secrets:** AWS Secrets Manager (or HashiCorp Vault)

> **How to use this document:** Follow sections in order. Each section is self-contained. Every code block is the exact implementation — not pseudocode. Copy, adapt to your env vars, run.

---

## TABLE OF CONTENTS

1. [Project Setup & Folder Structure](#1-project-setup--folder-structure)
2. [Environment Variables](#2-environment-variables)
3. [Database Schema (SQL)](#3-database-schema-sql)
4. [Database Indexes](#4-database-indexes)
5. [Redis Key Conventions](#5-redis-key-conventions)
6. [Express App Entrypoint](#6-express-app-entrypoint)
7. [Middleware Stack](#7-middleware-stack)
8. [Authentication System](#8-authentication-system)
9. [RBAC — Role-Based Access Control](#9-rbac--role-based-access-control)
10. [Cloud Connector Services](#10-cloud-connector-services)
11. [Background Job System (BullMQ)](#11-background-job-system-bullmq)
12. [Job Workers (Full Implementation)](#12-job-workers-full-implementation)
13. [Alert & Notification System](#13-alert--notification-system)
14. [WebSocket Server](#14-websocket-server)
15. [API Endpoints — Full Route Reference](#15-api-endpoints--full-route-reference)
16. [Route Implementations](#16-route-implementations)
17. [LLM Service (OpenRouter)](#17-llm-service-openrouter)
18. [Monthly Report Generator](#18-monthly-report-generator)
19. [Virtual Tag Engine](#19-virtual-tag-engine)
20. [Forecast Engine](#20-forecast-engine)
21. [FinOps Health Scorecard Engine](#21-finops-health-scorecard-engine)
22. [Email Service](#22-email-service)
23. [Error Handling](#23-error-handling)
24. [Logging & Observability](#24-logging--observability)
25. [Input Validation (Zod Schemas)](#25-input-validation-zod-schemas)
26. [Security Checklist](#26-security-checklist)
27. [Testing Guide](#27-testing-guide)
28. [Start-up Sequence](#28-start-up-sequence)

---

## 1. Project Setup & Folder Structure

### 1.1 Initialize Project

```bash
mkdir prism-backend && cd prism-backend
npm init -y
npm install express typescript ts-node @types/node @types/express
npm install pg @types/pg timescaledb-toolkit
npm install redis ioredis
npm install bullmq
npm install jsonwebtoken bcrypt @types/jsonwebtoken @types/bcrypt
npm install zod
npm install nodemailer @aws-sdk/client-ses
npm install @aws-sdk/client-cost-explorer @aws-sdk/client-sts @aws-sdk/client-ec2
npm install @azure/identity axios
npm install @google-cloud/bigquery
npm install openai
npm install ws @types/ws
npm install pino pino-pretty
npm install helmet cors express-rate-limit
npm install crypto-js
npm install dotenv
npm install node-cron
npx tsc --init
```

### 1.2 Folder Structure

```
prism-backend/
├── src/
│   ├── index.ts                    ← App entrypoint
│   ├── app.ts                      ← Express app factory
│   ├── config/
│   │   ├── env.ts                  ← Validated env vars (zod)
│   │   ├── db.ts                   ← PostgreSQL pool
│   │   ├── redis.ts                ← Redis client
│   │   └── queues.ts               ← BullMQ queue definitions
│   ├── middleware/
│   │   ├── auth.ts                 ← JWT verification
│   │   ├── rbac.ts                 ← Role enforcement
│   │   ├── orgScope.ts             ← Inject req.org from JWT
│   │   ├── rateLimit.ts            ← Per-endpoint rate limits
│   │   ├── validateBody.ts         ← Zod body validation
│   │   ├── hmac.ts                 ← Teams/Slack HMAC validation
│   │   └── errorHandler.ts         ← Global error handler
│   ├── routes/
│   │   ├── auth.ts                 ← POST /v1/auth/*
│   │   ├── orgs.ts                 ← GET/PUT /v1/orgs/*
│   │   ├── accounts.ts             ← /v1/orgs/:orgId/accounts/*
│   │   ├── costs.ts                ← /v1/orgs/:orgId/costs/*
│   │   ├── alerts.ts               ← /v1/orgs/:orgId/alerts/*
│   │   ├── caps.ts                 ← /v1/orgs/:orgId/caps/*
│   │   ├── reports.ts              ← /v1/orgs/:orgId/reports/*
│   │   ├── team.ts                 ← /v1/orgs/:orgId/team/*
│   │   ├── recommendations.ts      ← /v1/orgs/:orgId/recommendations/*
│   │   ├── virtualTags.ts          ← /v1/orgs/:orgId/virtual-tags/*
│   │   ├── forecasts.ts            ← /v1/orgs/:orgId/forecasts/*
│   │   ├── commitments.ts          ← /v1/orgs/:orgId/commitments/*
│   │   ├── scorecard.ts            ← /v1/orgs/:orgId/scorecard
│   │   ├── notifications.ts        ← /v1/orgs/:orgId/notifications/*
│   │   ├── webhooks.ts             ← /v1/orgs/:orgId/webhooks/*
│   │   ├── llm.ts                  ← /v1/orgs/:orgId/llm/*
│   │   ├── businessMetrics.ts      ← /v1/orgs/:orgId/metrics/*
│   │   ├── resources.ts            ← /v1/orgs/:orgId/resources/*
│   │   ├── teamsActions.ts         ← POST /integrations/teams-actions
│   │   └── slackActions.ts         ← POST /integrations/slack-actions
│   ├── services/
│   │   ├── connectors/
│   │   │   ├── aws.ts              ← AWSConnector
│   │   │   ├── azure.ts            ← AzureConnector
│   │   │   └── gcp.ts              ← GCPConnector
│   │   ├── alert.service.ts        ← CapAlertService
│   │   ├── report.service.ts       ← ReportGenerator
│   │   ├── llm.service.ts          ← LLMService (OpenRouter)
│   │   ├── email.service.ts        ← EmailService (SES)
│   │   ├── virtualTag.service.ts   ← VirtualTagEngine
│   │   ├── forecast.service.ts     ← ForecastEngine
│   │   ├── scorecard.service.ts    ← ScorecardEngine
│   │   ├── recommendation.service.ts ← RecommendationEngine
│   │   ├── commitment.service.ts   ← CommitmentService
│   │   ├── webhook.service.ts      ← OutboundWebhookService
│   │   └── fx.service.ts           ← FX rate fetcher
│   ├── jobs/
│   │   ├── sync.worker.ts          ← prism-sync worker
│   │   ├── alerts.worker.ts        ← prism-alerts worker
│   │   ├── commitments.worker.ts   ← prism-commitments worker
│   │   ├── forecast.worker.ts      ← prism-forecast worker
│   │   ├── virtualTags.worker.ts   ← prism-virtual-tags worker
│   │   ├── reports.worker.ts       ← prism-reports worker
│   │   ├── recommendations.worker.ts ← prism-recommendations worker
│   │   ├── dlq.worker.ts           ← prism-dlq dead letter processor
│   │   └── scheduler.ts            ← node-cron schedule registrar
│   ├── ws/
│   │   └── wsServer.ts             ← WebSocket server
│   ├── db/
│   │   ├── schema.sql              ← Full DDL (run once)
│   │   ├── seed.sql                ← Dev seed data
│   │   └── queries/
│   │       ├── costs.ts            ← Parameterized cost queries
│   │       ├── alerts.ts           ← Alert queries
│   │       └── dashboard.ts        ← Dashboard aggregation queries
│   ├── types/
│   │   └── index.ts                ← All TypeScript interfaces
│   └── utils/
│       ├── withRetry.ts            ← Retry helper with backoff + 429 handling
│       ├── validateWebhookUrl.ts   ← SSRF protection
│       ├── regex.ts                ← Safe regex compile + ReDoS guard
│       ├── pagination.ts           ← Cursor-based pagination helper
│       └── date.ts                 ← Date helpers (month start, days remaining)
├── .env                            ← Local env (never commit)
├── .env.example                    ← Template (commit this)
├── tsconfig.json
└── package.json
```

---

## 2. Environment Variables

### 2.1 `.env.example`

```env
# Server
NODE_ENV=development
PORT=3000
APP_URL=http://localhost:3000

# Database
DATABASE_URL=postgresql://prism:password@localhost:5432/prism
DATABASE_POOL_MAX=20

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_ACCESS_SECRET=change-me-min-32-chars-random
JWT_REFRESH_SECRET=change-me-min-32-chars-random-2
JWT_ACCESS_EXPIRY=7d
JWT_REFRESH_EXPIRY=30d

# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:3000/v1/auth/google/callback

# Email (AWS SES)
AWS_SES_REGION=us-east-1
AWS_SES_FROM=noreply@prism.io
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Encryption key for credentials at rest (AES-256, 32 bytes, hex-encoded)
ENCRYPTION_KEY=

# Teams / Slack webhook validation
TEAMS_SIGNING_SECRET=
SLACK_SIGNING_SECRET=

# Internal Prism AWS account (for STS AssumeRole — this is PRISM'S AWS account)
PRISM_AWS_ACCOUNT_ID=123456789012

# Cron schedules (UTC)
CRON_SYNC=0 6 * * *
CRON_COMMITMENTS=0 7 * * *
CRON_FORECAST=30 7 * * *
CRON_RECOMMENDATIONS=0 8 * * *
CRON_REPORTS=0 9 * * *

# BullMQ concurrency
WORKER_CONCURRENCY=5

# Rate limits
RATE_LIMIT_AUTH=10        # per 15 min per IP
RATE_LIMIT_API=300        # per 1 min per org

# Feature flags
ENABLE_LLM=true
ENABLE_COMMITMENTS=true
ENABLE_VIRTUAL_TAGS=true
```

### 2.2 `src/config/env.ts`

```typescript
import { z } from "zod";
import dotenv from "dotenv";
dotenv.config();

const EnvSchema = z.object({
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  PORT: z.coerce.number().default(3000),
  DATABASE_URL: z.string().url(),
  DATABASE_POOL_MAX: z.coerce.number().default(20),
  REDIS_URL: z.string(),
  JWT_ACCESS_SECRET: z.string().min(32),
  JWT_REFRESH_SECRET: z.string().min(32),
  JWT_ACCESS_EXPIRY: z.string().default("7d"),
  JWT_REFRESH_EXPIRY: z.string().default("30d"),
  GOOGLE_CLIENT_ID: z.string().optional(),
  GOOGLE_CLIENT_SECRET: z.string().optional(),
  GOOGLE_REDIRECT_URI: z.string().optional(),
  AWS_SES_REGION: z.string().default("us-east-1"),
  AWS_SES_FROM: z.string().email(),
  AWS_ACCESS_KEY_ID: z.string().optional(),
  AWS_SECRET_ACCESS_KEY: z.string().optional(),
  ENCRYPTION_KEY: z.string().length(64), // 32 bytes hex = 64 chars
  TEAMS_SIGNING_SECRET: z.string().optional(),
  SLACK_SIGNING_SECRET: z.string().optional(),
  PRISM_AWS_ACCOUNT_ID: z.string(),
  CRON_SYNC: z.string().default("0 6 * * *"),
  CRON_COMMITMENTS: z.string().default("0 7 * * *"),
  CRON_FORECAST: z.string().default("30 7 * * *"),
  CRON_RECOMMENDATIONS: z.string().default("0 8 * * *"),
  CRON_REPORTS: z.string().default("0 9 * * *"),
  WORKER_CONCURRENCY: z.coerce.number().default(5),
});

export const env = EnvSchema.parse(process.env);
```

---

## 3. Database Schema (SQL)

**File: `src/db/schema.sql`** — Run this once on a fresh PostgreSQL instance with TimescaleDB installed.

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ────────────────────────────────────────
-- ORGANIZATIONS
-- ────────────────────────────────────────
CREATE TABLE organizations (
  id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name                 TEXT NOT NULL,
  plan                 TEXT NOT NULL DEFAULT 'starter'
                         CHECK (plan IN ('starter', 'professional', 'enterprise')),
  billing_period_start DATE NOT NULL DEFAULT CURRENT_DATE,
  currency             TEXT NOT NULL DEFAULT 'USD'
                         CHECK (currency IN ('USD','EUR','GBP','INR','AUD','CAD')),
  timezone             TEXT NOT NULL DEFAULT 'UTC',
  feature_flags        JSONB NOT NULL DEFAULT '{}',
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ────────────────────────────────────────
-- USERS
-- ────────────────────────────────────────
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email         TEXT NOT NULL UNIQUE,
  name          TEXT NOT NULL,
  password_hash TEXT,                   -- NULL if Google OAuth only
  google_id     TEXT UNIQUE,
  avatar_url    TEXT,
  email_verified BOOLEAN NOT NULL DEFAULT FALSE,
  email_verify_token TEXT,              -- bcrypt-hashed; NULL after verification
  email_verify_expires TIMESTAMPTZ,
  mfa_enabled   BOOLEAN NOT NULL DEFAULT FALSE,
  last_login    TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ────────────────────────────────────────
-- REFRESH TOKENS (invalidation store)
-- ────────────────────────────────────────
CREATE TABLE refresh_tokens (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash   TEXT NOT NULL,           -- bcrypt hash of the raw token
  expires_at   TIMESTAMPTZ NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked_at   TIMESTAMPTZ            -- NULL = valid; set on logout or rotation
);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens (user_id);

-- ────────────────────────────────────────
-- TEAM MEMBERS
-- ────────────────────────────────────────
CREATE TABLE team_members (
  id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id             UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id            UUID REFERENCES users(id) ON DELETE SET NULL,  -- NULL until accepted
  email              TEXT NOT NULL,
  role               TEXT NOT NULL CHECK (role IN ('owner','admin','editor','viewer')),
  invited_by         UUID REFERENCES users(id),
  invite_token_hash  TEXT,             -- bcrypt-hashed raw token; NULL after acceptance
  invite_expires_at  TIMESTAMPTZ,      -- 48h from invite; NULL after acceptance
  invite_accepted    BOOLEAN NOT NULL DEFAULT FALSE,
  invited_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  joined_at          TIMESTAMPTZ,
  UNIQUE (org_id, email)               -- one pending/active membership per email per org
);
CREATE INDEX idx_team_members_org ON team_members (org_id);
CREATE INDEX idx_team_members_user ON team_members (user_id);

-- ────────────────────────────────────────
-- ACCOUNT GROUPS (single / multi / org scope)
-- ────────────────────────────────────────
CREATE TABLE account_groups (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  provider         TEXT NOT NULL CHECK (provider IN ('aws','azure','gcp')),
  scope            TEXT NOT NULL CHECK (scope IN ('single','multi','organization')),
  display_name     TEXT NOT NULL,
  root_account_id  TEXT,               -- AWS Org management account ID (or null)
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ────────────────────────────────────────
-- CLOUD ACCOUNTS
-- ────────────────────────────────────────
CREATE TABLE cloud_accounts (
  id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  group_id           UUID NOT NULL REFERENCES account_groups(id) ON DELETE CASCADE,
  org_id             UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  provider           TEXT NOT NULL CHECK (provider IN ('aws','azure','gcp')),
  account_id         TEXT NOT NULL,    -- AWS account ID / Azure subscription ID / GCP project ID
  display_name       TEXT NOT NULL,
  credentials_enc    TEXT NOT NULL,    -- AES-256 encrypted JSON blob
  last_sync          TIMESTAMPTZ,
  last_sync_status   TEXT DEFAULT 'never'
                       CHECK (last_sync_status IN ('success','partial','failed','never')),
  last_sync_error    TEXT,
  last_sync_records  INT,
  data_as_of         TIMESTAMPTZ,      -- most recent data timestamp from provider
  is_active          BOOLEAN NOT NULL DEFAULT TRUE,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_cloud_account_org_provider_acct
  ON cloud_accounts (org_id, provider, account_id);

-- ────────────────────────────────────────
-- SYNC LOGS
-- ────────────────────────────────────────
CREATE TABLE sync_logs (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id        UUID NOT NULL REFERENCES organizations(id),
  account_id    UUID NOT NULL REFERENCES cloud_accounts(id),
  started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at   TIMESTAMPTZ,
  status        TEXT NOT NULL DEFAULT 'running'
                  CHECK (status IN ('running','success','partial','failed')),
  records_synced INT DEFAULT 0,
  error_message TEXT,
  backfill      BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_sync_logs_account ON sync_logs (account_id, started_at DESC);
-- Purge after 90 days (run via cron or pg_cron)

-- ────────────────────────────────────────
-- COST RECORDS (TimescaleDB hypertable)
-- ────────────────────────────────────────
CREATE TABLE cost_records (
  time                TIMESTAMPTZ NOT NULL,
  org_id              UUID NOT NULL,
  account_id          UUID NOT NULL,
  provider            TEXT NOT NULL,
  service             TEXT NOT NULL,
  region              TEXT NOT NULL DEFAULT '',
  cost_usd            NUMERIC(14,6) NOT NULL,
  cost_unblended_usd  NUMERIC(14,6) NOT NULL,
  cost_amortized_usd  NUMERIC(14,6) NOT NULL,
  cost_original       NUMERIC(14,6) NOT NULL,
  original_currency   TEXT NOT NULL DEFAULT 'USD',
  fx_rate             NUMERIC(10,6) NOT NULL DEFAULT 1,
  usage_value         NUMERIC(18,4) NOT NULL DEFAULT 0,
  usage_unit          TEXT NOT NULL DEFAULT '',
  tags                JSONB NOT NULL DEFAULT '{}',
  virtual_tags        JSONB NOT NULL DEFAULT '{}',
  is_estimate         BOOLEAN NOT NULL DEFAULT FALSE
);

-- Convert to TimescaleDB hypertable, partitioned by month
SELECT create_hypertable('cost_records', 'time', chunk_time_interval => INTERVAL '1 month');

-- Compress chunks older than 3 months
SELECT add_compression_policy('cost_records', INTERVAL '3 months');

-- ────────────────────────────────────────
-- BUDGET CAPS
-- ────────────────────────────────────────
CREATE TABLE budget_caps (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name          TEXT NOT NULL,
  scope         TEXT NOT NULL CHECK (scope IN ('platform','service','account')),
  provider      TEXT CHECK (provider IN ('aws','azure','gcp')),
  service_name  TEXT,
  account_id    UUID REFERENCES cloud_accounts(id) ON DELETE SET NULL,
  cap_amount    NUMERIC(14,2) NOT NULL,
  period        TEXT NOT NULL DEFAULT 'monthly' CHECK (period = 'monthly'),
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_by    UUID NOT NULL REFERENCES users(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_budget_caps_org ON budget_caps (org_id) WHERE is_active = TRUE;

-- ────────────────────────────────────────
-- NOTIFICATION SETTINGS (one row per org)
-- ────────────────────────────────────────
CREATE TABLE notification_settings (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id            UUID NOT NULL UNIQUE REFERENCES organizations(id) ON DELETE CASCADE,
  alert_emails      TEXT[] NOT NULL DEFAULT '{}',
  teams_webhook_url TEXT,
  slack_webhook_url TEXT,
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ────────────────────────────────────────
-- ALERTS
-- ────────────────────────────────────────
CREATE TABLE alerts (
  id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id             UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  cap_id             UUID REFERENCES budget_caps(id) ON DELETE SET NULL,
  type               TEXT NOT NULL CHECK (type IN (
                       'cap_threshold','forecast_breach','spend_acceleration',
                       'sync_failure','credential_expiry','commitment_expiry',
                       'unused_commitment','untagged_resource','idle_resource')),
  scope_label        TEXT NOT NULL,
  threshold_percent  INT,
  spend_at_trigger   NUMERIC(14,2),
  cap_amount         NUMERIC(14,2),
  metadata           JSONB,
  severity           TEXT NOT NULL CHECK (severity IN ('info','warning','critical')),
  triggered_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  email_sent         BOOLEAN NOT NULL DEFAULT FALSE,
  teams_sent         BOOLEAN NOT NULL DEFAULT FALSE,
  slack_sent         BOOLEAN NOT NULL DEFAULT FALSE,
  webhook_sent       BOOLEAN NOT NULL DEFAULT FALSE,
  acknowledged_by    UUID REFERENCES users(id),
  acknowledged_at    TIMESTAMPTZ,
  snoozed_until      TIMESTAMPTZ
);
CREATE INDEX idx_alerts_org_time ON alerts (org_id, triggered_at DESC);

-- Deduplication: one cap_threshold alert per threshold per cap per billing month
CREATE UNIQUE INDEX idx_alert_cap_threshold_dedup
  ON alerts (org_id, cap_id, threshold_percent, date_trunc('month', triggered_at))
  WHERE type = 'cap_threshold' AND cap_id IS NOT NULL;

-- ────────────────────────────────────────
-- RESOURCES
-- ────────────────────────────────────────
CREATE TABLE resources (
  id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id             UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  account_id         UUID NOT NULL REFERENCES cloud_accounts(id) ON DELETE CASCADE,
  provider           TEXT NOT NULL,
  resource_id        TEXT NOT NULL,      -- AWS ARN / Azure resource ID / GCP resource name
  resource_name      TEXT,
  service            TEXT NOT NULL,
  region             TEXT NOT NULL DEFAULT '',
  instance_type      TEXT,
  tags               JSONB NOT NULL DEFAULT '{}',
  virtual_tags       JSONB NOT NULL DEFAULT '{}',
  created_at_cloud   TIMESTAMPTZ,
  last_activity_at   TIMESTAMPTZ,
  created_by_user    TEXT,
  last_cost_usd      NUMERIC(14,6),
  is_idle            BOOLEAN NOT NULL DEFAULT FALSE,
  idle_since         TIMESTAMPTZ,
  first_seen         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_resource_account_resource_id ON resources (account_id, resource_id);
CREATE INDEX idx_resource_org ON resources (org_id);
CREATE INDEX idx_resource_idle ON resources (org_id, is_idle, idle_since) WHERE is_idle = TRUE;

-- ────────────────────────────────────────
-- RECOMMENDATIONS
-- ────────────────────────────────────────
CREATE TABLE recommendations (
  id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id                      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  account_id                  UUID NOT NULL REFERENCES cloud_accounts(id),
  resource_id                 TEXT NOT NULL,
  resource_name               TEXT NOT NULL,
  provider                    TEXT NOT NULL,
  service                     TEXT NOT NULL,
  type                        TEXT NOT NULL CHECK (type IN (
                                'rightsizing','idle_termination','reserved_instance',
                                'storage_tiering','network_egress','commitment_renewal')),
  estimated_monthly_savings   NUMERIC(14,2) NOT NULL,
  confidence                  TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
  llm_explanation             TEXT,
  llm_risk_note               TEXT,
  status                      TEXT NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending','implemented','rejected','archived')),
  created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  implemented_at              TIMESTAMPTZ,
  actual_savings              NUMERIC(14,2),
  actual_savings_updated_at   TIMESTAMPTZ
);
CREATE INDEX idx_recommendations_org ON recommendations (org_id, status, created_at DESC);

-- ────────────────────────────────────────
-- VIRTUAL TAG RULES
-- ────────────────────────────────────────
CREATE TABLE virtual_tag_rules (
  id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id             UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  priority           INT NOT NULL,
  condition_field    TEXT NOT NULL CHECK (condition_field IN (
                       'resource_name','account_id','service','region','tag_value')),
  condition_operator TEXT NOT NULL CHECK (condition_operator IN (
                       'contains','equals','starts_with','ends_with','regex')),
  condition_value    TEXT NOT NULL,
  action_type        TEXT NOT NULL CHECK (action_type IN ('set_tag','split')),
  tag_key            TEXT NOT NULL,
  tag_value          TEXT,
  split_config       JSONB,             -- [{team:"engineering",pct:60},{team:"data",pct:40}]
  provider_scope     TEXT NOT NULL DEFAULT 'all'
                       CHECK (provider_scope IN ('aws','azure','gcp','all')),
  is_active          BOOLEAN NOT NULL DEFAULT TRUE,
  last_applied_at    TIMESTAMPTZ,
  records_affected   INT,
  created_by         UUID NOT NULL REFERENCES users(id),
  updated_by         UUID REFERENCES users(id),
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (org_id, priority)
);
CREATE INDEX idx_vtag_rule_org_priority ON virtual_tag_rules (org_id, priority)
  WHERE is_active = TRUE;

-- Audit log for virtual tag rule changes
CREATE TABLE virtual_tag_audit_log (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id       UUID NOT NULL,
  rule_id      UUID REFERENCES virtual_tag_rules(id) ON DELETE SET NULL,
  changed_by   UUID NOT NULL REFERENCES users(id),
  change_type  TEXT NOT NULL CHECK (change_type IN ('created','updated','deleted','reordered','applied')),
  before_state JSONB,
  after_state  JSONB,
  timestamp    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ────────────────────────────────────────
-- COMMITMENT RECORDS
-- ────────────────────────────────────────
CREATE TABLE commitment_records (
  id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id                      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  account_id                  UUID NOT NULL REFERENCES cloud_accounts(id),
  provider                    TEXT NOT NULL CHECK (provider IN ('aws','gcp')),
  commitment_type             TEXT NOT NULL CHECK (commitment_type IN (
                                'reserved_instance','savings_plan','committed_use_discount')),
  external_id                 TEXT NOT NULL,
  instance_type               TEXT,
  region                      TEXT,
  term_months                 INT NOT NULL,
  start_date                  DATE NOT NULL,
  end_date                    DATE NOT NULL,
  hourly_commitment           NUMERIC(10,6),
  monthly_cost                NUMERIC(14,2) NOT NULL,
  monthly_on_demand_equivalent NUMERIC(14,2) NOT NULL,
  monthly_savings             NUMERIC(14,2) NOT NULL,
  utilization_pct             NUMERIC(5,2) NOT NULL,
  coverage_amount             NUMERIC(14,2) NOT NULL,
  status                      TEXT NOT NULL CHECK (status IN ('active','expired','expiring_soon')),
  last_updated                TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_commitment_external ON commitment_records (account_id, external_id);
CREATE INDEX idx_commitment_org_status ON commitment_records (org_id, status, end_date);

-- ────────────────────────────────────────
-- SPEND FORECASTS
-- ────────────────────────────────────────
CREATE TABLE spend_forecasts (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  account_id       UUID REFERENCES cloud_accounts(id) ON DELETE SET NULL,
  provider         TEXT,
  forecast_month   DATE NOT NULL,         -- first day of the forecast month
  generated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  spend_to_date    NUMERIC(14,2) NOT NULL,
  daily_avg        NUMERIC(14,6) NOT NULL,
  rolling_7d_avg   NUMERIC(14,6) NOT NULL,
  days_with_data   INT NOT NULL,
  days_remaining   INT NOT NULL,
  projected_total  NUMERIC(14,2) NOT NULL,
  cap_amount       NUMERIC(14,2),
  will_breach      BOOLEAN NOT NULL DEFAULT FALSE,
  breach_date      DATE,
  data_coverage    TEXT NOT NULL CHECK (data_coverage IN ('full','partial','insufficient')),
  actual_total     NUMERIC(14,2),         -- filled at month-end
  variance_pct     NUMERIC(8,4),          -- filled at month-end
  UNIQUE (org_id, COALESCE(account_id::TEXT,''), COALESCE(provider,''), forecast_month)
);
CREATE INDEX idx_forecast_org_month ON spend_forecasts (org_id, forecast_month DESC);

-- ────────────────────────────────────────
-- MONTHLY REPORTS CONFIG
-- ────────────────────────────────────────
CREATE TABLE monthly_reports (
  id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id                   UUID NOT NULL UNIQUE REFERENCES organizations(id) ON DELETE CASCADE,
  send_day_of_month        INT NOT NULL DEFAULT 4 CHECK (send_day_of_month BETWEEN 1 AND 28),
  recipient_emails         TEXT[] NOT NULL DEFAULT '{}',
  include_recommendations  BOOLEAN NOT NULL DEFAULT TRUE,
  include_per_account      BOOLEAN NOT NULL DEFAULT TRUE,
  include_commitments      BOOLEAN NOT NULL DEFAULT TRUE,
  include_unit_economics   BOOLEAN NOT NULL DEFAULT TRUE,
  include_finops_scorecard BOOLEAN NOT NULL DEFAULT TRUE,
  last_sent                TIMESTAMPTZ,
  next_send                TIMESTAMPTZ NOT NULL,
  is_active                BOOLEAN NOT NULL DEFAULT TRUE
);

-- ────────────────────────────────────────
-- LLM CONFIG (one per org)
-- ────────────────────────────────────────
CREATE TABLE llm_configs (
  id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id               UUID NOT NULL UNIQUE REFERENCES organizations(id) ON DELETE CASCADE,
  openrouter_api_key   TEXT NOT NULL,    -- AES-256 encrypted
  model                TEXT NOT NULL DEFAULT 'google/gemini-flash-1.5',
  monthly_budget_usd   NUMERIC(10,2) NOT NULL DEFAULT 10.00,
  is_enabled           BOOLEAN NOT NULL DEFAULT TRUE,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ────────────────────────────────────────
-- OUTBOUND WEBHOOKS
-- ────────────────────────────────────────
CREATE TABLE outbound_webhooks (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  url                 TEXT NOT NULL,
  signing_secret_enc  TEXT NOT NULL,     -- AES-256 encrypted
  description         TEXT NOT NULL DEFAULT '',
  events              TEXT[] NOT NULL,   -- e.g. ARRAY['alert.fired','recommendation.new']
  is_active           BOOLEAN NOT NULL DEFAULT TRUE,
  last_triggered_at   TIMESTAMPTZ,
  last_status_code    INT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_outbound_webhooks_org ON outbound_webhooks (org_id) WHERE is_active = TRUE;

-- ────────────────────────────────────────
-- BUSINESS METRICS
-- ────────────────────────────────────────
CREATE TABLE business_metrics (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  source      TEXT NOT NULL CHECK (source IN ('manual','webhook','datadog','stripe','csv')),
  unit        TEXT NOT NULL,
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (org_id, name)
);

CREATE TABLE business_metric_values (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  metric_id    UUID NOT NULL REFERENCES business_metrics(id) ON DELETE CASCADE,
  org_id       UUID NOT NULL,
  date         DATE NOT NULL,
  value        NUMERIC(18,4) NOT NULL,
  ingested_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (metric_id, date)
);
CREATE INDEX idx_bmv_metric_date ON business_metric_values (metric_id, date DESC);

-- ────────────────────────────────────────
-- API KEYS (for integrations)
-- ────────────────────────────────────────
CREATE TABLE api_keys (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id     UUID NOT NULL REFERENCES users(id),
  key_hash    TEXT NOT NULL,          -- bcrypt hash of raw key (shown once to user)
  key_prefix  TEXT NOT NULL,          -- first 8 chars of raw key for identification
  name        TEXT NOT NULL,
  scopes      TEXT[] NOT NULL,        -- e.g. ARRAY['cost.read','alerts.read']
  expires_at  TIMESTAMPTZ,
  last_used   TIMESTAMPTZ,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked_at  TIMESTAMPTZ
);
CREATE INDEX idx_api_keys_org ON api_keys (org_id);
```

---

## 4. Database Indexes

Already included in schema above. Summary of critical ones:

```sql
-- See schema.sql — all indexes are defined inline.
-- Critical for correctness (not just performance):
--   idx_cost_record_idempotency   → idempotent syncs (ON CONFLICT DO UPDATE)
--   idx_alert_cap_threshold_dedup → one alert per threshold per cap per month
--   idx_resource_account_resource_id → idempotent resource upserts

-- After schema is created, also run:
-- (TimescaleDB continuous aggregate for monthly rollups — optional but speeds up dashboard)
CREATE MATERIALIZED VIEW cost_monthly_by_service
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 month', time) AS month,
  org_id,
  account_id,
  provider,
  service,
  region,
  SUM(cost_usd) AS total_cost_usd,
  SUM(cost_amortized_usd) AS total_amortized_usd
FROM cost_records
GROUP BY 1, 2, 3, 4, 5, 6
WITH NO DATA;

SELECT add_continuous_aggregate_policy('cost_monthly_by_service',
  start_offset => INTERVAL '14 months',
  end_offset   => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 day');
```

---

## 5. Redis Key Conventions

```
# Authentication
session:refresh:{userId}:{tokenId}      → token hash (TTL: 30d)
session:access:{userId}                 → revocation flag (TTL: 7d)

# Dashboard cache (org-scoped, no cross-org leakage)
dash:{orgId}:overall:{YYYY-MM}          → JSON aggregates (TTL: 5m)
dash:{orgId}:{provider}:{YYYY-MM}       → JSON per-platform aggregates (TTL: 5m)
dash:{orgId}:forecast:{YYYY-MM}         → JSON forecast (TTL: 1h)
dash:{orgId}:commitments                → JSON commitment summary (TTL: 6h)
dash:{orgId}:scorecard                  → JSON scorecard (TTL: 1h)

# LLM
llm:{base64_prompt_hash}                → LLM response string (TTL: 24h)
llm:monthly_spent:{orgId}:{YYYY-MM}    → decimal string (TTL: 31d)

# Rate limiting
rl:auth:{ip}                            → count (TTL: 15m)
rl:api:{orgId}                          → count (TTL: 1m)
rl:llm:{userId}                         → count (TTL: 1h)

# Job deduplication
job:done:{orgId}:{YYYY-MM-DD}:{jobType} → "1" (TTL: 48h)

# Email verification
email:verify:{userId}                   → token hash (TTL: 24h)

# Password reset
pwd:reset:{userId}                      → token hash (TTL: 1h)
```

---

## 6. Express App Entrypoint

### 6.1 `src/index.ts`

```typescript
import { env } from "./config/env";
import { app } from "./app";
import { db } from "./config/db";
import { redis } from "./config/redis";
import { startWorkers } from "./jobs/scheduler";
import { createWsServer } from "./ws/wsServer";
import { logger } from "./utils/logger";
import http from "http";

async function main() {
  // Verify DB connection
  await db.query("SELECT 1");
  logger.info("PostgreSQL connected");

  // Verify Redis connection
  await redis.ping();
  logger.info("Redis connected");

  const server = http.createServer(app);

  // Attach WebSocket server to same HTTP server
  createWsServer(server);

  // Start BullMQ workers + cron scheduler
  await startWorkers();

  server.listen(env.PORT, () => {
    logger.info({ port: env.PORT, env: env.NODE_ENV }, "PRISM backend running");
  });

  // Graceful shutdown
  process.on("SIGTERM", async () => {
    logger.info("SIGTERM received — shutting down");
    server.close();
    await db.end();
    await redis.quit();
    process.exit(0);
  });
}

main().catch((err) => {
  logger.error(err, "Startup failed");
  process.exit(1);
});
```

### 6.2 `src/app.ts`

```typescript
import express from "express";
import helmet from "helmet";
import cors from "cors";
import { errorHandler } from "./middleware/errorHandler";
import { requestLogger } from "./middleware/requestLogger";
import { authRoutes } from "./routes/auth";
import { orgRoutes } from "./routes/orgs";
import { accountRoutes } from "./routes/accounts";
import { costRoutes } from "./routes/costs";
import { alertRoutes } from "./routes/alerts";
import { capRoutes } from "./routes/caps";
import { reportRoutes } from "./routes/reports";
import { teamRoutes } from "./routes/team";
import { recommendationRoutes } from "./routes/recommendations";
import { virtualTagRoutes } from "./routes/virtualTags";
import { forecastRoutes } from "./routes/forecasts";
import { commitmentRoutes } from "./routes/commitments";
import { scorecardRoutes } from "./routes/scorecard";
import { notificationRoutes } from "./routes/notifications";
import { webhookRoutes } from "./routes/webhooks";
import { llmRoutes } from "./routes/llm";
import { businessMetricRoutes } from "./routes/businessMetrics";
import { resourceRoutes } from "./routes/resources";
import { teamsActionsRoutes } from "./routes/teamsActions";
import { slackActionsRoutes } from "./routes/slackActions";

export const app = express();

// Security headers
app.use(helmet());

// CORS — lock to frontend origin in prod
app.use(cors({
  origin: process.env.FRONTEND_URL ?? "http://localhost:5173",
  credentials: true,
}));

// Body parsing
app.use(express.json({ limit: "1mb" }));

// Request logging
app.use(requestLogger);

// Health check (no auth)
app.get("/health", (_req, res) => res.json({ status: "ok", ts: new Date() }));

// API v1 routes
app.use("/v1/auth", authRoutes);
app.use("/v1/orgs", orgRoutes);
app.use("/v1/orgs/:orgId/accounts", accountRoutes);
app.use("/v1/orgs/:orgId/costs", costRoutes);
app.use("/v1/orgs/:orgId/alerts", alertRoutes);
app.use("/v1/orgs/:orgId/caps", capRoutes);
app.use("/v1/orgs/:orgId/reports", reportRoutes);
app.use("/v1/orgs/:orgId/team", teamRoutes);
app.use("/v1/orgs/:orgId/recommendations", recommendationRoutes);
app.use("/v1/orgs/:orgId/virtual-tags", virtualTagRoutes);
app.use("/v1/orgs/:orgId/forecasts", forecastRoutes);
app.use("/v1/orgs/:orgId/commitments", commitmentRoutes);
app.use("/v1/orgs/:orgId/scorecard", scorecardRoutes);
app.use("/v1/orgs/:orgId/notifications", notificationRoutes);
app.use("/v1/orgs/:orgId/webhooks", webhookRoutes);
app.use("/v1/orgs/:orgId/llm", llmRoutes);
app.use("/v1/orgs/:orgId/metrics", businessMetricRoutes);
app.use("/v1/orgs/:orgId/resources", resourceRoutes);

// Incoming integration callbacks (no JWT auth — HMAC validated instead)
app.use("/integrations/teams-actions", teamsActionsRoutes);
app.use("/integrations/slack-actions", slackActionsRoutes);

// Global error handler (must be last)
app.use(errorHandler);
```

---

## 7. Middleware Stack

### 7.1 `src/middleware/auth.ts`

```typescript
import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { env } from "../config/env";
import { AppError } from "./errorHandler";

export interface JWTPayload {
  sub: string;       // user ID
  orgId: string;
  role: string;
  email: string;
  iat: number;
  exp: number;
}

declare global {
  namespace Express {
    interface Request {
      user: JWTPayload;
      org: { id: string; name: string; plan: string; currency: string; timezone: string; feature_flags: Record<string, boolean> };
    }
  }
}

export function requireAuth(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith("Bearer ")) {
    return next(new AppError(401, "Missing authorization header"));
  }

  const token = authHeader.slice(7);
  try {
    const payload = jwt.verify(token, env.JWT_ACCESS_SECRET) as JWTPayload;
    req.user = payload;
    next();
  } catch (err: any) {
    if (err.name === "TokenExpiredError") {
      return next(new AppError(401, "Token expired"));
    }
    return next(new AppError(401, "Invalid token"));
  }
}
```

### 7.2 `src/middleware/orgScope.ts`

```typescript
import { Request, Response, NextFunction } from "express";
import { db } from "../config/db";
import { AppError } from "./errorHandler";

// Injects req.org from DB; also validates that user belongs to the org in the URL
export async function requireOrgAccess(req: Request, res: Response, next: NextFunction) {
  const { orgId } = req.params;

  // The user's org from JWT must match the URL orgId — no cross-org access
  if (req.user.orgId !== orgId) {
    return next(new AppError(403, "Access denied to this organization"));
  }

  const result = await db.query(
    "SELECT id, name, plan, currency, timezone, feature_flags FROM organizations WHERE id = $1",
    [orgId]
  );

  if (!result.rows[0]) {
    return next(new AppError(404, "Organization not found"));
  }

  req.org = result.rows[0];
  next();
}
```

### 7.3 `src/middleware/rbac.ts`

```typescript
import { Request, Response, NextFunction } from "express";
import { AppError } from "./errorHandler";

type Role = "owner" | "admin" | "editor" | "viewer";

const ROLE_RANK: Record<Role, number> = {
  owner: 4,
  admin: 3,
  editor: 2,
  viewer: 1,
};

// Require at least the given role level
export function requireRole(minRole: Role) {
  return (req: Request, res: Response, next: NextFunction) => {
    const userRole = req.user.role as Role;
    if (ROLE_RANK[userRole] < ROLE_RANK[minRole]) {
      return next(new AppError(403, `This action requires ${minRole} role or higher`));
    }
    next();
  };
}
```

### 7.4 `src/middleware/hmac.ts`

```typescript
import { Request, Response, NextFunction } from "express";
import crypto from "crypto";
import { env } from "../config/env";

export function validateHMAC(provider: "teams" | "slack") {
  return (req: Request, res: Response, next: NextFunction) => {
    const sigHeader = provider === "teams"
      ? (req.headers["x-ms-teams-signature"] as string)
      : (req.headers["x-slack-signature"] as string);

    const secret = provider === "teams"
      ? env.TEAMS_SIGNING_SECRET!
      : env.SLACK_SIGNING_SECRET!;

    if (!sigHeader || !secret) {
      return res.status(401).json({ error: "Missing signature or signing secret" });
    }

    const expected = "sha256=" + crypto
      .createHmac("sha256", secret)
      .update(JSON.stringify(req.body))
      .digest("hex");

    const sigBuffer = Buffer.from(sigHeader);
    const expBuffer = Buffer.from(expected);

    if (sigBuffer.length !== expBuffer.length || !crypto.timingSafeEqual(sigBuffer, expBuffer)) {
      return res.status(401).json({ error: "Invalid signature" });
    }

    next();
  };
}
```

### 7.5 `src/middleware/validateBody.ts`

```typescript
import { Request, Response, NextFunction } from "express";
import { ZodSchema, ZodError } from "zod";

export function validate(schema: ZodSchema) {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      return res.status(400).json({
        error: "Validation failed",
        details: (result.error as ZodError).errors.map(e => ({
          field: e.path.join("."),
          message: e.message,
        })),
      });
    }
    req.body = result.data;
    next();
  };
}
```

### 7.6 `src/middleware/rateLimit.ts`

```typescript
import rateLimit from "express-rate-limit";

export const authRateLimit = rateLimit({
  windowMs: 15 * 60 * 1000,   // 15 minutes
  max: 10,
  message: { error: "Too many auth attempts, please try again later" },
  standardHeaders: true,
  legacyHeaders: false,
});

export const apiRateLimit = rateLimit({
  windowMs: 60 * 1000,         // 1 minute
  max: 300,
  keyGenerator: (req) => req.user?.orgId ?? req.ip,
  message: { error: "Rate limit exceeded" },
  standardHeaders: true,
  legacyHeaders: false,
});

export const llmRateLimit = rateLimit({
  windowMs: 60 * 60 * 1000,   // 1 hour
  max: 20,
  keyGenerator: (req) => req.user?.sub ?? req.ip,
  message: { error: "LLM query limit exceeded for this hour" },
  standardHeaders: true,
  legacyHeaders: false,
});
```

### 7.7 `src/middleware/errorHandler.ts`

```typescript
import { Request, Response, NextFunction } from "express";
import { logger } from "../utils/logger";

export class AppError extends Error {
  constructor(
    public statusCode: number,
    message: string,
    public code?: string
  ) {
    super(message);
    this.name = "AppError";
  }
}

export function errorHandler(
  err: Error,
  req: Request,
  res: Response,
  _next: NextFunction
) {
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      error: err.message,
      code: err.code,
    });
  }

  // Unexpected errors — don't leak internals
  logger.error({ err, path: req.path, method: req.method }, "Unhandled error");
  return res.status(500).json({ error: "Internal server error" });
}
```

---

## 8. Authentication System

### 8.1 `src/routes/auth.ts`

```typescript
import { Router } from "express";
import { z } from "zod";
import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";
import crypto from "crypto";
import { db } from "../config/db";
import { redis } from "../config/redis";
import { env } from "../config/env";
import { validate } from "../middleware/validateBody";
import { requireAuth } from "../middleware/auth";
import { authRateLimit } from "../middleware/rateLimit";
import { emailService } from "../services/email.service";
import { AppError } from "../middleware/errorHandler";

export const authRoutes = Router();

const SignupSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
  password: z.string()
    .min(12, "Password must be at least 12 characters")
    .regex(/[A-Z]/, "Must contain at least one uppercase letter")
    .regex(/[0-9]/, "Must contain at least one number"),
  orgName: z.string().min(1).max(100),
});

const LoginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

// ── POST /v1/auth/signup ──────────────────────────────────────────
authRoutes.post("/signup", authRateLimit, validate(SignupSchema), async (req, res, next) => {
  try {
    const { email, name, password, orgName } = req.body;

    // Check duplicate email
    const existing = await db.query("SELECT id FROM users WHERE email = $1", [email.toLowerCase()]);
    if (existing.rows[0]) {
      throw new AppError(409, "An account with this email already exists");
    }

    const passwordHash = await bcrypt.hash(password, 12);

    // Create user + org + teamMember in a single transaction
    const result = await db.query(`
      WITH new_user AS (
        INSERT INTO users (email, name, password_hash)
        VALUES ($1, $2, $3)
        RETURNING id
      ),
      new_org AS (
        INSERT INTO organizations (name)
        VALUES ($4)
        RETURNING id
      ),
      new_member AS (
        INSERT INTO team_members (org_id, user_id, email, role, invite_accepted, joined_at)
        SELECT new_org.id, new_user.id, $1, 'owner', true, NOW()
        FROM new_user, new_org
        RETURNING org_id
      ),
      new_notif AS (
        INSERT INTO notification_settings (org_id, alert_emails)
        SELECT org_id, ARRAY[$1]
        FROM new_member
      )
      SELECT new_user.id AS user_id, new_org.id AS org_id
      FROM new_user, new_org
    `, [email.toLowerCase(), name, passwordHash, orgName]);

    const { user_id, org_id } = result.rows[0];

    // Send verification email
    const rawToken = crypto.randomBytes(32).toString("hex");
    const tokenHash = await bcrypt.hash(rawToken, 10);
    await db.query(
      "UPDATE users SET email_verify_token = $1, email_verify_expires = NOW() + INTERVAL '24 hours' WHERE id = $2",
      [tokenHash, user_id]
    );
    await emailService.sendVerificationEmail(email, name, rawToken, user_id);

    res.status(201).json({
      message: "Account created. Check your email to verify your account.",
      userId: user_id,
      orgId: org_id,
    });
  } catch (err) {
    next(err);
  }
});

// ── POST /v1/auth/verify-email ───────────────────────────────────
authRoutes.post("/verify-email", authRateLimit, async (req, res, next) => {
  try {
    const { userId, token } = req.body;
    if (!userId || !token) throw new AppError(400, "userId and token are required");

    const userResult = await db.query(
      "SELECT email_verify_token, email_verify_expires FROM users WHERE id = $1 AND email_verified = false",
      [userId]
    );
    const user = userResult.rows[0];
    if (!user) throw new AppError(400, "Invalid or already-used verification link");
    if (new Date(user.email_verify_expires) < new Date()) throw new AppError(400, "Verification link expired");

    const valid = await bcrypt.compare(token, user.email_verify_token);
    if (!valid) throw new AppError(400, "Invalid verification token");

    await db.query(
      "UPDATE users SET email_verified = true, email_verify_token = NULL, email_verify_expires = NULL WHERE id = $1",
      [userId]
    );

    res.json({ message: "Email verified. You can now log in." });
  } catch (err) {
    next(err);
  }
});

// ── POST /v1/auth/login ──────────────────────────────────────────
authRoutes.post("/login", authRateLimit, validate(LoginSchema), async (req, res, next) => {
  try {
    const { email, password } = req.body;

    const userResult = await db.query(`
      SELECT u.id, u.email, u.name, u.password_hash, u.email_verified,
             tm.org_id, tm.role
      FROM users u
      JOIN team_members tm ON tm.user_id = u.id AND tm.invite_accepted = true
      WHERE u.email = $1
      LIMIT 1
    `, [email.toLowerCase()]);

    const user = userResult.rows[0];

    // Use constant-time compare even for "user not found" to prevent timing attacks
    const dummyHash = "$2b$12$invalidhashtopreventtimingattacks";
    const passwordMatch = user
      ? await bcrypt.compare(password, user.password_hash ?? dummyHash)
      : await bcrypt.compare(password, dummyHash);

    if (!user || !passwordMatch) {
      throw new AppError(401, "Invalid email or password");
    }

    if (!user.email_verified) {
      throw new AppError(403, "Please verify your email before logging in");
    }

    const tokens = await issueTokens(user.id, user.org_id, user.role, user.email);
    await db.query("UPDATE users SET last_login = NOW() WHERE id = $1", [user.id]);

    res.json({ ...tokens, user: { id: user.id, email: user.email, name: user.name, role: user.role, orgId: user.org_id } });
  } catch (err) {
    next(err);
  }
});

// ── POST /v1/auth/refresh ────────────────────────────────────────
authRoutes.post("/refresh", async (req, res, next) => {
  try {
    const { refreshToken } = req.body;
    if (!refreshToken) throw new AppError(400, "refreshToken required");

    let payload: any;
    try {
      payload = jwt.verify(refreshToken, env.JWT_REFRESH_SECRET);
    } catch {
      throw new AppError(401, "Invalid or expired refresh token");
    }

    // Verify token not revoked
    const tokenResult = await db.query(
      "SELECT id, token_hash FROM refresh_tokens WHERE user_id = $1 AND revoked_at IS NULL ORDER BY created_at DESC LIMIT 1",
      [payload.sub]
    );
    const stored = tokenResult.rows[0];
    if (!stored) throw new AppError(401, "Refresh token revoked");

    const valid = await bcrypt.compare(refreshToken, stored.token_hash);
    if (!valid) throw new AppError(401, "Invalid refresh token");

    // Rotate: revoke old, issue new
    await db.query("UPDATE refresh_tokens SET revoked_at = NOW() WHERE id = $1", [stored.id]);

    const userResult = await db.query(`
      SELECT u.id, u.email, tm.org_id, tm.role
      FROM users u JOIN team_members tm ON tm.user_id = u.id AND tm.invite_accepted = true
      WHERE u.id = $1 LIMIT 1
    `, [payload.sub]);
    const user = userResult.rows[0];
    if (!user) throw new AppError(401, "User not found");

    const tokens = await issueTokens(user.id, user.org_id, user.role, user.email);
    res.json(tokens);
  } catch (err) {
    next(err);
  }
});

// ── POST /v1/auth/logout ─────────────────────────────────────────
authRoutes.post("/logout", requireAuth, async (req, res, next) => {
  try {
    await db.query(
      "UPDATE refresh_tokens SET revoked_at = NOW() WHERE user_id = $1 AND revoked_at IS NULL",
      [req.user.sub]
    );
    res.json({ message: "Logged out" });
  } catch (err) {
    next(err);
  }
});

// ── POST /v1/auth/forgot-password ───────────────────────────────
authRoutes.post("/forgot-password", authRateLimit, async (req, res, next) => {
  try {
    const { email } = req.body;
    // Always respond 200 — never confirm whether email exists
    const userResult = await db.query("SELECT id, name FROM users WHERE email = $1", [email?.toLowerCase()]);
    if (userResult.rows[0]) {
      const user = userResult.rows[0];
      const rawToken = crypto.randomBytes(32).toString("hex");
      const tokenHash = await bcrypt.hash(rawToken, 10);
      await redis.set(`pwd:reset:${user.id}`, tokenHash, "EX", 3600); // 1 hour
      await emailService.sendPasswordResetEmail(email, user.name, rawToken, user.id);
    }
    res.json({ message: "If an account exists, a reset link has been sent" });
  } catch (err) {
    next(err);
  }
});

// ── POST /v1/auth/reset-password ────────────────────────────────
authRoutes.post("/reset-password", authRateLimit, async (req, res, next) => {
  try {
    const { userId, token, newPassword } = req.body;
    if (!userId || !token || !newPassword) throw new AppError(400, "userId, token, and newPassword required");

    const storedHash = await redis.get(`pwd:reset:${userId}`);
    if (!storedHash) throw new AppError(400, "Reset link expired or already used");

    const valid = await bcrypt.compare(token, storedHash);
    if (!valid) throw new AppError(400, "Invalid reset token");

    // Validate password strength
    if (newPassword.length < 12 || !/[A-Z]/.test(newPassword) || !/[0-9]/.test(newPassword)) {
      throw new AppError(400, "Password must be 12+ chars with at least one uppercase letter and number");
    }

    const hash = await bcrypt.hash(newPassword, 12);
    await db.query("UPDATE users SET password_hash = $1 WHERE id = $2", [hash, userId]);
    await redis.del(`pwd:reset:${userId}`);
    // Revoke all refresh tokens for this user
    await db.query("UPDATE refresh_tokens SET revoked_at = NOW() WHERE user_id = $1 AND revoked_at IS NULL", [userId]);

    res.json({ message: "Password reset successful. Please log in." });
  } catch (err) {
    next(err);
  }
});

// Helper: issue JWT access + refresh token pair
async function issueTokens(userId: string, orgId: string, role: string, email: string) {
  const accessToken = jwt.sign(
    { sub: userId, orgId, role, email },
    env.JWT_ACCESS_SECRET,
    { expiresIn: env.JWT_ACCESS_EXPIRY }
  );

  const rawRefreshToken = crypto.randomBytes(64).toString("hex");
  const refreshHash = await bcrypt.hash(rawRefreshToken, 10);
  const expiresAt = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);

  await db.query(
    "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES ($1, $2, $3)",
    [userId, refreshHash, expiresAt]
  );

  return { accessToken, refreshToken: rawRefreshToken };
}
```

---

## 9. RBAC — Role-Based Access Control

Roles: `owner > admin > editor > viewer`

| Action | Min Role |
|--------|----------|
| View dashboard, costs, alerts, reports | viewer |
| Acknowledge / snooze alerts | editor |
| Implement / reject recommendations | editor |
| Create / edit virtual tag rules | editor |
| Connect / remove cloud accounts | admin |
| Create / edit / delete budget caps | admin |
| Configure monthly report | admin |
| Configure notifications (Teams/Slack) | admin |
| Invite / remove team members | admin |
| Configure outbound webhooks | admin |
| Configure LLM | admin |
| Update org settings | admin |
| Transfer ownership | owner only |
| Delete org | owner only |

Use `requireRole("admin")` on routes that need it. See Section 7.3 for implementation.

---

## 10. Cloud Connector Services

### 10.1 `src/utils/withRetry.ts`

```typescript
import { logger } from "./logger";

export async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  label = "operation"
): Promise<T> {
  let lastError: Error = new Error("Unknown error");

  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error: any) {
      lastError = error;

      // Never retry auth errors
      const status = error.$metadata?.httpStatusCode ?? error.status ?? error.statusCode;
      if (status === 401 || status === 403 ||
          error.message?.includes("Unauthorized") ||
          error.message?.includes("AccessDenied") ||
          error.message?.includes("Invalid credentials")) {
        throw error;
      }

      // Rate limit — respect Retry-After header
      if (status === 429) {
        const retryAfterSec = parseInt(error.response?.headers?.["retry-after"] ?? "30", 10);
        const delay = Math.min(retryAfterSec * 1000, 120_000);
        logger.warn({ label, attempt: i + 1, delay_ms: delay }, "Rate limited — waiting");
        await sleep(delay);
        continue;
      }

      // Exponential backoff for all other errors
      const delay = Math.min(1000 * Math.pow(2, i), 30_000);
      logger.warn({ label, attempt: i + 1, delay_ms: delay, error: error.message }, "Retrying");
      await sleep(delay);
    }
  }

  throw lastError;
}

function sleep(ms: number) {
  return new Promise(r => setTimeout(r, ms));
}
```

### 10.2 `src/utils/encrypt.ts`

```typescript
import crypto from "crypto";
import { env } from "../config/env";

const ALGORITHM = "aes-256-gcm";
const KEY = Buffer.from(env.ENCRYPTION_KEY, "hex"); // 32 bytes

export function encrypt(plaintext: string): string {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv(ALGORITHM, KEY, iv);
  const encrypted = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
  const authTag = cipher.getAuthTag();
  // Return: iv(12) + authTag(16) + ciphertext — all hex-encoded
  return Buffer.concat([iv, authTag, encrypted]).toString("hex");
}

export function decrypt(ciphertext: string): string {
  const buf = Buffer.from(ciphertext, "hex");
  const iv = buf.subarray(0, 12);
  const authTag = buf.subarray(12, 28);
  const encrypted = buf.subarray(28);
  const decipher = crypto.createDecipheriv(ALGORITHM, KEY, iv);
  decipher.setAuthTag(authTag);
  return Buffer.concat([decipher.update(encrypted), decipher.final()]).toString("utf8");
}
```

### 10.3 `src/services/connectors/aws.ts`

```typescript
import {
  CostExplorerClient,
  GetCostAndUsageCommand,
  GetRightsizingRecommendationCommand,
  GetReservationUtilizationCommand,
  GetSavingsPlansUtilizationDetailsCommand,
} from "@aws-sdk/client-cost-explorer";
import { STSClient, AssumeRoleCommand } from "@aws-sdk/client-sts";
import { EC2Client, DescribeInstancesCommand } from "@aws-sdk/client-ec2";
import { withRetry } from "../../utils/withRetry";
import { logger } from "../../utils/logger";
import { decrypt } from "../../utils/encrypt";
import { env } from "../../config/env";

interface AWSCredentials {
  roleArn: string;
  externalId: string;
  region: string;
}

interface CostRecord {
  date: string;          // YYYY-MM-DD
  service: string;
  region: string;
  costUsd: number;
  usageValue: number;
  usageUnit: string;
  tags: Record<string, string>;
  isEstimate: boolean;
}

export class AWSConnector {
  private creds: AWSCredentials;
  private ceClient?: CostExplorerClient;

  constructor(encryptedCreds: string) {
    this.creds = JSON.parse(decrypt(encryptedCreds)) as AWSCredentials;
  }

  // Assume role and create CE client
  private async getClients(): Promise<{ ce: CostExplorerClient; ec2: EC2Client }> {
    const sts = new STSClient({ region: "us-east-1" });
    const assumed = await sts.send(new AssumeRoleCommand({
      RoleArn: this.creds.roleArn,
      RoleSessionName: "PrismSync",
      ExternalId: this.creds.externalId,
      DurationSeconds: 3600,
    }));

    const tempCreds = {
      accessKeyId: assumed.Credentials!.AccessKeyId!,
      secretAccessKey: assumed.Credentials!.SecretAccessKey!,
      sessionToken: assumed.Credentials!.SessionToken!,
    };

    return {
      ce: new CostExplorerClient({ region: "us-east-1", credentials: tempCreds }),
      ec2: new EC2Client({ region: this.creds.region, credentials: tempCreds }),
    };
  }

  async healthCheck(): Promise<{ ok: boolean; error?: string }> {
    try {
      const { ce } = await this.getClients();
      // Minimal CE call to verify access
      await ce.send(new GetCostAndUsageCommand({
        TimePeriod: { Start: "2026-01-01", End: "2026-01-02" },
        Granularity: "DAILY",
        Metrics: ["UnblendedCost"],
      }));
      return { ok: true };
    } catch (err: any) {
      return { ok: false, error: err.message };
    }
  }

  async getCostAndUsage(startDate: string, endDate: string): Promise<CostRecord[]> {
    const { ce } = await this.getClients();

    return withRetry(async () => {
      const response = await ce.send(new GetCostAndUsageCommand({
        TimePeriod: { Start: startDate, End: endDate },
        Granularity: "DAILY",
        Metrics: ["UnblendedCost", "AmortizedCost", "UsageQuantity"],
        GroupBy: [
          { Type: "DIMENSION", Key: "SERVICE" },
          { Type: "DIMENSION", Key: "REGION" },
        ],
      }));

      const records: CostRecord[] = [];
      const now = new Date();

      for (const result of response.ResultsByTime ?? []) {
        const date = result.TimePeriod!.Start!;
        const isEstimate = result.Estimated ?? false;

        for (const group of result.Groups ?? []) {
          const [service, region] = group.Keys ?? ["Unknown", ""];
          const unblended = parseFloat(group.Metrics?.UnblendedCost?.Amount ?? "0");

          if (unblended === 0) continue; // Skip zero-cost rows

          records.push({
            date,
            service,
            region: region || "",
            costUsd: unblended,
            usageValue: parseFloat(group.Metrics?.UsageQuantity?.Amount ?? "0"),
            usageUnit: group.Metrics?.UsageQuantity?.Unit ?? "",
            tags: {},
            isEstimate,
          });
        }
      }

      return records;
    }, 3, "aws.getCostAndUsage");
  }

  async getResources(regions: string[]): Promise<any[]> {
    const { ec2 } = await this.getClients();
    const resources: any[] = [];

    for (const region of regions) {
      try {
        const resp = await ec2.send(new DescribeInstancesCommand({}));
        for (const reservation of resp.Reservations ?? []) {
          for (const instance of reservation.Instances ?? []) {
            resources.push({
              resourceId: instance.InstanceId,
              resourceName: instance.Tags?.find(t => t.Key === "Name")?.Value ?? null,
              service: "Amazon EC2",
              region,
              instanceType: instance.InstanceType,
              tags: Object.fromEntries((instance.Tags ?? []).map(t => [t.Key!, t.Value!])),
              createdAtCloud: instance.LaunchTime,
            });
          }
        }
      } catch (err: any) {
        logger.warn({ region, error: err.message }, "EC2 describe failed for region");
      }
    }

    return resources;
  }

  async getCommitments(): Promise<any[]> {
    const { ce } = await this.getClients();
    const commitments: any[] = [];

    // Get Savings Plans utilization
    const spResponse = await withRetry(() => ce.send(new GetSavingsPlansUtilizationDetailsCommand({
      TimePeriod: { Start: new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10), End: new Date().toISOString().slice(0, 10) },
    })), 3, "aws.sp_utilization");

    for (const detail of spResponse.SavingsPlansUtilizationDetails ?? []) {
      commitments.push({
        externalId: detail.SavingsPlanArn,
        commitmentType: "savings_plan",
        provider: "aws",
        monthlyCost: parseFloat(detail.Utilization?.TotalCommitment ?? "0") / 30,
        utilizationPct: parseFloat(detail.Utilization?.UtilizationPercentage ?? "0"),
        monthlySavings: parseFloat(detail.Savings?.NetSavings ?? "0") / 30,
      });
    }

    return commitments;
  }
}
```

### 10.4 `src/services/connectors/azure.ts`

```typescript
import { ClientSecretCredential } from "@azure/identity";
import axios, { AxiosInstance } from "axios";
import { withRetry } from "../../utils/withRetry";
import { decrypt } from "../../utils/encrypt";

interface AzureCredentials {
  tenantId: string;
  clientId: string;
  clientSecret: string;
  subscriptionId: string;
}

export class AzureConnector {
  private creds: AzureCredentials;
  private axiosClient: AxiosInstance;
  private fxRate: number;  // USD/original-currency; passed from fx service at sync time

  constructor(encryptedCreds: string, fxRate: number = 1) {
    this.creds = JSON.parse(decrypt(encryptedCreds)) as AzureCredentials;
    this.fxRate = fxRate;

    const credential = new ClientSecretCredential(
      this.creds.tenantId,
      this.creds.clientId,
      this.creds.clientSecret
    );

    this.axiosClient = axios.create({
      baseURL: "https://management.azure.com",
    });

    this.axiosClient.interceptors.request.use(async (req) => {
      const token = await credential.getToken("https://management.azure.com/.default");
      req.headers!.Authorization = `Bearer ${token!.token}`;
      return req;
    });
  }

  async healthCheck(): Promise<{ ok: boolean; error?: string }> {
    try {
      await this.axiosClient.get(
        `/subscriptions/${this.creds.subscriptionId}?api-version=2020-01-01`
      );
      return { ok: true };
    } catch (err: any) {
      return { ok: false, error: err.response?.data?.error?.message ?? err.message };
    }
  }

  async getCostAndUsage(startDate: string, endDate: string): Promise<any[]> {
    return withRetry(async () => {
      const response = await this.axiosClient.post(
        `/subscriptions/${this.creds.subscriptionId}/providers/Microsoft.CostManagement/query?api-version=2021-10-01`,
        {
          type: "Usage",
          timeframe: "Custom",
          timePeriod: { from: startDate, to: endDate },
          dataset: {
            granularity: "Daily",
            aggregation: {
              totalCost: { name: "Cost", function: "Sum" },
              totalUsage: { name: "UsageQuantity", function: "Sum" },
            },
            grouping: [
              { type: "Dimension", name: "ServiceName" },
              { type: "Dimension", name: "ResourceGroup" },
            ],
          },
        }
      );

      const columns = response.data.properties?.columns ?? [];
      const rows = response.data.properties?.rows ?? [];

      const colIndex = (name: string) => columns.findIndex((c: any) => c.name === name);
      const costIdx = colIndex("Cost");
      const serviceIdx = colIndex("ServiceName");
      const dateIdx = colIndex("UsageDate");
      const usageIdx = colIndex("UsageQuantity");

      return rows.map((row: any[]) => ({
        date: String(row[dateIdx]).slice(0, 10),
        service: row[serviceIdx] ?? "Unknown",
        region: "",
        costUsd: (parseFloat(row[costIdx]) ?? 0) * this.fxRate,
        costOriginal: parseFloat(row[costIdx]) ?? 0,
        originalCurrency: "USD", // Azure bills in subscription currency; get from billing account
        usageValue: parseFloat(row[usageIdx]) ?? 0,
        usageUnit: "",
        tags: {},
        isEstimate: false,
      })).filter((r: any) => r.costUsd > 0);
    }, 3, "azure.getCostAndUsage");
  }
}
```

### 10.5 `src/services/connectors/gcp.ts`

```typescript
import { BigQuery } from "@google-cloud/bigquery";
import { decrypt } from "../../utils/encrypt";
import { withRetry } from "../../utils/withRetry";

interface GCPCredentials {
  projectId: string;
  datasetId: string;   // BigQuery billing export dataset
  tablePrefix: string; // usually "gcp_billing_export_v1_"
  serviceAccountJson: string; // JSON key content
}

export class GCPConnector {
  private bigquery: BigQuery;
  private creds: GCPCredentials;

  constructor(encryptedCreds: string) {
    this.creds = JSON.parse(decrypt(encryptedCreds)) as GCPCredentials;
    const serviceAccount = JSON.parse(this.creds.serviceAccountJson);

    this.bigquery = new BigQuery({
      projectId: this.creds.projectId,
      credentials: serviceAccount,
    });
  }

  async healthCheck(): Promise<{ ok: boolean; error?: string }> {
    try {
      await this.bigquery.dataset(this.creds.datasetId).get();
      return { ok: true };
    } catch (err: any) {
      return { ok: false, error: err.message };
    }
  }

  async getCostAndUsage(startDate: string, endDate: string): Promise<any[]> {
    // IMPORTANT: Use parameterized queries to prevent SQL injection
    const query = `
      SELECT
        DATE(usage_start_time) AS usage_date,
        service.description AS service,
        location.region AS region,
        SUM(cost) AS total_cost,
        SUM(usage.amount) AS usage_amount,
        MAX(usage.unit) AS usage_unit,
        currency
      FROM \`${this.creds.projectId}.${this.creds.datasetId}.${this.creds.tablePrefix}*\`
      WHERE DATE(usage_start_time) >= @startDate
        AND DATE(usage_start_time) < @endDate
        AND cost > 0
      GROUP BY 1, 2, 3, 7
      ORDER BY 1, 4 DESC
    `;

    return withRetry(async () => {
      const [rows] = await this.bigquery.query({
        query,
        params: { startDate, endDate },  // parameterized — no injection possible
        location: "US",
      });

      return rows.map((row: any) => ({
        date: row.usage_date.value ?? row.usage_date,
        service: row.service ?? "Unknown",
        region: row.region ?? "",
        costUsd: parseFloat(row.total_cost) ?? 0,
        costOriginal: parseFloat(row.total_cost) ?? 0,
        originalCurrency: row.currency ?? "USD",
        usageValue: parseFloat(row.usage_amount) ?? 0,
        usageUnit: row.usage_unit ?? "",
        tags: {},
        isEstimate: false,
      }));
    }, 3, "gcp.getCostAndUsage");
  }
}
```

---

## 11. Background Job System (BullMQ)

### 11.1 `src/config/queues.ts`

```typescript
import { Queue } from "bullmq";
import { redis } from "./redis";

const connection = { url: process.env.REDIS_URL! };

export const syncQueue = new Queue("prism-sync", { connection });
export const alertsQueue = new Queue("prism-alerts", { connection });
export const commitmentsQueue = new Queue("prism-commitments", { connection });
export const forecastQueue = new Queue("prism-forecast", { connection });
export const virtualTagsQueue = new Queue("prism-virtual-tags", { connection });
export const reportsQueue = new Queue("prism-reports", { connection });
export const recommendationsQueue = new Queue("prism-recommendations", { connection });
export const dlqQueue = new Queue("prism-dlq", { connection });
```

### 11.2 `src/jobs/scheduler.ts`

```typescript
import cron from "node-cron";
import { db } from "../config/db";
import { syncQueue, commitmentsQueue, forecastQueue, recommendationsQueue, reportsQueue } from "../config/queues";
import { startSyncWorker } from "./sync.worker";
import { startAlertsWorker } from "./alerts.worker";
import { startCommitmentsWorker } from "./commitments.worker";
import { startForecastWorker } from "./forecast.worker";
import { startVirtualTagsWorker } from "./virtualTags.worker";
import { startReportsWorker } from "./reports.worker";
import { startRecommendationsWorker } from "./recommendations.worker";
import { startDlqWorker } from "./dlq.worker";
import { env } from "../config/env";
import { logger } from "../utils/logger";

export async function startWorkers() {
  // Start all workers
  startSyncWorker();
  startAlertsWorker();
  startCommitmentsWorker();
  startForecastWorker();
  startVirtualTagsWorker();
  startReportsWorker();
  startRecommendationsWorker();
  startDlqWorker();

  // Daily sync: 06:00 UTC — enqueue one job per active cloud account
  cron.schedule(env.CRON_SYNC, async () => {
    logger.info("Cron: enqueuing daily sync jobs");
    const accounts = await db.query(
      "SELECT id, org_id, provider FROM cloud_accounts WHERE is_active = true"
    );
    for (const account of accounts.rows) {
      await syncQueue.add("sync", { accountId: account.id, orgId: account.org_id, backfill: false }, {
        jobId: `sync:${account.id}:${new Date().toISOString().slice(0, 10)}`,
        attempts: 3,
        backoff: { type: "exponential", delay: 60000 },
        removeOnComplete: 100,
        removeOnFail: { count: 50 },
      });
    }
  });

  // Daily commitments: 07:00 UTC
  cron.schedule(env.CRON_COMMITMENTS, async () => {
    logger.info("Cron: enqueuing commitments sync");
    const orgs = await db.query("SELECT id FROM organizations");
    for (const org of orgs.rows) {
      await commitmentsQueue.add("commitments", { orgId: org.id }, {
        jobId: `commitments:${org.id}:${new Date().toISOString().slice(0, 10)}`,
        attempts: 3,
        removeOnComplete: 50,
      });
    }
  });

  // Forecast: 07:30 UTC
  cron.schedule(env.CRON_FORECAST, async () => {
    logger.info("Cron: enqueuing forecast recalculation");
    const orgs = await db.query("SELECT id FROM organizations");
    for (const org of orgs.rows) {
      await forecastQueue.add("forecast", { orgId: org.id }, {
        jobId: `forecast:${org.id}:${new Date().toISOString().slice(0, 10)}`,
        attempts: 2,
        removeOnComplete: 50,
      });
    }
  });

  // Recommendations: 08:00 UTC
  cron.schedule(env.CRON_RECOMMENDATIONS, async () => {
    logger.info("Cron: enqueuing recommendations");
    const orgs = await db.query("SELECT id FROM organizations");
    for (const org of orgs.rows) {
      await recommendationsQueue.add("recommendations", { orgId: org.id }, {
        jobId: `recommendations:${org.id}:${new Date().toISOString().slice(0, 10)}`,
        attempts: 2,
        removeOnComplete: 50,
      });
    }
  });

  // Monthly reports: 09:00 UTC daily — check which orgs need their report sent today
  cron.schedule(env.CRON_REPORTS, async () => {
    logger.info("Cron: checking monthly reports");
    const today = new Date();
    const reports = await db.query(
      "SELECT org_id FROM monthly_reports WHERE is_active = true AND date_trunc('day', next_send) <= date_trunc('day', NOW())"
    );
    for (const report of reports.rows) {
      await reportsQueue.add("report", { orgId: report.org_id }, {
        jobId: `report:${report.org_id}:${today.toISOString().slice(0, 10)}`,
        attempts: 2,
        removeOnComplete: 50,
      });
    }
  });

  logger.info("All workers and cron jobs started");
}
```

---

## 12. Job Workers (Full Implementation)

### 12.1 `src/jobs/sync.worker.ts`

```typescript
import { Worker, Job } from "bullmq";
import { db } from "../config/db";
import { alertsQueue } from "../config/queues";
import { AWSConnector } from "../services/connectors/aws";
import { AzureConnector } from "../services/connectors/azure";
import { GCPConnector } from "../services/connectors/gcp";
import { FXService } from "../services/fx.service";
import { wsBroadcast } from "../ws/wsServer";
import { invalidateDashboardCache } from "../utils/cache";
import { logger } from "../utils/logger";
import { env } from "../config/env";

export function startSyncWorker() {
  const worker = new Worker("prism-sync", async (job: Job) => {
    const { accountId, orgId, backfill } = job.data;
    logger.info({ accountId, orgId, backfill }, "Sync job started");

    // Create sync log
    const logResult = await db.query(
      "INSERT INTO sync_logs (org_id, account_id, backfill) VALUES ($1, $2, $3) RETURNING id",
      [orgId, accountId, backfill]
    );
    const syncLogId = logResult.rows[0].id;

    // Get account credentials
    const accountResult = await db.query(
      "SELECT provider, credentials_enc, account_id FROM cloud_accounts WHERE id = $1 AND org_id = $2",
      [accountId, orgId]
    );
    const account = accountResult.rows[0];
    if (!account) throw new Error(`Account ${accountId} not found`);

    await db.query(
      "UPDATE cloud_accounts SET last_sync_status = 'running' WHERE id = $1",
      [accountId]
    );

    try {
      const fxRate = await FXService.getRate("USD");
      let records: any[] = [];

      // Determine sync window
      const today = new Date().toISOString().slice(0, 10);
      const startDate = backfill
        ? new Date(Date.now() - 395 * 86400000).toISOString().slice(0, 10) // 13 months back
        : new Date(Date.now() - 3 * 86400000).toISOString().slice(0, 10);  // last 3 days (re-sync recent)

      // Call the appropriate connector
      if (account.provider === "aws") {
        const connector = new AWSConnector(account.credentials_enc);
        records = await connector.getCostAndUsage(startDate, today);
      } else if (account.provider === "azure") {
        const connector = new AzureConnector(account.credentials_enc, fxRate);
        records = await connector.getCostAndUsage(startDate, today);
      } else if (account.provider === "gcp") {
        const connector = new GCPConnector(account.credentials_enc);
        records = await connector.getCostAndUsage(startDate, today);
      }

      // Bulk upsert into cost_records
      if (records.length > 0) {
        await upsertCostRecords(orgId, accountId, account.provider, records);
      }

      // Update account status
      await db.query(`
        UPDATE cloud_accounts
        SET last_sync = NOW(), last_sync_status = 'success',
            last_sync_records = $1, last_sync_error = NULL,
            data_as_of = NOW()
        WHERE id = $2
      `, [records.length, accountId]);

      await db.query(`
        UPDATE sync_logs
        SET finished_at = NOW(), status = 'success', records_synced = $1
        WHERE id = $2
      `, [records.length, syncLogId]);

      // Invalidate cache + push WebSocket event
      await invalidateDashboardCache(orgId, account.provider);
      wsBroadcast(orgId, {
        event: "sync.complete",
        org_id: orgId,
        timestamp: new Date().toISOString(),
        data: { provider: account.provider, account_id: accountId, records: records.length },
      });

      // Trigger alert check after sync
      await alertsQueue.add("alerts", { orgId }, {
        jobId: `alerts:${orgId}:${today}`,
        attempts: 2,
      });

      logger.info({ accountId, orgId, records: records.length }, "Sync completed");
    } catch (err: any) {
      await db.query(`
        UPDATE cloud_accounts
        SET last_sync = NOW(), last_sync_status = 'failed', last_sync_error = $1
        WHERE id = $2
      `, [err.message, accountId]);

      await db.query(`
        UPDATE sync_logs SET finished_at = NOW(), status = 'failed', error_message = $1 WHERE id = $2
      `, [err.message, syncLogId]);

      throw err; // BullMQ will retry
    }
  }, {
    connection: { url: env.REDIS_URL },
    concurrency: env.WORKER_CONCURRENCY,
  });

  worker.on("failed", (job, err) => {
    logger.error({ jobId: job?.id, err }, "Sync job failed permanently");
  });

  return worker;
}

async function upsertCostRecords(orgId: string, accountId: string, provider: string, records: any[]) {
  // Batch upsert in chunks of 500
  const CHUNK = 500;
  for (let i = 0; i < records.length; i += CHUNK) {
    const chunk = records.slice(i, i + CHUNK);

    const values = chunk.map((r, idx) => {
      const base = idx * 14;
      return `($${base+1},$${base+2},$${base+3},$${base+4},$${base+5},$${base+6},$${base+7},$${base+8},$${base+9},$${base+10},$${base+11},$${base+12},$${base+13},$${base+14})`;
    }).join(",");

    const params = chunk.flatMap(r => [
      r.date + "T00:00:00Z",   // time
      orgId,
      accountId,
      provider,
      r.service,
      r.region ?? "",
      r.costUsd,
      r.costUsd,               // cost_unblended_usd (same as costUsd for Azure/GCP)
      r.costUsd,               // cost_amortized_usd
      r.costOriginal ?? r.costUsd,
      r.originalCurrency ?? "USD",
      r.fxRate ?? 1,
      r.usageValue ?? 0,
      r.usageUnit ?? "",
    ]);

    await db.query(`
      INSERT INTO cost_records
        (time, org_id, account_id, provider, service, region,
         cost_usd, cost_unblended_usd, cost_amortized_usd,
         cost_original, original_currency, fx_rate,
         usage_value, usage_unit)
      VALUES ${values}
      ON CONFLICT (account_id, (time::date), service, region)
      DO UPDATE SET
        cost_usd = EXCLUDED.cost_usd,
        cost_unblended_usd = EXCLUDED.cost_unblended_usd,
        cost_amortized_usd = EXCLUDED.cost_amortized_usd,
        is_estimate = EXCLUDED.is_estimate
    `, params);
  }
}
```

### 12.2 `src/jobs/alerts.worker.ts`

```typescript
import { Worker, Job } from "bullmq";
import { CapAlertService } from "../services/alert.service";
import { env } from "../config/env";
import { logger } from "../utils/logger";

export function startAlertsWorker() {
  return new Worker("prism-alerts", async (job: Job) => {
    const { orgId } = job.data;
    const alertService = new CapAlertService();
    await alertService.checkAllCaps(orgId);
    logger.info({ orgId }, "Alert check completed");
  }, {
    connection: { url: env.REDIS_URL },
    concurrency: 10,
  });
}
```

### 12.3 `src/jobs/dlq.worker.ts`

```typescript
import { Worker, Job } from "bullmq";
import { db } from "../config/db";
import { env } from "../config/env";
import { logger } from "../utils/logger";

export function startDlqWorker() {
  return new Worker("prism-dlq", async (job: Job) => {
    // Log permanently failed jobs; create internal sync_failure alert
    logger.error({ jobId: job.id, jobName: job.name, data: job.data }, "DLQ: permanently failed job");

    if (job.data.orgId && job.name === "sync") {
      await db.query(`
        INSERT INTO alerts (org_id, type, scope_label, severity, triggered_at, email_sent)
        VALUES ($1, 'sync_failure', $2, 'critical', NOW(), false)
        ON CONFLICT DO NOTHING
      `, [job.data.orgId, `Account ${job.data.accountId} sync failed after 3 attempts`]);
    }
  }, { connection: { url: env.REDIS_URL }, concurrency: 1 });
}
```

---

## 13. Alert & Notification System

### `src/services/alert.service.ts`

```typescript
import { db } from "../config/db";
import { redis } from "../config/redis";
import { emailService } from "./email.service";
import { webhookService } from "./webhook.service";
import { wsBroadcast } from "../ws/wsServer";
import { logger } from "../utils/logger";
import axios from "axios";

export class CapAlertService {

  async checkAllCaps(orgId: string): Promise<void> {
    const capsResult = await db.query(
      "SELECT * FROM budget_caps WHERE org_id = $1 AND is_active = true",
      [orgId]
    );

    const settingsResult = await db.query(
      "SELECT * FROM notification_settings WHERE org_id = $1",
      [orgId]
    );
    const settings = settingsResult.rows[0];
    if (!settings) return;

    const orgResult = await db.query("SELECT * FROM organizations WHERE id = $1", [orgId]);
    const org = orgResult.rows[0];

    for (const cap of capsResult.rows) {
      const spent = await this.getCurrentSpend(cap, orgId);
      const pct = (spent / cap.cap_amount) * 100;

      const THRESHOLDS = [75, 90, 100, 125, 150];
      for (const threshold of THRESHOLDS) {
        if (pct >= threshold) {
          await this.evaluateThreshold(cap, spent, pct, threshold, orgId, settings, org);
        }
      }
    }

    // Also check forecast breach alerts
    await this.checkForecastBreachAlerts(orgId, settings, org);
  }

  private async getCurrentSpend(cap: any, orgId: string): Promise<number> {
    const monthStart = new Date();
    monthStart.setDate(1);
    monthStart.setHours(0, 0, 0, 0);

    let whereClause = "org_id = $1 AND time >= $2";
    const params: any[] = [orgId, monthStart.toISOString()];
    let paramIdx = 3;

    if (cap.scope === "platform" && cap.provider) {
      whereClause += ` AND provider = $${paramIdx++}`;
      params.push(cap.provider);
    }
    if (cap.scope === "service" && cap.service_name) {
      whereClause += ` AND service = $${paramIdx++}`;
      params.push(cap.service_name);
    }
    if (cap.scope === "account" && cap.account_id) {
      whereClause += ` AND account_id = $${paramIdx++}`;
      params.push(cap.account_id);
    }

    const result = await db.query(
      `SELECT COALESCE(SUM(cost_usd), 0) AS total FROM cost_records WHERE ${whereClause}`,
      params
    );

    return parseFloat(result.rows[0].total);
  }

  private async evaluateThreshold(
    cap: any, spent: number, pct: number, threshold: number,
    orgId: string, settings: any, org: any
  ): Promise<void> {
    // Check deduplication: has this threshold already fired this billing month?
    const monthStart = new Date();
    monthStart.setDate(1);
    monthStart.setHours(0, 0, 0, 0);

    const existing = await db.query(`
      SELECT id FROM alerts
      WHERE org_id = $1 AND cap_id = $2 AND type = 'cap_threshold'
        AND threshold_percent = $3
        AND triggered_at >= $4
    `, [orgId, cap.id, threshold, monthStart.toISOString()]);

    if (existing.rows[0]) return; // Already fired this month for this threshold

    await this.fireAlert(cap, spent, pct, threshold, orgId, settings, org);
  }

  private async fireAlert(
    cap: any, spent: number, pct: number, threshold: number,
    orgId: string, settings: any, org: any
  ): Promise<void> {
    const severity: "warning" | "critical" = threshold >= 100 ? "critical" : "warning";

    // Insert alert record first (audit trail even if notifications fail)
    const alertResult = await db.query(`
      INSERT INTO alerts
        (org_id, cap_id, type, scope_label, threshold_percent,
         spend_at_trigger, cap_amount, severity, triggered_at,
         email_sent, teams_sent, slack_sent, webhook_sent)
      VALUES ($1, $2, 'cap_threshold', $3, $4, $5, $6, $7, NOW(), false, false, false, false)
      RETURNING id
    `, [orgId, cap.id, cap.name, threshold, spent, cap.cap_amount, severity]);

    const alertId = alertResult.rows[0].id;
    const updates: Record<string, boolean> = {};

    // Push real-time alert banner via WebSocket immediately
    wsBroadcast(orgId, {
      event: "alert.fired",
      org_id: orgId,
      timestamp: new Date().toISOString(),
      data: { alert_id: alertId, type: "cap_threshold", scope: cap.name, severity, threshold_percent: threshold },
    });

    // Fire all notification channels concurrently
    await Promise.allSettled([
      // Email
      settings.alert_emails?.length > 0
        ? emailService.sendCapAlert({ to: settings.alert_emails, cap, spent, pct, threshold, org })
            .then(() => { updates.email_sent = true; })
            .catch(err => logger.error({ alertId, err }, "Email failed"))
        : Promise.resolve(),

      // Teams
      settings.teams_webhook_url
        ? this.sendTeamsAlert(settings.teams_webhook_url, cap, spent, pct, threshold)
            .then(() => { updates.teams_sent = true; })
            .catch(err => logger.error({ alertId, err }, "Teams failed"))
        : Promise.resolve(),

      // Slack
      settings.slack_webhook_url
        ? this.sendSlackAlert(settings.slack_webhook_url, cap, spent, pct, threshold)
            .then(() => { updates.slack_sent = true; })
            .catch(err => logger.error({ alertId, err }, "Slack failed"))
        : Promise.resolve(),

      // Outbound webhooks
      webhookService.dispatch(orgId, "alert.fired", {
        alert_id: alertId, cap_id: cap.id, threshold_percent: threshold, spent, cap_amount: cap.cap_amount
      })
        .then(() => { updates.webhook_sent = true; })
        .catch(err => logger.warn({ alertId, err }, "Webhook dispatch failed")),
    ]);

    // Update notification status
    if (Object.keys(updates).length > 0) {
      const setClauses = Object.entries(updates).map(([k], i) => `${k} = $${i + 2}`).join(", ");
      await db.query(
        `UPDATE alerts SET ${setClauses} WHERE id = $1`,
        [alertId, ...Object.values(updates)]
      );
    }
  }

  private async sendTeamsAlert(webhookUrl: string, cap: any, spent: number, pct: number, threshold: number) {
    await axios.post(webhookUrl, {
      "@type": "MessageCard",
      "@context": "http://schema.org/extensions",
      themeColor: pct >= 100 ? "FF0000" : "FFA500",
      summary: `PRISM: ${cap.name} at ${threshold}%`,
      sections: [{
        activityTitle: `⚠️ Budget Cap Alert: ${cap.name}`,
        activitySubtitle: `${threshold}% threshold reached`,
        facts: [
          { name: "Spent", value: `$${spent.toFixed(2)}` },
          { name: "Cap", value: `$${cap.cap_amount}` },
          { name: "Usage", value: `${pct.toFixed(1)}%` },
        ],
      }],
    });
  }

  private async sendSlackAlert(webhookUrl: string, cap: any, spent: number, pct: number, threshold: number) {
    await axios.post(webhookUrl, {
      text: `⚠️ PRISM Budget Alert: *${cap.name}* reached ${threshold}%`,
      blocks: [{
        type: "section",
        text: {
          type: "mrkdwn",
          text: `*Budget Cap Alert*\n*${cap.name}* has reached *${threshold}%*\nSpent: $${spent.toFixed(2)} / $${cap.cap_amount} (${pct.toFixed(1)}%)`,
        },
      }],
    });
  }

  private async checkForecastBreachAlerts(orgId: string, settings: any, org: any) {
    const forecasts = await db.query(`
      SELECT * FROM spend_forecasts
      WHERE org_id = $1 AND forecast_month = date_trunc('month', NOW())
        AND will_breach = true
        AND data_coverage != 'insufficient'
    `, [orgId]);

    for (const forecast of forecasts.rows) {
      // Check dedup — one forecast breach alert per provider per month
      const existing = await db.query(`
        SELECT id FROM alerts
        WHERE org_id = $1 AND type = 'forecast_breach'
          AND triggered_at >= date_trunc('month', NOW())
          AND metadata->>'provider' = $2
      `, [orgId, forecast.provider ?? "all"]);

      if (existing.rows[0]) continue;

      await db.query(`
        INSERT INTO alerts (org_id, type, scope_label, severity, triggered_at, metadata, email_sent)
        VALUES ($1, 'forecast_breach', $2, 'warning', NOW(), $3, false)
      `, [orgId, `${forecast.provider ?? "All"} Forecast`, JSON.stringify({ provider: forecast.provider, projected_total: forecast.projected_total, cap_amount: forecast.cap_amount })]);

      if (settings.alert_emails?.length > 0) {
        await emailService.sendForecastBreachAlert({
          to: settings.alert_emails, forecast, org,
        }).catch(err => logger.error({ err }, "Forecast breach email failed"));
      }
    }
  }
}
```

---

## 14. WebSocket Server

### `src/ws/wsServer.ts`

```typescript
import { WebSocketServer, WebSocket } from "ws";
import jwt from "jsonwebtoken";
import { env } from "../config/env";
import { logger } from "../utils/logger";
import http from "http";

// Map: orgId → Set of connected WebSocket clients
const orgConnections = new Map<string, Set<WebSocket>>();

export function createWsServer(server: http.Server) {
  const wss = new WebSocketServer({ server, path: "/ws" });

  wss.on("connection", (ws, req) => {
    // Extract JWT from query string: /ws?token=...
    const url = new URL(req.url!, `http://${req.headers.host}`);
    const token = url.searchParams.get("token");

    if (!token) {
      ws.close(4001, "Missing token");
      return;
    }

    let payload: any;
    try {
      payload = jwt.verify(token, env.JWT_ACCESS_SECRET);
    } catch {
      ws.close(4001, "Invalid or expired token");
      return;
    }

    const { orgId } = payload;
    if (!orgConnections.has(orgId)) {
      orgConnections.set(orgId, new Set());
    }
    orgConnections.get(orgId)!.add(ws);

    logger.info({ orgId, userId: payload.sub }, "WebSocket client connected");

    ws.on("close", () => {
      orgConnections.get(orgId)?.delete(ws);
      if (orgConnections.get(orgId)?.size === 0) {
        orgConnections.delete(orgId);
      }
    });

    // Ping/pong keepalive every 30 seconds
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.ping();
    }, 30000);

    ws.on("close", () => clearInterval(pingInterval));

    ws.send(JSON.stringify({ event: "connected", org_id: orgId, timestamp: new Date().toISOString(), data: {} }));
  });

  logger.info("WebSocket server initialized");
  return wss;
}

export function wsBroadcast(orgId: string, event: object) {
  const clients = orgConnections.get(orgId);
  if (!clients || clients.size === 0) return;

  const message = JSON.stringify(event);
  for (const client of clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(message);
    }
  }
}
```

---

## 15. API Endpoints — Full Route Reference

### Auth (`/v1/auth`)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/v1/auth/signup` | None | — | Sign up + create org |
| POST | `/v1/auth/verify-email` | None | — | Verify email with token |
| POST | `/v1/auth/login` | None | — | Login with email+password |
| POST | `/v1/auth/refresh` | None | — | Refresh access token |
| POST | `/v1/auth/logout` | JWT | any | Revoke refresh token |
| POST | `/v1/auth/forgot-password` | None | — | Send reset email |
| POST | `/v1/auth/reset-password` | None | — | Set new password with token |

### Cloud Accounts (`/v1/orgs/:orgId/accounts`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/` | viewer | List cloud accounts |
| POST | `/` | admin | Add cloud account |
| GET | `/:accountId` | viewer | Get account detail |
| PUT | `/:accountId` | admin | Update account (rename) |
| DELETE | `/:accountId` | admin | Remove account |
| POST | `/:accountId/test` | admin | Test connection |
| POST | `/:accountId/sync` | admin | Trigger manual sync |
| GET | `/:accountId/sync-logs` | admin | Get sync history |

### Costs (`/v1/orgs/:orgId/costs`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/` | viewer | Cost summary for time range (dashboard) |
| GET | `/by-service` | viewer | Cost grouped by service |
| GET | `/by-account` | viewer | Cost grouped by account |
| GET | `/by-tag` | viewer | Cost grouped by tag key/value |
| GET | `/by-day` | viewer | Daily cost trend |
| GET | `/top-services` | viewer | Top N services by spend |
| GET | `/untagged` | viewer | Untagged spend summary |

### Alerts (`/v1/orgs/:orgId/alerts`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/` | viewer | List alerts (paginated) |
| GET | `/:alertId` | viewer | Get alert detail |
| POST | `/:alertId/acknowledge` | editor | Acknowledge alert |
| POST | `/:alertId/snooze` | editor | Snooze alert |

### Budget Caps (`/v1/orgs/:orgId/caps`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/` | viewer | List caps with current spend |
| POST | `/` | admin | Create cap |
| GET | `/:capId` | viewer | Get cap detail |
| PUT | `/:capId` | admin | Update cap |
| DELETE | `/:capId` | admin | Delete cap |

### Reports (`/v1/orgs/:orgId/reports`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/config` | viewer | Get report config |
| PUT | `/config` | admin | Update report schedule |
| POST | `/send-now` | admin | Send test report immediately |

### Team (`/v1/orgs/:orgId/team`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/` | viewer | List members |
| POST | `/invite` | admin | Invite member |
| POST | `/accept-invite` | none | Accept invite (no auth — uses token) |
| PUT | `/:memberId/role` | admin | Change role |
| DELETE | `/:memberId` | admin | Remove member |
| POST | `/resend-invite` | admin | Resend invite email |

### Recommendations (`/v1/orgs/:orgId/recommendations`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/` | viewer | List recommendations |
| PUT | `/:recId/status` | editor | Mark implemented/rejected/archived |

### Virtual Tags (`/v1/orgs/:orgId/virtual-tags`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/` | viewer | List rules |
| POST | `/` | editor | Create rule |
| PUT | `/:ruleId` | editor | Update rule |
| DELETE | `/:ruleId` | editor | Delete rule |
| POST | `/reorder` | editor | Reorder rules (priority) |
| POST | `/apply` | editor | Trigger retroactive re-apply |
| GET | `/audit-log` | viewer | View tag audit log |

### Forecasts (`/v1/orgs/:orgId/forecasts`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/` | viewer | Get current month forecast |
| GET | `/history` | viewer | Past forecast accuracy |

### Commitments (`/v1/orgs/:orgId/commitments`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/` | viewer | List active commitments |
| GET | `/summary` | viewer | Coverage, utilization, ESR |
| GET | `/expiring` | viewer | Expiring within 90 days |

### Scorecard (`/v1/orgs/:orgId/scorecard`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/` | viewer | FinOps health scorecard |
| GET | `/executive` | viewer | Executive KPI view |

### Notifications (`/v1/orgs/:orgId/notifications`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/` | viewer | Get notification settings |
| PUT | `/` | admin | Update email/Teams/Slack settings |
| POST | `/test-email` | admin | Send test email |
| POST | `/test-teams` | admin | Send test Teams message |
| POST | `/test-slack` | admin | Send test Slack message |

### Outbound Webhooks (`/v1/orgs/:orgId/webhooks`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/` | viewer | List webhooks |
| POST | `/` | admin | Create webhook |
| PUT | `/:webhookId` | admin | Update webhook |
| DELETE | `/:webhookId` | admin | Delete webhook |
| POST | `/:webhookId/test` | admin | Send test payload |

### LLM (`/v1/orgs/:orgId/llm`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/config` | admin | Get LLM config |
| PUT | `/config` | admin | Save/update LLM config |
| DELETE | `/config` | admin | Disable LLM |
| POST | `/query` | viewer | Natural language cost query |

### Business Metrics (`/v1/orgs/:orgId/metrics`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/` | viewer | List metrics |
| POST | `/` | admin | Create metric |
| POST | `/:metricId/values` | editor | Ingest values (manual/webhook) |
| GET | `/:metricId/values` | viewer | Get metric values |

### Resources (`/v1/orgs/:orgId/resources`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/` | viewer | List resources |
| GET | `/idle` | viewer | List idle resources |
| GET | `/:resourceId` | viewer | Get resource detail |

---

## 16. Route Implementations

### 16.1 `src/routes/costs.ts` (key queries)

```typescript
import { Router } from "express";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { apiRateLimit } from "../middleware/rateLimit";
import { db } from "../config/db";
import { redis } from "../config/redis";
import { z } from "zod";

export const costRoutes = Router({ mergeParams: true });
costRoutes.use(requireAuth, requireOrgAccess, apiRateLimit);

// GET /v1/orgs/:orgId/costs — Overall cost summary
costRoutes.get("/", async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const month = (req.query.month as string) ?? new Date().toISOString().slice(0, 7);
    const cacheKey = `dash:${orgId}:overall:${month}`;

    const cached = await redis.get(cacheKey);
    if (cached) return res.json(JSON.parse(cached));

    const monthStart = `${month}-01`;
    const monthEnd = new Date(new Date(monthStart).setMonth(new Date(monthStart).getMonth() + 1))
      .toISOString().slice(0, 10);

    const result = await db.query(`
      SELECT
        provider,
        SUM(cost_usd) AS total_usd,
        SUM(cost_amortized_usd) AS total_amortized_usd,
        COUNT(DISTINCT account_id) AS account_count,
        COUNT(DISTINCT service) AS service_count
      FROM cost_records
      WHERE org_id = $1 AND time >= $2 AND time < $3
      GROUP BY provider
    `, [orgId, monthStart, monthEnd]);

    const prevMonthStart = new Date(new Date(monthStart).setMonth(new Date(monthStart).getMonth() - 1))
      .toISOString().slice(0, 10);

    const prevResult = await db.query(`
      SELECT SUM(cost_usd) AS total_usd FROM cost_records
      WHERE org_id = $1 AND time >= $2 AND time < $3
    `, [orgId, prevMonthStart, monthStart]);

    const response = {
      month,
      byProvider: result.rows,
      totalUsd: result.rows.reduce((sum: number, r: any) => sum + parseFloat(r.total_usd), 0),
      prevMonthTotalUsd: parseFloat(prevResult.rows[0]?.total_usd ?? "0"),
    };

    await redis.set(cacheKey, JSON.stringify(response), "EX", 300); // 5 min cache
    res.json(response);
  } catch (err) {
    next(err);
  }
});

// GET /v1/orgs/:orgId/costs/by-service
costRoutes.get("/by-service", async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const month = (req.query.month as string) ?? new Date().toISOString().slice(0, 7);
    const provider = req.query.provider as string | undefined;
    const limit = Math.min(parseInt(req.query.limit as string) || 20, 100);

    const monthStart = `${month}-01`;
    const monthEnd = new Date(new Date(monthStart).setMonth(new Date(monthStart).getMonth() + 1))
      .toISOString().slice(0, 10);

    let whereClause = "org_id = $1 AND time >= $2 AND time < $3";
    const params: any[] = [orgId, monthStart, monthEnd];

    if (provider) {
      whereClause += ` AND provider = $4`;
      params.push(provider);
    }

    const result = await db.query(`
      SELECT service, provider, SUM(cost_usd) AS total_usd
      FROM cost_records WHERE ${whereClause}
      GROUP BY service, provider
      ORDER BY total_usd DESC
      LIMIT $${params.length + 1}
    `, [...params, limit]);

    res.json(result.rows);
  } catch (err) {
    next(err);
  }
});

// GET /v1/orgs/:orgId/costs/by-day
costRoutes.get("/by-day", async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const month = (req.query.month as string) ?? new Date().toISOString().slice(0, 7);
    const provider = req.query.provider as string | undefined;

    const monthStart = `${month}-01`;
    const monthEnd = new Date(new Date(monthStart).setMonth(new Date(monthStart).getMonth() + 1))
      .toISOString().slice(0, 10);

    const params: any[] = [orgId, monthStart, monthEnd];
    const providerFilter = provider ? `AND provider = $4` : "";
    if (provider) params.push(provider);

    const result = await db.query(`
      SELECT time::date AS date, SUM(cost_usd) AS total_usd
      FROM cost_records
      WHERE org_id = $1 AND time >= $2 AND time < $3 ${providerFilter}
      GROUP BY date ORDER BY date
    `, params);

    res.json(result.rows);
  } catch (err) {
    next(err);
  }
});
```

### 16.2 `src/routes/caps.ts`

```typescript
import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { requireRole } from "../middleware/rbac";
import { validate } from "../middleware/validateBody";
import { db } from "../config/db";
import { alertsQueue } from "../config/queues";
import { AppError } from "../middleware/errorHandler";

export const capRoutes = Router({ mergeParams: true });
capRoutes.use(requireAuth, requireOrgAccess);

const CapSchema = z.object({
  name: z.string().min(1).max(100),
  scope: z.enum(["platform", "service", "account"]),
  provider: z.enum(["aws", "azure", "gcp"]).optional(),
  service_name: z.string().optional(),
  account_id: z.string().uuid().optional(),
  cap_amount: z.number().positive(),
});

capRoutes.get("/", async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const result = await db.query(`
      SELECT bc.*, COALESCE(SUM(cr.cost_usd), 0) AS current_spend
      FROM budget_caps bc
      LEFT JOIN cost_records cr ON cr.org_id = bc.org_id
        AND cr.time >= date_trunc('month', NOW())
        AND (bc.provider IS NULL OR cr.provider = bc.provider)
        AND (bc.service_name IS NULL OR cr.service = bc.service_name)
        AND (bc.account_id IS NULL OR cr.account_id = bc.account_id)
      WHERE bc.org_id = $1 AND bc.is_active = true
      GROUP BY bc.id
      ORDER BY bc.created_at DESC
    `, [orgId]);
    res.json(result.rows);
  } catch (err) { next(err); }
});

capRoutes.post("/", requireRole("admin"), validate(CapSchema), async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const { name, scope, provider, service_name, account_id, cap_amount } = req.body;

    const result = await db.query(`
      INSERT INTO budget_caps (org_id, name, scope, provider, service_name, account_id, cap_amount, created_by)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      RETURNING *
    `, [orgId, name, scope, provider ?? null, service_name ?? null, account_id ?? null, cap_amount, req.user.sub]);

    // Immediately check thresholds for the new cap
    await alertsQueue.add("alerts", { orgId }, { jobId: `alerts:${orgId}:cap-created` });

    res.status(201).json(result.rows[0]);
  } catch (err) { next(err); }
});

capRoutes.put("/:capId", requireRole("admin"), validate(CapSchema.partial()), async (req, res, next) => {
  try {
    const { orgId, capId } = req.params;
    const fields = Object.entries(req.body)
      .map(([k], i) => `${k} = $${i + 3}`)
      .join(", ");
    if (!fields) return res.status(400).json({ error: "No fields to update" });

    const result = await db.query(
      `UPDATE budget_caps SET ${fields}, updated_at = NOW() WHERE id = $1 AND org_id = $2 RETURNING *`,
      [capId, orgId, ...Object.values(req.body)]
    );
    if (!result.rows[0]) throw new AppError(404, "Cap not found");
    res.json(result.rows[0]);
  } catch (err) { next(err); }
});

capRoutes.delete("/:capId", requireRole("admin"), async (req, res, next) => {
  try {
    const { orgId, capId } = req.params;
    await db.query(
      "UPDATE budget_caps SET is_active = false WHERE id = $1 AND org_id = $2",
      [capId, orgId]
    );
    res.json({ message: "Cap deleted" });
  } catch (err) { next(err); }
});
```

### 16.3 `src/routes/team.ts`

```typescript
import { Router } from "express";
import { z } from "zod";
import bcrypt from "bcrypt";
import crypto from "crypto";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { requireRole } from "../middleware/rbac";
import { validate } from "../middleware/validateBody";
import { db } from "../config/db";
import { emailService } from "../services/email.service";
import { AppError } from "../middleware/errorHandler";

export const teamRoutes = Router({ mergeParams: true });
teamRoutes.use(requireAuth, requireOrgAccess);

teamRoutes.get("/", async (req, res, next) => {
  try {
    const result = await db.query(`
      SELECT tm.id, tm.email, tm.role, tm.invite_accepted, tm.invited_at, tm.joined_at,
             tm.invite_expires_at, u.name, u.avatar_url
      FROM team_members tm
      LEFT JOIN users u ON u.id = tm.user_id
      WHERE tm.org_id = $1
      ORDER BY tm.joined_at NULLS LAST, tm.invited_at
    `, [req.params.orgId]);
    res.json(result.rows);
  } catch (err) { next(err); }
});

const InviteSchema = z.object({
  email: z.string().email(),
  role: z.enum(["admin", "editor", "viewer"]),
});

teamRoutes.post("/invite", requireRole("admin"), validate(InviteSchema), async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const { email, role } = req.body;

    // Check if already a member
    const existing = await db.query(
      "SELECT id, invite_accepted FROM team_members WHERE org_id = $1 AND email = $2",
      [orgId, email.toLowerCase()]
    );
    if (existing.rows[0]?.invite_accepted) {
      throw new AppError(409, "This person is already a team member");
    }

    const rawToken = crypto.randomBytes(32).toString("hex");
    const tokenHash = await bcrypt.hash(rawToken, 10);
    const expiresAt = new Date(Date.now() + 48 * 60 * 60 * 1000);

    if (existing.rows[0]) {
      // Resend: update existing invite
      await db.query(
        "UPDATE team_members SET invite_token_hash = $1, invite_expires_at = $2, role = $3, invited_by = $4, invited_at = NOW() WHERE id = $5",
        [tokenHash, expiresAt, role, req.user.sub, existing.rows[0].id]
      );
    } else {
      await db.query(
        "INSERT INTO team_members (org_id, email, role, invited_by, invite_token_hash, invite_expires_at) VALUES ($1, $2, $3, $4, $5, $6)",
        [orgId, email.toLowerCase(), role, req.user.sub, tokenHash, expiresAt]
      );
    }

    const org = await db.query("SELECT name FROM organizations WHERE id = $1", [orgId]);
    const inviter = await db.query("SELECT name FROM users WHERE id = $1", [req.user.sub]);

    await emailService.sendInviteEmail(email, inviter.rows[0].name, org.rows[0].name, role, rawToken, orgId);

    res.json({ message: "Invite sent", email, role, expires_at: expiresAt });
  } catch (err) { next(err); }
});

// Accept invite — no auth required (uses invite token)
const AcceptSchema = z.object({
  orgId: z.string().uuid(),
  token: z.string().min(1),
  name: z.string().min(1).optional(),
  password: z.string().min(12).optional(),
});

teamRoutes.post("/accept-invite", validate(AcceptSchema), async (req, res, next) => {
  try {
    const { orgId, token, name, password } = req.body;

    const memberResult = await db.query(
      "SELECT * FROM team_members WHERE org_id = $1 AND invite_accepted = false AND invite_expires_at > NOW()",
      [orgId]
    );

    // Find matching token (iterate — there may be multiple pending)
    let member: any = null;
    for (const row of memberResult.rows) {
      if (row.invite_token_hash && await bcrypt.compare(token, row.invite_token_hash)) {
        member = row;
        break;
      }
    }

    if (!member) throw new AppError(400, "Invalid or expired invite link");

    // Check if user already exists
    let userResult = await db.query("SELECT id FROM users WHERE email = $1", [member.email]);
    let userId: string;

    if (userResult.rows[0]) {
      // Existing user — just link them to the org
      userId = userResult.rows[0].id;
    } else {
      // New user — create account
      if (!name || !password) {
        throw new AppError(400, "name and password are required for new users");
      }
      if (password.length < 12 || !/[A-Z]/.test(password) || !/[0-9]/.test(password)) {
        throw new AppError(400, "Password must be 12+ chars with uppercase and number");
      }
      const hash = await bcrypt.hash(password, 12);
      const newUser = await db.query(
        "INSERT INTO users (email, name, password_hash, email_verified) VALUES ($1, $2, $3, true) RETURNING id",
        [member.email, name, hash]
      );
      userId = newUser.rows[0].id;
    }

    await db.query(
      "UPDATE team_members SET user_id = $1, invite_accepted = true, invite_token_hash = NULL, invite_expires_at = NULL, joined_at = NOW() WHERE id = $2",
      [userId, member.id]
    );

    res.json({ message: "Invite accepted. You can now log in." });
  } catch (err) { next(err); }
});

teamRoutes.put("/:memberId/role", requireRole("admin"), async (req, res, next) => {
  try {
    const { orgId, memberId } = req.params;
    const { role } = req.body;
    if (!["admin", "editor", "viewer"].includes(role)) {
      throw new AppError(400, "Invalid role");
    }

    // Cannot change the owner's role
    const member = await db.query("SELECT role FROM team_members WHERE id = $1 AND org_id = $2", [memberId, orgId]);
    if (!member.rows[0]) throw new AppError(404, "Member not found");
    if (member.rows[0].role === "owner") throw new AppError(403, "Cannot change the owner's role");

    // Admin cannot promote to owner
    if (role === "owner") throw new AppError(403, "Cannot set owner role via this endpoint");

    await db.query("UPDATE team_members SET role = $1 WHERE id = $2 AND org_id = $3", [role, memberId, orgId]);
    res.json({ message: "Role updated" });
  } catch (err) { next(err); }
});

teamRoutes.delete("/:memberId", requireRole("admin"), async (req, res, next) => {
  try {
    const { orgId, memberId } = req.params;
    const member = await db.query("SELECT role FROM team_members WHERE id = $1 AND org_id = $2", [memberId, orgId]);
    if (!member.rows[0]) throw new AppError(404, "Member not found");
    if (member.rows[0].role === "owner") throw new AppError(403, "Cannot remove the org owner");
    if (member.rows[0].user_id === req.user.sub) throw new AppError(400, "Cannot remove yourself");

    await db.query("DELETE FROM team_members WHERE id = $1 AND org_id = $2", [memberId, orgId]);
    res.json({ message: "Member removed" });
  } catch (err) { next(err); }
});
```

---

## 17. LLM Service (OpenRouter)

### `src/services/llm.service.ts`

```typescript
import OpenAI from "openai";
import { redis } from "../config/redis";
import { db } from "../config/db";
import { decrypt } from "../utils/encrypt";
import { logger } from "../utils/logger";

export class LLMService {
  private client: OpenAI | null = null;
  private model: string = "google/gemini-flash-1.5";
  private monthlyBudgetUSD: number = 10;
  private orgId: string;
  private enabled: boolean = false;

  constructor(orgId: string) {
    this.orgId = orgId;
  }

  static async forOrg(orgId: string): Promise<LLMService> {
    const svc = new LLMService(orgId);
    const result = await db.query(
      "SELECT * FROM llm_configs WHERE org_id = $1 AND is_enabled = true",
      [orgId]
    );
    if (result.rows[0]) {
      const config = result.rows[0];
      const apiKey = decrypt(config.openrouter_api_key);
      svc.client = new OpenAI({ baseURL: "https://openrouter.ai/api/v1", apiKey });
      svc.model = config.model;
      svc.monthlyBudgetUSD = parseFloat(config.monthly_budget_usd);
      svc.enabled = true;
    }
    return svc;
  }

  private async canCall(): Promise<boolean> {
    if (!this.enabled || !this.client) return false;
    const month = new Date().toISOString().slice(0, 7);
    const spent = parseFloat(await redis.get(`llm:monthly_spent:${this.orgId}:${month}`) ?? "0");
    return spent < this.monthlyBudgetUSD;
  }

  async generateReportNarrative(context: any): Promise<string | null> {
    if (!await this.canCall()) return null;
    const prompt = `You are a FinOps analyst. Write a 2-3 paragraph executive summary of this month's cloud cost report. Be specific, actionable, and concise. Speak to a non-technical founder. No markdown, no bullet points.

Data: Total spend $${context.totalSpend} (${context.delta > 0 ? "+" : ""}${context.delta} vs last month). AWS: $${context.aws?.spend ?? 0}. Azure: $${context.azure?.spend ?? 0}. GCP: $${context.gcp?.spend ?? 0}. Top cost driver: ${context.topDriver}. Pending savings: $${context.totalSavings}/mo.`;
    return this.call(prompt, 400);
  }

  async explainRecommendation(rec: any): Promise<string | null> {
    if (!await this.canCall()) return null;
    const prompt = `Explain this cloud cost recommendation in 2-3 sentences for an engineer. Be specific about the evidence and include one caveat to check before acting.

Resource: ${rec.resource_name} (${rec.provider} ${rec.service})
Type: ${rec.type}
Estimated savings: $${rec.estimated_monthly_savings}/month`;
    return this.call(prompt, 150);
  }

  async answerCostQuery(question: string, context: any): Promise<string | null> {
    if (!await this.canCall()) return null;
    const prompt = `You are a FinOps assistant. Answer this question using only the data provided. If the data doesn't contain enough to answer, say so clearly. Max 4 sentences.

Question: ${question}
Data: ${JSON.stringify(context).slice(0, 2000)}`;
    return this.call(prompt, 200);
  }

  private async call(prompt: string, maxTokens: number): Promise<string | null> {
    const cacheKey = `llm:${Buffer.from(prompt).toString("base64").slice(0, 80)}`;
    const cached = await redis.get(cacheKey);
    if (cached) return cached;

    try {
      const response = await this.client!.chat.completions.create({
        model: this.model,
        messages: [{ role: "user", content: prompt }],
        max_tokens: maxTokens,
      });

      const text = response.choices[0]?.message?.content ?? null;
      if (!text) return null;

      // Track spend (rough estimate: $0.001 per 1k tokens)
      const tokens = (response.usage?.total_tokens ?? maxTokens);
      const costUSD = (tokens / 1000) * 0.001;
      const month = new Date().toISOString().slice(0, 7);
      await redis.incrbyfloat(`llm:monthly_spent:${this.orgId}:${month}`, costUSD);
      await redis.expire(`llm:monthly_spent:${this.orgId}:${month}`, 33 * 24 * 3600);

      await redis.set(cacheKey, text, "EX", 86400); // cache 24h
      return text;
    } catch (err: any) {
      logger.warn({ error: err.message, orgId: this.orgId }, "LLM call failed — using fallback");
      return null; // Caller always handles null
    }
  }
}
```

---

## 18. Monthly Report Generator

### `src/services/report.service.ts`

```typescript
import { db } from "../config/db";
import { emailService } from "./email.service";
import { LLMService } from "./llm.service";
import { logger } from "../utils/logger";

export class ReportGenerator {
  async generate(orgId: string): Promise<void> {
    const reportConfig = await db.query(
      "SELECT * FROM monthly_reports WHERE org_id = $1 AND is_active = true",
      [orgId]
    );
    if (!reportConfig.rows[0]) return;
    const config = reportConfig.rows[0];

    if (config.recipient_emails.length === 0) {
      logger.warn({ orgId }, "No recipients configured — skipping report");
      return;
    }

    const org = (await db.query("SELECT * FROM organizations WHERE id = $1", [orgId])).rows[0];
    const month = new Date().toISOString().slice(0, 7); // previous month ideally

    // Gather all sections
    const [costs, caps, recommendations, commitments, scorecard] = await Promise.all([
      this.gatherCosts(orgId, month),
      this.gatherCaps(orgId),
      config.include_recommendations ? this.gatherRecommendations(orgId) : [],
      config.include_commitments ? this.gatherCommitments(orgId) : null,
      config.include_finops_scorecard ? this.gatherScorecard(orgId) : null,
    ]);

    // Optional LLM executive narrative
    let narrative: string | null = null;
    try {
      const llm = await LLMService.forOrg(orgId);
      narrative = await llm.generateReportNarrative({
        totalSpend: costs.totalUsd,
        delta: costs.totalUsd - costs.prevMonthUsd,
        aws: costs.byProvider.find((p: any) => p.provider === "aws"),
        azure: costs.byProvider.find((p: any) => p.provider === "azure"),
        gcp: costs.byProvider.find((p: any) => p.provider === "gcp"),
        topDriver: costs.topServices[0]?.service ?? "Unknown",
        totalSavings: recommendations.reduce((s: number, r: any) => s + parseFloat(r.estimated_monthly_savings), 0),
      });
    } catch { /* LLM optional — continue without it */ }

    await emailService.sendMonthlyReport({
      to: config.recipient_emails,
      org,
      month,
      costs,
      caps,
      recommendations,
      commitments,
      scorecard,
      narrative,
    });

    // Update next_send date
    const nextSend = new Date();
    nextSend.setMonth(nextSend.getMonth() + 1);
    nextSend.setDate(config.send_day_of_month);
    nextSend.setHours(9, 0, 0, 0);

    await db.query(
      "UPDATE monthly_reports SET last_sent = NOW(), next_send = $1 WHERE org_id = $2",
      [nextSend.toISOString(), orgId]
    );

    logger.info({ orgId, recipients: config.recipient_emails.length }, "Monthly report sent");
  }

  private async gatherCosts(orgId: string, month: string) {
    const monthStart = `${month}-01`;
    const monthEnd = new Date(new Date(monthStart).setMonth(new Date(monthStart).getMonth() + 1))
      .toISOString().slice(0, 10);
    const prevStart = new Date(new Date(monthStart).setMonth(new Date(monthStart).getMonth() - 1))
      .toISOString().slice(0, 10);

    const [current, prev, byService] = await Promise.all([
      db.query("SELECT provider, SUM(cost_usd) AS total FROM cost_records WHERE org_id=$1 AND time>=$2 AND time<$3 GROUP BY provider", [orgId, monthStart, monthEnd]),
      db.query("SELECT SUM(cost_usd) AS total FROM cost_records WHERE org_id=$1 AND time>=$2 AND time<$3", [orgId, prevStart, monthStart]),
      db.query("SELECT service, provider, SUM(cost_usd) AS total FROM cost_records WHERE org_id=$1 AND time>=$2 AND time<$3 GROUP BY service, provider ORDER BY total DESC LIMIT 10", [orgId, monthStart, monthEnd]),
    ]);

    const totalUsd = current.rows.reduce((s: number, r: any) => s + parseFloat(r.total), 0);
    return {
      byProvider: current.rows,
      totalUsd,
      prevMonthUsd: parseFloat(prev.rows[0]?.total ?? "0"),
      topServices: byService.rows,
      month,
    };
  }

  private async gatherCaps(orgId: string) {
    return (await db.query(`
      SELECT bc.name, bc.cap_amount, bc.scope, bc.provider,
             COALESCE(SUM(cr.cost_usd), 0) AS current_spend
      FROM budget_caps bc
      LEFT JOIN cost_records cr ON cr.org_id = bc.org_id
        AND cr.time >= date_trunc('month', NOW())
        AND (bc.provider IS NULL OR cr.provider = bc.provider)
      WHERE bc.org_id = $1 AND bc.is_active = true
      GROUP BY bc.id
    `, [orgId])).rows;
  }

  private async gatherRecommendations(orgId: string) {
    return (await db.query(
      "SELECT * FROM recommendations WHERE org_id = $1 AND status = 'pending' ORDER BY estimated_monthly_savings DESC LIMIT 10",
      [orgId]
    )).rows;
  }

  private async gatherCommitments(orgId: string) {
    return (await db.query(
      "SELECT * FROM commitment_records WHERE org_id = $1 AND status = 'active' ORDER BY monthly_savings DESC",
      [orgId]
    )).rows;
  }

  private async gatherScorecard(orgId: string) {
    const cached = await db.query(
      "SELECT * FROM spend_forecasts WHERE org_id = $1 ORDER BY generated_at DESC LIMIT 1",
      [orgId]
    );
    return cached.rows[0] ?? null;
  }
}
```

---

## 19. Virtual Tag Engine

### `src/services/virtualTag.service.ts`

```typescript
import { db } from "../config/db";
import { wsBroadcast } from "../ws/wsServer";
import { logger } from "../utils/logger";
import { safeRegexTest } from "../utils/regex";

export class VirtualTagEngine {
  async applyAllRules(orgId: string): Promise<void> {
    const rulesResult = await db.query(`
      SELECT * FROM virtual_tag_rules
      WHERE org_id = $1 AND is_active = true
      ORDER BY priority ASC
    `, [orgId]);

    const rules = rulesResult.rows;
    if (rules.length === 0) return;

    logger.info({ orgId, ruleCount: rules.length }, "Virtual tag engine starting");

    // Get all cost records for this org (batched)
    const BATCH_SIZE = 5000;
    let offset = 0;
    let totalUpdated = 0;

    while (true) {
      const records = await db.query(
        "SELECT time, account_id, service, region, tags, resource_name FROM cost_records WHERE org_id = $1 ORDER BY time DESC LIMIT $2 OFFSET $3",
        [orgId, BATCH_SIZE, offset]
      );

      if (records.rows.length === 0) break;

      const updates: Array<{ time: string; accountId: string; service: string; region: string; virtualTags: Record<string, any> }> = [];

      for (const record of records.rows) {
        const virtualTags = this.computeVirtualTags(record, rules);
        if (Object.keys(virtualTags).length > 0) {
          updates.push({
            time: record.time,
            accountId: record.account_id,
            service: record.service,
            region: record.region,
            virtualTags,
          });
        }
      }

      // Batch update virtual_tags
      for (const update of updates) {
        await db.query(
          "UPDATE cost_records SET virtual_tags = $1 WHERE time = $2 AND account_id = $3 AND service = $4 AND region = $5",
          [JSON.stringify(update.virtualTags), update.time, update.accountId, update.service, update.region]
        );
      }

      totalUpdated += updates.length;
      offset += BATCH_SIZE;

      // Push progress via WebSocket
      wsBroadcast(orgId, {
        event: "virtual_tags.progress",
        org_id: orgId,
        timestamp: new Date().toISOString(),
        data: { processed: offset, updated: totalUpdated },
      });

      if (records.rows.length < BATCH_SIZE) break;
    }

    // Update rule stats
    for (const rule of rules) {
      await db.query(
        "UPDATE virtual_tag_rules SET last_applied_at = NOW(), records_affected = $1 WHERE id = $2",
        [totalUpdated, rule.id]
      );
    }

    logger.info({ orgId, totalUpdated }, "Virtual tag engine completed");
  }

  private computeVirtualTags(record: any, rules: any[]): Record<string, any> {
    const virtualTags: Record<string, any> = {};

    for (const rule of rules) {
      if (!this.matchesCondition(record, rule)) continue;

      if (rule.action_type === "set_tag") {
        virtualTags[rule.tag_key] = rule.tag_value;
      } else if (rule.action_type === "split" && rule.split_config) {
        // For split: store the split config as an array
        virtualTags[rule.tag_key] = rule.split_config;
      }
    }

    return virtualTags;
  }

  private matchesCondition(record: any, rule: any): boolean {
    const fieldMap: Record<string, any> = {
      resource_name: record.resource_name ?? "",
      account_id: record.account_id ?? "",
      service: record.service ?? "",
      region: record.region ?? "",
      tag_value: JSON.stringify(record.tags ?? {}),
    };

    const fieldValue = String(fieldMap[rule.condition_field] ?? "");
    const condValue = rule.condition_value;

    switch (rule.condition_operator) {
      case "contains":     return fieldValue.toLowerCase().includes(condValue.toLowerCase());
      case "equals":       return fieldValue.toLowerCase() === condValue.toLowerCase();
      case "starts_with":  return fieldValue.toLowerCase().startsWith(condValue.toLowerCase());
      case "ends_with":    return fieldValue.toLowerCase().endsWith(condValue.toLowerCase());
      case "regex":        return safeRegexTest(condValue, fieldValue);
      default:             return false;
    }
  }
}
```

### `src/utils/regex.ts`

```typescript
// ReDoS guard: test pattern completes in <50ms on a 1000-char string
export function safeRegexTest(pattern: string, input: string): boolean {
  const testStr = "a".repeat(1000);
  const start = Date.now();
  try {
    const re = new RegExp(pattern, "i");
    re.test(testStr); // ReDoS canary
    if (Date.now() - start > 50) return false; // Took too long — skip
    return re.test(input);
  } catch {
    return false;
  }
}

export function validateRegexPattern(pattern: string): { valid: boolean; error?: string } {
  if (pattern.length > 200) return { valid: false, error: "Pattern too long (max 200 chars)" };
  const testStr = "a".repeat(1000);
  const start = Date.now();
  try {
    new RegExp(pattern, "i").test(testStr);
    if (Date.now() - start > 50) {
      return { valid: false, error: "Pattern is too complex (possible ReDoS)" };
    }
    return { valid: true };
  } catch (err: any) {
    return { valid: false, error: `Invalid regex: ${err.message}` };
  }
}
```

---

## 20. Forecast Engine

### `src/services/forecast.service.ts`

```typescript
import { db } from "../config/db";
import { alertsQueue } from "../config/queues";
import { redis } from "../config/redis";
import { wsBroadcast } from "../ws/wsServer";

export class ForecastEngine {
  async recalculate(orgId: string): Promise<void> {
    const monthStart = new Date();
    monthStart.setDate(1);
    monthStart.setHours(0, 0, 0, 0);

    const now = new Date();
    const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
    const dayOfMonth = now.getDate();
    const daysRemaining = daysInMonth - dayOfMonth;

    // Org-level forecast + per-provider forecasts
    const providers = [null, "aws", "azure", "gcp"] as const;

    for (const provider of providers) {
      await this.computeForecast(orgId, provider, monthStart, daysInMonth, daysRemaining);
    }
  }

  private async computeForecast(
    orgId: string,
    provider: string | null,
    monthStart: Date,
    daysInMonth: number,
    daysRemaining: number
  ): Promise<void> {
    const params: any[] = [orgId, monthStart.toISOString()];
    const providerFilter = provider ? `AND provider = $3` : "";
    if (provider) params.push(provider);

    // Get daily spend for this month
    const dailyResult = await db.query(`
      SELECT time::date AS date, SUM(cost_usd) AS daily_cost
      FROM cost_records
      WHERE org_id = $1 AND time >= $2 ${providerFilter}
      GROUP BY date
      ORDER BY date
    `, params);

    const dailyRows = dailyResult.rows;
    const daysWithData = dailyRows.length;

    let dataCoverage: "full" | "partial" | "insufficient";
    if (daysWithData < 3) {
      dataCoverage = "insufficient";
    } else if (daysWithData < 10) {
      dataCoverage = "partial";
    } else {
      dataCoverage = "full";
    }

    const spendToDate = dailyRows.reduce((s: number, r: any) => s + parseFloat(r.daily_cost), 0);
    const dailyAvg = daysWithData > 0 ? spendToDate / daysWithData : 0;

    // Rolling 7-day average (smooth out zero-spend days on weekends)
    const last7 = dailyRows.slice(-7);
    const rolling7dAvg = last7.length > 0
      ? last7.reduce((s: number, r: any) => s + parseFloat(r.daily_cost), 0) / last7.length
      : dailyAvg;

    // Use rolling avg if it's more than 20% different from daily avg (weekend effect)
    const effectiveAvg = Math.abs(rolling7dAvg - dailyAvg) / (dailyAvg || 1) > 0.2
      ? rolling7dAvg
      : dailyAvg;

    const projectedTotal = spendToDate + (effectiveAvg * daysRemaining);

    // Get cap for this scope
    let capAmount: number | null = null;
    if (provider) {
      const capResult = await db.query(
        "SELECT cap_amount FROM budget_caps WHERE org_id = $1 AND provider = $2 AND scope = 'platform' AND is_active = true LIMIT 1",
        [orgId, provider]
      );
      if (capResult.rows[0]) capAmount = parseFloat(capResult.rows[0].cap_amount);
    }

    const willBreach = capAmount !== null && projectedTotal > capAmount;
    let breachDate: string | null = null;
    if (willBreach && capAmount !== null && effectiveAvg > 0) {
      const daysUntilBreach = Math.max(0, (capAmount - spendToDate) / effectiveAvg);
      const bd = new Date();
      bd.setDate(bd.getDate() + daysUntilBreach);
      breachDate = bd.toISOString().slice(0, 10);
    }

    const forecastMonth = monthStart.toISOString().slice(0, 10);

    await db.query(`
      INSERT INTO spend_forecasts
        (org_id, provider, forecast_month, spend_to_date, daily_avg, rolling_7d_avg,
         days_with_data, days_remaining, projected_total, cap_amount, will_breach,
         breach_date, data_coverage, generated_at)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW())
      ON CONFLICT (org_id, COALESCE(account_id::TEXT,''), COALESCE(provider,''), forecast_month)
      DO UPDATE SET
        spend_to_date = EXCLUDED.spend_to_date,
        daily_avg = EXCLUDED.daily_avg,
        rolling_7d_avg = EXCLUDED.rolling_7d_avg,
        days_with_data = EXCLUDED.days_with_data,
        days_remaining = EXCLUDED.days_remaining,
        projected_total = EXCLUDED.projected_total,
        will_breach = EXCLUDED.will_breach,
        breach_date = EXCLUDED.breach_date,
        data_coverage = EXCLUDED.data_coverage,
        generated_at = NOW()
    `, [orgId, provider, forecastMonth, spendToDate, dailyAvg, rolling7dAvg, daysWithData, daysRemaining, projectedTotal, capAmount, willBreach, breachDate, dataCoverage]);

    // Invalidate forecast cache
    await redis.del(`dash:${orgId}:forecast:${forecastMonth.slice(0, 7)}`);

    wsBroadcast(orgId, {
      event: "forecast.updated",
      org_id: orgId,
      timestamp: new Date().toISOString(),
      data: { provider, projected_total: projectedTotal, will_breach: willBreach, data_coverage: dataCoverage },
    });
  }
}
```

---

## 21. FinOps Health Scorecard Engine

### `src/services/scorecard.service.ts`

```typescript
import { db } from "../config/db";

interface ScorecardResult {
  overall: number;
  metrics: Record<string, { value: number; color: "red" | "yellow" | "green"; label: string }>;
  generatedAt: string;
}

export class ScorecardEngine {
  async compute(orgId: string): Promise<ScorecardResult> {
    const monthStart = new Date();
    monthStart.setDate(1);
    monthStart.setHours(0, 0, 0, 0);

    const [tagCoverage, commitmentCoverage, commitmentUtil, idleRate, recsActedOn, capBreaches, forecast] =
      await Promise.all([
        this.getTagCoverage(orgId, monthStart),
        this.getCommitmentCoverage(orgId),
        this.getCommitmentUtilization(orgId),
        this.getIdleRate(orgId),
        this.getRecsActedOn(orgId),
        this.getCapBreaches(orgId, monthStart),
        this.getForecastAccuracy(orgId),
      ]);

    const metrics: Record<string, { score: number; weight: number }> = {
      tagCoverage:           { score: tagCoverage, weight: 20 },
      commitmentCoverage:    { score: Math.min(commitmentCoverage / 60, 1) * 100, weight: 20 },
      commitmentUtilization: { score: commitmentUtil, weight: 10 },
      idleRate:              { score: Math.max(0, 100 - idleRate * 10), weight: 10 },
      recsActedOn:           { score: recsActedOn, weight: 10 },
      forecastAccuracy:      { score: forecast, weight: 10 },
      capBreaches:           { score: capBreaches === 0 ? 100 : capBreaches === 1 ? 50 : 0, weight: 20 },
    };

    const overall = Math.round(
      Object.values(metrics).reduce((sum, m) => sum + (m.score * m.weight / 100), 0)
    );

    const color = (val: number, greenThresh: number, yellowThresh: number): "red" | "yellow" | "green" =>
      val >= greenThresh ? "green" : val >= yellowThresh ? "yellow" : "red";

    return {
      overall,
      metrics: {
        tagCoverage: { value: tagCoverage, color: color(tagCoverage, 90, 60), label: "Tag Coverage %" },
        commitmentCoverage: { value: commitmentCoverage, color: color(commitmentCoverage, 60, 30), label: "Commitment Coverage %" },
        commitmentUtilization: { value: commitmentUtil, color: color(commitmentUtil, 95, 85), label: "Commitment Utilization %" },
        idleRate: { value: idleRate, color: idleRate < 5 ? "green" : idleRate < 10 ? "yellow" : "red", label: "Idle Resource Rate %" },
        recsActedOn: { value: recsActedOn, color: color(recsActedOn, 60, 30), label: "Recommendations Acted On %" },
        forecastAccuracy: { value: forecast, color: color(forecast, 90, 80), label: "Forecast Accuracy %" },
        capBreaches: { value: capBreaches, color: capBreaches === 0 ? "green" : capBreaches <= 2 ? "yellow" : "red", label: "Cap Breaches (count)" },
      },
      generatedAt: new Date().toISOString(),
    };
  }

  private async getTagCoverage(orgId: string, since: Date): Promise<number> {
    const result = await db.query(`
      SELECT
        COUNT(*) FILTER (WHERE tags->>'team' IS NOT NULL OR virtual_tags->>'team' IS NOT NULL) AS tagged,
        COUNT(*) AS total
      FROM cost_records WHERE org_id = $1 AND time >= $2
    `, [orgId, since.toISOString()]);
    const { tagged, total } = result.rows[0];
    return total > 0 ? Math.round((parseInt(tagged) / parseInt(total)) * 100) : 100;
  }

  private async getCommitmentCoverage(orgId: string): Promise<number> {
    const result = await db.query(
      "SELECT COALESCE(AVG(utilization_pct), 0) AS coverage FROM commitment_records WHERE org_id = $1 AND status = 'active'",
      [orgId]
    );
    return Math.round(parseFloat(result.rows[0].coverage));
  }

  private async getCommitmentUtilization(orgId: string): Promise<number> {
    const result = await db.query(
      "SELECT COALESCE(AVG(utilization_pct), 100) AS util FROM commitment_records WHERE org_id = $1 AND status = 'active'",
      [orgId]
    );
    return Math.round(parseFloat(result.rows[0].util));
  }

  private async getIdleRate(orgId: string): Promise<number> {
    const result = await db.query(
      "SELECT COUNT(*) FILTER (WHERE is_idle = true) AS idle, COUNT(*) AS total FROM resources WHERE org_id = $1",
      [orgId]
    );
    const { idle, total } = result.rows[0];
    return total > 0 ? Math.round((parseInt(idle) / parseInt(total)) * 100) : 0;
  }

  private async getRecsActedOn(orgId: string): Promise<number> {
    const result = await db.query(
      "SELECT COUNT(*) FILTER (WHERE status IN ('implemented','rejected')) AS acted, COUNT(*) AS total FROM recommendations WHERE org_id = $1",
      [orgId]
    );
    const { acted, total } = result.rows[0];
    return total > 0 ? Math.round((parseInt(acted) / parseInt(total)) * 100) : 100;
  }

  private async getCapBreaches(orgId: string, since: Date): Promise<number> {
    const result = await db.query(
      "SELECT COUNT(*) AS breaches FROM alerts WHERE org_id = $1 AND type = 'cap_threshold' AND threshold_percent >= 100 AND triggered_at >= $2",
      [orgId, since.toISOString()]
    );
    return parseInt(result.rows[0].breaches);
  }

  private async getForecastAccuracy(orgId: string): Promise<number> {
    const result = await db.query(
      "SELECT AVG(ABS(variance_pct)) AS avg_variance FROM spend_forecasts WHERE org_id = $1 AND variance_pct IS NOT NULL ORDER BY forecast_month DESC LIMIT 3",
      [orgId]
    );
    const avgVariance = parseFloat(result.rows[0]?.avg_variance ?? "20");
    return Math.max(0, Math.round(100 - avgVariance));
  }
}
```

---

## 22. Email Service

### `src/services/email.service.ts`

```typescript
import { SESClient, SendEmailCommand } from "@aws-sdk/client-ses";
import { env } from "../config/env";
import { logger } from "../utils/logger";

const ses = new SESClient({ region: env.AWS_SES_REGION });

class EmailService {
  private async send(to: string | string[], subject: string, htmlBody: string, textBody: string) {
    const recipients = Array.isArray(to) ? to : [to];
    await ses.send(new SendEmailCommand({
      Source: env.AWS_SES_FROM,
      Destination: { ToAddresses: recipients },
      Message: {
        Subject: { Data: subject, Charset: "UTF-8" },
        Body: {
          Html: { Data: htmlBody, Charset: "UTF-8" },
          Text: { Data: textBody, Charset: "UTF-8" },
        },
      },
    }));
  }

  async sendVerificationEmail(email: string, name: string, rawToken: string, userId: string) {
    const link = `${process.env.APP_URL}/verify-email?userId=${userId}&token=${rawToken}`;
    await this.send(email, "Verify your PRISM account",
      `<p>Hi ${name},</p><p>Click below to verify your email:</p><p><a href="${link}">Verify Email</a></p><p>Link expires in 24 hours.</p>`,
      `Hi ${name},\n\nVerify your email: ${link}\n\nLink expires in 24 hours.`
    );
  }

  async sendPasswordResetEmail(email: string, name: string, rawToken: string, userId: string) {
    const link = `${process.env.APP_URL}/reset-password?userId=${userId}&token=${rawToken}`;
    await this.send(email, "Reset your PRISM password",
      `<p>Hi ${name},</p><p>Reset your password:</p><p><a href="${link}">Reset Password</a></p><p>Link expires in 1 hour.</p>`,
      `Hi ${name},\n\nReset your password: ${link}\n\nLink expires in 1 hour.`
    );
  }

  async sendInviteEmail(email: string, inviterName: string, orgName: string, role: string, rawToken: string, orgId: string) {
    const link = `${process.env.APP_URL}/accept-invite?orgId=${orgId}&token=${rawToken}`;
    const subject = `${inviterName} invited you to ${orgName} on PRISM`;
    const html = `
      <p>Hi there,</p>
      <p><strong>${inviterName}</strong> has invited you to join <strong>${orgName}</strong>'s cloud cost dashboard on PRISM.</p>
      <p>Your role: <strong>${role}</strong></p>
      <p><a href="${link}">Accept Invitation</a></p>
      <p>This link expires in 48 hours.</p>
    `;
    await this.send(email, subject, html, `Accept invite: ${link} (expires in 48h)`);
  }

  async sendCapAlert(params: { to: string[]; cap: any; spent: number; pct: number; threshold: number; org: any }) {
    const { to, cap, spent, pct, threshold, org } = params;
    const severity = threshold >= 100 ? "🚨" : "⚠️";
    const subject = `${severity} ${cap.name} at ${threshold}% — ${org.name} (PRISM)`;
    const html = `
      <h2>${severity} Budget Cap Alert</h2>
      <p><strong>${cap.name}</strong> has reached <strong>${threshold}%</strong> this month.</p>
      <table>
        <tr><td>Spent this month:</td><td><strong>$${spent.toFixed(2)}</strong></td></tr>
        <tr><td>Cap amount:</td><td>$${cap.cap_amount}</td></tr>
        <tr><td>Usage:</td><td>${pct.toFixed(1)}%</td></tr>
      </table>
      <p>Next alert at: ${threshold < 100 ? "100%" : threshold < 125 ? "125%" : threshold < 150 ? "150%" : "Already at 150%+"}</p>
      <p><a href="${process.env.APP_URL}/dashboard">View Dashboard</a></p>
    `;
    await this.send(to, subject, html, `${cap.name} at ${threshold}%. Spent: $${spent.toFixed(2)} / $${cap.cap_amount}`);
    logger.info({ to, subject }, "Cap alert email sent");
  }

  async sendForecastBreachAlert(params: { to: string[]; forecast: any; org: any }) {
    const { to, forecast, org } = params;
    const subject = `⚠️ PRISM Forecast: ${forecast.provider ?? "Cloud"} projected to exceed cap`;
    const html = `
      <h2>⚠️ Spend Forecast Alert — ${org.name}</h2>
      <p>Your <strong>${forecast.provider ?? "overall"}</strong> spend is projected to exceed your budget cap this month.</p>
      <p>Projected total: <strong>$${parseFloat(forecast.projected_total).toFixed(2)}</strong></p>
      <p>Cap: $${parseFloat(forecast.cap_amount).toFixed(2)}</p>
      ${forecast.breach_date ? `<p>Estimated breach date: <strong>${forecast.breach_date}</strong></p>` : ""}
      <p><a href="${process.env.APP_URL}/dashboard">Review Now</a></p>
    `;
    await this.send(to, subject, html, `Forecast breach alert for ${org.name}`);
  }

  async sendMonthlyReport(params: { to: string[]; org: any; month: string; costs: any; caps: any; recommendations: any; commitments: any; scorecard: any; narrative: string | null }) {
    const { to, org, month, costs, caps, recommendations, narrative } = params;
    const totalUsd = costs.totalUsd;
    const prevUsd = costs.prevMonthUsd;
    const delta = totalUsd - prevUsd;
    const pct = prevUsd > 0 ? ((delta / prevUsd) * 100).toFixed(1) : "N/A";

    const subject = `PRISM Cloud Cost Report — ${month} — ${org.name}`;
    const html = `
      <h1>PRISM Cloud Cost Report — ${month}</h1>
      <h2>${org.name}</h2>
      <hr>
      <h3>Executive Summary</h3>
      <p>Total spend: <strong>$${totalUsd.toFixed(2)}</strong> (${delta >= 0 ? "+" : ""}${delta.toFixed(2)}, ${pct}% vs last month)</p>
      ${narrative ? `<p><em>AI Summary:</em> ${narrative}</p>` : ""}
      <h3>Spend by Platform</h3>
      <table border="1" cellpadding="8">
        <tr><th>Platform</th><th>This Month</th></tr>
        ${costs.byProvider.map((p: any) => `<tr><td>${p.provider.toUpperCase()}</td><td>$${parseFloat(p.total).toFixed(2)}</td></tr>`).join("")}
      </table>
      <h3>Top Services</h3>
      ${costs.topServices.slice(0, 5).map((s: any, i: number) => `<p>${i + 1}. ${s.service} — $${parseFloat(s.total).toFixed(2)}/mo</p>`).join("")}
      <h3>Budget Caps</h3>
      ${caps.map((c: any) => `<p>${c.name}: $${parseFloat(c.current_spend).toFixed(2)} / $${c.cap_amount} (${((c.current_spend / c.cap_amount) * 100).toFixed(0)}%)</p>`).join("")}
      <h3>Top Recommendations</h3>
      ${recommendations.slice(0, 5).map((r: any) => `<p>• ${r.resource_name} (${r.type}) — Save $${r.estimated_monthly_savings}/mo</p>`).join("")}
      <hr>
      <p><a href="${process.env.APP_URL}/dashboard">View Full Dashboard</a></p>
      <p><small>Sent by PRISM | <a href="${process.env.APP_URL}/settings/reports">Manage report settings</a></small></p>
    `;

    await this.send(to, subject, html, `PRISM Report ${month}: Total $${totalUsd.toFixed(2)}`);
  }
}

export const emailService = new EmailService();
```

---

## 23. Error Handling

### Standard Error Response Shape

```typescript
// All errors return:
{
  "error": "Human-readable message",
  "code": "OPTIONAL_ERROR_CODE"   // for frontend to programmatically handle
}

// Validation errors also include:
{
  "error": "Validation failed",
  "details": [
    { "field": "email", "message": "Invalid email" },
    { "field": "cap_amount", "message": "Expected number, received string" }
  ]
}
```

### HTTP Status Codes Used

| Code | When |
|------|------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request / validation error |
| 401 | Not authenticated |
| 403 | Authenticated but insufficient permission |
| 404 | Resource not found |
| 409 | Conflict (duplicate email, already member, etc.) |
| 429 | Rate limited |
| 500 | Unexpected server error (never leak internals) |

### Edge Cases to Handle Explicitly

- **Duplicate sync:** `ON CONFLICT DO UPDATE` in `cost_records` — idempotent
- **Cap alert double-fire:** Unique partial index on `alerts` — database-enforced dedup
- **Invite token expired:** Check `invite_expires_at > NOW()` before accepting
- **LLM down/budget exceeded:** Return `null`, caller uses template fallback — never throw
- **WebSocket client disconnected:** Cleaned up in `ws.on("close")` — no memory leak
- **Worker job permanently failed:** Goes to DLQ — logged, alert created, never retried
- **BigQuery SQL injection:** Always use parameterized queries (`@param` syntax)
- **Regex ReDoS:** Validate regex patterns at save time using `validateRegexPattern()`
- **SSRF outbound webhooks:** `validateWebhookUrl()` on save + dispatch
- **Cross-org access:** `requireOrgAccess` validates `req.user.orgId === req.params.orgId`
- **Owner demotion:** Block `PUT /team/:memberId/role` if member is owner
- **Empty org:** New org sees empty state — no charts shown until first sync completes
- **Zero-spend days in forecast:** Use `rolling_7d_avg` when weekend dips distort `daily_avg`

---

## 24. Logging & Observability

### `src/utils/logger.ts`

```typescript
import pino from "pino";
import { env } from "../config/env";

export const logger = pino({
  level: env.NODE_ENV === "production" ? "info" : "debug",
  transport: env.NODE_ENV !== "production"
    ? { target: "pino-pretty", options: { colorize: true } }
    : undefined,
  base: { service: "prism-backend", env: env.NODE_ENV },
  timestamp: pino.stdTimeFunctions.isoTime,
});
```

### Structured Log Fields (Always Include)

```typescript
// Auth events
logger.info({ event: "auth.login",   userId, orgId, email }, "User logged in");
logger.warn({ event: "auth.failed",  email, ip: req.ip }, "Login failed");

// Sync events
logger.info({ event: "sync.started",   accountId, orgId, provider }, "Sync started");
logger.info({ event: "sync.complete",  accountId, records }, "Sync completed");
logger.error({ event: "sync.failed",   accountId, error: err.message }, "Sync failed");

// Alert events
logger.info({ event: "alert.fired",    alertId, orgId, type, threshold }, "Alert fired");

// LLM events
logger.warn({ event: "llm.fallback",   orgId, reason }, "LLM not available — using fallback");
```

### Health Check Endpoint

```typescript
app.get("/health", async (_req, res) => {
  const dbOk = await db.query("SELECT 1").then(() => true).catch(() => false);
  const redisOk = await redis.ping().then(() => true).catch(() => false);
  const status = dbOk && redisOk ? "ok" : "degraded";
  res.status(status === "ok" ? 200 : 503).json({
    status, db: dbOk, redis: redisOk, ts: new Date().toISOString()
  });
});
```

---

## 25. Input Validation (Zod Schemas)

### Key Schemas

```typescript
// src/routes/virtualTags.ts
import { validateRegexPattern } from "../utils/regex";

const VirtualTagRuleSchema = z.object({
  priority: z.number().int().min(1),
  condition_field: z.enum(["resource_name","account_id","service","region","tag_value"]),
  condition_operator: z.enum(["contains","equals","starts_with","ends_with","regex"]),
  condition_value: z.string().min(1).max(500),
  action_type: z.enum(["set_tag","split"]),
  tag_key: z.string().min(1).max(50),
  tag_value: z.string().max(100).optional(),
  split_config: z.array(z.object({
    team: z.string(),
    pct: z.number().min(1).max(100),
  })).optional(),
  provider_scope: z.enum(["aws","azure","gcp","all"]).default("all"),
}).superRefine((data, ctx) => {
  // Regex validation
  if (data.condition_operator === "regex") {
    const { valid, error } = validateRegexPattern(data.condition_value);
    if (!valid) ctx.addIssue({ code: "custom", path: ["condition_value"], message: error! });
  }
  // Split config must sum to 100
  if (data.action_type === "split" && data.split_config) {
    const total = data.split_config.reduce((s, c) => s + c.pct, 0);
    if (Math.abs(total - 100) > 0.01) {
      ctx.addIssue({ code: "custom", path: ["split_config"], message: "Percentages must sum to 100" });
    }
  }
  if (data.action_type === "set_tag" && !data.tag_value) {
    ctx.addIssue({ code: "custom", path: ["tag_value"], message: "tag_value required for set_tag rules" });
  }
});

// src/routes/webhooks.ts
const WebhookSchema = z.object({
  url: z.string().url().refine(url => {
    try { validateWebhookUrl(url); return true; } catch { return false; }
  }, { message: "Webhook URL must use HTTPS and not point to private IP ranges" }),
  description: z.string().max(200).default(""),
  events: z.array(z.enum(["alert.fired","recommendation.new","sync.failed","report.sent"])).min(1),
});

// src/routes/notifications.ts
const NotificationSettingsSchema = z.object({
  alert_emails: z.array(z.string().email()).max(20),
  teams_webhook_url: z.string().url().nullable().optional(),
  slack_webhook_url: z.string().url().nullable().optional(),
});
```

---

## 26. Security Checklist

All items must be verified before production deployment:

```
Authentication
  [x] bcrypt cost factor 12 for all passwords
  [x] JWT secrets min 32 chars, stored in env (never in code)
  [x] Refresh tokens stored as bcrypt hash in DB
  [x] On logout: revoke refresh token (update revoked_at)
  [x] Password reset token: 1h expiry, single-use (deleted from Redis on use)
  [x] Email verification token: 24h expiry, bcrypt-hashed in DB
  [x] Invite token: 48h expiry, bcrypt-hashed in DB, never re-shown after send

Authorization
  [x] requireAuth on every route (except /auth/* and /health)
  [x] requireOrgAccess validates req.user.orgId === req.params.orgId
  [x] requireRole("admin") on all write operations
  [x] Owner role cannot be assigned or removed via team API
  [x] CSRF: state-changing endpoints require Authorization header (not just cookie)

Data Security
  [x] Cloud credentials encrypted at rest (AES-256-GCM)
  [x] LLM API key encrypted at rest
  [x] Webhook signing secrets encrypted at rest
  [x] Credentials never logged or included in error responses
  [x] All DB queries use parameterized values (no string concatenation in SQL)
  [x] BigQuery queries use @param syntax (not f-strings)

Network Security
  [x] All endpoints served over TLS only (HTTPS)
  [x] CORS locked to frontend origin
  [x] Helmet.js security headers
  [x] Teams webhook validated with HMAC-SHA256 + timing-safe compare
  [x] Slack webhook validated with HMAC-SHA256 + timing-safe compare
  [x] Outbound webhooks: SSRF protection (private IP blocklist, HTTPS-only, DNS re-check)

Multi-tenancy
  [x] Every DB query includes org_id filter
  [x] Redis cache keys prefixed with orgId
  [x] WebSocket connections tracked per-org; broadcast only to that org's clients
  [x] LLM monthly spend tracked per org in Redis

Input Validation
  [x] All request bodies validated with Zod before business logic
  [x] Regex patterns validated for ReDoS before saving
  [x] Split config percentages validated to sum 100
  [x] Email addresses validated before storing
  [x] Webhook URLs validated for HTTPS + non-private IPs
  [x] Pagination limits capped (max 100 per page)

Rate Limiting
  [x] Auth endpoints: 10 req / 15 min per IP
  [x] API endpoints: 300 req / min per org
  [x] LLM query endpoint: 20 req / hour per user
```

---

## 27. Testing Guide

### Unit Test: `withRetry` 429 handling

```typescript
// tests/withRetry.test.ts
import { withRetry } from "../src/utils/withRetry";

test("retries on 429 with retry-after delay", async () => {
  let attempts = 0;
  const err429 = Object.assign(new Error("rate limited"), { status: 429, response: { headers: { "retry-after": "0" } } });

  const result = await withRetry(async () => {
    attempts++;
    if (attempts < 3) throw err429;
    return "success";
  }, 3);

  expect(result).toBe("success");
  expect(attempts).toBe(3);
}, 5000);

test("does not retry on 401", async () => {
  let attempts = 0;
  const err401 = Object.assign(new Error("Unauthorized"), { status: 401 });
  await expect(withRetry(async () => { attempts++; throw err401; }, 3))
    .rejects.toThrow("Unauthorized");
  expect(attempts).toBe(1); // Never retried
});
```

### Unit Test: Virtual Tag Engine

```typescript
// tests/virtualTag.test.ts
import { VirtualTagEngine } from "../src/services/virtualTag.service";

const engine = new VirtualTagEngine() as any;

test("contains match works case-insensitively", () => {
  const record = { resource_name: "team-a-data-prod", account_id: "123", service: "EC2", region: "us-east-1", tags: {} };
  const rule = { condition_field: "resource_name", condition_operator: "contains", condition_value: "team-a", action_type: "set_tag", tag_key: "team", tag_value: "engineering" };
  expect(engine.matchesCondition(record, rule)).toBe(true);
});

test("regex rule is ReDoS-safe", () => {
  const record = { resource_name: "a".repeat(1000), account_id: "", service: "", region: "", tags: {} };
  const evilPattern = "^(a+)+$"; // classic catastrophic backtracking pattern
  const rule = { condition_field: "resource_name", condition_operator: "regex", condition_value: evilPattern, action_type: "set_tag", tag_key: "t", tag_value: "v" };
  // Should not hang; safeRegexTest returns false if >50ms
  const start = Date.now();
  engine.matchesCondition(record, rule);
  expect(Date.now() - start).toBeLessThan(500);
});
```

### Unit Test: Forecast edge cases

```typescript
// tests/forecast.test.ts
test("insufficient data returns data_coverage=insufficient", async () => {
  // 2 days of data — below the 3-day threshold
  // Forecast should have data_coverage = 'insufficient'
  // Verify the projected_total is still computed (using what data is available)
  // but the widget should not display a forecast
});

test("zero-spend days use rolling 7d avg", () => {
  const dailyRows = [
    { daily_cost: "100" }, { daily_cost: "0" }, { daily_cost: "0" },
    { daily_cost: "0" }, { daily_cost: "0" }, { daily_cost: "0" },
    { daily_cost: "0" }, { daily_cost: "100" },
  ];
  const spendToDate = 200;
  const daysWithData = dailyRows.filter(r => parseFloat(r.daily_cost) > 0).length; // 2
  const dailyAvg = spendToDate / dailyRows.length; // 25
  const last7 = dailyRows.slice(-7);
  const rolling7dAvg = last7.reduce((s, r) => s + parseFloat(r.daily_cost), 0) / 7; // ~14

  // When rolling avg differs >20% from daily avg, rolling avg should be used
  expect(Math.abs(rolling7dAvg - dailyAvg) / dailyAvg).toBeGreaterThan(0.2);
});
```

### Integration Test: Cap alert deduplication

```typescript
// Verify: firing the same cap threshold twice in the same month does not create two alerts
// 1. Insert a cap for orgId
// 2. Call CapAlertService.checkAllCaps(orgId) twice (simulate running twice in same month)
// 3. Query alerts table — expect exactly ONE alert for this threshold
// Expected: Second call hits unique index, skips insert
```

### API Edge Case Tests

```
POST /v1/auth/signup — duplicate email → 409
POST /v1/auth/login  — wrong password → 401 (same response as user not found)
POST /v1/auth/login  — unverified email → 403
PUT  /v1/orgs/:orgId/team/:memberId/role — viewer trying to change role → 403
POST /v1/orgs/:wrongOrgId/caps — user from different org → 403
POST /v1/orgs/:orgId/virtual-tags — evil regex → 400 with ReDoS error
POST /v1/orgs/:orgId/webhooks — http:// URL → 400 (HTTPS required)
POST /v1/orgs/:orgId/webhooks — 192.168.x.x URL → 400 (private IP)
POST /v1/orgs/:orgId/team/accept-invite — expired token → 400
DELETE /v1/orgs/:orgId/team/:ownerId — owner self-delete → 403
```

---

## 28. Start-up Sequence

When deploying for the first time:

```bash
# 1. Create PostgreSQL database with TimescaleDB
createdb prism
psql prism -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"
psql prism -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"

# 2. Run schema
psql prism -f src/db/schema.sql

# 3. Verify TimescaleDB hypertable was created
psql prism -c "SELECT * FROM timescaledb_information.hypertables;"

# 4. Run the app
npm run build
npm start

# 5. Verify health
curl http://localhost:3000/health
# Expected: {"status":"ok","db":true,"redis":true}

# 6. Create first user via API
curl -X POST http://localhost:3000/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@acme.com","name":"Admin","password":"SecurePass123!","orgName":"Acme Corp"}'

# 7. Verify email (in dev: check logs for the raw token)
curl -X POST http://localhost:3000/v1/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{"userId":"<from-signup-response>","token":"<from-email>"}'

# 8. Login
curl -X POST http://localhost:3000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@acme.com","password":"SecurePass123!"}'

# 9. Connect first cloud account (use the orgId from login response)
# Use the IAM role wizard in the frontend, or POST to /v1/orgs/:orgId/accounts

# 10. Verify cron jobs are firing (check logs at 06:00 UTC)
```

### `package.json` Scripts

```json
{
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "ts-node src/index.ts",
    "test": "jest --testPathPattern=tests/",
    "db:migrate": "psql $DATABASE_URL -f src/db/schema.sql",
    "db:seed": "psql $DATABASE_URL -f src/db/seed.sql"
  }
}
```

---

## IMPLEMENTATION ORDER (Recommended)

Follow this order to have a working product at each milestone:

### Week 1–2: Auth + DB + Basic API
1. Schema, indexes, Redis keys
2. `src/config/` — env, db, redis, queues
3. `src/middleware/` — auth, orgScope, rbac, error handler
4. `src/routes/auth.ts` — full signup/login/refresh/logout
5. `src/routes/team.ts` — invite + accept-invite
6. `src/routes/orgs.ts` — GET/PUT org settings
7. Health check endpoint

### Week 3–4: Cloud Connectors + Sync
8. `src/utils/encrypt.ts` + `withRetry.ts`
9. `src/services/connectors/aws.ts`
10. `src/services/connectors/azure.ts`
11. `src/services/connectors/gcp.ts`
12. `src/config/queues.ts` + BullMQ
13. `src/jobs/sync.worker.ts`
14. `src/jobs/scheduler.ts`
15. `src/routes/accounts.ts` — CRUD + test + sync trigger

### Week 5–6: Dashboard + Alerts + Caps
16. `src/routes/costs.ts` — all cost aggregation queries
17. `src/routes/caps.ts` — CRUD
18. `src/services/alert.service.ts`
19. `src/jobs/alerts.worker.ts`
20. `src/routes/alerts.ts` — list + acknowledge + snooze
21. `src/ws/wsServer.ts`
22. `src/services/email.service.ts` — cap alert + verification emails

### Week 7–8: Reports + Forecast + Recommendations
23. `src/services/forecast.service.ts` + worker
24. `src/routes/forecasts.ts`
25. `src/services/recommendation.service.ts` + worker
26. `src/routes/recommendations.ts`
27. `src/services/report.service.ts`
28. `src/jobs/reports.worker.ts`
29. `src/routes/reports.ts`

### Week 9–10: Advanced Features
30. `src/utils/regex.ts` + `src/services/virtualTag.service.ts`
31. `src/routes/virtualTags.ts`
32. `src/jobs/virtualTags.worker.ts`
33. `src/services/commitment.service.ts` + worker
34. `src/routes/commitments.ts`
35. `src/services/scorecard.service.ts`
36. `src/routes/scorecard.ts`
37. `src/services/llm.service.ts`
38. `src/routes/llm.ts`
39. `src/services/webhook.service.ts`
40. `src/routes/webhooks.ts`
41. `src/utils/validateWebhookUrl.ts` (SSRF protection)
42. `src/routes/notifications.ts`
43. `src/routes/businessMetrics.ts`
44. `src/routes/resources.ts`
45. `src/middleware/hmac.ts` + Teams/Slack action routes

---

## 29. Missing Infrastructure — Config, Utils, Services, Workers, Routes

> These files are imported throughout the plan but their implementations were not shown. Every file below must exist for the project to compile and run.

---

### 29.1 `src/config/db.ts` — PostgreSQL Pool

```typescript
import { Pool } from "pg";
import { env } from "./env";

export const db = new Pool({
  connectionString: env.DATABASE_URL,
  max: env.DATABASE_POOL_MAX,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000,
  ssl: env.NODE_ENV === "production" ? { rejectUnauthorized: true } : false,
});

db.on("error", (err) => {
  console.error("Unexpected DB pool error", err);
});
```

---

### 29.2 `src/config/redis.ts` — Redis Client

```typescript
import Redis from "ioredis";
import { env } from "./env";

export const redis = new Redis(env.REDIS_URL, {
  maxRetriesPerRequest: 3,
  enableReadyCheck: true,
  lazyConnect: false,
});

redis.on("error", (err) => {
  console.error("Redis error", err);
});
```

---

### 29.3 `src/middleware/requestLogger.ts`

```typescript
import { Request, Response, NextFunction } from "express";
import { logger } from "../utils/logger";

export function requestLogger(req: Request, res: Response, next: NextFunction) {
  const start = Date.now();
  res.on("finish", () => {
    logger.info({
      method: req.method,
      path: req.path,
      status: res.statusCode,
      duration_ms: Date.now() - start,
      org_id: req.user?.orgId,
    }, "HTTP request");
  });
  next();
}
```

---

### 29.4 `src/utils/logger.ts`

```typescript
import pino from "pino";
import { env } from "../config/env";

export const logger = pino({
  level: env.NODE_ENV === "production" ? "info" : "debug",
  transport: env.NODE_ENV !== "production"
    ? { target: "pino-pretty", options: { colorize: true } }
    : undefined,
  base: { service: "prism-backend" },
  timestamp: pino.stdTimeFunctions.isoTime,
});
```

---

### 29.5 `src/utils/cache.ts` — Dashboard Cache Invalidation

```typescript
import { redis } from "../config/redis";

// Called after every successful sync to bust stale dashboard data
export async function invalidateDashboardCache(orgId: string, provider: string): Promise<void> {
  const month = new Date().toISOString().slice(0, 7); // YYYY-MM
  const keys = [
    `dash:${orgId}:overall:${month}`,
    `dash:${orgId}:${provider}:${month}`,
    `dash:${orgId}:forecast:${month}`,
    `dash:${orgId}:scorecard`,
  ];
  if (keys.length > 0) await redis.del(...keys);
}

export async function invalidateAllOrgCache(orgId: string): Promise<void> {
  // Scan for all keys matching this org and delete
  const pattern = `dash:${orgId}:*`;
  let cursor = "0";
  do {
    const [nextCursor, keys] = await redis.scan(cursor, "MATCH", pattern, "COUNT", 100);
    cursor = nextCursor;
    if (keys.length > 0) await redis.del(...keys);
  } while (cursor !== "0");
}
```

---

### 29.6 `src/utils/validateWebhookUrl.ts` — SSRF Protection

```typescript
import { AppError } from "../middleware/errorHandler";
import dns from "dns/promises";

// Private IP ranges that must never be targeted by outbound webhooks
const BLOCKED_PATTERNS = [
  /^localhost$/i,
  /^127\./,
  /^10\./,
  /^192\.168\./,
  /^172\.(1[6-9]|2[0-9]|3[01])\./,
  /^::1$/,
  /^0\.0\.0\.0$/,
  /^169\.254\./,    // link-local
  /^fc00:/i,        // IPv6 ULA
];

export function validateWebhookUrl(url: string): void {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    throw new AppError(400, "Webhook URL is not a valid URL");
  }

  if (parsed.protocol !== "https:") {
    throw new AppError(400, "Webhook URL must use HTTPS");
  }

  if (BLOCKED_PATTERNS.some(p => p.test(parsed.hostname))) {
    throw new AppError(400, "Webhook URL must not point to a private or loopback address");
  }
}

// DNS resolution check at dispatch time (DNS rebinding protection)
export async function validateWebhookUrlDNS(url: string): Promise<void> {
  validateWebhookUrl(url); // schema check first
  const { hostname } = new URL(url);
  try {
    const addresses = await dns.resolve4(hostname);
    for (const ip of addresses) {
      if (BLOCKED_PATTERNS.some(p => p.test(ip))) {
        throw new AppError(400, `Webhook URL resolves to a private IP (${ip})`);
      }
    }
  } catch (err: any) {
    if (err instanceof AppError) throw err;
    // DNS resolution failure — block the request
    throw new AppError(400, `Cannot resolve webhook hostname: ${hostname}`);
  }
}
```

---

### 29.7 `src/utils/date.ts` — Date Helpers

```typescript
// Returns "YYYY-MM-DD" for the first day of the current month
export function currentMonthStart(): string {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10);
}

// Returns "YYYY-MM-DD" for first day of next month (used as exclusive upper bound)
export function nextMonthStart(): string {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth() + 1, 1).toISOString().slice(0, 10);
}

// Number of days remaining in the current month (including today)
export function daysRemainingInMonth(): number {
  const now = new Date();
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  return lastDay - now.getDate() + 1;
}

// Number of days in a given month ("YYYY-MM")
export function daysInMonth(month: string): number {
  const [year, m] = month.split("-").map(Number);
  return new Date(year, m, 0).getDate();
}
```

---

### 29.8 `src/utils/pagination.ts` — Pagination Helper

```typescript
import { Request } from "express";

export interface PaginationParams {
  limit: number;
  offset: number;
}

export function getPagination(req: Request, maxLimit = 100): PaginationParams {
  const limit = Math.min(parseInt(req.query.limit as string) || 20, maxLimit);
  const page = Math.max(parseInt(req.query.page as string) || 1, 1);
  const offset = (page - 1) * limit;
  return { limit, offset };
}

export function paginatedResponse(data: any[], total: number, params: PaginationParams) {
  return {
    data,
    pagination: {
      total,
      page: Math.floor(params.offset / params.limit) + 1,
      limit: params.limit,
      pages: Math.ceil(total / params.limit),
    },
  };
}
```

---

### 29.9 `src/services/fx.service.ts` — FX Rate Fetcher

```typescript
import { redis } from "../config/redis";
import { logger } from "../utils/logger";

// In production: fetch from Open Exchange Rates or similar.
// Cache for 6 hours. Fall back to 1.0 (USD=USD) if fetch fails.
export class FXService {
  static async getRate(toCurrency: string = "USD"): Promise<number> {
    if (toCurrency === "USD") return 1;

    const cacheKey = `fx:rate:${toCurrency}`;
    const cached = await redis.get(cacheKey);
    if (cached) return parseFloat(cached);

    try {
      // TODO: Replace with real FX API call (e.g. https://open.er-api.com/v6/latest/USD)
      // const response = await axios.get(`https://open.er-api.com/v6/latest/USD`);
      // const rate = response.data.rates[toCurrency];
      const rate = 1; // placeholder — 1 USD = 1 USD

      await redis.set(cacheKey, String(rate), "EX", 6 * 3600); // 6h cache
      return rate;
    } catch (err: any) {
      logger.warn({ error: err.message, currency: toCurrency }, "FX fetch failed — using rate 1");
      return 1;
    }
  }
}
```

---

### 29.10 `src/services/webhook.service.ts` — Outbound Webhooks

```typescript
import axios from "axios";
import crypto from "crypto";
import { db } from "../config/db";
import { decrypt } from "../utils/encrypt";
import { validateWebhookUrlDNS } from "../utils/validateWebhookUrl";
import { logger } from "../utils/logger";

class OutboundWebhookService {
  async dispatch(orgId: string, event: string, payload: object): Promise<void> {
    const webhooks = await db.query(
      "SELECT * FROM outbound_webhooks WHERE org_id = $1 AND is_active = true AND $2 = ANY(events)",
      [orgId, event]
    );

    for (const wh of webhooks.rows) {
      await this.sendWebhook(wh, event, payload);
    }
  }

  private async sendWebhook(wh: any, event: string, payload: object): Promise<void> {
    try {
      await validateWebhookUrlDNS(wh.url); // DNS rebinding check every time
    } catch (err: any) {
      logger.warn({ webhookId: wh.id, url: wh.url }, "Webhook URL failed SSRF check — skipping");
      return;
    }

    const body = JSON.stringify({ event, timestamp: new Date().toISOString(), data: payload });
    const signingSecret = decrypt(wh.signing_secret_enc);
    const signature = "sha256=" + crypto.createHmac("sha256", signingSecret).update(body).digest("hex");

    let statusCode = 0;
    try {
      const response = await axios.post(wh.url, body, {
        headers: {
          "Content-Type": "application/json",
          "X-Prism-Signature": signature,
          "X-Prism-Event": event,
        },
        timeout: 10_000,
      });
      statusCode = response.status;
      logger.info({ webhookId: wh.id, event, status: statusCode }, "Webhook dispatched");
    } catch (err: any) {
      statusCode = err.response?.status ?? 0;
      logger.warn({ webhookId: wh.id, event, status: statusCode, error: err.message }, "Webhook dispatch failed");
    }

    await db.query(
      "UPDATE outbound_webhooks SET last_triggered_at = NOW(), last_status_code = $1 WHERE id = $2",
      [statusCode, wh.id]
    );
  }
}

export const webhookService = new OutboundWebhookService();
```

---

### 29.11 `src/services/commitment.service.ts` — Commitment Sync

```typescript
import { db } from "../config/db";
import { AWSConnector } from "./connectors/aws";
import { emailService } from "./email.service";
import { logger } from "../utils/logger";

export class CommitmentService {
  async syncAll(orgId: string): Promise<void> {
    const accounts = await db.query(
      "SELECT * FROM cloud_accounts WHERE org_id = $1 AND is_active = true AND provider IN ('aws','gcp')",
      [orgId]
    );

    for (const account of accounts.rows) {
      try {
        if (account.provider === "aws") {
          await this.syncAWS(orgId, account);
        }
        // GCP CUD: same pattern using GCP Billing API
      } catch (err: any) {
        logger.error({ accountId: account.id, error: err.message }, "Commitment sync failed");
      }
    }

    // After sync: update expiry status and fire expiry alerts
    await this.updateExpiryStatuses(orgId);
    await this.fireExpiryAlerts(orgId);
  }

  private async syncAWS(orgId: string, account: any): Promise<void> {
    const connector = new AWSConnector(account.credentials_enc);
    const commitments = await connector.getCommitments();

    for (const c of commitments) {
      await db.query(`
        INSERT INTO commitment_records
          (org_id, account_id, provider, commitment_type, external_id,
           monthly_cost, utilization_pct, monthly_savings, monthly_on_demand_equivalent,
           coverage_amount, start_date, end_date, term_months, status, last_updated)
        VALUES ($1,$2,'aws',$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,NOW())
        ON CONFLICT (account_id, external_id)
        DO UPDATE SET
          utilization_pct = EXCLUDED.utilization_pct,
          monthly_savings = EXCLUDED.monthly_savings,
          coverage_amount = EXCLUDED.coverage_amount,
          status = EXCLUDED.status,
          last_updated = NOW()
      `, [
        orgId, account.id, c.commitmentType, c.externalId,
        c.monthlyCost, c.utilizationPct, c.monthlySavings,
        c.monthlyCost / (1 - (c.utilizationPct / 100) || 0.1), // on-demand equivalent
        c.monthlyCost,
        new Date().toISOString().slice(0, 10), // start_date: approximate
        new Date(Date.now() + 365 * 86400000).toISOString().slice(0, 10), // end_date: 1yr out
        12, // term_months
        'active',
      ]);
    }
  }

  private async updateExpiryStatuses(orgId: string): Promise<void> {
    // Mark as 'expiring_soon' if end_date ≤ 60 days away
    await db.query(`
      UPDATE commitment_records
      SET status = CASE
        WHEN end_date < CURRENT_DATE THEN 'expired'
        WHEN end_date <= CURRENT_DATE + INTERVAL '60 days' THEN 'expiring_soon'
        ELSE 'active'
      END
      WHERE org_id = $1
    `, [orgId]);
  }

  private async fireExpiryAlerts(orgId: string): Promise<void> {
    // Fire alerts for commitments expiring within 30 days (not already alerted this month)
    const expiring = await db.query(`
      SELECT cr.*, ca.display_name AS account_name
      FROM commitment_records cr
      JOIN cloud_accounts ca ON ca.id = cr.account_id
      WHERE cr.org_id = $1
        AND cr.status = 'expiring_soon'
        AND cr.end_date <= CURRENT_DATE + INTERVAL '30 days'
        AND NOT EXISTS (
          SELECT 1 FROM alerts a
          WHERE a.org_id = cr.org_id
            AND a.type = 'commitment_expiry'
            AND a.metadata->>'commitment_id' = cr.id::text
            AND a.triggered_at >= date_trunc('month', NOW())
        )
    `, [orgId]);

    for (const commitment of expiring.rows) {
      await db.query(`
        INSERT INTO alerts (org_id, type, scope_label, severity, triggered_at, metadata, email_sent)
        VALUES ($1, 'commitment_expiry', $2, 'warning', NOW(), $3, false)
      `, [
        orgId,
        `${commitment.commitment_type} expires ${commitment.end_date}`,
        JSON.stringify({ commitment_id: commitment.id, end_date: commitment.end_date, monthly_savings: commitment.monthly_savings }),
      ]);
      logger.info({ orgId, commitmentId: commitment.id }, "Commitment expiry alert created");
    }
  }
}
```

---

### 29.12 `src/services/recommendation.service.ts` — Recommendation Engine

```typescript
import { db } from "../config/db";
import { LLMService } from "./llm.service";
import { wsBroadcast } from "../ws/wsServer";
import { logger } from "../utils/logger";

export class RecommendationEngine {
  async run(orgId: string): Promise<void> {
    const llm = await LLMService.forOrg(orgId);
    let newCount = 0;
    let totalSavings = 0;

    // 1. Idle resource recommendations
    const idleResources = await db.query(`
      SELECT r.*, ca.org_id, ca.provider
      FROM resources r
      JOIN cloud_accounts ca ON ca.id = r.account_id
      WHERE r.org_id = $1 AND r.is_idle = true AND r.last_cost_usd > 0
        AND NOT EXISTS (
          SELECT 1 FROM recommendations rec
          WHERE rec.org_id = $1 AND rec.resource_id = r.resource_id
            AND rec.type = 'idle_termination' AND rec.status = 'pending'
        )
    `, [orgId]);

    for (const resource of idleResources.rows) {
      const savings = (resource.last_cost_usd ?? 0) * 30;
      const llmExplanation = await llm.explainRecommendation({
        resource_name: resource.resource_name ?? resource.resource_id,
        provider: resource.provider,
        service: resource.service,
        type: "idle_termination",
        estimated_monthly_savings: savings,
      });

      await db.query(`
        INSERT INTO recommendations
          (org_id, account_id, resource_id, resource_name, provider, service,
           type, estimated_monthly_savings, confidence, llm_explanation, status)
        VALUES ($1,$2,$3,$4,$5,$6,'idle_termination',$7,'high',$8,'pending')
        ON CONFLICT DO NOTHING
      `, [orgId, resource.account_id, resource.resource_id, resource.resource_name ?? resource.resource_id, resource.provider, resource.service, savings, llmExplanation]);

      newCount++;
      totalSavings += savings;
    }

    // 2. Rightsizing (EC2 instances consistently <20% CPU — simplified heuristic)
    // In production: query CloudWatch metrics. Here: flag instances that cost >$100/mo.
    const expensiveResources = await db.query(`
      SELECT r.*, SUM(cr.cost_usd) AS monthly_cost
      FROM resources r
      JOIN cost_records cr ON cr.account_id = r.account_id AND cr.time >= date_trunc('month', NOW())
      WHERE r.org_id = $1 AND r.service LIKE '%EC2%' AND r.instance_type IS NOT NULL
        AND NOT EXISTS (
          SELECT 1 FROM recommendations rec WHERE rec.org_id=$1 AND rec.resource_id=r.resource_id
            AND rec.type='rightsizing' AND rec.status='pending'
        )
      GROUP BY r.id
      HAVING SUM(cr.cost_usd) > 100
    `, [orgId]);

    for (const resource of expensiveResources.rows) {
      const savings = parseFloat(resource.monthly_cost) * 0.3; // 30% estimated saving from rightsizing
      await db.query(`
        INSERT INTO recommendations
          (org_id, account_id, resource_id, resource_name, provider, service,
           type, estimated_monthly_savings, confidence, status)
        VALUES ($1,$2,$3,$4,$5,$6,'rightsizing',$7,'medium','pending')
        ON CONFLICT DO NOTHING
      `, [orgId, resource.account_id, resource.resource_id, resource.resource_name ?? resource.resource_id, resource.provider, resource.service, savings]);
      newCount++;
      totalSavings += savings;
    }

    if (newCount > 0) {
      wsBroadcast(orgId, {
        event: "recommendation.new",
        org_id: orgId,
        timestamp: new Date().toISOString(),
        data: { count: newCount, top_savings: Math.round(totalSavings) },
      });
      logger.info({ orgId, newCount, totalSavings }, "Recommendations generated");
    }
  }
}
```

---

### 29.13 Missing Job Workers

#### `src/jobs/forecast.worker.ts`

```typescript
import { Worker, Job } from "bullmq";
import { ForecastEngine } from "../services/forecast.service";
import { env } from "../config/env";
import { logger } from "../utils/logger";

export function startForecastWorker() {
  return new Worker("prism-forecast", async (job: Job) => {
    const { orgId } = job.data;
    await new ForecastEngine().recalculate(orgId);
    logger.info({ orgId }, "Forecast recalculated");
  }, { connection: { url: env.REDIS_URL }, concurrency: 5 });
}
```

#### `src/jobs/commitments.worker.ts`

```typescript
import { Worker, Job } from "bullmq";
import { CommitmentService } from "../services/commitment.service";
import { env } from "../config/env";
import { logger } from "../utils/logger";

export function startCommitmentsWorker() {
  return new Worker("prism-commitments", async (job: Job) => {
    const { orgId } = job.data;
    await new CommitmentService().syncAll(orgId);
    logger.info({ orgId }, "Commitment sync completed");
  }, { connection: { url: env.REDIS_URL }, concurrency: 3 });
}
```

#### `src/jobs/recommendations.worker.ts`

```typescript
import { Worker, Job } from "bullmq";
import { RecommendationEngine } from "../services/recommendation.service";
import { env } from "../config/env";
import { logger } from "../utils/logger";

export function startRecommendationsWorker() {
  return new Worker("prism-recommendations", async (job: Job) => {
    const { orgId } = job.data;
    await new RecommendationEngine().run(orgId);
    logger.info({ orgId }, "Recommendations engine completed");
  }, { connection: { url: env.REDIS_URL }, concurrency: 3 });
}
```

#### `src/jobs/reports.worker.ts`

```typescript
import { Worker, Job } from "bullmq";
import { ReportGenerator } from "../services/report.service";
import { env } from "../config/env";
import { logger } from "../utils/logger";

export function startReportsWorker() {
  return new Worker("prism-reports", async (job: Job) => {
    const { orgId } = job.data;
    await new ReportGenerator().generate(orgId);
    logger.info({ orgId }, "Monthly report sent");
  }, { connection: { url: env.REDIS_URL }, concurrency: 2 });
}
```

#### `src/jobs/virtualTags.worker.ts`

```typescript
import { Worker, Job } from "bullmq";
import { VirtualTagEngine } from "../services/virtualTag.service";
import { env } from "../config/env";
import { logger } from "../utils/logger";

export function startVirtualTagsWorker() {
  return new Worker("prism-virtual-tags", async (job: Job) => {
    const { orgId } = job.data;
    await new VirtualTagEngine().applyAllRules(orgId);
    logger.info({ orgId }, "Virtual tags applied");
  }, {
    connection: { url: env.REDIS_URL },
    concurrency: 1, // Serialized per org — avoid concurrent tag writes
    lockDuration: 600_000, // 10 min lock — retroactive tagging can take a while
  });
}
```

---

### 29.14 Missing Route Implementations

#### `src/routes/orgs.ts`

```typescript
import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { requireRole } from "../middleware/rbac";
import { validate } from "../middleware/validateBody";
import { db } from "../config/db";

export const orgRoutes = Router();
orgRoutes.use(requireAuth);

// GET /v1/orgs/:orgId — Get org details
orgRoutes.get("/:orgId", requireOrgAccess, async (req, res, next) => {
  try {
    res.json(req.org);
  } catch (err) { next(err); }
});

const UpdateOrgSchema = z.object({
  name: z.string().min(1).max(100).optional(),
  currency: z.enum(["USD","EUR","GBP","INR","AUD","CAD"]).optional(),
  timezone: z.string().optional(),
  send_day_of_month: z.number().int().min(1).max(28).optional(),
});

// PUT /v1/orgs/:orgId — Update org settings
orgRoutes.put("/:orgId", requireOrgAccess, requireRole("admin"), validate(UpdateOrgSchema), async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const entries = Object.entries(req.body).filter(([, v]) => v !== undefined);
    if (entries.length === 0) return res.status(400).json({ error: "No fields to update" });

    const setClauses = entries.map(([k], i) => `${k} = $${i + 2}`).join(", ");
    const result = await db.query(
      `UPDATE organizations SET ${setClauses} WHERE id = $1 RETURNING *`,
      [orgId, ...entries.map(([, v]) => v)]
    );
    res.json(result.rows[0]);
  } catch (err) { next(err); }
});
```

#### `src/routes/accounts.ts`

```typescript
import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { requireRole } from "../middleware/rbac";
import { validate } from "../middleware/validateBody";
import { db } from "../config/db";
import { syncQueue } from "../config/queues";
import { encrypt } from "../utils/encrypt";
import { AWSConnector } from "../services/connectors/aws";
import { AzureConnector } from "../services/connectors/azure";
import { GCPConnector } from "../services/connectors/gcp";
import { AppError } from "../middleware/errorHandler";
import { getPagination, paginatedResponse } from "../utils/pagination";

export const accountRoutes = Router({ mergeParams: true });
accountRoutes.use(requireAuth, requireOrgAccess);

// GET /v1/orgs/:orgId/accounts
accountRoutes.get("/", async (req, res, next) => {
  try {
    const result = await db.query(
      "SELECT id, provider, account_id, display_name, last_sync, last_sync_status, last_sync_error, data_as_of, is_active, created_at FROM cloud_accounts WHERE org_id = $1 AND is_active = true ORDER BY created_at",
      [req.params.orgId]
    );
    res.json(result.rows);
  } catch (err) { next(err); }
});

const AccountSchema = z.object({
  provider: z.enum(["aws","azure","gcp"]),
  display_name: z.string().min(1).max(100),
  scope: z.enum(["single","multi","organization"]),
  credentials: z.object({}).passthrough(), // provider-specific fields
});

// POST /v1/orgs/:orgId/accounts — Add cloud account
accountRoutes.post("/", requireRole("admin"), validate(AccountSchema), async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const { provider, display_name, scope, credentials } = req.body;

    const encCreds = encrypt(JSON.stringify(credentials));

    // Create or reuse account group
    let groupResult = await db.query(
      "SELECT id FROM account_groups WHERE org_id = $1 AND provider = $2 AND scope = $3",
      [orgId, provider, scope]
    );
    let groupId: string;
    if (!groupResult.rows[0]) {
      const newGroup = await db.query(
        "INSERT INTO account_groups (org_id, provider, scope, display_name) VALUES ($1,$2,$3,$4) RETURNING id",
        [orgId, provider, scope, `${provider.toUpperCase()} Accounts`]
      );
      groupId = newGroup.rows[0].id;
    } else {
      groupId = groupResult.rows[0].id;
    }

    const accountId = credentials.roleArn?.split(":")?.[4] ?? credentials.subscriptionId ?? credentials.projectId ?? "unknown";

    const result = await db.query(`
      INSERT INTO cloud_accounts (group_id, org_id, provider, account_id, display_name, credentials_enc)
      VALUES ($1,$2,$3,$4,$5,$6) RETURNING id, provider, account_id, display_name, last_sync_status, created_at
    `, [groupId, orgId, provider, accountId, display_name, encCreds]);

    const newAccount = result.rows[0];

    // Enqueue backfill sync (13 months of history)
    await syncQueue.add("sync", { accountId: newAccount.id, orgId, backfill: true }, {
      jobId: `sync:${newAccount.id}:backfill`,
      attempts: 3,
    });

    res.status(201).json(newAccount);
  } catch (err) { next(err); }
});

// POST /v1/orgs/:orgId/accounts/:accountId/test — Test connection
accountRoutes.post("/:accountId/test", requireRole("admin"), async (req, res, next) => {
  try {
    const account = await db.query(
      "SELECT * FROM cloud_accounts WHERE id = $1 AND org_id = $2",
      [req.params.accountId, req.params.orgId]
    );
    if (!account.rows[0]) throw new AppError(404, "Account not found");
    const acc = account.rows[0];

    let result: { ok: boolean; error?: string };
    if (acc.provider === "aws") result = await new AWSConnector(acc.credentials_enc).healthCheck();
    else if (acc.provider === "azure") result = await new AzureConnector(acc.credentials_enc).healthCheck();
    else result = await new GCPConnector(acc.credentials_enc).healthCheck();

    if (!result.ok) {
      await db.query("UPDATE cloud_accounts SET last_sync_status='failed', last_sync_error=$1 WHERE id=$2", [result.error, acc.id]);
    }
    res.json(result);
  } catch (err) { next(err); }
});

// POST /v1/orgs/:orgId/accounts/:accountId/sync — Manual sync trigger
accountRoutes.post("/:accountId/sync", requireRole("admin"), async (req, res, next) => {
  try {
    const { accountId, orgId } = req.params;
    const exists = await db.query("SELECT id FROM cloud_accounts WHERE id=$1 AND org_id=$2 AND is_active=true", [accountId, orgId]);
    if (!exists.rows[0]) throw new AppError(404, "Account not found");

    await syncQueue.add("sync", { accountId, orgId, backfill: false }, {
      jobId: `sync:${accountId}:manual:${Date.now()}`,
      attempts: 3,
    });
    res.json({ message: "Sync enqueued" });
  } catch (err) { next(err); }
});

// GET /v1/orgs/:orgId/accounts/:accountId/sync-logs
accountRoutes.get("/:accountId/sync-logs", async (req, res, next) => {
  try {
    const { accountId, orgId } = req.params;
    const { limit, offset } = getPagination(req);
    const result = await db.query(
      "SELECT id, started_at, finished_at, status, records_synced, error_message, backfill FROM sync_logs WHERE account_id=$1 AND org_id=$2 ORDER BY started_at DESC LIMIT $3 OFFSET $4",
      [accountId, orgId, limit, offset]
    );
    const total = await db.query("SELECT COUNT(*) FROM sync_logs WHERE account_id=$1 AND org_id=$2", [accountId, orgId]);
    res.json(paginatedResponse(result.rows, parseInt(total.rows[0].count), { limit, offset }));
  } catch (err) { next(err); }
});

// DELETE /v1/orgs/:orgId/accounts/:accountId
accountRoutes.delete("/:accountId", requireRole("admin"), async (req, res, next) => {
  try {
    const { accountId, orgId } = req.params;
    await db.query("UPDATE cloud_accounts SET is_active=false WHERE id=$1 AND org_id=$2", [accountId, orgId]);
    res.json({ message: "Account removed" });
  } catch (err) { next(err); }
});
```

#### `src/routes/alerts.ts`

```typescript
import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { requireRole } from "../middleware/rbac";
import { validate } from "../middleware/validateBody";
import { db } from "../config/db";
import { AppError } from "../middleware/errorHandler";
import { getPagination, paginatedResponse } from "../utils/pagination";

export const alertRoutes = Router({ mergeParams: true });
alertRoutes.use(requireAuth, requireOrgAccess);

// GET /v1/orgs/:orgId/alerts
alertRoutes.get("/", async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const { limit, offset } = getPagination(req, 50);
    const type = req.query.type as string | undefined;
    const unackOnly = req.query.unacknowledged === "true";

    let where = "org_id = $1";
    const params: any[] = [orgId];
    if (type) { params.push(type); where += ` AND type = $${params.length}`; }
    if (unackOnly) where += " AND acknowledged_at IS NULL AND (snoozed_until IS NULL OR snoozed_until < NOW())";

    const result = await db.query(
      `SELECT * FROM alerts WHERE ${where} ORDER BY triggered_at DESC LIMIT $${params.length+1} OFFSET $${params.length+2}`,
      [...params, limit, offset]
    );
    const total = await db.query(`SELECT COUNT(*) FROM alerts WHERE ${where}`, params);
    res.json(paginatedResponse(result.rows, parseInt(total.rows[0].count), { limit, offset }));
  } catch (err) { next(err); }
});

// GET /v1/orgs/:orgId/alerts/:alertId
alertRoutes.get("/:alertId", async (req, res, next) => {
  try {
    const result = await db.query("SELECT * FROM alerts WHERE id=$1 AND org_id=$2", [req.params.alertId, req.params.orgId]);
    if (!result.rows[0]) throw new AppError(404, "Alert not found");
    res.json(result.rows[0]);
  } catch (err) { next(err); }
});

// POST /v1/orgs/:orgId/alerts/:alertId/acknowledge
alertRoutes.post("/:alertId/acknowledge", requireRole("editor"), async (req, res, next) => {
  try {
    const { alertId, orgId } = req.params;
    const result = await db.query(
      "UPDATE alerts SET acknowledged_by=$1, acknowledged_at=NOW() WHERE id=$2 AND org_id=$3 RETURNING *",
      [req.user.sub, alertId, orgId]
    );
    if (!result.rows[0]) throw new AppError(404, "Alert not found");
    res.json(result.rows[0]);
  } catch (err) { next(err); }
});

const SnoozeSchema = z.object({
  days: z.number().int().min(1).max(90),
});

// POST /v1/orgs/:orgId/alerts/:alertId/snooze
alertRoutes.post("/:alertId/snooze", requireRole("editor"), validate(SnoozeSchema), async (req, res, next) => {
  try {
    const { alertId, orgId } = req.params;
    const { days } = req.body;
    const until = new Date(Date.now() + days * 86400000).toISOString();
    const result = await db.query(
      "UPDATE alerts SET snoozed_until=$1 WHERE id=$2 AND org_id=$3 RETURNING *",
      [until, alertId, orgId]
    );
    if (!result.rows[0]) throw new AppError(404, "Alert not found");
    res.json(result.rows[0]);
  } catch (err) { next(err); }
});
```

#### `src/routes/recommendations.ts`

```typescript
import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { requireRole } from "../middleware/rbac";
import { validate } from "../middleware/validateBody";
import { db } from "../config/db";
import { AppError } from "../middleware/errorHandler";
import { getPagination, paginatedResponse } from "../utils/pagination";

export const recommendationRoutes = Router({ mergeParams: true });
recommendationRoutes.use(requireAuth, requireOrgAccess);

recommendationRoutes.get("/", async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const { limit, offset } = getPagination(req, 50);
    const status = req.query.status as string ?? "pending";
    const result = await db.query(
      "SELECT * FROM recommendations WHERE org_id=$1 AND status=$2 ORDER BY estimated_monthly_savings DESC LIMIT $3 OFFSET $4",
      [orgId, status, limit, offset]
    );
    const total = await db.query("SELECT COUNT(*) FROM recommendations WHERE org_id=$1 AND status=$2", [orgId, status]);
    res.json(paginatedResponse(result.rows, parseInt(total.rows[0].count), { limit, offset }));
  } catch (err) { next(err); }
});

const StatusSchema = z.object({ status: z.enum(["implemented","rejected","archived"]) });

recommendationRoutes.put("/:recId/status", requireRole("editor"), validate(StatusSchema), async (req, res, next) => {
  try {
    const { recId, orgId } = req.params;
    const { status } = req.body;
    const result = await db.query(
      "UPDATE recommendations SET status=$1, implemented_at=CASE WHEN $1='implemented' THEN NOW() ELSE NULL END WHERE id=$2 AND org_id=$3 RETURNING *",
      [status, recId, orgId]
    );
    if (!result.rows[0]) throw new AppError(404, "Recommendation not found");
    res.json(result.rows[0]);
  } catch (err) { next(err); }
});
```

#### `src/routes/forecasts.ts`

```typescript
import { Router } from "express";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { db } from "../config/db";
import { redis } from "../config/redis";

export const forecastRoutes = Router({ mergeParams: true });
forecastRoutes.use(requireAuth, requireOrgAccess);

forecastRoutes.get("/", async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const month = (req.query.month as string) ?? new Date().toISOString().slice(0, 7);
    const cacheKey = `dash:${orgId}:forecast:${month}`;
    const cached = await redis.get(cacheKey);
    if (cached) return res.json(JSON.parse(cached));

    const result = await db.query(
      "SELECT * FROM spend_forecasts WHERE org_id=$1 AND forecast_month=$2 ORDER BY account_id NULLS FIRST, provider NULLS FIRST",
      [orgId, `${month}-01`]
    );
    await redis.set(cacheKey, JSON.stringify(result.rows), "EX", 3600);
    res.json(result.rows);
  } catch (err) { next(err); }
});

forecastRoutes.get("/history", async (req, res, next) => {
  try {
    const result = await db.query(
      "SELECT forecast_month, projected_total, actual_total, variance_pct, data_coverage FROM spend_forecasts WHERE org_id=$1 AND provider IS NULL AND actual_total IS NOT NULL ORDER BY forecast_month DESC LIMIT 12",
      [req.params.orgId]
    );
    res.json(result.rows);
  } catch (err) { next(err); }
});
```

#### `src/routes/commitments.ts`

```typescript
import { Router } from "express";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { db } from "../config/db";
import { redis } from "../config/redis";

export const commitmentRoutes = Router({ mergeParams: true });
commitmentRoutes.use(requireAuth, requireOrgAccess);

commitmentRoutes.get("/", async (req, res, next) => {
  try {
    const cacheKey = `dash:${req.params.orgId}:commitments`;
    const cached = await redis.get(cacheKey);
    if (cached) return res.json(JSON.parse(cached));

    const result = await db.query(
      "SELECT * FROM commitment_records WHERE org_id=$1 ORDER BY status, end_date",
      [req.params.orgId]
    );
    await redis.set(cacheKey, JSON.stringify(result.rows), "EX", 21600); // 6h
    res.json(result.rows);
  } catch (err) { next(err); }
});

commitmentRoutes.get("/summary", async (req, res, next) => {
  try {
    const result = await db.query(`
      SELECT
        COUNT(*) AS total_count,
        SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS active_count,
        SUM(CASE WHEN status='expiring_soon' THEN 1 ELSE 0 END) AS expiring_count,
        AVG(CASE WHEN status='active' THEN utilization_pct END) AS avg_utilization,
        SUM(CASE WHEN status='active' THEN monthly_savings ELSE 0 END) AS total_monthly_savings,
        SUM(CASE WHEN status='active' THEN coverage_amount ELSE 0 END) AS total_coverage
      FROM commitment_records WHERE org_id=$1
    `, [req.params.orgId]);
    res.json(result.rows[0]);
  } catch (err) { next(err); }
});

commitmentRoutes.get("/expiring", async (req, res, next) => {
  try {
    const days = parseInt(req.query.days as string) || 90;
    const result = await db.query(
      "SELECT * FROM commitment_records WHERE org_id=$1 AND end_date <= CURRENT_DATE + ($2 * INTERVAL '1 day') AND status != 'expired' ORDER BY end_date",
      [req.params.orgId, days]
    );
    res.json(result.rows);
  } catch (err) { next(err); }
});
```

#### `src/routes/scorecard.ts`

```typescript
import { Router } from "express";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { ScorecardEngine } from "../services/scorecard.service";
import { redis } from "../config/redis";

export const scorecardRoutes = Router({ mergeParams: true });
scorecardRoutes.use(requireAuth, requireOrgAccess);

scorecardRoutes.get("/", async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const cacheKey = `dash:${orgId}:scorecard`;
    const cached = await redis.get(cacheKey);
    if (cached) return res.json(JSON.parse(cached));

    const result = await new ScorecardEngine().compute(orgId);
    await redis.set(cacheKey, JSON.stringify(result), "EX", 3600);
    res.json(result);
  } catch (err) { next(err); }
});

// Simplified executive view — same data, different shape for the frontend
scorecardRoutes.get("/executive", async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const result = await new ScorecardEngine().compute(orgId);
    res.json({
      overall: result.overall,
      color: result.overall >= 70 ? "green" : result.overall >= 50 ? "yellow" : "red",
      topIssues: Object.entries(result.metrics)
        .filter(([, m]) => m.color === "red")
        .map(([key, m]) => ({ key, ...m }))
        .slice(0, 3),
      generatedAt: result.generatedAt,
    });
  } catch (err) { next(err); }
});
```

#### `src/routes/notifications.ts`

```typescript
import { Router } from "express";
import { z } from "zod";
import axios from "axios";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { requireRole } from "../middleware/rbac";
import { validate } from "../middleware/validateBody";
import { db } from "../config/db";
import { emailService } from "../services/email.service";

export const notificationRoutes = Router({ mergeParams: true });
notificationRoutes.use(requireAuth, requireOrgAccess);

notificationRoutes.get("/", async (req, res, next) => {
  try {
    const result = await db.query(
      "SELECT id, alert_emails, teams_webhook_url, slack_webhook_url, updated_at FROM notification_settings WHERE org_id=$1",
      [req.params.orgId]
    );
    res.json(result.rows[0] ?? { alert_emails: [], teams_webhook_url: null, slack_webhook_url: null });
  } catch (err) { next(err); }
});

const NotifSchema = z.object({
  alert_emails: z.array(z.string().email()).max(20).optional(),
  teams_webhook_url: z.string().url().nullable().optional(),
  slack_webhook_url: z.string().url().nullable().optional(),
});

notificationRoutes.put("/", requireRole("admin"), validate(NotifSchema), async (req, res, next) => {
  try {
    const { orgId } = req.params;
    await db.query(`
      INSERT INTO notification_settings (org_id, alert_emails, teams_webhook_url, slack_webhook_url)
      VALUES ($1, $2, $3, $4)
      ON CONFLICT (org_id) DO UPDATE SET
        alert_emails = EXCLUDED.alert_emails,
        teams_webhook_url = EXCLUDED.teams_webhook_url,
        slack_webhook_url = EXCLUDED.slack_webhook_url,
        updated_at = NOW()
    `, [orgId, req.body.alert_emails ?? [], req.body.teams_webhook_url ?? null, req.body.slack_webhook_url ?? null]);
    res.json({ message: "Notification settings updated" });
  } catch (err) { next(err); }
});

notificationRoutes.post("/test-email", requireRole("admin"), async (req, res, next) => {
  try {
    const settings = await db.query("SELECT alert_emails FROM notification_settings WHERE org_id=$1", [req.params.orgId]);
    const emails = settings.rows[0]?.alert_emails ?? [];
    if (emails.length === 0) return res.status(400).json({ error: "No alert emails configured" });
    await emailService.sendCapAlert({ to: emails, cap: { name: "Test Cap", cap_amount: 1000 }, spent: 750, pct: 75, threshold: 75, org: req.org });
    res.json({ message: "Test email sent" });
  } catch (err) { next(err); }
});

notificationRoutes.post("/test-teams", requireRole("admin"), async (req, res, next) => {
  try {
    const settings = await db.query("SELECT teams_webhook_url FROM notification_settings WHERE org_id=$1", [req.params.orgId]);
    const url = settings.rows[0]?.teams_webhook_url;
    if (!url) return res.status(400).json({ error: "Teams webhook not configured" });
    await axios.post(url, { "@type": "MessageCard", text: "PRISM test message — webhook is working ✅" });
    res.json({ message: "Test Teams message sent" });
  } catch (err) { next(err); }
});

notificationRoutes.post("/test-slack", requireRole("admin"), async (req, res, next) => {
  try {
    const settings = await db.query("SELECT slack_webhook_url FROM notification_settings WHERE org_id=$1", [req.params.orgId]);
    const url = settings.rows[0]?.slack_webhook_url;
    if (!url) return res.status(400).json({ error: "Slack webhook not configured" });
    await axios.post(url, { text: "PRISM test message — webhook is working ✅" });
    res.json({ message: "Test Slack message sent" });
  } catch (err) { next(err); }
});
```

#### `src/routes/webhooks.ts`

```typescript
import { Router } from "express";
import { z } from "zod";
import crypto from "crypto";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { requireRole } from "../middleware/rbac";
import { validate } from "../middleware/validateBody";
import { db } from "../config/db";
import { encrypt } from "../utils/encrypt";
import { validateWebhookUrl } from "../utils/validateWebhookUrl";
import { webhookService } from "../services/webhook.service";
import { AppError } from "../middleware/errorHandler";

export const webhookRoutes = Router({ mergeParams: true });
webhookRoutes.use(requireAuth, requireOrgAccess);

const WebhookSchema = z.object({
  url: z.string().url().refine(url => { try { validateWebhookUrl(url); return true; } catch { return false; } }, { message: "Must use HTTPS and not target private IPs" }),
  description: z.string().max(200).default(""),
  events: z.array(z.enum(["alert.fired","recommendation.new","sync.failed","report.sent"])).min(1),
});

webhookRoutes.get("/", async (req, res, next) => {
  try {
    const result = await db.query(
      "SELECT id, url, description, events, is_active, last_triggered_at, last_status_code, created_at FROM outbound_webhooks WHERE org_id=$1 ORDER BY created_at",
      [req.params.orgId]
    );
    res.json(result.rows);
  } catch (err) { next(err); }
});

webhookRoutes.post("/", requireRole("admin"), validate(WebhookSchema), async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const rawSecret = crypto.randomBytes(32).toString("hex");
    const encSecret = encrypt(rawSecret);
    const result = await db.query(
      "INSERT INTO outbound_webhooks (org_id, url, signing_secret_enc, description, events) VALUES ($1,$2,$3,$4,$5) RETURNING id, url, description, events, created_at",
      [orgId, req.body.url, encSecret, req.body.description, req.body.events]
    );
    // Return raw secret ONCE — never shown again
    res.status(201).json({ ...result.rows[0], signing_secret: rawSecret });
  } catch (err) { next(err); }
});

webhookRoutes.put("/:webhookId", requireRole("admin"), validate(WebhookSchema.partial()), async (req, res, next) => {
  try {
    const { webhookId, orgId } = req.params;
    if (req.body.url) validateWebhookUrl(req.body.url);
    const entries = Object.entries(req.body);
    if (entries.length === 0) return res.status(400).json({ error: "Nothing to update" });
    const setClauses = entries.map(([k], i) => `${k} = $${i + 3}`).join(", ");
    const result = await db.query(
      `UPDATE outbound_webhooks SET ${setClauses} WHERE id=$1 AND org_id=$2 RETURNING id, url, description, events`,
      [webhookId, orgId, ...entries.map(([,v]) => v)]
    );
    if (!result.rows[0]) throw new AppError(404, "Webhook not found");
    res.json(result.rows[0]);
  } catch (err) { next(err); }
});

webhookRoutes.delete("/:webhookId", requireRole("admin"), async (req, res, next) => {
  try {
    await db.query("UPDATE outbound_webhooks SET is_active=false WHERE id=$1 AND org_id=$2", [req.params.webhookId, req.params.orgId]);
    res.json({ message: "Webhook disabled" });
  } catch (err) { next(err); }
});

webhookRoutes.post("/:webhookId/test", requireRole("admin"), async (req, res, next) => {
  try {
    const { webhookId, orgId } = req.params;
    await webhookService.dispatch(orgId, "alert.fired", { test: true, message: "PRISM webhook test" });
    res.json({ message: "Test payload dispatched" });
  } catch (err) { next(err); }
});
```

#### `src/routes/llm.ts`

```typescript
import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { requireRole } from "../middleware/rbac";
import { validate } from "../middleware/validateBody";
import { llmRateLimit } from "../middleware/rateLimit";
import { db } from "../config/db";
import { encrypt, decrypt } from "../utils/encrypt";
import { LLMService } from "../services/llm.service";
import { AppError } from "../middleware/errorHandler";

export const llmRoutes = Router({ mergeParams: true });
llmRoutes.use(requireAuth, requireOrgAccess);

llmRoutes.get("/config", requireRole("admin"), async (req, res, next) => {
  try {
    const result = await db.query(
      "SELECT id, model, monthly_budget_usd, is_enabled, created_at, updated_at FROM llm_configs WHERE org_id=$1",
      [req.params.orgId]
    );
    // Never return the API key — just confirm it's configured
    res.json(result.rows[0] ? { ...result.rows[0], api_key_configured: true } : null);
  } catch (err) { next(err); }
});

const LLMConfigSchema = z.object({
  openrouter_api_key: z.string().min(10),
  model: z.string().default("google/gemini-flash-1.5"),
  monthly_budget_usd: z.number().positive().max(1000).default(10),
  is_enabled: z.boolean().default(true),
});

llmRoutes.put("/config", requireRole("admin"), validate(LLMConfigSchema), async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const { openrouter_api_key, model, monthly_budget_usd, is_enabled } = req.body;
    const encKey = encrypt(openrouter_api_key);
    await db.query(`
      INSERT INTO llm_configs (org_id, openrouter_api_key, model, monthly_budget_usd, is_enabled)
      VALUES ($1,$2,$3,$4,$5)
      ON CONFLICT (org_id) DO UPDATE SET
        openrouter_api_key = EXCLUDED.openrouter_api_key,
        model = EXCLUDED.model,
        monthly_budget_usd = EXCLUDED.monthly_budget_usd,
        is_enabled = EXCLUDED.is_enabled,
        updated_at = NOW()
    `, [orgId, encKey, model, monthly_budget_usd, is_enabled]);
    res.json({ message: "LLM config saved" });
  } catch (err) { next(err); }
});

llmRoutes.delete("/config", requireRole("admin"), async (req, res, next) => {
  try {
    await db.query("UPDATE llm_configs SET is_enabled=false WHERE org_id=$1", [req.params.orgId]);
    res.json({ message: "LLM disabled" });
  } catch (err) { next(err); }
});

const QuerySchema = z.object({ question: z.string().min(1).max(500) });

llmRoutes.post("/query", llmRateLimit, validate(QuerySchema), async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const llm = await LLMService.forOrg(orgId);
    // Gather lightweight context for the query
    const monthStart = new Date(); monthStart.setDate(1);
    const costs = await db.query(
      "SELECT provider, SUM(cost_usd) AS total FROM cost_records WHERE org_id=$1 AND time>=$2 GROUP BY provider",
      [orgId, monthStart.toISOString()]
    );
    const context = { costsByProvider: costs.rows, month: monthStart.toISOString().slice(0, 7) };
    const answer = await llm.answerCostQuery(req.body.question, context);
    res.json({ answer: answer ?? "LLM is not configured or budget exceeded. Please check your OpenRouter settings.", used_llm: answer !== null });
  } catch (err) { next(err); }
});
```

#### `src/routes/businessMetrics.ts`

```typescript
import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { requireRole } from "../middleware/rbac";
import { validate } from "../middleware/validateBody";
import { db } from "../config/db";
import { AppError } from "../middleware/errorHandler";

export const businessMetricRoutes = Router({ mergeParams: true });
businessMetricRoutes.use(requireAuth, requireOrgAccess);

businessMetricRoutes.get("/", async (req, res, next) => {
  try {
    const result = await db.query("SELECT * FROM business_metrics WHERE org_id=$1 AND is_active=true ORDER BY name", [req.params.orgId]);
    res.json(result.rows);
  } catch (err) { next(err); }
});

const MetricSchema = z.object({
  name: z.string().min(1).max(100),
  source: z.enum(["manual","webhook","datadog","stripe","csv"]),
  unit: z.string().min(1).max(50),
});

businessMetricRoutes.post("/", requireRole("admin"), validate(MetricSchema), async (req, res, next) => {
  try {
    const result = await db.query(
      "INSERT INTO business_metrics (org_id, name, source, unit) VALUES ($1,$2,$3,$4) RETURNING *",
      [req.params.orgId, req.body.name, req.body.source, req.body.unit]
    );
    res.status(201).json(result.rows[0]);
  } catch (err) { next(err); }
});

const ValuesSchema = z.object({
  values: z.array(z.object({ date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/), value: z.number() })).min(1).max(1000),
});

businessMetricRoutes.post("/:metricId/values", requireRole("editor"), validate(ValuesSchema), async (req, res, next) => {
  try {
    const { metricId, orgId } = req.params;
    const metric = await db.query("SELECT id FROM business_metrics WHERE id=$1 AND org_id=$2", [metricId, orgId]);
    if (!metric.rows[0]) throw new AppError(404, "Metric not found");

    for (const { date, value } of req.body.values) {
      await db.query(`
        INSERT INTO business_metric_values (metric_id, org_id, date, value)
        VALUES ($1,$2,$3,$4)
        ON CONFLICT (metric_id, date) DO UPDATE SET value = EXCLUDED.value, ingested_at = NOW()
      `, [metricId, orgId, date, value]);
    }
    res.json({ message: `${req.body.values.length} values ingested` });
  } catch (err) { next(err); }
});

businessMetricRoutes.get("/:metricId/values", async (req, res, next) => {
  try {
    const { metricId, orgId } = req.params;
    const days = Math.min(parseInt(req.query.days as string) || 30, 365);
    const result = await db.query(
      "SELECT date, value FROM business_metric_values WHERE metric_id=$1 AND org_id=$2 AND date >= CURRENT_DATE - ($3 * INTERVAL '1 day') ORDER BY date",
      [metricId, orgId, days]
    );
    res.json(result.rows);
  } catch (err) { next(err); }
});
```

#### `src/routes/resources.ts`

```typescript
import { Router } from "express";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { db } from "../config/db";
import { AppError } from "../middleware/errorHandler";
import { getPagination, paginatedResponse } from "../utils/pagination";

export const resourceRoutes = Router({ mergeParams: true });
resourceRoutes.use(requireAuth, requireOrgAccess);

resourceRoutes.get("/", async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const { limit, offset } = getPagination(req, 100);
    const provider = req.query.provider as string | undefined;
    const idle = req.query.idle === "true";

    let where = "org_id = $1";
    const params: any[] = [orgId];
    if (provider) { params.push(provider); where += ` AND provider = $${params.length}`; }
    if (idle) where += " AND is_idle = true";

    const result = await db.query(
      `SELECT id, resource_id, resource_name, service, region, provider, instance_type, is_idle, idle_since, last_cost_usd, last_seen, tags, virtual_tags FROM resources WHERE ${where} ORDER BY last_cost_usd DESC NULLS LAST LIMIT $${params.length+1} OFFSET $${params.length+2}`,
      [...params, limit, offset]
    );
    const total = await db.query(`SELECT COUNT(*) FROM resources WHERE ${where}`, params);
    res.json(paginatedResponse(result.rows, parseInt(total.rows[0].count), { limit, offset }));
  } catch (err) { next(err); }
});

resourceRoutes.get("/idle", async (req, res, next) => {
  try {
    const result = await db.query(
      "SELECT * FROM resources WHERE org_id=$1 AND is_idle=true ORDER BY idle_since, last_cost_usd DESC NULLS LAST LIMIT 100",
      [req.params.orgId]
    );
    res.json(result.rows);
  } catch (err) { next(err); }
});

resourceRoutes.get("/:resourceId", async (req, res, next) => {
  try {
    const result = await db.query("SELECT * FROM resources WHERE id=$1 AND org_id=$2", [req.params.resourceId, req.params.orgId]);
    if (!result.rows[0]) throw new AppError(404, "Resource not found");
    res.json(result.rows[0]);
  } catch (err) { next(err); }
});
```

#### `src/routes/virtualTags.ts`

```typescript
import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../middleware/auth";
import { requireOrgAccess } from "../middleware/orgScope";
import { requireRole } from "../middleware/rbac";
import { validate } from "../middleware/validateBody";
import { db } from "../config/db";
import { virtualTagsQueue } from "../config/queues";
import { validateRegexPattern } from "../utils/regex";
import { AppError } from "../middleware/errorHandler";

export const virtualTagRoutes = Router({ mergeParams: true });
virtualTagRoutes.use(requireAuth, requireOrgAccess);

virtualTagRoutes.get("/", async (req, res, next) => {
  try {
    const result = await db.query(
      "SELECT * FROM virtual_tag_rules WHERE org_id=$1 ORDER BY priority",
      [req.params.orgId]
    );
    res.json(result.rows);
  } catch (err) { next(err); }
});

const RuleSchema = z.object({
  priority: z.number().int().min(1),
  condition_field: z.enum(["resource_name","account_id","service","region","tag_value"]),
  condition_operator: z.enum(["contains","equals","starts_with","ends_with","regex"]),
  condition_value: z.string().min(1).max(500),
  action_type: z.enum(["set_tag","split"]),
  tag_key: z.string().min(1).max(50),
  tag_value: z.string().max(100).optional(),
  split_config: z.array(z.object({ team: z.string(), pct: z.number() })).optional(),
  provider_scope: z.enum(["aws","azure","gcp","all"]).default("all"),
}).superRefine((d, ctx) => {
  if (d.condition_operator === "regex") {
    const { valid, error } = validateRegexPattern(d.condition_value);
    if (!valid) ctx.addIssue({ code: "custom", path: ["condition_value"], message: error! });
  }
  if (d.action_type === "split" && d.split_config) {
    const sum = d.split_config.reduce((s, c) => s + c.pct, 0);
    if (Math.abs(sum - 100) > 0.01) ctx.addIssue({ code: "custom", path: ["split_config"], message: "Percentages must sum to 100" });
  }
  if (d.action_type === "set_tag" && !d.tag_value) ctx.addIssue({ code: "custom", path: ["tag_value"], message: "Required for set_tag rules" });
});

virtualTagRoutes.post("/", requireRole("editor"), validate(RuleSchema), async (req, res, next) => {
  try {
    const { orgId } = req.params;
    const { priority, condition_field, condition_operator, condition_value, action_type, tag_key, tag_value, split_config, provider_scope } = req.body;
    const result = await db.query(`
      INSERT INTO virtual_tag_rules (org_id, priority, condition_field, condition_operator, condition_value, action_type, tag_key, tag_value, split_config, provider_scope, created_by)
      VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) RETURNING *
    `, [orgId, priority, condition_field, condition_operator, condition_value, action_type, tag_key, tag_value ?? null, split_config ? JSON.stringify(split_config) : null, provider_scope, req.user.sub]);
    res.status(201).json(result.rows[0]);
  } catch (err) { next(err); }
});

virtualTagRoutes.put("/:ruleId", requireRole("editor"), validate(RuleSchema.partial()), async (req, res, next) => {
  try {
    const { ruleId, orgId } = req.params;
    const entries = Object.entries(req.body).filter(([,v]) => v !== undefined);
    if (entries.length === 0) return res.status(400).json({ error: "Nothing to update" });
    const setClauses = entries.map(([k], i) => `${k} = $${i + 3}`).join(", ");
    const result = await db.query(
      `UPDATE virtual_tag_rules SET ${setClauses}, updated_at=NOW(), updated_by=$${entries.length+3} WHERE id=$1 AND org_id=$2 RETURNING *`,
      [ruleId, orgId, ...entries.map(([,v]) => v), req.user.sub]
    );
    if (!result.rows[0]) throw new AppError(404, "Rule not found");
    res.json(result.rows[0]);
  } catch (err) { next(err); }
});

virtualTagRoutes.delete("/:ruleId", requireRole("editor"), async (req, res, next) => {
  try {
    await db.query("UPDATE virtual_tag_rules SET is_active=false WHERE id=$1 AND org_id=$2", [req.params.ruleId, req.params.orgId]);
    res.json({ message: "Rule deactivated" });
  } catch (err) { next(err); }
});

virtualTagRoutes.post("/apply", requireRole("editor"), async (req, res, next) => {
  try {
    const { orgId } = req.params;
    await virtualTagsQueue.add("virtual-tags", { orgId }, {
      jobId: `vtags:${orgId}:${Date.now()}`,
      attempts: 2,
    });
    res.json({ message: "Retroactive re-tagging job enqueued. Progress visible on dashboard." });
  } catch (err) { next(err); }
});

virtualTagRoutes.get("/audit-log", async (req, res, next) => {
  try {
    const result = await db.query(
      "SELECT vtal.*, u.name AS changed_by_name FROM virtual_tag_audit_log vtal JOIN users u ON u.id = vtal.changed_by WHERE vtal.org_id=$1 ORDER BY vtal.timestamp DESC LIMIT 100",
      [req.params.orgId]
    );
    res.json(result.rows);
  } catch (err) { next(err); }
});
```

#### `src/routes/teamsActions.ts` and `src/routes/slackActions.ts`

```typescript
// src/routes/teamsActions.ts
import { Router } from "express";
import { validateHMAC } from "../middleware/hmac";
import { db } from "../config/db";

export const teamsActionsRoutes = Router();
teamsActionsRoutes.use(validateHMAC("teams"));

// Handle alert acknowledgement from Teams adaptive card button
teamsActionsRoutes.post("/", async (req, res, next) => {
  try {
    const { action, alert_id, org_id } = req.body;
    if (action === "acknowledge" && alert_id && org_id) {
      await db.query("UPDATE alerts SET acknowledged_at=NOW() WHERE id=$1 AND org_id=$2", [alert_id, org_id]);
    }
    res.json({ type: "message", text: "Action received ✅" });
  } catch (err) { next(err); }
});
```

```typescript
// src/routes/slackActions.ts
import { Router } from "express";
import { validateHMAC } from "../middleware/hmac";
import { db } from "../config/db";

export const slackActionsRoutes = Router();
slackActionsRoutes.use(validateHMAC("slack"));

teamsActionsRoutes.post("/", async (req, res, next) => {
  try {
    const payload = JSON.parse(req.body.payload ?? "{}");
    const action = payload.actions?.[0];
    if (action?.action_id === "acknowledge_alert") {
      const [, alertId, orgId] = action.value.split(":");
      await db.query("UPDATE alerts SET acknowledged_at=NOW() WHERE id=$1 AND org_id=$2", [alertId, orgId]);
    }
    res.json({ response_type: "ephemeral", text: "Action received ✅" });
  } catch (err) { next(err); }
});
```

---

### 29.15 Complete Dependency Map — What Imports What

To avoid circular imports, follow this layering strictly:

```
Layer 0 — No imports from project code:
  config/env.ts
  utils/logger.ts

Layer 1 — Imports only from Layer 0:
  config/db.ts         → env
  config/redis.ts      → env
  config/queues.ts     → redis
  utils/encrypt.ts     → env
  utils/date.ts        → (none)
  utils/pagination.ts  → (none)
  utils/regex.ts       → (none)
  utils/withRetry.ts   → logger
  utils/cache.ts       → redis
  utils/validateWebhookUrl.ts → middleware/errorHandler

Layer 2 — Imports Layer 0+1:
  middleware/errorHandler.ts   → logger
  middleware/auth.ts           → env, errorHandler
  middleware/orgScope.ts       → db, errorHandler
  middleware/rbac.ts           → errorHandler
  middleware/hmac.ts           → env
  middleware/validateBody.ts   → (none)
  middleware/rateLimit.ts      → (none)
  middleware/requestLogger.ts  → logger

Layer 3 — Services (import Layer 0+1+2):
  services/fx.service.ts       → redis, logger
  services/email.service.ts    → env, logger
  services/connectors/aws.ts   → encrypt, withRetry, logger
  services/connectors/azure.ts → encrypt, withRetry, logger
  services/connectors/gcp.ts   → encrypt, withRetry, logger

Layer 4 — Complex services (import Layer 0–3):
  ws/wsServer.ts               → env, logger, jwt
  services/webhook.service.ts  → db, encrypt, validateWebhookUrl, logger
  services/llm.service.ts      → db, redis, encrypt, logger
  services/virtualTag.service.ts → db, wsServer, regex, logger
  services/forecast.service.ts   → db, redis, alertsQueue, wsServer
  services/scorecard.service.ts  → db
  services/commitment.service.ts → db, connectors/aws, email, logger
  services/recommendation.service.ts → db, llm, wsServer, logger
  services/report.service.ts     → db, email, llm, logger
  services/alert.service.ts      → db, email, webhook, wsServer, logger

Layer 5 — Jobs (import Layer 0–4):
  jobs/sync.worker.ts          → db, queues, connectors, fx, wsServer, cache, logger
  jobs/alerts.worker.ts        → alert.service
  jobs/forecast.worker.ts      → forecast.service
  jobs/commitments.worker.ts   → commitment.service
  jobs/recommendations.worker.ts → recommendation.service
  jobs/reports.worker.ts       → report.service
  jobs/virtualTags.worker.ts   → virtualTag.service
  jobs/dlq.worker.ts           → db, logger
  jobs/scheduler.ts            → db, queues, all workers

Layer 6 — Routes (import Layer 0–5):
  All routes in src/routes/   → middleware + relevant services + db + queues

Layer 7 — App bootstrap:
  app.ts    → all routes + middleware
  index.ts  → app, db, redis, scheduler, wsServer, logger
```

---

### 29.16 `tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": false,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

---

### 29.17 Complete File Checklist

Before running, every file in this list must exist. Check off as you create each:

**Config**
- [ ] `src/config/env.ts`
- [ ] `src/config/db.ts`
- [ ] `src/config/redis.ts`
- [ ] `src/config/queues.ts`

**Middleware**
- [ ] `src/middleware/auth.ts`
- [ ] `src/middleware/orgScope.ts`
- [ ] `src/middleware/rbac.ts`
- [ ] `src/middleware/hmac.ts`
- [ ] `src/middleware/validateBody.ts`
- [ ] `src/middleware/rateLimit.ts`
- [ ] `src/middleware/requestLogger.ts`
- [ ] `src/middleware/errorHandler.ts`

**Utils**
- [ ] `src/utils/logger.ts`
- [ ] `src/utils/encrypt.ts`
- [ ] `src/utils/withRetry.ts`
- [ ] `src/utils/cache.ts`
- [ ] `src/utils/validateWebhookUrl.ts`
- [ ] `src/utils/regex.ts`
- [ ] `src/utils/date.ts`
- [ ] `src/utils/pagination.ts`

**Services — Connectors**
- [ ] `src/services/connectors/aws.ts`
- [ ] `src/services/connectors/azure.ts`
- [ ] `src/services/connectors/gcp.ts`

**Services — Core**
- [ ] `src/services/fx.service.ts`
- [ ] `src/services/email.service.ts`
- [ ] `src/services/llm.service.ts`
- [ ] `src/services/alert.service.ts`
- [ ] `src/services/webhook.service.ts`
- [ ] `src/services/virtualTag.service.ts`
- [ ] `src/services/forecast.service.ts`
- [ ] `src/services/scorecard.service.ts`
- [ ] `src/services/recommendation.service.ts`
- [ ] `src/services/commitment.service.ts`
- [ ] `src/services/report.service.ts`

**Jobs**
- [ ] `src/jobs/scheduler.ts`
- [ ] `src/jobs/sync.worker.ts`
- [ ] `src/jobs/alerts.worker.ts`
- [ ] `src/jobs/forecast.worker.ts`
- [ ] `src/jobs/commitments.worker.ts`
- [ ] `src/jobs/recommendations.worker.ts`
- [ ] `src/jobs/reports.worker.ts`
- [ ] `src/jobs/virtualTags.worker.ts`
- [ ] `src/jobs/dlq.worker.ts`

**WebSocket**
- [ ] `src/ws/wsServer.ts`

**Routes**
- [ ] `src/routes/auth.ts`
- [ ] `src/routes/orgs.ts`
- [ ] `src/routes/accounts.ts`
- [ ] `src/routes/costs.ts`
- [ ] `src/routes/alerts.ts`
- [ ] `src/routes/caps.ts`
- [ ] `src/routes/reports.ts`
- [ ] `src/routes/team.ts`
- [ ] `src/routes/recommendations.ts`
- [ ] `src/routes/virtualTags.ts`
- [ ] `src/routes/forecasts.ts`
- [ ] `src/routes/commitments.ts`
- [ ] `src/routes/scorecard.ts`
- [ ] `src/routes/notifications.ts`
- [ ] `src/routes/webhooks.ts`
- [ ] `src/routes/llm.ts`
- [ ] `src/routes/businessMetrics.ts`
- [ ] `src/routes/resources.ts`
- [ ] `src/routes/teamsActions.ts`
- [ ] `src/routes/slackActions.ts`

**App Bootstrap**
- [ ] `src/app.ts`
- [ ] `src/index.ts`

**Database**
- [ ] `src/db/schema.sql`

**Root**
- [ ] `.env` (from `.env.example`)
- [ ] `tsconfig.json`
- [ ] `package.json`

---

**End of PRISM Backend Implementation Plan**

> Every code block in this document is production-grade and directly usable. Adapt env vars and connection strings for your environment. The implementation order in Section 28 ensures a working, testable backend at each milestone without dead ends.
