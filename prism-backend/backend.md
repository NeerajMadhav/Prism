# PRISM Backend — Complete Inventory

> Generated from the **live** `prism-backend` codebase (FastAPI + asyncpg + TimescaleDB + optional Redis/Celery).  
> This is the catalog of what exists end-to-end: stack, data, APIs, workers, security, realtime, and ops.

---

## 1. Stack & runtime

| Layer | Technology |
|-------|------------|
| API | FastAPI (`src/main.py`, `src/server.py`) |
| DB | PostgreSQL 16 + TimescaleDB (`src/db/schema.sql`) |
| Cache / KV | Redis (optional) + Postgres `app_kv` fallback |
| Jobs | Celery + Beat (optional; sync falls back to **inline** in API) |
| Auth | JWT (access 15m + opaque refresh) + Google OAuth + API keys (`prism_…`) |
| Crypto | AES-256-GCM for credentials / secrets (`ENCRYPTION_KEY`) |
| Email | AWS SES (skips cleanly if not configured) |
| Cloud connectors | AWS CE (boto3), Azure Cost Management (httpx), GCP BigQuery |
| Logging | structlog JSON (prod) / console (dev); `X-Request-Id` |
| Realtime | WebSocket `/ws` + internal `/internal/ws-broadcast` |
| Tests | pytest + docker-compose.test.yml (Postgres `:55432`, Redis `:6380`) |

**Redis optional behavior:** API + DB work when Redis is down. Health returns `status: degraded`. Password reset / OAuth state use `app_kv`. Sync uses Celery when available, otherwise **inline** in the API process.

---

## 2. End-to-end product flow (what the backend enables)

```
Signup / Google OAuth
  → verify email → login (JWT + refresh)
  → org + owner membership
  → invite team (admin/editor/viewer)
  → connect AWS / Azure / GCP (credentials encrypted)
  → sync (Celery or inline) → cost_records (day grain) + resources
  → dashboard costs (total / by-service / by-day / by-tag / top)
  → budget caps → threshold alerts (75/90/100/125/150%)
  → email / Teams / Slack / outbound webhooks
  → forecasts, commitments, recommendations, scorecard
  → virtual tags + audit log
  → monthly reports + LLM assist
  → business metrics / unit economics
  → API keys for scoped machine access
  → WebSocket sync.complete / connected / ping
```

---

## 3. System endpoints (non-org)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health` | none | DB + Redis status: `ok` / `degraded` / `down` |
| WS | `/ws?token=` | JWT in query | Org-scoped realtime events |
| POST | `/internal/ws-broadcast` | `X-Prism-Internal` | Worker → API WS fan-out |

---

## 4. Auth — `/v1/auth`

| Method | Path | Rate limit | Purpose |
|--------|------|------------|---------|
| POST | `/signup` | 10/15m | Create user + org + owner membership + notification_settings |
| POST | `/verify-email` | 10/15m | Confirm email with token |
| POST | `/resend-verification` | 10/15m | Resend verify link (no user enumeration) |
| POST | `/login` | 10/15m | Password login → access + refresh; updates `last_login` |
| POST | `/refresh` | 10/15m | Atomic refresh rotation (one-time use) |
| POST | `/logout` | 10/15m | Revoke refresh token |
| POST | `/forgot-password` | 10/15m | Reset token (Redis or `app_kv` / DB) |
| POST | `/reset-password` | 10/15m | Set new password |
| GET | `/me` | — | Current user + org + role |
| PUT | `/me` | — | Update profile |
| POST | `/change-password` | — | Change password (authenticated) |
| GET | `/google` | — | Start Google OAuth (state) |
| GET | `/google/callback` | — | OAuth callback → one-time exchange code |
| POST | `/oauth/exchange` | 20/15m | Exchange OAuth code → tokens |

**Tokens:** access JWT (~15m); refresh opaque, SHA-256 hashed, atomic revoke-on-use.  
**Roles in JWT:** reloaded from DB on each request (demotion/removal takes effect immediately).

---

## 5. Organizations — `/v1/orgs`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `/{org_id}` | viewer | Org details |
| PUT | `/{org_id}` | admin | Update org (name, currency, timezone, etc.) |

All org-scoped routes enforce membership via `get_org_access` + `org_id` match.

---

## 6. Team — `/v1/orgs/{org_id}/team`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `` | viewer | List members |
| POST | `/invite` | admin | Invite admin/editor/viewer |
| POST | `/accept-invite` | none (token) | Accept invite → user + membership |
| PUT | `/{member_id}/role` | admin | Change role (owner protections) |
| DELETE | `/{member_id}` | admin | Remove member |

**RBAC ranks:** `viewer(1) < editor(2) < admin(3) < owner(4)`.

---

## 7. Cloud accounts — `/v1/orgs/{org_id}/accounts`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `` | viewer | List accounts (no credentials) |
| POST | `` | admin | Connect AWS/Azure/GCP; encrypt creds; queue/inline sync (backfill) |
| GET | `/{account_id}` | viewer | Account detail |
| PUT | `/{account_id}` | admin | Update name / credentials |
| DELETE | `/{account_id}` | admin | Soft-deactivate / remove |
| POST | `/{account_id}/test` | admin | Live connector health check |
| POST | `/{account_id}/sync` | admin | Trigger incremental sync (Celery or inline); ≤5/hour when Redis up |
| GET | `/{account_id}/sync-logs` | viewer | Sync history |

**Providers & credential shapes**

- **AWS:** `role_arn`, `external_id`, `region` → STS assume-role → Cost Explorer  
- **Azure:** `tenant_id`, `client_id`, `client_secret`, `subscription_id` → Cost Management Query  
- **GCP:** `project_id`, `dataset_id`, `table_prefix`, `service_account_json` → BigQuery billing export  

**Sync modes:** `queued` (Celery) or `inline` (API process). Response includes `sync_task_id` + `sync_mode`.

---

## 8. Costs / dashboard — `/v1/orgs/{org_id}/costs`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `` | viewer | Month total, MoM, estimate flags, filters |
| GET | `/by-service` | viewer | Spend by service (+ MoM) |
| GET | `/by-day` | viewer | UTC day series (fills zero days) |
| GET | `/by-tag` | viewer | Spend by tag key/value |
| GET | `/top-services` | viewer | Top services |

**Cost views:** unblended / amortized (query `view`).  
**Grain:** UTC calendar day. Cached under `dash:{org_id}:…` when Redis available.

---

## 9. Budget caps — `/v1/orgs/{org_id}/caps`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `/` | viewer | List caps |
| POST | `/` | editor | Create cap |
| GET | `/{cap_id}` | viewer | Cap + current spend % |
| PUT | `/{cap_id}` | editor | Update |
| DELETE | `/{cap_id}` | admin | Soft delete |

**Scopes:** `platform` | `service` | `account`.  
**Period:** monthly (default).

---

## 10. Alerts — `/v1/orgs/{org_id}/alerts`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `/` | viewer | List alerts |
| POST | `/{alert_id}/acknowledge` | viewer | Acknowledge |
| POST | `/{alert_id}/snooze` | viewer | Snooze until |

**Cap thresholds:** 75 / 90 / 100 / 125 / 150 % (per notification_settings toggles).  
**Delivery tracking columns:** `email_sent`, `teams_sent`, `slack_sent`, `webhook_sent` (only set true when delivery succeeds).  
**Dedup:** one `cap_threshold` alert per cap/threshold/month.

---

## 11. Notifications — `/v1/orgs/{org_id}/notifications`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `/` | viewer | Get settings |
| PUT | `/` | admin | Update emails, Teams/Slack URLs, threshold toggles |
| POST | `/test/email` | admin | Test email |
| POST | `/test/teams` | admin | Test Teams webhook |
| POST | `/test/slack` | admin | Test Slack webhook |

Webhook URLs validated against SSRF (no private IPs / redirects).

---

## 12. Reports — `/v1/orgs/{org_id}/reports`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `/` | viewer | Monthly report config |
| PUT | `/` | admin | Enable, recipients, send_day, section flags |
| POST | `/send-now` | admin | Queue/force send |

Sections: recommendations, FinOps scorecard, commitments, unit economics (flag).

---

## 13. Recommendations — `/v1/orgs/{org_id}/recommendations`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `/` | viewer | List (filter by status) |
| PUT | `/{rec_id}/status` | editor | open / implemented / rejected / archived |

Generated by daily Celery recommendations worker.

---

## 14. Forecasts — `/v1/orgs/{org_id}/forecasts`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `/` | viewer | Current month projection / breach |
| GET | `/history` | viewer | Historical forecasts + accuracy fields |

---

## 15. Commitments — `/v1/orgs/{org_id}/commitments`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `/` | viewer | RI/SP/CUD-style records |
| GET | `/summary` | viewer | Coverage / utilization rollup |
| GET | `/expiring` | viewer | Expiring soon |

---

## 16. FinOps scorecard — `/v1/orgs/{org_id}/scorecard`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `/` | viewer | Weighted health score + grade |
| GET | `/executive` | viewer | Executive KPI view |

**Weights (implemented):** tagging_coverage 20, idle_resource_rate 20, commitment_coverage 20, budget_cap_coverage 15, forecast_accuracy 10, alert_response_time 10, recommendation_action_rate 5.

---

## 17. Resources — `/v1/orgs/{org_id}/resources`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `/` | viewer | Inventory list |
| GET | `/idle` | viewer | Idle resources |
| GET | `/{resource_id}` | viewer | Detail |

---

## 18. Virtual tags — `/v1/orgs/{org_id}/virtual-tags`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `/` | viewer | List rules |
| POST | `/` | editor | Create rule |
| PUT | `/{rule_id}` | editor | Update |
| DELETE | `/{rule_id}` | editor | Delete |
| PUT | `/reorder` | editor | Priority reorder |
| POST | `/{rule_id}/apply` | editor | Retroactive apply (async worker) |
| GET | `/audit-log` | viewer | Apply audit trail |

---

## 19. Outbound webhooks — `/v1/orgs/{org_id}/webhooks`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `/` | viewer | List |
| POST | `/` | admin | Create (URL + events + signing secret) |
| PUT | `/{webhook_id}` | admin | Update |
| DELETE | `/{webhook_id}` | admin | Delete |
| POST | `/{webhook_id}/test` | admin | Test delivery |

**Events:** e.g. `alert.fired`, `sync.complete`, … (HMAC-signed payloads).

---

## 20. LLM — `/v1/orgs/{org_id}/llm`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `/` | admin | Config (key never returned plain) |
| PUT | `/` | admin | Set API key / model / monthly budget |
| DELETE | `/` | admin | Disable / clear |
| POST | `/query` | viewer | Ask question (20/hour); falls back if LLM fails |

Spend tracked (Redis preferred). Used also for report narrative / recommendation notes.

---

## 21. Business metrics — `/v1/orgs/{org_id}/metrics`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `/` | viewer | List metrics |
| POST | `/` | admin | Create metric |
| DELETE | `/{metric_id}` | admin | Delete |
| POST | `/{metric_id}/values` | editor | Ingest value |
| GET | `/{metric_id}/values` | viewer | Time series |
| GET | `/unit-economics` | viewer | Cost per unit metrics |

---

## 22. API keys — `/v1/orgs/{org_id}/api-keys`

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| GET | `/` | admin | List (prefix only) |
| POST | `/` | admin | Create (`prism_…` shown once) |
| DELETE | `/{key_id}` | admin | Revoke |

**Scopes enforced for API-key auth:**  
`cost.read`, `alerts.read`, `reports.read`, `webhooks.write` (path-marker mapped).

---

## 23. Chat integrations

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/v1/integrations/teams` | Teams HMAC | Acknowledge / snooze from Teams |
| POST | `/v1/integrations/slack` | Slack HMAC | Acknowledge / snooze from Slack |

---

## 24. Database tables (all)

| Table | Purpose |
|-------|---------|
| `organizations` | Tenant; plan, currency, timezone, feature_flags |
| `users` | Identity; password/Google; verify/reset tokens; last_login |
| `app_kv` | Ephemeral KV when Redis down (OAuth state, etc.) |
| `refresh_tokens` | Hashed refresh tokens; revoke support |
| `team_members` | Org membership + role |
| `invites` | Pending invites |
| `account_groups` | Optional grouping of cloud accounts |
| `cloud_accounts` | Provider accounts; AES credentials; sync status |
| `sync_logs` | Per-sync run history (90-day purge) |
| `cost_records` | **Timescale hypertable** — day-grain cost rows + tags JSONB |
| `resources` | Discovered resources; idle flags |
| `budget_caps` | Budget caps (soft-delete) |
| `alerts` | Cap / sync_failure / etc.; channel delivery flags |
| `notification_settings` | Emails, Teams/Slack, threshold toggles |
| `monthly_reports` | Report schedule + section flags |
| `recommendations` | Savings recommendations |
| `virtual_tag_rules` | Virtual tag rules + priority |
| `virtual_tag_audit_log` | Retroactive apply audit |
| `spend_forecasts` | Monthly projections + accuracy |
| `commitment_records` | RI/SP/CUD tracking |
| `outbound_webhooks` | Customer webhooks + signing secrets |
| `llm_configs` | Per-org LLM key/budget |
| `business_metrics` | Named business metrics |
| `business_metric_values` | Daily metric values |
| `api_keys` | Hashed API keys + scopes |

---

## 25. Background jobs (Celery)

| Task | Queue | Schedule / trigger |
|------|-------|--------------------|
| `prism-sync.sync_account` | prism-sync | On connect / Sync Now / daily |
| `prism-sync.schedule_daily` | — | Beat 06:00 UTC |
| `prism-sync.purge_old_data` | — | Beat 02:00 UTC (sync_logs, etc.) |
| `prism-alerts.check_org` | prism-alerts | After sync / cap changes |
| `prism-forecast.run` | prism-forecast | Daily 07:30 |
| `prism-forecast.compute_accuracy` | — | 1st of month 10:00 |
| `prism-commitments.run` | prism-commitments | Daily 07:00 |
| `prism-recommendations.run` | prism-recommendations | Daily 08:00 |
| `prism-reports.send` | prism-reports | Daily 09:00 + send-now |
| `prism-virtual-tags.apply` | prism-virtual-tags | On apply |
| `prism-dlq.handle` | prism-dlq | Failed task DLQ |

**Inline fallback (API):** if Celery broker unavailable → `run_sync_inline` + local WS broadcast + in-process alert check.

---

## 26. Cloud connectors (data pull)

| Provider | Source | Day grain notes |
|----------|--------|-----------------|
| AWS | Cost Explorer `GetCostAndUsage` | Exclusive end; `NetUnblendedCost` + `NetAmortizedCost`; exclude Credit/Refund; `Estimated` flag; pagination |
| Azure | Cost Management Query | Daily max **31-day chunks**; inclusive ISO timePeriod; `nextLink` GET pagination; ActualCost |
| GCP | BigQuery billing export | `DATE(usage_start_time)`; **net cost = cost + credits** |

Credentials never returned on API responses. Stored as `credentials_enc` (AES-GCM).

---

## 27. Realtime / WebSocket

**Client:** `WS /ws?token=<access_jwt>`  
**Events envelope:** `{ event, org_id, timestamp, data }`

| Event | When |
|-------|------|
| `connected` | After accept |
| `ping` | Every ~30s |
| `sync.complete` | After successful sync (`provider`, `account_id`, `records`) |

Workers POST to `/internal/ws-broadcast` with internal secret. Inline sync calls `ws_broadcast` in-process.

---

## 28. Security (implemented)

- Multi-tenant `org_id` scoping on queries + membership check  
- RBAC via `require_role`  
- API-key scopes for machine clients  
- AES-256-GCM for secrets at rest  
- Opaque refresh + atomic rotation  
- Google OAuth: JWKS verify, CSRF state, one-time exchange code  
- Webhook SSRF protection (`validate_webhook_url`, no redirects)  
- Teams/Slack action HMAC verification  
- Rate limits on auth + LLM query  
- Sync trigger rate limit (Redis INCR; skipped if Redis down)  
- No credentials in logs; structured events with `request_id`, `org_id`, `user_id`  
- CORS locked to `FRONTEND_URL`

---

## 29. Observability (structured logs)

| Event | Level | Notes |
|-------|-------|-------|
| `http_request` | info | method, path, status, duration_ms (+ request_id) |
| `user_signup` / `user_login` / `login_failed` | info/warn | Auth trail |
| `account_connected` | info | sync_mode |
| `sync_started` / `sync_completed` / `sync_failed` | info/error | + duration_ms; DB `sync_logs` |
| `alert_fired` | info | channel delivery flags |
| `email_sent` / `email_failed` / `email_skipped_no_ses` | info/error | bool return for accurate tracking |
| `report_sent` / `report_send_failed` | info/error | |
| `llm_fallback` | warn | |
| `dlq_task` | error | |
| `unhandled_error` | error | |

Response header: `X-Request-Id`.

---

## 30. Config / environment (required & key optional)

**Required:** `DATABASE_URL`, `JWT_ACCESS_SECRET`, `JWT_REFRESH_SECRET`, `ENCRYPTION_KEY` (64 hex), `FRONTEND_URL`

**Optional / degrade:** `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, Google OAuth, SES keys, `PRISM_INTERNAL_SECRET`, Teams/Slack signing secrets, `PRISM_AWS_ACCOUNT_ID`, `API_INTERNAL_URL`

---

## 31. Services & modules map

| Area | Path |
|------|------|
| App factory | `src/main.py` |
| Settings / DB / Redis | `src/config/` |
| Routers | `src/routers/*.py` |
| Middleware | auth, rbac, org_scope, rate_limit, request_logging, hmac |
| Connectors | `src/services/connectors/{aws,azure,gcp}.py` |
| Domain services | alert, report, forecast, commitment, recommendation, scorecard, virtual_tag, llm, fx, email, webhook |
| Workers | `src/workers/*` |
| WS | `src/ws/ws_manager.py` |
| Schema | `src/db/schema.sql` |
| Utils | encrypt, security, logger, cache, kv_store, date_utils, retry, pagination, regex, SSRF |

---

## 32. Test coverage (present)

- Unit: day grain, Azure windows, encrypt, regex, security, webhook SSRF, request logging  
- Integration: auth, team/RBAC, accounts/costs/caps, remaining endpoints, validation, rate limit, security fixes, e2e journey, concurrency/load, Redis-optional, **inline sync realtime**  
- Infra: `docker-compose.test.yml`

---

## 33. Frontend contract checklist (consume these)

1. Auth: signup → verify → login → store access+refresh → refresh/logout  
2. `/v1/auth/me` on load for org_id + role  
3. Team invite/accept flows  
4. Connect cloud → show `sync_mode` / sync logs / health test  
5. Costs dashboard: total, by-service, **by-day**, by-tag  
6. Caps + alerts acknowledge/snooze  
7. Notifications + test channels  
8. Reports config + send-now  
9. Forecasts, commitments, recommendations status  
10. Scorecard + executive  
11. Resources / idle  
12. Virtual tags + audit log  
13. Webhooks CRUD  
14. LLM config + query  
15. Business metrics / unit economics  
16. API keys  
17. WebSocket `/ws` for `sync.complete`  
18. Health for degraded Redis UX  
19. Respect RBAC (hide admin actions for viewers)  
20. Never expect credentials in GET account responses  

---

*Source of truth for “what exists today” is this inventory + the code under `prism-backend/src`. Update this file when APIs or tables change.*
