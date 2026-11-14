-- PRISM schema — PostgreSQL 16 + TimescaleDB
-- Run after: CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- organizations
CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  plan TEXT NOT NULL DEFAULT 'starter',
  billing_period_start DATE,
  currency TEXT NOT NULL DEFAULT 'USD',
  timezone TEXT NOT NULL DEFAULT 'UTC',
  feature_flags JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- users
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  password_hash TEXT,
  google_id TEXT UNIQUE,
  microsoft_id TEXT UNIQUE,
  avatar_url TEXT,
  email_verified BOOLEAN NOT NULL DEFAULT FALSE,
  email_verify_token TEXT,
  email_verify_expires TIMESTAMPTZ,
  password_reset_token TEXT,
  password_reset_expires TIMESTAMPTZ,
  mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  last_login TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ephemeral KV for OAuth state/codes when Redis is unavailable
CREATE TABLE IF NOT EXISTS app_kv (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS app_kv_expires_idx ON app_kv (expires_at);

-- refresh_tokens
CREATE TABLE IF NOT EXISTS refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL,
  revoked_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS refresh_tokens_hash_live_idx
  ON refresh_tokens (token_hash)
  WHERE revoked_at IS NULL;

-- team_members
CREATE TABLE IF NOT EXISTS team_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'editor', 'viewer')),
  invite_accepted BOOLEAN NOT NULL DEFAULT FALSE,
  invited_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (org_id, user_id)
);

-- invites
CREATE TABLE IF NOT EXISTS invites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin', 'editor', 'viewer')),
  token_hash TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  accepted_at TIMESTAMPTZ,
  invited_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS invites_active_unique
  ON invites (org_id, email) WHERE accepted_at IS NULL;

-- account_groups
CREATE TABLE IF NOT EXISTS account_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  provider TEXT NOT NULL CHECK (provider IN ('aws', 'azure', 'gcp')),
  name TEXT NOT NULL,
  scope TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- cloud_accounts
CREATE TABLE IF NOT EXISTS cloud_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  group_id UUID REFERENCES account_groups(id),
  provider TEXT NOT NULL CHECK (provider IN ('aws', 'azure', 'gcp')),
  account_id TEXT NOT NULL,
  display_name TEXT NOT NULL,
  scope TEXT NOT NULL,
  credentials_enc TEXT NOT NULL,
  last_sync TIMESTAMPTZ,
  last_sync_status TEXT NOT NULL DEFAULT 'never'
    CHECK (last_sync_status IN ('never', 'running', 'success', 'failed')),
  last_sync_error TEXT,
  last_sync_records INTEGER,
  data_as_of DATE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (org_id, provider, account_id)
);

-- sync_logs
CREATE TABLE IF NOT EXISTS sync_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES cloud_accounts(id) ON DELETE CASCADE,
  org_id UUID NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  records_synced INTEGER,
  error TEXT
);

-- cost_records (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS cost_records (
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL,
  account_id UUID NOT NULL REFERENCES cloud_accounts(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  time TIMESTAMPTZ NOT NULL,
  service TEXT NOT NULL,
  region TEXT NOT NULL DEFAULT '',
  cost_usd NUMERIC(14,6) NOT NULL DEFAULT 0,
  cost_unblended_usd NUMERIC(14,6) NOT NULL DEFAULT 0,
  cost_amortized_usd NUMERIC(14,6) NOT NULL DEFAULT 0,
  usage_quantity NUMERIC,
  usage_unit TEXT,
  tags JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_estimate BOOLEAN NOT NULL DEFAULT FALSE
);

SELECT create_hypertable('cost_records', 'time', if_not_exists => TRUE, migrate_data => TRUE);

-- TimescaleDB requires the partition column `time` in unique indexes (not an expression)
CREATE UNIQUE INDEX IF NOT EXISTS cost_records_upsert_idx
  ON cost_records (account_id, time, service, region);
CREATE INDEX IF NOT EXISTS cost_records_org_time_idx
  ON cost_records (org_id, time DESC);
CREATE INDEX IF NOT EXISTS cost_records_org_provider_time_idx
  ON cost_records (org_id, provider, time DESC);
CREATE INDEX IF NOT EXISTS cost_records_tags_gin
  ON cost_records USING GIN (tags);

-- resources
CREATE TABLE IF NOT EXISTS resources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL,
  account_id UUID NOT NULL REFERENCES cloud_accounts(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  name TEXT,
  region TEXT,
  tags JSONB NOT NULL DEFAULT '{}'::jsonb,
  last_cost_usd NUMERIC,
  last_activity_at TIMESTAMPTZ,
  is_idle BOOLEAN NOT NULL DEFAULT FALSE,
  idle_since DATE,
  first_seen DATE NOT NULL DEFAULT CURRENT_DATE,
  last_seen DATE NOT NULL DEFAULT CURRENT_DATE,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (account_id, resource_id)
);
CREATE INDEX IF NOT EXISTS resources_idle_idx
  ON resources (org_id, is_idle, idle_since) WHERE is_idle = TRUE;

-- budget_caps
CREATE TABLE IF NOT EXISTS budget_caps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  scope TEXT NOT NULL CHECK (scope IN ('platform', 'service', 'account')),
  scope_value TEXT NOT NULL,
  cap_amount NUMERIC NOT NULL,
  period TEXT NOT NULL DEFAULT 'monthly',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  deleted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- alerts
CREATE TABLE IF NOT EXISTS alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  cap_id UUID REFERENCES budget_caps(id) ON DELETE SET NULL,
  type TEXT NOT NULL,
  scope TEXT,
  scope_value TEXT,
  severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
  threshold_percent NUMERIC,
  message TEXT NOT NULL,
  triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  acknowledged_at TIMESTAMPTZ,
  acknowledged_by UUID REFERENCES users(id),
  snoozed_until TIMESTAMPTZ,
  email_sent BOOLEAN NOT NULL DEFAULT FALSE,
  teams_sent BOOLEAN NOT NULL DEFAULT FALSE,
  slack_sent BOOLEAN NOT NULL DEFAULT FALSE,
  webhook_sent BOOLEAN NOT NULL DEFAULT FALSE
);
-- date_trunc on timestamptz is STABLE; cast via UTC timestamp for IMMUTABLE index
CREATE UNIQUE INDEX IF NOT EXISTS alerts_cap_threshold_dedup_idx
  ON alerts (
    org_id,
    cap_id,
    threshold_percent,
    (date_trunc('month', (triggered_at AT TIME ZONE 'UTC')))
  )
  WHERE type = 'cap_threshold';

-- notification_settings
CREATE TABLE IF NOT EXISTS notification_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID UNIQUE NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  alert_emails TEXT[] NOT NULL DEFAULT '{}',
  teams_webhook_url TEXT,
  slack_webhook_url TEXT,
  teams_signing_secret_enc TEXT,
  slack_signing_secret_enc TEXT,
  alert_threshold_75 BOOLEAN NOT NULL DEFAULT TRUE,
  alert_threshold_90 BOOLEAN NOT NULL DEFAULT TRUE,
  alert_threshold_100 BOOLEAN NOT NULL DEFAULT TRUE,
  alert_threshold_125 BOOLEAN NOT NULL DEFAULT TRUE,
  alert_threshold_150 BOOLEAN NOT NULL DEFAULT TRUE
);

-- monthly_reports
CREATE TABLE IF NOT EXISTS monthly_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID UNIQUE NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  is_active BOOLEAN NOT NULL DEFAULT FALSE,
  recipient_emails TEXT[] NOT NULL DEFAULT '{}',
  send_day INTEGER NOT NULL DEFAULT 1 CHECK (send_day >= 1 AND send_day <= 28),
  next_send TIMESTAMPTZ,
  last_sent TIMESTAMPTZ,
  include_recommendations BOOLEAN NOT NULL DEFAULT TRUE,
  include_finops_scorecard BOOLEAN NOT NULL DEFAULT TRUE,
  include_commitments BOOLEAN NOT NULL DEFAULT TRUE,
  include_unit_economics BOOLEAN NOT NULL DEFAULT FALSE
);

-- recommendations
CREATE TABLE IF NOT EXISTS recommendations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  account_id UUID REFERENCES cloud_accounts(id) ON DELETE SET NULL,
  resource_id UUID REFERENCES resources(id) ON DELETE SET NULL,
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  savings_usd NUMERIC,
  confidence TEXT CHECK (confidence IN ('high', 'medium', 'low')),
  status TEXT NOT NULL DEFAULT 'open'
    CHECK (status IN ('open', 'implemented', 'rejected', 'archived')),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- virtual_tag_rules
CREATE TABLE IF NOT EXISTS virtual_tag_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  tag_key TEXT NOT NULL,
  tag_value TEXT NOT NULL,
  conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
  split_config JSONB,
  priority INTEGER NOT NULL DEFAULT 100,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS virtual_tag_rules_priority_idx
  ON virtual_tag_rules (org_id, priority) WHERE is_active = TRUE;

-- virtual_tag_audit_log
CREATE TABLE IF NOT EXISTS virtual_tag_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  rule_id UUID REFERENCES virtual_tag_rules(id) ON DELETE SET NULL,
  triggered_by UUID REFERENCES users(id),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  rows_processed INTEGER,
  rows_updated INTEGER,
  status TEXT NOT NULL DEFAULT 'running'
    CHECK (status IN ('running', 'completed', 'failed'))
);

-- spend_forecasts
CREATE TABLE IF NOT EXISTS spend_forecasts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  forecast_month DATE NOT NULL,
  daily_avg NUMERIC,
  projected_total NUMERIC,
  cap_amount NUMERIC,
  will_breach BOOLEAN NOT NULL DEFAULT FALSE,
  days_elapsed INTEGER,
  days_with_data INTEGER,
  data_coverage TEXT NOT NULL DEFAULT 'insufficient'
    CHECK (data_coverage IN ('sufficient', 'insufficient')),
  actual_total NUMERIC,
  variance_pct NUMERIC,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (org_id, provider, forecast_month)
);
CREATE INDEX IF NOT EXISTS spend_forecasts_lookup_idx
  ON spend_forecasts (org_id, forecast_month DESC);

-- commitment_records
CREATE TABLE IF NOT EXISTS commitment_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  account_id UUID REFERENCES cloud_accounts(id) ON DELETE SET NULL,
  provider TEXT NOT NULL,
  commitment_type TEXT NOT NULL,
  resource_type TEXT,
  arn_or_id TEXT,
  start_date DATE,
  end_date DATE,
  monthly_cost NUMERIC,
  utilization_pct NUMERIC,
  coverage_pct NUMERIC,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'expired', 'expiring_soon')),
  last_synced TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS commitment_expiry_idx
  ON commitment_records (org_id, status, end_date);

-- outbound_webhooks
CREATE TABLE IF NOT EXISTS outbound_webhooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  signing_secret_enc TEXT NOT NULL,
  events TEXT[] NOT NULL DEFAULT '{}',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_delivery_status TEXT,
  last_delivery_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- llm_configs
CREATE TABLE IF NOT EXISTS llm_configs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID UNIQUE NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  api_key_enc TEXT,
  model TEXT NOT NULL DEFAULT 'openai/gpt-4o-mini',
  monthly_budget_usd NUMERIC NOT NULL DEFAULT 20,
  is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- business_metrics
CREATE TABLE IF NOT EXISTS business_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'manual',
  unit TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (org_id, name)
);

-- business_metric_values
CREATE TABLE IF NOT EXISTS business_metric_values (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  metric_id UUID NOT NULL REFERENCES business_metrics(id) ON DELETE CASCADE,
  org_id UUID NOT NULL,
  date DATE NOT NULL,
  value NUMERIC NOT NULL,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (metric_id, date)
);

-- api_keys
CREATE TABLE IF NOT EXISTS api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  key_hash TEXT NOT NULL,
  key_prefix TEXT NOT NULL,
  name TEXT NOT NULL,
  scopes TEXT[] NOT NULL DEFAULT '{}',
  expires_at TIMESTAMPTZ,
  last_used TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked_at TIMESTAMPTZ
);

-- Idempotent upgrades for existing databases
ALTER TABLE users ADD COLUMN IF NOT EXISTS microsoft_id TEXT;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'users_microsoft_id_key'
  ) THEN
    ALTER TABLE users ADD CONSTRAINT users_microsoft_id_key UNIQUE (microsoft_id);
  END IF;
END $$;
