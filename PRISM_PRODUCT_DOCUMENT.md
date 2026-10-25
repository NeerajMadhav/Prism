# **PRISM — Multi-Cloud Cost Management & Governance Platform**

**Version:** 3.4 (Added: End-to-End User Journey — Sign Up → Org Creation → Connect Cloud Account → Invite Team → Budget Caps → Report Schedule → Autopilot Operations → Alert Emails → Monthly Report email template → Settings map. Full screen wireframes, invite email templates, cap alert email template, daily autopilot schedule, complete flow diagram.)
**Last Updated:** October 25, 2026
**Status:** Ready for Development  
**Primary Platforms:** AWS, Azure, GCP
**Notifications:** Email (primary), Microsoft Teams (optional)
**LLM:** OpenRouter (optional — features degrade gracefully when not configured)

---

## **Table of Contents**

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Solution Overview](#solution-overview)
4. [Core Features](#core-features)
5. [Dashboard Specification](#dashboard-specification)
6. [LLM Integration (OpenRouter)](#llm-integration-openrouter)
7. [Virtual Tagging](#virtual-tagging)
8. [Spend Forecasting](#spend-forecasting)
9. [Commitment Management](#commitment-management)
10. [FinOps Health Scorecard](#finops-health-scorecard)
11. [Primary Integrations](#primary-integrations)
12. [Technical Architecture](#technical-architecture)
13. [Configuration & Setup Guide](#configuration--setup-guide)
14. [IAM Roles & Permissions](#iam-roles--permissions)
15. [API Implementation Guide](#api-implementation-guide)
16. [Budget Cap System](#budget-cap-system)
17. [Alerts & Notifications](#alerts--notifications)
18. [Monthly Report System](#monthly-report-system)
19. [User Management & Access Control](#user-management--access-control)
20. [Security & Compliance](#security--compliance)
21. [Pricing Model](#pricing-model)
22. [Implementation Roadmap](#implementation-roadmap)
23. [Success Metrics](#success-metrics)
24. [Debug & Observability](#debug--observability)
25. [Deployment Checklist](#deployment-checklist)

---

## **Executive Summary**

**Prism** is a unified multi-cloud cost management and governance platform built for startups and growing teams. It consolidates spending across **AWS, Azure, and GCP** into a single real-time dashboard with configurable budget caps, automated email alerts, and monthly cost reports.

**One-Line Promise:** Connect your clouds. Set your caps. Get alerted before surprises. Know exactly where every dollar goes.

**Key Metrics:**
- **ROI: 20:1** ($299/month → saves $5K–$50K/month per customer)
- **Time Saved:** 20+ hours/week (automation of manual cost reporting)
- **Cost Savings:** Average 30% reduction in first 6 months

**LLM is optional:** All core features work without an LLM key. When OpenRouter is configured, Prism enhances reports, recommendations, and alerts with AI-generated context — but never blocks core functionality if the LLM is down or unconfigured.

---

## **Problem Statement**

### **Market Context**
- 80%+ of startups run on multiple cloud providers simultaneously
- $182 billion/year in cloud waste (27% of total spend)
- 68% cite cost allocation and governance as top priorities
- Startups lack budget for enterprise FinOps tools ($5K–$50K/month)

### **Critical Gaps**
1. **Fragmentation** — Teams jump between AWS Console, Azure Portal, GCP Console separately
2. **Opacity** — Monthly bills arrive too late; costs are discovered after the fact
3. **No Accountability** — Costs aren't traced to teams/owners; shared resources spiral
4. **Reactive Model** — Reports show history; no prevention of waste
5. **No Caps** — Teams set spend caps in theory but have no automated enforcement or alerts
6. **Complexity Mismatch** — Enterprise tools require tagging discipline startups lack

---

## **Solution Overview**

### **Six-Pillar Architecture**

**Connect** → **Visualize** → **Allocate** → **Alert** → **Report** → **Explain (LLM, optional)**

```
┌──────────────────────────────────────────────────────────────────┐
│ Prism Multi-Cloud Cost Platform                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  CONNECTORS          CORE ENGINE            OUTPUTS              │
│  ───────────         ──────────             ───────              │
│  ┌─────────┐    ┌──────────────┐      ┌──────────────┐          │
│  │   AWS   │    │   Cost       │      │  Dashboard   │          │
│  │ CE API  │    │   Service    │──→   │  (Overall +  │          │
│  └─────────┘    │              │      │  Per-Platform│          │
│  ┌─────────┐    │ • Normalize  │      ├──────────────┤          │
│  │  Azure  │    │ • Aggregate  │      │  Email Alerts│          │
│  │  ARM    │    │ • Cap check  │      ├──────────────┤          │
│  └─────────┘    │ • Recommend  │      │  Monthly     │          │
│  ┌─────────┐    │ • Report gen │      │  Reports     │          │
│  │   GCP   │    │              │      ├──────────────┤          │
│  │Billing  │    └──────┬───────┘      │  Teams       │          │
│  └─────────┘           │              │  (optional)  │          │
│                         │              └──────────────┘          │
│                    ┌────▼────┐                                   │
│                    │OpenRouter│  ← optional; all features work   │
│                    │  (LLM)  │    without it                     │
│                    └─────────┘                                   │
│                   PostgreSQL + TimescaleDB (daily aggregates)    │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## **Core Features**

### **Feature #1: Multi-Cloud Integration**

**Phase 1 (Launch):**
- **AWS:** Cost & Usage Report API, CloudTrail, EC2/S3/RDS/Lambda/EKS discovery
- **Azure:** Cost Management API, Resource Manager, subscription enumeration
- **GCP:** Cloud Billing API, BigQuery billing export, resource inventory

**Account Scope Support (per platform):**
- **Single Account** — one AWS account / one Azure subscription / one GCP project
- **Multi-Account** — multiple accounts added individually, each with its own credentials
- **Organization** — AWS Organizations (management account enumerates all members), Azure Management Groups, GCP Billing Account spanning multiple projects

**Auth:**
- AWS: IAM role assumption with ExternalId (no permanent keys)
- Azure: Service principal with client secret (90-day rotation)
- GCP: Service account JSON key (90-day rotation)

**Phase 2 (Future):**
- GitHub Actions billing
- Snowflake Account Usage

---

### **Feature #2: Unified Cost Dashboard**

See [Dashboard Specification](#dashboard-specification) for full layout and component detail.

- **Overall view:** Total cross-platform spend, cap status, active alerts, top cost drivers, end-of-month forecast — all at a glance
- **Per-platform view:** Drill into AWS / Azure / GCP individually — accounts, services, tags, caps, commitments, network egress, recommendations
- **Cost View Toggle:** Unblended / Amortized / Blended — user switches per their role (finance = amortized, dev = unblended)
- **Tagging Coverage %** shown on dashboard — "78% of spend is tagged" with week-over-week trend
- **Data Freshness Indicator:** Each platform shows "Data as of [timestamp]" — yellow if >24h old, red if sync failed
- **Time Ranges:** This month, Last month, Last 7 days, Custom; auto-refresh every 5 minutes
- **Partial Data State:** One connector failing never hides the others — clear error banner per failed platform
- **Executive KPI View:** Separate single-page summary for CTO/CFO with FinOps health score, ESR, and top actions
- **Export:** CSV / PDF per view

---

### **Feature #3: Cost Allocation**

- **Primary:** Tag-based — `owner`, `team`, `project`, `environment`
- **Tags normalized** across providers (AWS `tag:Team` = Azure `tags.team` = GCP `labels.team` → stored as unified `team` key)
- **Virtual Tagging:** Define tag rules inside Prism without touching cloud infrastructure — see [Virtual Tagging](#virtual-tagging)
- **Shared Cost Allocation:** Split shared resources (databases, NAT gateways, Kubernetes clusters) across teams by equal split, fixed %, or usage ratio
- **Untagged fallback:** Resources without tags are grouped into "Untagged" bucket per platform — not silently dropped; tagging coverage % shown
- **Unit Economics:** Cost per service, cost per environment, cost per team; optional business metric ingestion (cost per customer, cost per API request)
- **Chargeback view:** Cost breakdown per team/project exportable to CSV for finance

---

### **Feature #4: Budget Cap System**

See [Budget Cap System](#budget-cap-system) section for full detail.

- Set caps at: **platform level**, **service level**, **account level**
- Alert thresholds: 75% / 90% / 100% / 125% / 150% of cap
- Delivery: Email (always) + Teams (if configured)
- One alert per threshold crossing per billing period — no repeated spam

---

### **Feature #5: Recommendations (Rule-Based + Optional LLM Context)**

All rules are deterministic and run regardless of LLM configuration:

- **Rightsizing:** Flag resources with <20% CPU/memory for 7+ consecutive days
- **Idle resources:** Flag resources with zero usage for 7+ days — shown with resource age (e.g., "Created 6 months ago, idle 45 days")
- **Reserved Instance / Savings Plan opportunities:** Flag on-demand instances running 24/7 for 30+ days; show projected savings vs. commitment term
- **Storage tiering:** Flag S3/Azure Blob/GCS data untouched for 30+ days
- **Network egress:** Flag unexpectedly high cross-AZ or cross-region traffic
- **Commitment expiry:** Flag RI/SP/CUDs expiring within 60 days that haven't been renewed
- **Confidence:** High / Medium / Low based on data completeness
- **Resource age:** Every recommendation card shows resource creation date and last-activity date
- **Estimated monthly savings** shown per recommendation
- **Realized savings tracking:** After marking `implemented`, Prism tracks actual savings vs. estimated over the next 30 days
- **Status tracking:** `pending` → `implemented` / `rejected` / `archived`

**When LLM is configured (OpenRouter):**
- Each recommendation gets a 1–3 sentence **plain-English explanation** of why it was flagged and what to do — instead of a generic rule description
- LLM adds **risk context**: "Terminating this instance will affect the `prod-api` service — confirm with the engineering team first"
- Untagged resources get an **ownership suggestion**: "This resource's name (`data-pipeline-prod`) and region suggest it belongs to the data team"
- LLM call is made once per recommendation, result cached for 24 hours — no repeated API calls

---

### **Feature #6: Monthly Automated Report**

See [Monthly Report System](#monthly-report-system) section for full detail.

- One structured email report per month
- User sets the day of month and the recipient email list
- Covers: total spend, per-platform breakdown, cap status, top cost drivers, recommendations

**Without LLM:** Deterministic template — all numbers and tables, no narrative.  
**With LLM (OpenRouter):** Adds a 2–3 paragraph executive summary in plain English explaining the month's trends, anomalies, and top actions. Template data is identical — LLM only adds the narrative wrapper.

---

### **Feature #7: User Management & Team Access**

See [User Management & Access Control](#user-management--access-control) section for full detail.

- **Roles:** Owner, Admin, Editor, Viewer
- **Auth:** Email + password (primary), Google OAuth (alternative)
- **Team invites:** Owner/Admin invites members by email; member sets password on first login
- **Role per member:** Set individually; Owner role is non-transferable without explicit action

---

### **Feature #8: Configuration & Integration Setup**

See [Configuration & Setup Guide](#configuration--setup-guide) section for full detail.

- Guided per-platform setup with copy-paste IAM/CLI code blocks
- "Test Connection" button per account
- Manual sync trigger
- Last sync status and error display per account
- LLM configuration (OpenRouter API key + model selection) — optional, separate from cloud credentials
- **Notification channels:** Email (primary), Teams webhook (optional), Slack webhook (optional), custom outbound webhook (optional, for Jira/ServiceNow/custom)
- **Onboarding checklist:** First-run wizard showing setup completion (connect platforms → set cap → add team → configure report)

---

### **Feature #9: LLM Integration (OpenRouter — Optional)**

See [LLM Integration (OpenRouter)](#llm-integration-openrouter) section for full detail.

- User provides their own OpenRouter API key — Prism never bills for LLM usage separately
- All LLM features are **additive** — the platform works fully without them
- LLM is invoked only for: report narrative, recommendation explanations, alert context, natural language queries
- Responses are cached (Redis, 24h TTL) to minimize API cost

---

### **Feature #10: Virtual Tagging**

See [Virtual Tagging](#virtual-tagging) section for full detail.

- Define tag rules *inside Prism* — no cloud infra changes needed
- Rules retroactively re-tag historical cost records
- Covers untaggable resources (data transfer, support charges, NAT gateways)
- Audit log of every rule change

---

### **Feature #11: Spend Forecasting**

See [Spend Forecasting](#spend-forecasting) section for full detail.

- End-of-month projection on dashboard: "Projected: $14,200 (cap: $15,000)"
- Per-platform and per-cap forecasts
- Forecast accuracy KPI tracked in monthly report
- With LLM: driver-based narrative ("Forecast is high because 3 EC2 instances were added Oct 22")

---

### **Feature #12: Commitment Management**

See [Commitment Management](#commitment-management) section for full detail.

- Track AWS Reserved Instances, Savings Plans, GCP Committed Use Discounts
- Commitment Coverage Rate, Utilization Rate, Effective Savings Rate (ESR) metrics
- Expiry calendar — alerts 60/30/14 days before commitment expires
- Unused commitment detection (you paid for it but aren't using it)

---

### **Feature #13: FinOps Health Scorecard**

See [FinOps Health Scorecard](#finops-health-scorecard) section for full detail.

- One-page health score: Tag Coverage %, Allocation %, Commitment Coverage %, ESR, Idle Rate, Recommendations acted on
- Executive KPI view: single-page snapshot for CTO/CFO
- Monthly trend of each metric — improving or degrading?

---

### **Feature #14: Network & Egress Cost Breakdown**

- Dedicated tab in per-platform dashboard
- Breaks out: Internet Egress / Cross-Region / Cross-AZ / NAT Gateway / Data Transfer charges
- Flags unexpectedly high egress as a recommendation with savings estimate
- Per-account, per-region breakdown

**Data Sources & Prerequisites:**

| Provider | Source | Breakdown Level | Prerequisite |
|----------|--------|-----------------|-------------|
| AWS | Cost Explorer `DataTransfer` line items | Service + region | None (Cost Explorer always has this) |
| AWS | VPC Flow Logs → CloudWatch Logs Insights | Per-VPC / AZ breakdown | **Must enable VPC Flow Logs** — UI warns if not enabled |
| Azure | Cost Management `Bandwidth` meter | Resource group | None (billing API includes it) |
| GCP | Billing export to BigQuery, `network` service | Project + region | BigQuery billing export must be set up |

> **VPC Flow Logs Note:** The basic network cost breakdown uses Cost Explorer data only (no prerequisite). The detailed per-VPC / per-AZ / per-destination breakdown requires VPC Flow Logs to be enabled on the customer's VPCs. If Flow Logs are not enabled, Prism shows a callout: *"Enable VPC Flow Logs to see per-AZ egress breakdown → [Show me how]"* linking to the AWS documentation. Prism never enables Flow Logs itself — this requires the customer to opt in due to cost ($0.50/GB for log ingestion).

---

### **Feature #15: Onboarding Checklist**

- First-run wizard shown on the dashboard until all steps completed
- **5 steps (no duplicates):**
  1. **Connect your first cloud account** → Settings → Cloud Accounts → Connect
  2. **Invite a team member** → Settings → Team → Invite (skip-able if solo)
  3. **Set an org-level budget cap** → Settings → Budget Caps → New Cap
  4. **Configure monthly report recipients** → Settings → Reports → Edit
  5. **Review your first cost sync** → dismiss once a sync completes successfully
- Progress shown as `3/5 complete ▓▓▓░░` until all steps done
- Each incomplete step has a direct link to the relevant settings page
- Fully dismissible after Step 1 for users who just want to explore first
- Checklist disappears permanently once all 5 steps are done

### **Empty State (New Organization)**

New organizations have no data on Day 1. The dashboard must not show blank charts or confusing zeros.

```
Day 1 Dashboard — No Cloud Accounts Connected Yet
──────────────────────────────────────────────────────────────────
  ┌─────────────────────────────────────────────────────────────┐
  │  👋 Welcome to PRISM, Acme Inc.!                            │
  │                                                             │
  │  Connect your first cloud account to start tracking spend.  │
  │  It takes about 2 minutes.                                  │
  │                                                             │
  │  [Connect AWS]   [Connect Azure]   [Connect GCP]           │
  │                                                             │
  │  Or  [Import a cost CSV ↑]  to preview with historical data │
  └─────────────────────────────────────────────────────────────┘

Checklist:  ░░░░░  0/5 complete
──────────────────────────────────────────────────────────────────

All widgets below are hidden until at least one account is connected and one sync completes.
No empty charts, no "$0.00" totals — just the empty-state CTA above.
```

After first sync completes: empty state disappears, onboarding checklist shows at top of page, all dashboard widgets render with real data. This first sync takes ~5 minutes; a progress banner shows: *"Syncing your AWS data — this takes a few minutes the first time."*

---

## **End-to-End User Journey**

> This section is the canonical flow. Every screen, API call, job, and email in the system must map back to one of these steps. If something doesn't fit, it doesn't belong in v1.

---

### **Stage 0 — Sign Up & Org Creation**

**Entry point:** `prism.io/signup`

```
┌─────────────────────────────────────────────┐
│  Create your PRISM account                  │
│                                             │
│  Full name   [                    ]         │
│  Work email  [                    ]         │
│  Password    [                    ]         │
│              (min 12 chars)                 │
│                                             │
│  Company / org name  [            ]         │
│                                             │
│            [Create Account]                 │
│                                             │
│  ─────────────── or ────────────────        │
│  [  Continue with Google  ]                 │
└─────────────────────────────────────────────┘
```

**What happens on submit:**
1. Prism creates a `User` record + hashed password (bcrypt, cost 12)
2. Prism creates an `Organization` record (plan: `starter`, currency: `USD`, billing_period_start: today)
3. Prism creates a `TeamMember` record: this user = `Owner` of the org
4. Prism sends a **verification email** — user must click to confirm before accessing the dashboard
5. User clicks link → email marked verified → redirected to dashboard

**Verification email:**
```
Subject: Verify your PRISM account

Hi Neeraj,

Click below to verify your email and start using PRISM.
[Verify Email →]  (link expires in 24 hours)
```

**Error states:**
- Email already registered → "Account exists — [Sign in] or [Reset password]"
- Org name blank → inline validation error
- Weak password → inline strength indicator + specific hint

---

### **Stage 1 — First Login & Dashboard (Empty State)**

After verification, user lands on the dashboard. No data yet.

```
┌─────────────────────────────────────────────────────────────────────┐
│ PRISM                                        👤 Neeraj (Owner) [↗]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  👋 Welcome to PRISM, Acme Corp!                                     │
│                                                                      │
│  Connect your first cloud account to start tracking spend.           │
│  It takes about 2 minutes.                                           │
│                                                                      │
│  [ Connect AWS ]      [ Connect Azure ]      [ Connect GCP ]        │
│                                                                      │
│  Checklist: ░░░░░  0/5 complete                                      │
│   ○ Connect your first cloud account                                 │
│   ○ Invite a team member           (skip-able)                       │
│   ○ Set an org-level budget cap                                      │
│   ○ Configure monthly report                                         │
│   ○ Review your first cost sync                                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**No blank charts are shown.** All widgets are hidden until the first sync completes.

---

### **Stage 2 — Connect a Cloud Account (Configuration)**

User clicks **[Connect AWS]** (or Azure / GCP). A setup wizard opens.

#### **2a. AWS — Step-by-Step Wizard**

```
Step 1 of 4: Account Scope
──────────────────────────────────────────────────────
  ○ Single Account   — one AWS account
  ● Multi-Account    — several accounts individually
  ○ AWS Organization — all accounts under AWS Org

  [ Back ]  [ Next → ]
```

```
Step 2 of 4: Create IAM Role in AWS
──────────────────────────────────────────────────────
  1. Go to AWS IAM Console
  2. Create a new Policy — paste this JSON:
     ┌──────────────────────────────────────────┐
     │ { "Version": "2012-10-17", ... }  [Copy] │
     └──────────────────────────────────────────┘
  3. Create a new Role (type: "Another AWS account")
     Paste this Trust Policy:
     ┌──────────────────────────────────────────┐
     │ { "Principal": {"AWS": "arn:aws:..."} }  │
     │  ExternalId: "prism-xxxx-yyyy"  [Copy]   │
     └──────────────────────────────────────────┘
  4. Name the role: "PrismCostAccess"
  5. Attach the policy you just created

  [ Back ]  [ Next → ]
```

```
Step 3 of 4: Enter Role ARN
──────────────────────────────────────────────────────
  Role ARN:   [ arn:aws:iam::123456789012:role/PrismCostAccess ]
  Account name (label):  [ Production ]
  Region:     [ us-east-1 ▼ ]

  [ Test Connection ]   ← calls STS AssumeRole + ce:GetCostAndUsage

  ✅ Connection successful — role assumed, Cost Explorer accessible

  [ Back ]  [ Save & Sync → ]
```

```
Step 4 of 4: First Sync Initiated
──────────────────────────────────────────────────────
  🔄 Syncing your AWS data...
  This takes 3–5 minutes the first time.

  We're pulling the last 13 months of cost data.
  You'll get a notification when it's done.

  [ Go to Dashboard ]
```

**What happens in the background (Step 4):**
1. `CloudAccount` record created (`provider=aws`, `status=syncing`)
2. `prism-sync` job enqueued with `{ org_id, account_id, backfill: true }`
3. Job calls `AWSConnector.getCostAndUsage()` for each of the past 13 months
4. Results bulk-inserted into `cost_records` (idempotent `ON CONFLICT DO UPDATE`)
5. Job calls `AWSConnector.getResources()` — upserts into `resources` table
6. On completion: `CloudAccount.status = connected`, `last_sync = now()`
7. WebSocket event `sync.complete` pushed to browser → dashboard refreshes
8. Onboarding checklist step 1 marked ✅ automatically

**Azure and GCP follow the same 4-step pattern with platform-specific credential steps.**

---

### **Stage 3 — Invite Team Members**

Owner or Admin goes to **Settings → Team**.

```
Team Members                                   [+ Invite Member]
──────────────────────────────────────────────────────────────────
Name          Email                Role      Joined        Actions
Neeraj K.     neeraj@acme.com      Owner     Oct 25, 2026  —
──────────────────────────────────────────────────────────────────
```

Clicking **[+ Invite Member]** opens a modal:

```
┌─────────────────────────────────────────────┐
│  Invite a team member                       │
│                                             │
│  Email    [ finance@acme.com      ]         │
│  Role     [ Viewer             ▼  ]         │
│           ○ Admin                           │
│           ○ Editor                          │
│           ● Viewer                          │
│                                             │
│  [Cancel]          [Send Invite]            │
└─────────────────────────────────────────────┘
```

**What happens on Send Invite:**
1. `TeamMember` record created: `email=finance@acme.com`, `role=viewer`, `invite_accepted=false`, `invite_expires_at = now() + 48h`
2. A secure invite token is generated (`crypto.randomBytes(32)`) — bcrypt-hashed version stored in DB
3. Invite email sent with magic link (raw token in URL, hashed token in DB)

**Invite email:**
```
Subject: Neeraj invited you to PRISM — Acme Corp

Hi there,

Neeraj Kapoor has invited you to join Acme Corp's cloud cost dashboard on PRISM.

Your role: Viewer

[Accept Invitation →]   (link expires in 48 hours)
```

**On accepting the invite:**
- **New user:** Clicks link → lands on "Set your password" screen → sets password → `User` record created → `TeamMember.invite_accepted = true`, `joined_at = now()` → redirected to dashboard
- **Existing user (already has PRISM account):** Clicks link → logged in automatically → added to org → redirected to dashboard
- **Expired invite:** "This invite has expired — ask Neeraj to resend it." Owner/Admin sees **[Resend]** button in Team settings.

**Role permissions at a glance:**
| What | Owner | Admin | Editor | Viewer |
|------|-------|-------|--------|--------|
| View dashboard & reports | ✅ | ✅ | ✅ | ✅ |
| Connect / remove cloud accounts | ✅ | ✅ | ❌ | ❌ |
| Create / edit budget caps | ✅ | ✅ | ❌ | ❌ |
| Invite / remove members | ✅ | ✅ (not Owner) | ❌ | ❌ |
| Configure monthly report | ✅ | ✅ | ❌ | ❌ |
| Acknowledge / snooze alerts | ✅ | ✅ | ✅ | ❌ |
| Implement recommendations | ✅ | ✅ | ✅ | ❌ |
| Transfer ownership | ✅ only | ❌ | ❌ | ❌ |

---

### **Stage 4 — Set Budget Caps**

Owner or Admin goes to **Settings → Budget Caps → [+ New Cap]**.

```
┌─────────────────────────────────────────────┐
│  New Budget Cap                             │
│                                             │
│  Name      [ AWS Monthly Total    ]         │
│  Scope     [ Platform         ▼   ]         │
│  Platform  [ AWS              ▼   ]         │
│  Amount    [ $ 8,000              ]         │
│  Period    [ Monthly          ▼   ]         │
│                                             │
│  Alert at: [✓] 75%  [✓] 90%  [✓] 100%     │
│            [✓] 125% [✓] 150%               │
│                                             │
│  Notify:   [✓] Email   [ ] Teams  [ ] Slack │
│                                             │
│  [Cancel]         [Create Cap]              │
└─────────────────────────────────────────────┘
```

**What happens on Create:**
1. `BudgetCap` record saved
2. `CapAlertService.checkAllCaps(orgId)` runs after next sync — immediately checks current spend
3. If already past a threshold, alert fires immediately
4. Onboarding checklist step 3 marked ✅

---

### **Stage 5 — Configure Monthly Report**

Owner or Admin goes to **Settings → Reports**.

```
┌──────────────────────────────────────────────────────────┐
│  Monthly Report Schedule                                 │
│                                                          │
│  Send on day   [ 4 ▼ ] of each month                    │
│                                                          │
│  Recipients:                                             │
│   neeraj@acme.com           [×]                          │
│   finance@acme.com          [×]                          │
│   cto@acme.com              [×]                          │
│   [+ Add recipient]                                      │
│                                                          │
│  Include in report:                                      │
│   [✓] Recommendations                                    │
│   [✓] Per-account breakdown                              │
│   [✓] Commitment coverage (RI/SP/CUD)                    │
│   [✓] FinOps health scorecard                            │
│   [✓] Unit economics (if metrics configured)             │
│                                                          │
│  LLM narrative (if OpenRouter configured):               │
│   [✓] AI executive summary                               │
│                                                          │
│  [Save]   [Send Test Report Now]                         │
└──────────────────────────────────────────────────────────┘
```

**What happens on Save:**
1. `MonthlyReport` record saved with `send_day_of_month`, `recipient_emails`, `next_send` computed
2. `next_send = next occurrence of day N in the current or next month`
3. Cron job checks daily: does any org have `next_send = today`? → enqueue `prism-reports` job
4. Onboarding checklist step 4 marked ✅

**What [Send Test Report Now] does:**
- Generates the full report for the current month's data immediately (one-shot)
- Sends to the configured recipients right now
- Does **not** change `next_send` or `last_sent`

---

### **Stage 6 — Ongoing Operations (Day-to-Day)**

Once set up, PRISM runs on autopilot. Here's what happens every day without user action:

```
Every day at 06:00 UTC
──────────────────────────────────────────────────────────────────────
  prism-sync job fires for each connected cloud account
     └→ Pulls yesterday's cost data from AWS/Azure/GCP
     └→ Upserts into cost_records (idempotent)
     └→ Updates resources table (upserts, new idle flags)
     └→ WebSocket sync.complete event → dashboard auto-refreshes

At 07:00 UTC — after syncs complete
──────────────────────────────────────────────────────────────────────
  prism-commitments   → refreshes RI/SP/CUD records from AWS + GCP
  prism-forecast      → recalculates EOMonth projection for each org
  prism-alerts        → checks every BudgetCap against today's spend
     └→ Threshold breached? → email + Teams/Slack (if configured)
     └→ Alert deduplicated: same threshold not re-fired same month

At 08:00 UTC
──────────────────────────────────────────────────────────────────────
  prism-recommendations → generates/refreshes savings recommendations
     └→ Rightsizing, idle termination, RI/SP purchase, storage tiering
     └→ LLM explanation added if OpenRouter configured

On configured report day (e.g. 4th of every month)
──────────────────────────────────────────────────────────────────────
  prism-reports job fires for orgs with next_send = today
     └→ Generates full structured PDF/email report
     └→ LLM executive narrative generated if OpenRouter configured
     └→ Sent to all configured recipient emails
     └→ last_sent = today; next_send = same day next month
```

---

### **Stage 7 — Alerts: What the User Sees**

**In-app alert banner (real-time via WebSocket):**
```
🔔  AWS EC2 cap at 90% — $3,150 spent of $3,500 cap this month.
    [View Cap]  [Acknowledge]  [Snooze 7 days]
```

**Email alert:**
```
Subject: ⚠️ AWS EC2 cap at 90% — Acme Corp (PRISM)

Hi Neeraj,

Your AWS EC2 budget cap has reached 90% for October 2026.

  Spent this month:  $3,150
  Cap amount:        $3,500
  Usage:             90% ⚠️

Forecasted end-of-month spend: $3,900  (exceeds cap by $400)

What to do:
→ Review EC2 spend breakdown → [View Dashboard]
→ Adjust the cap → [Edit Cap]
→ Silence this alert → [Snooze 7 days]

Next alert: at 100% (if spend continues rising).

— PRISM
```

**Alert thresholds for this cap example ($3,500 EC2 cap):**
| Threshold | Spend Trigger | Email Subject |
|-----------|-------------|---------------|
| 75% | $2,625 | "AWS EC2 cap at 75%" — informational |
| 90% | $3,150 | "AWS EC2 cap at 90% ⚠️" — warning |
| 100% | $3,500 | "AWS EC2 cap REACHED 🚨" — critical |
| 125% | $4,375 | "AWS EC2 cap exceeded by 25% 🚨" — critical |
| 150% | $5,250 | "AWS EC2 cap exceeded by 50% 🚨" — critical |

Each threshold fires **once per billing month per cap** — no spam.

---

### **Stage 8 — Monthly Report: What the User Receives**

On the 4th of each month (or configured day), every recipient email gets:

```
Subject: PRISM Cloud Cost Report — October 2026 — Acme Corp

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM CLOUD COST REPORT   |   October 2026   |  Acme Corp
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXECUTIVE SUMMARY
Total spend: $12,450  (+15.3% vs September)
Budget used: 83% of $15,000 org cap — on track
Top cost driver: EC2 Compute (+$800 month-over-month)
Biggest saving opportunity: $1,855/month in recommendations

[Optional LLM narrative if OpenRouter configured]
"October saw a 15% cost increase driven by a new microservices
deployment on EC2. EC2 coverage is at 45% — below your 60-80%
target. Purchasing a 1-year Savings Plan for ~$1,200 of EC2
baseline could save $340/month." (AI-generated, review before acting)

SPEND BY PLATFORM
AWS    $7,200   90% of $8,000 cap   ⚠️
Azure  $3,800   76% of $5,000 cap   ✅
GCP    $1,450   73% of $2,000 cap   ✅

TOP RECOMMENDATIONS
1. Rightsize prod-api-03 (EC2)     → Save $340/month   [High confidence]
2. Terminate staging-db (RDS)      → Save $180/month   [High confidence]
3. Enable S3 Intelligent Tiering   → Save $120/month   [Medium confidence]

FinOps Health Score: 62/100  (↑5 from last month)
Commitment coverage: 45%  ⚠️  Target: 60–80%

Full dashboard → https://app.prism.io
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sent by PRISM · Manage report settings · Unsubscribe
```

---

### **Stage 9 — Settings & Ongoing Management**

All ongoing configuration lives in **Settings** (top-right nav):

| Settings Tab | What you can do |
|-------------|----------------|
| **Cloud Accounts** | Add / remove / reconnect accounts; Sync Now; view sync history |
| **Team** | Invite members; change roles; remove members; view pending invites |
| **Budget Caps** | Create / edit / delete caps; see current month spend per cap |
| **Reports** | Set schedule, recipients, included sections; send test report |
| **Notifications** | Configure Teams webhook URL; Slack webhook URL; Outbound webhook URL |
| **Integrations** | Generate API keys; configure OpenRouter (LLM); connect Stripe/Datadog (unit economics) |
| **Virtual Tags** | Create / edit / reorder tag rules; apply retroactively |
| **Organization** | Name, timezone, currency, billing period start, plan |
| **Billing** | Prism subscription plan, usage, invoices |

---

### **Complete Flow in One View**

```
prism.io/signup
    │
    ▼
[Sign Up] → email verified
    │
    ▼
Dashboard (empty state) — "Connect your first cloud account"
    │
    ├─► [Connect AWS / Azure / GCP]
    │        └── IAM role wizard → Test → Save → 1st sync (background)
    │        └── Dashboard populates with real data ← WebSocket push
    │
    ├─► [Invite Team] (Settings → Team → + Invite Member)
    │        └── Email sent → member accepts → joins org with their role
    │
    ├─► [Set Budget Caps] (Settings → Budget Caps → + New Cap)
    │        └── Threshold alerts armed: 75/90/100/125/150%
    │
    ├─► [Configure Reports] (Settings → Reports)
    │        └── Recipients + schedule saved → monthly job armed
    │
    ▼
Autopilot kicks in every day:
    Daily 06:00 UTC → sync → alerts → forecast → recommendations
    Monthly (day N) → report emailed to all recipients
    Real-time       → WebSocket updates → alert banners in dashboard
```

---

## **Dashboard Specification**

The dashboard has two levels: **Overall** (all platforms at once) and **Per-Platform** (drill into AWS / Azure / GCP). Both auto-refresh every 5 minutes via WebSocket. All data shown is scoped to the selected time range (default: current month).

---

### **Overall Dashboard**

One screen. Everything a founder, CTO, or finance person needs to understand their cloud spend right now.

```
┌──────────────────────────────────────────────────────────────────────┐
│ PRISM   [Overall ▼]  [This Month ▼]              🔔 3 Alerts         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  TOTAL SPEND THIS MONTH         BUDGET STATUS                        │
│  ┌─────────────────────┐        ┌──────────────────────────────────┐ │
│  │   $12,450           │        │ ████████████████░░░░  83%       │ │
│  │   ↑ $1,650 vs last  │        │ $12,450 of $15,000 org cap      │ │
│  │   month (+15.3%)    │        │ ~$2,550 remaining               │ │
│  └─────────────────────┘        └──────────────────────────────────┘ │
│                                                                       │
│  BY PLATFORM                                                          │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐     │
│  │ AWS              │ │ Azure            │ │ GCP              │     │
│  │ $7,200           │ │ $3,800           │ │ $1,450           │     │
│  │ ↑ 18% MoM        │ │ ↑ 8% MoM         │ │ ↑ 21% MoM        │     │
│  │ ██████████░  90% │ │ ████████░░░  76% │ │ ███████░░░░  73% │     │
│  │ of $8,000 cap ⚠️ │ │ of $5,000 cap ✅ │ │ of $2,000 cap ✅ │     │
│  │ 🟡 Data: Oct 23  │ │ ✅ Data: Oct 23  │ │ 🟡 Data: Oct 22  │     │
│  │ [View →]         │ │ [View →]         │ │ [View →]         │     │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘     │
│                                                                       │
│  SPEND TREND — Last 6 Months                                         │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  $16K ┤                                                      │    │
│  │  $14K ┤          ██                   ██                    │    │
│  │  $12K ┤    ██    ██    ██    ██        ██                    │    │
│  │  $10K ┤    ██    ██    ██    ██    ██  ██                    │    │
│  │       └───May──Jun───Jul───Aug───Sep───Oct                   │    │
│  │        ■ AWS  ■ Azure  ■ GCP                                 │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌────────────────────────────┐  ┌───────────────────────────────┐   │
│  │ 🚨 ACTIVE ALERTS (3)       │  │ 💡 RECOMMENDATIONS (8)        │   │
│  │                            │  │                               │   │
│  │ ⚠️ AWS EC2 at 91% of cap  │  │ Est. savings: $1,855/month    │   │
│  │ ⚠️ AWS Total at 90% of cap│  │                               │   │
│  │ ℹ️ Azure creds expire 7d  │  │ Top: Rightsize prod-api-03    │   │
│  │                            │  │      → save $340/mo (High)    │   │
│  │ [View All Alerts →]        │  │ [View All Recommendations →]  │   │
│  └────────────────────────────┘  └───────────────────────────────┘   │
│                                                                       │
│  TOP COST DRIVERS (This Month)                                        │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ EC2 Compute        AWS   ████████████████████  $3,200  26%  │    │
│  │ Azure VMs          Azure ████████████          $2,100  17%  │    │
│  │ RDS PostgreSQL     AWS   ██████████            $1,800  14%  │    │
│  │ S3 Storage         AWS   ██████                $900     7%  │    │
│  │ Cloud Run          GCP   █████                 $750     6%  │    │
│  │ Azure App Service  Azure ████                  $650     5%  │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  BY TEAM (Tag: team)                                                  │
│  Tag Coverage: 78% ⚠️  ↑ from 71% last month  [View Untagged →]     │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ engineering   ████████████████████████  $6,800  55%         │    │
│  │ data          █████████████             $3,100  25%         │    │
│  │ infrastructure ████████                 $1,900  15%         │    │
│  │ (untagged)    ███                       $650     5%  ⚠️     │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  FORECAST — End of Month                                              │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ Spent so far: $12,450  Daily avg: $889/day  Days left: 8     │    │
│  │ Projected total: $19,562  Cap: $15,000  🔴 Will exceed cap   │    │
│  │ Estimated breach: ~Nov 2 (3 days away)                       │    │
│  │ FinOps Health: 64/100 ⚠️  [View Scorecard →]                │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  Cost View: [Unblended ▼]  (Amortized | Blended available)           │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

**Key rules:**
- Platform cards always visible even if that platform has no data — shows "Not connected" or "Sync failed"
- "Untagged" row always appears if any untagged spend exists — never hidden
- Tag Coverage % shown above the By Team section with week-over-week trend
- Forecast panel always visible; shows "Not enough data" in first 3 days of month
- FinOps Health score links to full scorecard page
- Cost View toggle applies to all spend numbers on the page; persisted per user preference
- Spend trend chart shows stacked bars by platform (not just total)
- Clicking any platform card navigates to the Per-Platform dashboard for that provider
- Clicking any team row navigates to a filtered view of that team's spend across all platforms

---

### **Per-Platform Dashboard (Example: AWS)**

Activated by clicking "View →" on a platform card, or via the sidebar nav.

```
┌──────────────────────────────────────────────────────────────────────┐
│ PRISM   [AWS ▼]  [This Month ▼]           🔔 2 Alerts  [← Overall]  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  AWS — October 2026                                                   │
│  ┌───────────────────────┐   ┌────────────────────────────────────┐  │
│  │ Total: $7,200         │   │ Cap: ██████████░  90% of $8,000 ⚠️│  │
│  │ ↑ $1,100 vs last month│   │ $800 remaining · 8 days left       │  │
│  │ (+18%)                │   │ At burn rate: will exceed in ~2d   │  │
│  └───────────────────────┘   └────────────────────────────────────┘  │
│  🟡 Data as of: Oct 23, 2026 (24h lag — normal)                      │
│  Last sync: 2h ago · 1,243 records  [Sync Now]                       │
│                                                                       │
│  ACCOUNTS                                                             │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ prod-account (123456789012)   $5,500  ████████████████  76%  │    │
│  │ staging (234567890123)        $1,200  ████              17%  │    │
│  │ dev (345678901234)            $500    ██                 7%  │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  TOP SERVICES (This Month)                                            │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ EC2 Compute       $3,200  ████████████████████  Cap: 91% ⚠️ │    │
│  │ RDS               $1,800  ███████████                        │    │
│  │ S3                $900    ██████                             │    │
│  │ Data Transfer     $650    ████                               │    │
│  │ Lambda            $400    ███                                │    │
│  │ EKS               $250    ██                                 │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  SPEND TREND — Daily (Last 30 Days)                                   │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ $300 ┤                          ╭──╮                         │    │
│  │ $250 ┤          ╭──────────────╯  ╰─────────────╮           │    │
│  │ $200 ┤──────────╯                               ╰──         │    │
│  │      └───Sep 24──────────────────────────Oct 24             │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  CAPS FOR AWS                                                         │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ AWS Total   $7,200 / $8,000  ██████████░  90% ⚠️  [Edit]   │    │
│  │ AWS EC2     $3,200 / $3,500  ██████████░  91% ⚠️  [Edit]   │    │
│  │ AWS RDS     $1,800 / $3,000  ██████░░░░   60% ✅  [Edit]   │    │
│  │             [+ Add Cap]                                       │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  BY TAG                                                               │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ [team ▼]  [environment ▼]  [owner ▼]                         │    │
│  │                                                               │    │
│  │ engineering   $4,200  ████████████████████                   │    │
│  │ data          $1,800  █████████                              │    │
│  │ infrastructure $800   ████                                   │    │
│  │ (untagged)    $400    ██  ⚠️ [View untagged resources]       │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  RECOMMENDATIONS (3 for AWS)                        $1,540 savings   │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ ● prod-api-03 (m5.2xlarge)  Rightsize → m5.large  $340/mo  │    │
│  │   High confidence · CPU avg 8% over 14 days                 │    │
│  │   [Implement] [Reject] [Details]                             │    │
│  │                                                               │    │
│  │ ● staging-db (RDS)  Idle 9 days → Terminate        $180/mo  │    │
│  │   High confidence · Zero connections since Oct 15            │    │
│  │   [Implement] [Reject] [Details]                             │    │
│  │                                                               │    │
│  │ ● 5× m5.xlarge on-demand  Reserved Instance (1yr) $1,020/mo │    │
│  │   High confidence · Running 24/7 for 45 days                │    │
│  │   [Implement] [Reject] [Details]                             │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  COMMITMENTS (AWS)                                                    │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ Coverage: 45% ⚠️   Utilization: 91% ✅   ESR: 18% ⚠️       │    │
│  │ EC2 RI (m5.xlarge · 1yr)   $2,100/mo · 98% util   ✅        │    │
│  │ Compute SP · 1yr           $1,800/mo · 87% util   ✅        │    │
│  │ ⚠️ EC2 RI expiring Dec 22 (58 days) — consider renewing     │    │
│  │ [View Full Commitment Details →]                              │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  NETWORK & EGRESS (This Month)                                        │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ Total data transfer cost: $650                                │    │
│  │ Internet egress (us-east-1):  $320  ████████████            │    │
│  │ Cross-AZ traffic:             $210  ████████  ⚠️ High       │    │
│  │ Cross-region (us→eu):         $80   ███                      │    │
│  │ NAT Gateway:                  $40   ██                       │    │
│  │ 💡 Cross-AZ traffic is 32% of data transfer — co-locate     │    │
│  │    services in same AZ to save ~$150/month                   │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  FORECAST (AWS)                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ Projected month-end: $8,750  Cap: $8,000  🔴 Will exceed    │    │
│  │ Days until cap breach: ~2 days (Oct 26 est.)                 │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ACTIVE ALERTS (2)                                                    │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ ⚠️ EC2 at 91% of $3,500 cap · Triggered Oct 24              │    │
│  │    [Acknowledge] [Snooze 24h]                                │    │
│  │ ⚠️ AWS Total at 90% of $8,000 cap · Triggered Oct 23        │    │
│  │    [Acknowledge] [Snooze 24h]                                │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

**Key rules:**
- Account breakdown only shows if more than one account is connected for this platform
- "By Tag" selector lets user switch between `team`, `environment`, `owner`, `project` views
- Spend Trend line chart is daily for "This Month" / "Last 7 days"; weekly for "Last 3 months"
- Cap rows show inline even if no cap is set — with "No cap set" and [+ Add Cap] shortcut
- Commitments section shows even if no commitments exist — "No commitments found. Buy RI/SP to save 30–60%."
- Network & Egress section shows if data transfer cost >$50/month; hidden if negligible
- Recommendations show only those related to this platform's resources
- All empty states are explicit: "No recommendations for AWS this month" — never blank sections

---

### **Dashboard: Untagged Resources View**

Accessible by clicking "(untagged)" in any tag breakdown row.

```
┌──────────────────────────────────────────────────────────────────────┐
│ Untagged Resources — AWS — October 2026                              │
│ 7 resources · $400 this month · Missing: team, owner tags            │
├──────────────────────────────────────────────────────────────────────┤
│ Resource              Type      Account    Region     Cost/mo  Tags  │
│ ───────────────────────────────────────────────────────────────────  │
│ i-0a1b2c3d4e5f        EC2       prod       us-east-1  $180     none  │
│ backup-logs-2026      S3        prod       us-east-1  $90      none  │
│ tmp-worker-01         EC2       staging    eu-west-1  $65      none  │
│ ...                                                                   │
│                                                                       │
│ [Export CSV]  [Set Tags in AWS Console →]                            │
└──────────────────────────────────────────────────────────────────────┘
```

If LLM is configured, each untagged resource row shows a suggested owner based on naming patterns — displayed as "Suggested: engineering team" with a confidence label.

---

## **LLM Integration (OpenRouter)**

### **Overview**

LLM features are **fully optional**. Every feature in Prism works without an LLM key. When a user configures OpenRouter, certain surfaces get richer, AI-generated context layered on top of the existing deterministic data. If the LLM API is down or the key is invalid, Prism falls back gracefully to the non-LLM version — no errors, no broken pages.

**Why OpenRouter instead of a direct provider?**
OpenRouter gives users access to many models (GPT-4o, Claude 3.5 Sonnet, Llama 3, Mistral, etc.) through a single API key and lets them control costs. Prism doesn't lock users into one model or bill for LLM usage itself.

---

### **LLM Configuration (in Settings)**

```
LLM / AI Features (Optional)
─────────────────────────────
OpenRouter API Key:   [ sk-or-v1-xxxxxxxxx ]   [Test]
Model:                [ google/gemini-flash-1.5 ▼ ]
                        anthropic/claude-3.5-sonnet
                        openai/gpt-4o
                        google/gemini-flash-1.5  ← (recommended — fast + cheap)
                        meta-llama/llama-3.1-70b
                        mistralai/mixtral-8x7b
Monthly LLM budget:   [ $10 ▼ ] — Prism stops LLM calls when this is exceeded
Status:               ✅ Connected · Model: gemini-flash-1.5

[Save]  [Disable LLM Features]
```

- User provides their own OpenRouter key
- Prism tracks approximate token usage and stops LLM calls if the configured monthly budget is exceeded (prevents surprise bills)
- Budget exceeded → silently fall back to non-LLM output; no error shown to end user

---

### **Where LLM Adds Value (Exhaustive List)**

#### **1. Monthly Report — Executive Narrative**

**Without LLM:** Report starts directly with the data tables.

**With LLM:** A 2–3 paragraph executive summary is prepended:

> *"October was your most expensive month since August, driven primarily by a 24% increase in EC2 spend on the prod account. The spike correlates with the new staging cluster added on October 8th, which has been running at low utilization. Your AWS cap is at 90% with 8 days remaining — at current burn rate you'll exceed it before month end.*
>
> *On the positive side, your GCP Cloud Run costs are up 21% but this aligns with the reported traffic growth. Azure remains stable. The top recommendation this month is converting 5 on-demand EC2 instances to Reserved Instances — this single change would save $1,020/month.*
>
> *Three actions worth taking this week: (1) Review the staging cluster size, (2) implement the EC2 rightsizing for prod-api-03, (3) rotate your Azure client secret expiring in 7 days."*

LLM prompt uses: total spend delta, top cost drivers, cap status, pending recommendations, active alerts. No raw resource data or credentials are sent.

---

#### **2. Recommendations — Plain-English Explanations**

**Without LLM:** Generic rule description shown.
```
prod-api-03 (EC2 m5.2xlarge)
Type: Rightsizing
Reason: CPU utilization below 20% for 7+ days
Est. savings: $340/month
Confidence: High
```

**With LLM:** A specific, actionable explanation:
```
prod-api-03 (EC2 m5.2xlarge)
Type: Rightsizing
Est. savings: $340/month · High confidence

"This instance has averaged 7% CPU over the past 14 days with a peak
of 18% on Oct 12. An m5.large would handle this comfortably and costs
$340 less per month. Before downsizing, confirm no memory-intensive
batch jobs run on this instance that don't show up in CPU metrics."
```

---

#### **3. Alert Emails — Likely Cause Sentence**

**Without LLM:** Alert email shows spend numbers and threshold.

**With LLM:** One sentence of context is added to the alert email:

> *"This spike coincides with 3 new EC2 instances launched in us-east-1 on Oct 22 — these appear to be running continuously and are not tagged."*

LLM uses: previous 7-day spend pattern, current spend, resource delta from CloudTrail summary. No credentials sent.

---

#### **4. Natural Language Cost Queries (In-App Chat)**

A simple query box appears in the dashboard sidebar when LLM is configured:

```
Ask Prism ✨
─────────────
[ Why did AWS costs jump last week?        ] [Ask]

Answer:
AWS spend increased $1,100 (18%) week-over-week.
The main driver was EC2 in us-east-1 (+$800), which
matches the 3 new instances launched on Oct 22.
These instances have no team tag and are running 24/7.
Suggestion: tag them and evaluate if they're needed.

Source: cost data Oct 16–24, 2026 · Generated by gemini-flash-1.5
```

**Supported query types:**
- "Why did [platform] cost spike [time period]?"
- "What's our biggest waste right now?"
- "How much did [team] spend last month?"
- "Which services are approaching their cap?"
- "What would save us the most money?"
- "Summarize this month's spend for our board"

**How it works:** Prism pre-aggregates relevant data (top cost drivers, deltas, cap status, recommendations) into a structured context block and sends that — not raw database rows — to the LLM. Response is streamed back to the UI.

---

#### **5. Untagged Resource Ownership Suggestions**

When LLM is configured, each untagged resource gets a suggested owner based on its name, region, account, and service type.

```
i-0a1b2c3d4e5f (EC2)   Cost: $180/mo   Tags: none
Suggested owner: engineering team
Reason: "Name pattern 'prod-api' and region us-east-1 match other
engineering-tagged EC2 instances in this account."
Confidence: Medium
[Accept suggestion] [Tag differently] [Ignore]
```

If user clicks "Accept suggestion" → Prism adds the tag in its own records (does not write back to the cloud provider — read-only).

---

### **LLM Implementation**

```typescript
import OpenAI from "openai"; // OpenRouter is OpenAI-compatible

const openrouter = new OpenAI({
  baseURL: "https://openrouter.ai/api/v1",
  apiKey: process.env.OPENROUTER_API_KEY, // user's key from vault
});

export class LLMService {
  private enabled: boolean;
  private model: string;
  private monthlyBudgetUSD: number;
  private spentThisMonth: number;

  constructor(config: LLMConfig | null) {
    this.enabled = config !== null && !!config.apiKey;
    this.model = config?.model ?? "google/gemini-flash-1.5";
    this.monthlyBudgetUSD = config?.monthlyBudget ?? 10;
    this.spentThisMonth = 0; // loaded from Redis at startup
  }

  async generateReportNarrative(context: ReportContext): Promise<string | null> {
    if (!this.canCall()) return null; // caller uses template fallback

    const prompt = `
You are a FinOps analyst for a startup. Write a 2-3 paragraph executive summary
of this month's cloud cost report. Be specific, actionable, and concise.
Highlight anomalies, wins, and top 3 actions to take this week.

Data:
- Total spend: ${context.totalSpend} (${context.totalDelta > 0 ? "+" : ""}${context.totalDelta} vs last month)
- AWS: ${context.aws.spend} (${context.aws.capPct}% of cap)
- Azure: ${context.azure.spend} (${context.azure.capPct}% of cap)
- GCP: ${context.gcp.spend} (${context.gcp.capPct}% of cap)
- Top cost driver: ${context.topDriver.service} +${context.topDriver.delta}
- Pending recommendations: ${context.recommendations.length} (est. $${context.totalSavings}/mo)
- Active alerts: ${context.alerts.map(a => a.label).join(", ")}

Write in plain English, no markdown, no bullet points. Speak to a non-technical founder.
    `.trim();

    return this.call(prompt, 400); // max 400 tokens for narrative
  }

  async explainRecommendation(rec: Recommendation, metrics: ResourceMetrics): Promise<string | null> {
    if (!this.canCall()) return null;

    const prompt = `
Explain this cloud cost recommendation in 2-3 sentences for an engineer.
Be specific about the evidence and include one caveat to check before acting.

Resource: ${rec.resource_name} (${rec.provider} ${rec.service})
Type: ${rec.type}
Evidence: ${metrics.cpuAvg}% avg CPU over ${metrics.days} days, peak ${metrics.cpuPeak}%
Estimated savings: $${rec.estimated_monthly_savings}/month
    `.trim();

    return this.call(prompt, 150);
  }

  async answerCostQuery(question: string, context: CostQueryContext): Promise<string | null> {
    if (!this.canCall()) return null;

    const prompt = `
You are a FinOps assistant. Answer this question using only the data provided.
If the data doesn't contain enough to answer, say so clearly. Be concise (max 4 sentences).

Question: ${question}

Data context:
${JSON.stringify(context, null, 2)}
    `.trim();

    return this.call(prompt, 200);
  }

  private async call(prompt: string, maxTokens: number): Promise<string | null> {
    // Check Redis cache first
    const cacheKey = `llm:${Buffer.from(prompt).toString("base64").slice(0, 64)}`;
    const cached = await redis.get(cacheKey);
    if (cached) return cached;

    try {
      const response = await openrouter.chat.completions.create({
        model: this.model,
        messages: [{ role: "user", content: prompt }],
        max_tokens: maxTokens,
      });

      const text = response.choices[0]?.message?.content ?? null;
      const costUSD = this.estimateCost(response.usage, maxTokens);
      this.spentThisMonth += costUSD;
      await redis.set(`llm:monthly_spent`, this.spentThisMonth, "EX", 86400 * 31);

      if (text) await redis.set(cacheKey, text, "EX", 86400); // cache 24h
      return text;
    } catch (err: any) {
      logger.warn({ error: err.message }, "LLM call failed — using fallback");
      return null; // caller always handles null gracefully
    }
  }

  private canCall(): boolean {
    return this.enabled && this.spentThisMonth < this.monthlyBudgetUSD;
  }

  private estimateCost(usage: any, maxTokens: number): number {
    // Rough estimate — actual cost depends on model
    // gemini-flash-1.5: ~$0.000075/1K tokens
    const tokens = (usage?.total_tokens ?? maxTokens) / 1000;
    return tokens * 0.000075;
  }
}
```

**Key design decisions:**
- `canCall()` checks budget before every LLM call — if budget exceeded, returns `null`, caller uses template fallback
- All callers check for `null` return and have a non-LLM path — LLM is never a hard dependency
- Prompt never includes credentials, raw API keys, or personally identifiable information
- Response cached 24h in Redis — same question asked multiple times hits cache, not API
- LLM errors are logged as `warn`, not `error` — they don't trigger alerts or affect uptime metrics

---

## **Virtual Tagging**

### **Overview**

Virtual Tagging lets users define tag rules *inside Prism* without touching cloud infrastructure. Rules run at ingestion time and retroactively apply to historical records. This solves the biggest FinOps problem at startups: 40–70% of spend is untagged, making cost allocation impossible.

> **⚠️ Retroactive Re-tagging:** Applying a rule to 13 months of historical data can affect millions of CostRecord rows. This is **never done synchronously** — it always runs as a background job (`prism-virtual-tags` queue). The UI shows a progress indicator ("Re-tagging 847,293 records — 34% done") while the job runs. Queries during re-tagging use the old `virtual_tags` values until the job completes. The job is idempotent: cancelled and restarted jobs produce the same output. Estimated runtime: ~2 minutes per 1M records on a PgBouncer-fronted TimescaleDB.

**Without Virtual Tagging:** Team A's S3 bucket named `team-a-data-prod` shows as "Untagged" because no one added the `team: team-a` tag in AWS.  
**With Virtual Tagging:** Rule says `IF resource_name CONTAINS "team-a" THEN team = "team-a"` — the bucket is allocated correctly with zero AWS changes.

---

### **Rule Types**

| Rule Type | Example | Use Case |
|-----------|---------|---------|
| **Name pattern** | resource_name CONTAINS "prod-api" → team = engineering | Consistent naming conventions |
| **Account-based** | account_id = "123456789012" → environment = production | Dedicated AWS accounts per environment |
| **Service-based** | service = "Amazon RDS" AND region = "eu-west-1" → team = data | All DBs in EU belong to data team |
| **Fixed % split** | resource_id = "i-0a1b2c3d" → 60% engineering / 40% data | Shared resource split |
| **Tag override** | existing tag `env = prod` → override with `environment = production` | Normalize inconsistent tags |

### **Rule Builder UI**

```
Virtual Tag Rules                                    [+ New Rule]
──────────────────────────────────────────────────────────────────
Priority  Rule                                 Applies to    Action
  1       name CONTAINS "prod-api"             All accounts  team = engineering
  2       account = "dev-account"              AWS           environment = development
  3       service = "Amazon RDS"               AWS           team = data (60%) / infra (40%)
  4       name CONTAINS "shared-"              All           equal split across all teams
──────────────────────────────────────────────────────────────────
Last applied: Oct 24, 2026 06:05 AM · 1,243 records re-tagged
[Apply Rules Now]  [View Audit Log]
```

Rules are evaluated top-to-bottom. First match wins (unless split rule, which always runs).

### **Virtual Tag Data Model**

```typescript
VirtualTagRule {
  id: UUID
  org_id: UUID
  priority: int                    // evaluation order; lower = higher priority
  condition_field: 'resource_name' | 'account_id' | 'service' | 'region' | 'tag_key'
  condition_operator: 'contains' | 'equals' | 'starts_with' | 'ends_with' | 'regex'
  condition_value: string
  action_type: 'set_tag' | 'split'
  tag_key: string                  // e.g. "team", "environment", "owner"
  tag_value: string | null         // for set_tag; null for split
  split_config: jsonb | null       // [{team: "engineering", pct: 60}, {team: "data", pct: 40}]
  provider_scope: 'aws' | 'azure' | 'gcp' | 'all'
  is_active: boolean
  created_by: UUID
  created_at: timestamp
  last_applied_at: timestamp | null
  records_affected: int | null
}

VirtualTagAuditLog {
  id: UUID
  org_id: UUID
  rule_id: UUID
  changed_by: UUID
  change_type: 'created' | 'updated' | 'deleted' | 'reordered'
  before: jsonb | null
  after: jsonb | null
  timestamp: timestamp
}
```

### **Tagging Coverage Score**

Displayed prominently on both the Overall Dashboard and the Per-Platform Dashboard:

```
Tag Coverage: 78% of spend tagged  ↑ from 71% last month ✅
  AWS:   83% ✅     Azure: 74% ⚠️     GCP: 69% ⚠️
  Untagged spend: $2,730/month  [View Untagged Resources →]
```

Target: >90% coverage. Red if <60%, Yellow if 60–89%, Green if ≥90%.

---

## **Spend Forecasting**

### **Overview**

Prism projects end-of-month spend using a simple, transparent linear model — no ML required. Formula: `daily_avg_spend × days_in_month + adjustment_for_known_one-offs`. Shown on both Overall and Per-Platform dashboards. Compared to actuals at month-end in the monthly report to track accuracy over time.

### **Forecast Widget (Dashboard)**

Shown on the Overall Dashboard and each Per-Platform dashboard:

```
┌────────────────────────────────────────────────────────┐
│ Forecast: End of Month                                  │
│                                                        │
│ Spent so far:     $8,400  (14 days)                    │
│ Daily avg:        $600/day                             │
│ Days remaining:   17 days                              │
│ Projected total:  $8,400 + ($600 × 17) = $18,600      │
│                                                        │
│ Cap:              $15,000                              │
│ Gap to cap:       -$3,600  🔴 Will exceed cap          │
│ Days until breach: ~11 days (Nov 4 est.)               │
│                                                        │
│ Last month actual: $12,450                             │
│ Forecast accuracy: ±12% over last 3 months             │
└────────────────────────────────────────────────────────┘
```

### **Forecast Alert**

A new alert type added to the alert system:

| Alert | Trigger | Severity |
|-------|---------|---------|
| **Forecast breach** | Projection exceeds cap before month-end | Warning |
| **Acceleration** | Daily spend rate increased >30% week-over-week | Warning |

These fire even if no threshold has been breached yet — they're *predictive* alerts, not reactive.

**Email subject:** "⚠️ Prism Forecast: AWS projected to exceed $8,000 cap by Nov 4"

### **Forecast Accuracy Tracking**

At month-end, Prism compares the forecast made on day 15 of that month to the actual final spend:

```
Forecast Accuracy — October 2026
  Forecast (made Oct 15):  $13,800
  Actual (month-end):      $12,450
  Variance:                -$1,350 (-9.8%)  ✅ Within ±10% target
```

Shown in the monthly report as a running 3-month track record. Improves trust in forecasts over time.

### **Forecast Edge Cases**

| Situation | Behavior |
|-----------|---------|
| **First 3 days of month** | Insufficient data — widget shows "Not enough data yet (need 3+ days)" |
| **Org connected mid-month** | Use days-since-connection as denominator, not days-since-month-start |
| **Spend = $0 for several days** (e.g. weekends with no usage) | Use rolling 7-day average instead of simple daily average to smooth weekend dips |
| **Month just closed** | Widget shows "Month closed: Final $X" instead of forecast |
| **No cap set** | Forecast shows projected total without breach warning |
| **Provider sync failed** | Forecast based on last successful sync data, with note: "Based on data as of [date]" |

### **Forecast Data Model**

```typescript
SpendForecast {
  id: UUID
  org_id: UUID
  account_id: UUID | null    // null = org-level forecast
  provider: string | null    // null = cross-platform
  forecast_month: date       // first day of the month being forecast
  generated_at: timestamp
  spend_to_date: decimal
  daily_avg: decimal
  rolling_7d_avg: decimal    // used when simple avg is distorted by zero-spend days
  days_with_data: int        // actual days with data (not just calendar days)
  days_remaining: int
  projected_total: decimal
  cap_amount: decimal | null
  will_breach: boolean
  breach_date: date | null
  data_coverage: 'full' | 'partial' | 'insufficient'  // 'insufficient' if days_with_data < 3
  // Filled at month-end:
  actual_total: decimal | null
  variance_pct: decimal | null
}
```

---

## **Commitment Management**

### **Overview**

Reserved Instances (AWS), Savings Plans (AWS), and Committed Use Discounts (GCP CUD) can save 30–60% on compute — but only if you know what you have, how much you're using, and when things expire. This section tracks all three dimensions.

### **Key Metrics**

| Metric | Formula | Target |
|--------|---------|--------|
| **Commitment Coverage Rate** | Commitment-covered spend ÷ eligible on-demand spend | 60–80% |
| **Commitment Utilization Rate** | Commitment hours used ÷ commitment hours purchased | >95% |
| **Effective Savings Rate (ESR)** | Savings from commitments ÷ on-demand-equivalent spend | >20% (mature: 30–40%) |
| **Unused Commitment Cost** | Hours purchased but not consumed × hourly rate | $0 target |

### **Commitment Dashboard (Per-Platform Tab)**

```
AWS Commitments — October 2026
──────────────────────────────────────────────────────────────────
Coverage:     45% of eligible compute  ⚠️  (target: 60–80%)
Utilization:  91% of purchased hours   ✅
ESR:          18%                      ⚠️  (target: >20%)
Unused cost:  $280/month               ⚠️

Active Commitments:
  Type          Term    Expires     Coverage    Utilization  Monthly Savings
  EC2 RI        1yr     Mar 2027    $2,100/mo   98%          $630/mo
  Compute SP    1yr     Jun 2027    $1,800/mo   87%          $450/mo
  EC2 RI        3yr     Jan 2028    $800/mo     79% ⚠️       $300/mo ← underutilized

Expiring Soon:
  ⚠️ EC2 RI for m5.xlarge (us-east-1) — expires in 58 days (Dec 22, 2026)
     Renew? Current on-demand rate: $0.192/hr | RI rate: $0.110/hr

Opportunities:
  💡 5× m5.xlarge running 24/7 for 45 days → 1yr Compute SP saves $1,020/month
     [View Recommendation]
──────────────────────────────────────────────────────────────────
```

### **Commitment Expiry Alerts**

| Alert | Trigger | Delivery |
|-------|---------|---------|
| Commitment expiring in 60 days | RI/SP/CUD expiry date approaching | Email |
| Commitment expiring in 30 days | — | Email |
| Commitment expiring in 14 days | — | Email + Teams/Slack |
| Commitment expired (unused remaining) | Term ended with unused hours | Email |

### **Commitment Sync Frequency**

| Provider | Sync Frequency | Source | Notes |
|----------|---------------|--------|-------|
| AWS RI / SP | Daily, 07:00 UTC | Cost Explorer APIs | Utilization data has ~24h lag |
| GCP CUD | Daily, 07:00 UTC | Billing API | CUD list is near-real-time; usage data has ~24h lag |
| All | On account add | Backfill last 3 months | Initial load; uses async background job |
| Expiry alerts | Daily check | Local CommitmentRecord table | Fires when `end_date` ≤ 30 days away |

### **Commitment Data Model**

```typescript
CommitmentRecord {
  id: UUID
  org_id: UUID
  account_id: UUID
  provider: 'aws' | 'gcp'
  commitment_type: 'reserved_instance' | 'savings_plan' | 'committed_use_discount'
  external_id: string          // AWS RI ID, SP ARN, GCP CUD ID
  instance_type: string | null // e.g. "m5.xlarge"
  region: string | null
  term_months: int             // 12 or 36
  start_date: date
  end_date: date
  hourly_commitment: decimal   // for SPs
  monthly_cost: decimal        // amortized
  monthly_on_demand_equivalent: decimal
  monthly_savings: decimal
  utilization_pct: decimal     // 0–100
  coverage_amount: decimal     // spend covered this month
  status: 'active' | 'expired' | 'expiring_soon'
  last_updated: timestamp
}
```

### **Commitment API Endpoints Used**

| Provider | API | Data Pulled |
|----------|-----|------------|
| AWS | `ce:GetReservationUtilizationSummary` | RI utilization % per day |
| AWS | `ce:GetReservationCoverage` | What % of eligible EC2 is RI-covered |
| AWS | `ce:GetSavingsPlansUtilizationDetails` | SP utilization per plan |
| AWS | `ce:GetSavingsPlansCoverage` | SP coverage % of eligible spend |
| GCP | Billing API `commitments.list` | CUD list, terms, applied usage |

These permissions need to be added to the AWS IAM policy (already partially present — `ce:GetSavingsPlansUtilization` exists; add `ce:GetReservationUtilizationSummary`, `ce:GetReservationCoverage`, `ce:GetSavingsPlansUtilizationDetails`, `ce:GetSavingsPlansCoverage`).

---

## **FinOps Health Scorecard**

### **Overview**

A single-page health score for the org's FinOps practice. Updated daily. Shows whether key metrics are improving or degrading. Designed for two audiences: engineers (working-level view) and executives (1-page summary).

### **Scorecard Metrics**

| Metric | How Calculated | Red | Yellow | Green |
|--------|---------------|-----|--------|-------|
| **Tag Coverage** | % of spend with owner + team + environment tags | <60% | 60–89% | ≥90% |
| **Allocation Coverage** | % of spend allocated to a team/project (not "untagged") | <80% | 80–94% | ≥95% |
| **Commitment Coverage** | % of eligible compute under RI/SP/CUD | <30% | 30–59% | ≥60% |
| **Commitment Utilization** | % of purchased commitment hours used | <85% | 85–94% | ≥95% |
| **Effective Savings Rate** | Savings from commitments ÷ on-demand-equivalent spend | <10% | 10–19% | ≥20% |
| **Idle Resource Rate** | % of resources with <5% utilization for 14+ days | >10% | 5–10% | <5% |
| **Recommendations Acted On** | % of recs implemented or rejected (not ignored) | <30% | 30–59% | ≥60% |
| **Forecast Accuracy** | Avg deviation of forecast vs actual (last 3 months) | >20% | 10–20% | <10% |
| **Cap Breaches** | Number of cap thresholds exceeded at 100%+ this month | >2 | 1–2 | 0 |

**Overall Score** = weighted average (0–100). Weights: Tag Coverage 20%, Allocation 15%, Commitment Coverage 20%, Commitment Utilization 10%, ESR 15%, Idle Rate 10%, Recs Acted On 10%.

### **Working-Level Scorecard (Engineering/FinOps view)**

```
FinOps Health Score — October 2026                Overall: 64/100 ⚠️

Metric                  Score   Trend    Detail
─────────────────────────────────────────────────────────────────
Tag Coverage            78%  ⚠️  ↑ +7%   $2,730 untagged/month
Allocation Coverage     95%  ✅  ↑ +2%   Only $650 in "untagged"
Commitment Coverage     45%  🔴  →  0%   Target: 60–80%
Commitment Utilization  91%  ✅  ↓ -3%   $280/mo wasted on unused RI
Effective Savings Rate  18%  ⚠️  ↑ +3%   Target: >20%
Idle Resource Rate      3%   ✅  ↓ -1%   2 idle resources flagged
Recs Acted On           52%  ⚠️  ↑ +8%   8 pending, 9 implemented
Forecast Accuracy       91%  ✅  ↑ +5%   ±9% avg last 3 months
Cap Breaches            0    ✅  →  0    No caps exceeded this month

Top 3 actions to improve score:
1. Increase commitment coverage from 45% → 60% (buy $1,800/mo Compute SP)
2. Tag 3 untagged resources in AWS (saves $800/mo from allocation blind spot)
3. Act on 8 pending recommendations ($1,855/mo potential savings)
```

### **Executive KPI View (CTO / CFO)**

A separate simplified view accessible from the top nav. No drill-downs. Printable.

```
Cloud Spend Executive Summary — October 2026        [Print/Export PDF]
────────────────────────────────────────────────────────────────────
SPEND
  This month:     $12,450   ↑ +15% vs last month
  Last month:     $10,800
  YTD total:      $98,200
  EOMonth forecast: $12,450 (actual — month closed)

BUDGET CONTROL
  Caps breached:    0  ✅
  At risk (>80%):   AWS EC2 at 91% ⚠️
  Remaining budget: $2,550 of $15,000 org cap

SAVINGS
  Captured this month: $1,200  (from 3 implemented recommendations)
  Pipeline (pending):  $1,855  (8 recommendations not yet acted on)
  Commitment savings:  $1,380  (ESR: 18%)
  Total captured YTD:  $8,400

EFFICIENCY
  Cost per active user: $4.20/month  ↓ from $4.80 last month ✅
  Cloud as % of revenue: 12%  (target: <15%) ✅

HEALTH SCORE
  FinOps Score: 64/100 ⚠️
  Biggest gap: Commitment coverage 45% (target: 60–80%)
  Action: Purchase Compute Savings Plan → save $1,020/month
────────────────────────────────────────────────────────────────────
```

---

## **Primary Integrations**

### **Integration Matrix**

| Platform | Data Source | Auth Method | Granularity | Data Lag | Rate Limit |
|----------|------------|-------------|-------------|----------|-----------|
| **AWS** | Cost Explorer API + CloudTrail | IAM role (STS assume) | Daily (hourly for current month) | 24–48h | 5 TPS |
| **Azure** | Cost Management API | Service principal (OAuth2) | Daily | 24–72h | 30 req/min |
| **GCP** | Cloud Billing API + BigQuery export | Service account (JWT) | Daily | 24–48h | 5 QPS |

**Note on Data Lag:** Cloud providers batch and finalize billing data with a 24–72 hour delay. Prism shows the latest available data and displays the data-as-of timestamp clearly on the dashboard. Real-time spend estimates are available for AWS (Cost Explorer current month) but are estimates until the billing period closes.

---

## **Technical Architecture**

### **Data Storage Philosophy**

Prism stores the **minimum data needed** to power the dashboard, alerts, reports, and recommendations. It does not store raw API responses, full billing line items, or logs it doesn't query.

| What We Store | Why | Granularity |
|--------------|-----|-------------|
| Daily cost totals per service per account | Dashboard, trend charts, cap checks | 1 row/service/day |
| Tag snapshot per cost record | Team allocation, chargeback | Stored with cost row |
| Virtual tag rules | Tag-less allocation | Config table |
| Resource inventory (name, type, region, age, last-seen cost) | Recommendations, idle detection, lifecycle | 1 row/resource |
| Commitment records (RI/SP/CUD) | Commitment dashboard, ESR, expiry alerts | 1 row/commitment |
| Spend forecasts | Forecast widget, accuracy tracking | 1 row/month/scope |
| Business metrics + daily values | Unit economics | 1 row/metric/day |
| Budget caps + thresholds | Alert engine | Config table |
| Outbound webhook configs | Custom integrations | Config table |
| Alert history | Audit trail, deduplication | 1 row/alert |
| Recommendation list + status + actual savings | Dashboard, report, ROI tracking | 1 row/recommendation |
| Sync logs | Debug, health checks | 1 row/sync run |
| User / org / member data | Auth, RBAC | Config tables |
| LLM responses | Cache to avoid repeat calls | Redis only, 24h TTL |

| What We Do NOT Store | Reason |
|---------------------|--------|
| Raw API responses from AWS/Azure/GCP | Too large, never queried directly |
| Full CloudTrail event logs | Only resource-attribution summary kept |
| Per-hour cost breakdowns | Daily is sufficient; hourly multiplies storage 24× |
| Every individual billing line item | Top 20 services per account per day is enough |
| LLM prompts/responses in DB | Redis cache covers re-use; no need to persist |
| User IP addresses or browser fingerprints | Not needed, privacy-first |

**Retention:**
- `CostRecord` (TimescaleDB): 13 months hot → compressed to S3 Parquet after that
- `Alert`, `Recommendation`: indefinite (small tables, <1M rows even at scale)
- `SyncLog`: 90 days, then purged
- `LLM cache` (Redis): 24-hour TTL per entry

---

### **Backend Stack**
- **Runtime:** Node.js + Express (or Python + FastAPI — team's choice)
- **Database:** PostgreSQL (relational data) + TimescaleDB (time-series cost records)
- **Cache:** Redis (cost aggregations, session tokens, LLM response cache)
- **Queue:** AWS SQS or BullMQ (daily sync jobs, report generation, alert checks)
- **Auth:** Email/password (bcrypt), Google OAuth 2.0, JWT (7-day access, 30-day refresh)
- **Email:** AWS SES or SendGrid (alerts, reports, invites)
- **LLM:** OpenRouter API (user-configured, optional — `openai`-compatible SDK)
- **Real-time:** WebSocket (dashboard auto-refresh every 5 min; alert banners pushed live)
- **Hosting:** AWS EKS (Kubernetes); CDN CloudFront; PgBouncer connection pooling

### **Frontend Stack**
- **Framework:** React 19 + TypeScript
- **Styling:** Tailwind CSS
- **Charts:** Recharts, Plotly
- **Components:** Shadcn/UI (headless, accessible)
- **State:** React Query (server data), Zustand (UI state)
- **Real-time:** WebSocket client + auto-reconnect

### **Data Models**

```typescript
// Core entities in PostgreSQL

Organization {
  id: UUID
  name: string
  plan: 'starter' | 'professional' | 'enterprise'
  billing_period_start: date
  currency: 'USD' | 'EUR' | 'GBP' | 'INR' | 'AUD' | 'CAD'  // default: USD
  timezone: string          // IANA tz, e.g. "America/New_York" — used for daily digest send time and sync schedule display
  feature_flags: jsonb      // {"virtual_tagging": true, "commitments": false} — for staged rollout
  created_at: timestamp
}

// Hierarchy: Org → AccountGroup → CloudAccount
AccountGroup {
  id: UUID
  org_id: UUID
  provider: 'aws' | 'azure' | 'gcp'
  scope: 'single' | 'multi' | 'organization'
  display_name: string
  // For org-level: management account / billing account / billing account ID
  root_account_id: string | null
}

CloudAccount {
  id: UUID
  group_id: UUID
  org_id: UUID
  provider: 'aws' | 'azure' | 'gcp'
  account_id: string          // AWS account ID, Azure subscription ID, GCP project ID
  display_name: string
  credentials: encrypted_blob
  last_sync: timestamp | null
  last_sync_status: 'success' | 'partial' | 'failed' | 'never'
  last_sync_error: string | null
  last_sync_records: int | null
  data_as_of: timestamp | null // most recent data timestamp from provider
  is_active: boolean
}

CostRecord (TimescaleDB hypertable) {
  time: timestamp
  org_id: UUID
  account_id: UUID
  provider: string
  service: string
  region: string
  cost_usd: decimal          // always stored in USD; converted at ingestion
  cost_unblended_usd: decimal  // AWS unblended cost (same as cost_usd for Azure/GCP)
  cost_amortized_usd: decimal  // AWS amortized cost (RI/SP spread); same as unblended for others
  cost_original: decimal     // original currency amount
  original_currency: string
  fx_rate: decimal           // rate used at conversion
  usage_value: decimal
  usage_unit: string
  tags: jsonb                // normalized: {team, owner, project, environment}
  virtual_tags: jsonb        // tags applied by VirtualTagRule engine (separate from provider tags)
  is_estimate: boolean       // true if from current billing period (not yet finalized)
  // UNIQUE CONSTRAINT: (account_id, time::date, service, region) — enforces idempotency
  // Duplicate syncs do INSERT ... ON CONFLICT DO UPDATE SET cost_usd = EXCLUDED.cost_usd
}

BudgetCap {
  id: UUID
  org_id: UUID
  name: string                                 // display name, e.g. "AWS EC2 Production"
  scope: 'platform' | 'service' | 'account'
  provider: 'aws' | 'azure' | 'gcp' | null    // null = all platforms
  service_name: string | null                  // null = all services
  account_id: UUID | null                      // null = all accounts
  cap_amount: decimal                          // in org currency
  period: 'monthly'
  is_active: boolean
  created_by: UUID
  created_at: timestamp
  updated_at: timestamp
}

Alert {
  id: UUID
  org_id: UUID
  cap_id: UUID | null
  type: 'cap_threshold'       // budget cap crossed 75/90/100/125/150%
       | 'forecast_breach'    // projected EOMonth spend will exceed cap
       | 'spend_acceleration' // daily avg increased >30% WoW
       | 'sync_failure'       // cloud account sync failed 2+ times
       | 'credential_expiry'  // Azure/GCP credential expires in <14 days
       | 'commitment_expiry'  // RI/SP/CUD expires within 60 days
       | 'unused_commitment'  // commitment utilization <80%
       | 'untagged_resource'  // new resource with no owner/team tag
       | 'idle_resource'      // resource with zero usage for 7+ days
  scope_label: string         // e.g. "AWS EC2", "Azure total", "GCP (dev account)"
  threshold_percent: int | null  // 75, 90, 100, 125, 150 (cap_threshold only)
  spend_at_trigger: decimal | null
  cap_amount: decimal | null
  metadata: jsonb | null      // extra context: {commitment_id, resource_id, days_until_expiry, etc.}
  severity: 'info' | 'warning' | 'critical'
  triggered_at: timestamp
  email_sent: boolean
  teams_sent: boolean
  slack_sent: boolean
  webhook_sent: boolean
  acknowledged_by: UUID | null
  acknowledged_at: timestamp | null
  snoozed_until: timestamp | null
  // UNIQUE partial index: (org_id, cap_id, type, threshold_percent, date_trunc('month', triggered_at))
  // Prevents duplicate cap_threshold alerts for the same threshold in the same billing period
}

Recommendation {
  id: UUID
  org_id: UUID
  account_id: UUID
  resource_id: string
  resource_name: string
  provider: string
  service: string
  type: 'rightsizing'         // CPU/memory underutilized
       | 'idle_termination'   // zero usage for 7+ days
       | 'reserved_instance'  // on-demand running 24/7 for 30+ days
       | 'storage_tiering'    // cold data on hot storage
       | 'network_egress'     // high cross-AZ or cross-region traffic
       | 'commitment_renewal' // RI/SP/CUD expiring, should renew
  estimated_monthly_savings: decimal
  confidence: 'high' | 'medium' | 'low'
  llm_explanation: string | null   // LLM-generated plain-English explanation (null if LLM off)
  llm_risk_note: string | null     // LLM-generated risk caveat
  created_at: timestamp
  status: 'pending' | 'implemented' | 'rejected' | 'archived'
  implemented_at: timestamp | null
  actual_savings: decimal | null   // measured 30 days after implementation
  actual_savings_updated_at: timestamp | null
}

MonthlyReport {
  id: UUID
  org_id: UUID
  send_day_of_month: int      // 1–28
  recipient_emails: string[]
  include_recommendations: boolean
  include_per_account: boolean
  include_commitments: boolean      // default: true if org has any CommitmentRecords
  include_unit_economics: boolean   // default: true if org has any BusinessMetrics configured
  include_finops_scorecard: boolean // default: true
  last_sent: timestamp | null
  next_send: timestamp
  is_active: boolean
}

LLMConfig {
  id: UUID
  org_id: UUID
  openrouter_api_key: encrypted_string   // user's own key, AES-256
  model: string                          // e.g. "google/gemini-flash-1.5"
  monthly_budget_usd: decimal            // default: 10.00
  is_enabled: boolean
  created_at: timestamp
  updated_at: timestamp
  // spent_this_month tracked in Redis, not DB — avoids write amplification
}

VirtualTagRule {
  id: UUID
  org_id: UUID
  priority: int                           // lower = higher priority; rules applied in priority order
  condition_field: 'resource_name' | 'account_id' | 'service' | 'region' | 'tag_value'
  condition_operator: 'contains' | 'equals' | 'starts_with' | 'ends_with' | 'regex'
  condition_value: string
  // IMPORTANT: if condition_operator = 'regex', validate at save time:
  //   1. Pattern must compile without error
  //   2. Pattern must complete on a 1000-char test string in <50ms (ReDoS guard)
  //   3. Max pattern length: 200 chars
  action_type: 'set_tag' | 'split'
  tag_key: string                         // e.g. "team", "environment"
  tag_value: string | null                // null if action_type = split
  split_config: jsonb | null              // [{team:"engineering",pct:60},{team:"data",pct:40}]
  // split_config pct values must sum to 100 — validated at save time
  provider_scope: 'aws' | 'azure' | 'gcp' | 'all'
  is_active: boolean
  last_applied_at: timestamp | null
  records_affected: int | null
  created_by: UUID
  created_at: timestamp
  updated_at: timestamp
  updated_by: UUID | null
}

CommitmentRecord {
  id: UUID
  org_id: UUID
  account_id: UUID
  provider: 'aws' | 'gcp'
  commitment_type: 'reserved_instance' | 'savings_plan' | 'committed_use_discount'
  external_id: string
  instance_type: string | null
  region: string | null
  term_months: int
  start_date: date
  end_date: date
  monthly_cost: decimal                   // amortized
  monthly_on_demand_equivalent: decimal
  monthly_savings: decimal
  utilization_pct: decimal
  coverage_amount: decimal
  status: 'active' | 'expired' | 'expiring_soon'
  last_updated: timestamp
}

SpendForecast {
  id: UUID
  org_id: UUID
  account_id: UUID | null                // null = org-level
  provider: 'aws' | 'azure' | 'gcp' | null // null = cross-platform
  forecast_month: date
  generated_at: timestamp
  spend_to_date: decimal
  daily_avg: decimal
  days_remaining: int
  projected_total: decimal
  cap_amount: decimal | null
  will_breach: boolean
  breach_date: date | null
  actual_total: decimal | null           // filled at month-end
  variance_pct: decimal | null           // filled at month-end
}

BusinessMetric {
  id: UUID
  org_id: UUID
  name: string                           // e.g. "active_customers", "api_requests"
  source: 'manual' | 'webhook' | 'datadog' | 'stripe' | 'csv'
  unit: string                           // e.g. "customers", "requests", "transactions"
  is_active: boolean
  created_at: timestamp
}

BusinessMetricValue {
  id: UUID
  metric_id: UUID
  org_id: UUID
  date: date
  value: decimal
  ingested_at: timestamp
}

OutboundWebhook {
  id: UUID
  org_id: UUID
  url: string
  signing_secret: encrypted_string       // for HMAC-SHA256 signature
  description: string
  events: string[]                       // e.g. ["alert.fired", "recommendation.implemented"]
  is_active: boolean
  last_triggered_at: timestamp | null
  last_status_code: int | null
  created_at: timestamp
}

NotificationSettings {
  id: UUID
  org_id: UUID
  alert_emails: string[]
  teams_webhook_url: string | null       // null = Teams disabled
  slack_webhook_url: string | null       // null = Slack disabled
  updated_at: timestamp
}

Resource {
  id: UUID
  org_id: UUID
  account_id: UUID
  provider: string
  resource_id: string                    // AWS resource ARN or ID
  resource_name: string | null
  service: string
  region: string
  instance_type: string | null
  tags: jsonb                            // provider tags
  virtual_tags: jsonb                    // tags applied by VirtualTagRule (computed, refreshed on rule change)
  created_at_cloud: timestamp | null     // from CloudTrail/Activity Log/GCP Audit Log
  last_activity_at: timestamp | null     // last usage signal from CloudWatch/Azure Monitor/GCP Monitoring
  created_by_user: string | null         // from CloudTrail / Activity Log
  last_cost_usd: decimal | null          // most recent daily cost
  is_idle: boolean                       // computed: no usage for 7+ days
  idle_since: timestamp | null           // when is_idle became true
  first_seen: timestamp                  // when Prism first discovered it
  last_seen: timestamp
  // UNIQUE CONSTRAINT: (account_id, resource_id) — one row per physical resource
  // Upserted on every sync: INSERT ... ON CONFLICT DO UPDATE SET last_seen = NOW()
}

TeamMember {
  id: UUID
  org_id: UUID
  user_id: UUID | null        // null until invite is accepted
  email: string               // invite target email (set at invite time)
  role: 'owner' | 'admin' | 'editor' | 'viewer'
  invited_by: UUID | null
  invite_token: string | null // bcrypt-hashed token stored; raw token emailed once
  invite_expires_at: timestamp | null  // 48h after invite sent; expired invites rejected
  invite_accepted: boolean
  invited_at: timestamp
  joined_at: timestamp | null
}

User {
  id: UUID
  email: string
  name: string
  password_hash: string | null   // null if Google OAuth only
  google_id: string | null
  avatar_url: string | null
  mfa_enabled: boolean
  last_login: timestamp | null
  created_at: timestamp
}
```

---

### **Database Indexes**

Critical indexes for query performance. Missing any of these causes full table scans at scale.

```sql
-- TimescaleDB: CostRecord (hypertable partitioned by time)
CREATE UNIQUE INDEX idx_cost_record_idempotency
  ON cost_records (account_id, time::date, service, region);
  -- Enables INSERT ... ON CONFLICT DO UPDATE for idempotent syncs

CREATE INDEX idx_cost_record_org_time
  ON cost_records (org_id, time DESC);        -- dashboard time-range queries

CREATE INDEX idx_cost_record_org_provider
  ON cost_records (org_id, provider, time DESC); -- per-platform queries

CREATE INDEX idx_cost_record_tags_team
  ON cost_records USING GIN (tags);           -- tag-based allocation queries

-- PostgreSQL: Alert
CREATE UNIQUE INDEX idx_alert_cap_threshold_dedup
  ON alerts (org_id, cap_id, threshold_percent, date_trunc('month', triggered_at))
  WHERE type = 'cap_threshold' AND cap_id IS NOT NULL;
  -- Enforces one alert per threshold per billing period

-- PostgreSQL: Resource
CREATE UNIQUE INDEX idx_resource_account_resource_id
  ON resources (account_id, resource_id);     -- upsert idempotency

CREATE INDEX idx_resource_is_idle
  ON resources (org_id, is_idle, idle_since)
  WHERE is_idle = true;                       -- fast idle resource queries

-- PostgreSQL: CommitmentRecord
CREATE INDEX idx_commitment_org_status
  ON commitment_records (org_id, status, end_date); -- expiry calendar queries

-- PostgreSQL: SpendForecast
CREATE INDEX idx_forecast_org_month
  ON spend_forecasts (org_id, forecast_month DESC); -- current forecast lookup

-- PostgreSQL: VirtualTagRule
CREATE INDEX idx_vtag_rule_org_priority
  ON virtual_tag_rules (org_id, priority)
  WHERE is_active = true;                     -- rule evaluation order
```

---

### **Dashboard Query Caching Strategy**

Raw DB queries on every dashboard load would be unacceptably slow at scale. Cache at two levels:

| Cache Key | What | TTL | Invalidated by |
|-----------|------|-----|---------------|
| `dash:${orgId}:overall:${month}` | Overall dashboard aggregates | 5 min | New sync completion |
| `dash:${orgId}:${provider}:${month}` | Per-platform aggregates | 5 min | New sync for that provider |
| `dash:${orgId}:forecast:${month}` | EOMonth forecast | 1 hour | New sync or manual recalculate |
| `dash:${orgId}:commitments` | Commitment dashboard data | 6 hours | Commitment sync job |
| `dash:${orgId}:scorecard` | FinOps health score | 1 hour | Any metric update |
| `llm:${hash(prompt)}` | LLM response | 24 hours | Never (immutable for same input) |

**Implementation:** All cache keys prefixed by `org_id` — no cross-org leakage possible. Cache layer is Redis. On sync completion, the job publishes `sync.complete:{orgId}:{provider}` event; a subscriber deletes the relevant cache keys and pushes a WebSocket `dashboard.refresh` event to all connected clients for that org.

---

### **WebSocket Event Schema**

All real-time events pushed to connected dashboard clients:

```typescript
// All events share this envelope
interface WSEvent {
  event: string;
  org_id: string;
  timestamp: string; // ISO 8601
  data: object;
}

// Pushed after sync completes — triggers dashboard refresh
{ event: "sync.complete",   data: { provider: "aws", account_id: "...", records: 1243 } }

// Pushed when a cap alert fires — shows alert banner immediately
{ event: "alert.fired",     data: { alert_id: "...", type: "cap_threshold", scope: "AWS EC2", severity: "warning" } }

// Pushed when forecast updates — refreshes forecast widget
{ event: "forecast.updated", data: { provider: "aws", projected_total: 8750, will_breach: true } }

// Pushed when recommendation created — badge counter updates
{ event: "recommendation.new", data: { count: 9, top_savings: 1855 } }

// Auth: WebSocket connection requires a valid JWT in the initial handshake
// ws://api.prism.io/ws?token={jwt}
// Server validates JWT before accepting; closes connection on expiry
// Client: reconnect with new JWT from /auth/refresh on 4001 close code
```

---

### **Background Job Architecture**

```
Job Types (SQS queues or BullMQ):
  prism-sync          → daily cost sync per account (triggered 06:00 UTC by cron)
  prism-alerts        → cap + forecast checks (triggered after every sync)
  prism-commitments   → commitment record refresh (daily, 07:00 UTC)
  prism-forecast      → forecast recalculation (daily, 07:30 UTC)
  prism-virtual-tags  → virtual tag re-application (triggered on rule save)
  prism-reports       → monthly report generation (triggered on org report day)
  prism-recommendations → recommendation engine (daily, 08:00 UTC)

Dead Letter Queue (DLQ):
  prism-dlq           → receives messages that failed 3 retry attempts
  DLQ processor: logs structured error, creates internal alert, does NOT retry
  Operations team reviews DLQ daily; max retention 14 days

Idempotency:
  Every job has a unique job_id (org_id + date + job_type)
  Jobs check: "Did I already complete successfully today?" before running
  CostRecord upsert (ON CONFLICT DO UPDATE) ensures duplicate syncs are safe
```

---

## **Configuration & Setup Guide**

This is the core onboarding experience for every new user. After creating an account and org, the user lands on the **Configuration** page to connect their cloud accounts.

### **Configuration Page Layout**

```
┌─────────────────────────────────────────────────────┐
│ Cloud Connections                    [+ Add Account] │
├─────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────┐ │
│ │ 🟢 AWS — Production Account                    │ │
│ │    Last sync: 2h ago · 1,243 records            │ │
│ │    Data as of: Oct 23, 2026 11:00 PM UTC        │ │
│ │    [Sync Now] [Edit] [Remove]                   │ │
│ └─────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 🔴 Azure — Subscription: Dev                   │ │
│ │    Last sync: Failed · 6h ago                   │ │
│ │    Error: Client secret expired                  │ │
│ │    [Reconnect] [Edit] [Remove]                  │ │
│ └─────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────┐ │
│ │ [+] Connect GCP                                 │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

Status indicators:
- 🟢 Green — connected, sync healthy
- 🟡 Yellow — connected, data >24h stale
- 🔴 Red — sync failed, error shown inline
- ⚪ Grey — configured but never synced

---

### **AWS Setup Wizard**

**Step 1 — Choose Account Scope**
```
○ Single Account    — Connect one AWS account
○ Multi-Account     — Connect several accounts individually
○ AWS Organization  — Connect all accounts under your AWS Org (via management account)
```

**Step 2 — Create IAM Role in AWS**

Display the following block with a **[Copy]** button:

```json
// Paste this as a new IAM Policy in your AWS Console
// IAM → Policies → Create Policy → JSON tab
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PrismCostExplorer",
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetCostAndUsageWithResources",
        "ce:GetDimensionValues",
        "ce:GetReservationPurchaseRecommendation",
        "ce:GetRightsizingRecommendation",
        "ce:GetSavingsPlansUtilization"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PrismCloudTrail",
      "Effect": "Allow",
      "Action": [
        "cloudtrail:DescribeTrails",
        "cloudtrail:LookupEvents",
        "cloudtrail:GetTrailStatus"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PrismResourceDiscovery",
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "s3:ListAllMyBuckets",
        "s3:GetBucketLocation",
        "rds:DescribeDBInstances",
        "lambda:ListFunctions",
        "dynamodb:ListTables",
        "eks:ListClusters"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PrismTagging",
      "Effect": "Allow",
      "Action": [
        "tag:GetResources",
        "tag:GetTagKeys",
        "tag:GetTagValues"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PrismOrganizations",
      "Effect": "Allow",
      "Action": [
        "organizations:DescribeOrganization",
        "organizations:ListAccounts",
        "sts:AssumeRole"
      ],
      "Resource": "*"
    }
  ]
}
```

Display the following Trust Policy block with a **[Copy]** button:

```json
// Paste this as the Trust Policy when creating the IAM Role
// IAM → Roles → Create Role → Custom trust policy
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::PRISM_ACCOUNT_ID:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "PRISM_GENERATED_EXTERNAL_ID"
        }
      }
    }
  ]
}
```

> ℹ️ `PRISM_ACCOUNT_ID` and `PRISM_GENERATED_EXTERNAL_ID` are pre-filled dynamically in the UI for the user's org.

**Step 3 — Enter Role ARN**
```
Role ARN: [ arn:aws:iam::123456789012:role/PrismCostVisibilityRole ]
          [Test Connection]
```

On success: "✅ Connected — 3 services found, billing access confirmed."  
On failure: show the exact AWS error message.

**For AWS Organizations:** Additionally ask for the Management Account ID. Prism will enumerate member accounts and assume the same-named role in each (customer must deploy role to all member accounts using AWS CloudFormation StackSets).

---

### **Azure Setup Wizard**

**Step 1 — Choose Scope**
```
○ Single Subscription
○ Multiple Subscriptions  — add individually
○ Management Group        — covers all subscriptions beneath it
```

**Step 2 — Create Service Principal**

Display with **[Copy]** button:

```bash
# Run in Azure Cloud Shell or local Azure CLI
# Replace {subscriptionId} with your subscription ID

az ad sp create-for-rbac \
  --name "prism-cost-reader" \
  --role "Cost Management Reader" \
  --scopes "/subscriptions/{subscriptionId}"

# For Management Group scope:
# --scopes "/providers/Microsoft.Management/managementGroups/{groupId}"

# Output will contain: appId, password, tenant
# Copy those values into Prism below
```

**Step 3 — Enter Credentials**
```
Tenant ID:       [ xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx ]
Client ID:       [ xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx ]
Client Secret:   [ ••••••••••••••••••••••••• ]
Subscription ID: [ xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx ]
               [Test Connection]
```

> ⚠️ Client secrets expire. Set a 90-day reminder to rotate. Prism will warn you 14 days before expiry.

---

### **GCP Setup Wizard**

**Step 1 — Choose Scope**
```
○ Single Project
○ Multiple Projects  — add individually
○ Billing Account    — covers all projects under the billing account
```

**Step 2 — Create Service Account**

Display with **[Copy]** button:

```bash
# Run in Google Cloud Shell or local gcloud CLI
# Replace variables with your values

PROJECT_ID="your-project-id"
BILLING_ACCOUNT_ID="0X0X0X-0X0X0X-0X0X0X"

# Create service account
gcloud iam service-accounts create prism-cost-reader \
  --display-name="Prism Cost Reader" \
  --project=$PROJECT_ID

SA_EMAIL="prism-cost-reader@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant billing viewer role
gcloud billing accounts add-iam-policy-binding $BILLING_ACCOUNT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/billing.viewer"

# Grant BigQuery access for billing export (if BigQuery export is configured)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/bigquery.dataViewer"

# Create and download key
gcloud iam service-accounts keys create prism-key.json \
  --iam-account=$SA_EMAIL

# Upload prism-key.json in the Prism UI below
```

**Step 3 — Upload Key**
```
Service Account Key (JSON):  [Upload File] or [Paste JSON content]
BigQuery Dataset (optional): [ project.dataset.gcp_billing_export ]
                             [Test Connection]
```

---

### **General Configuration Settings**

Beyond cloud connections, the Configuration page also covers:

**Organization Settings:**
```
Organization Name:     [ Acme Corp                    ]
Currency:              [ USD ▼ ] (USD, EUR, GBP, INR, AUD, CAD)
Sync Schedule:         [ Daily at 06:00 UTC ▼ ]
```

**Notification Settings:**
```
Alert Email Recipients:   [ engineering@acme.com ] [+ Add]
                          [ finance@acme.com      ] [×]

Microsoft Teams Webhook:  [ https://outlook.webhook.office.com/... ]
                          (Leave blank to disable Teams notifications)

Slack Webhook:            [ https://hooks.slack.com/services/...   ]
                          (Leave blank to disable Slack notifications)
                          [Test Slack]

Outbound Webhook (Jira / custom):
  URL:     [ https://your-system.com/prism-webhook ]
  Events:  [✓] Alert fired  [✓] Sync failed  [ ] Recommendation implemented
  Secret:  [ auto-generated — copy to your system for signature validation ]
  [Test Webhook]
```

**Report Settings (see Monthly Report System):**
```
Monthly Report Day:       [ 4 ▼ ] (day of month, 1–28)
Report Recipients:        [ neeraj@acme.com ] [+ Add]
                          [ team@acme.com   ] [×]
Include FinOps Scorecard: [✓]
Include Commitments:      [✓]
Include Unit Economics:   [ ] (only if business metrics are configured)
```

**Unit Economics Settings (optional):**
```
Business Metrics
────────────────────────────────────────────────────
Metric Name:   [ Active Customers ▼ ]  Unit: customers
Source:        [ Stripe ▼ ]  (Stripe, Datadog, CSV upload, Manual entry, Webhook)
Status:        ✅ Connected · Last value: 2,964 customers (Oct 31)

[ + Add Business Metric ]
```

---

## **IAM Roles & Permissions**

Full IAM policy JSON blocks are embedded in the [Configuration & Setup Guide](#configuration--setup-guide) above for user-facing copy-paste. This section documents the permissions and their rationale.

### **AWS Permissions Summary**

| Permission Group | Actions | Purpose |
|-----------------|---------|---------|
| Cost Explorer | `ce:GetCostAndUsage`, `ce:GetDimensionValues`, `ce:GetRightsizingRecommendation`, `ce:GetSavingsPlansUtilization` | Pull cost data, get rightsizing suggestions |
| CloudTrail | `cloudtrail:DescribeTrails`, `cloudtrail:LookupEvents` | Attribute resource creation to users |
| Resource Discovery | `ec2:Describe*`, `s3:ListAllMyBuckets`, `rds:DescribeDBInstances`, `lambda:ListFunctions`, `eks:ListClusters` | Discover idle/untagged resources |
| Tagging | `tag:GetResources`, `tag:GetTagKeys` | Read resource tags for cost allocation |
| Organizations | `organizations:ListAccounts`, `sts:AssumeRole` | Multi-account enumeration and role assumption |

**Note:** All AWS permissions are **read-only**. Prism never modifies, creates, or deletes AWS resources.  
**Activation required:** Enable IAM access in AWS Console → Billing → Cost Management preferences (must be done by account owner).

### **Azure Permissions Summary**

Built-in role assigned to the service principal:
- `Cost Management Reader` — grants `Microsoft.CostManagement/*/read` and `Microsoft.CostManagement/query/action`
- `Reader` (optional) — for resource discovery and tag reading

### **GCP Permissions Summary**

Roles assigned to the service account:
- `roles/billing.viewer` — view billing and cost data at billing account level
- `roles/bigquery.dataViewer` — query exported billing data from BigQuery (if BigQuery export is configured)

### **Credential Storage & Rotation**

| Platform | Stored | Rotation |
|----------|--------|---------|
| AWS | Role ARN + ExternalId (no secret) | N/A — role trust managed in AWS |
| Azure | `AZURE_CLIENT_SECRET` (AES-256 encrypted) | 90 days — Prism warns 14 days before expiry |
| GCP | Service account JSON key (AES-256 encrypted) | 90 days — Prism warns 14 days before expiry |

Credentials are stored in **HashiCorp Vault or AWS Secrets Manager** — never in the application database in plaintext.

---

## **API Implementation Guide**

### **Connector Architecture**

Each cloud provider has a dedicated connector class handling authentication, data fetching, normalization, error handling, and health checks.

#### **AWS Connector**

```typescript
import { CostExplorerClient, GetCostAndUsageCommand } from "@aws-sdk/client-ce";
import { STSClient, AssumeRoleCommand } from "@aws-sdk/client-sts";

export class AWSConnector {
  private ceClient: CostExplorerClient | null = null;

  async assumeRole(): Promise<void> {
    const stsClient = new STSClient({ region: "us-east-1" });
    const result = await stsClient.send(
      new AssumeRoleCommand({
        RoleArn: this.config.roleArn,
        RoleSessionName: `prism-${Date.now()}`,
        ExternalId: this.config.externalId,
        DurationSeconds: 3600,
      })
    );
    const creds = result.Credentials!;
    this.ceClient = new CostExplorerClient({
      region: "us-east-1",
      credentials: {
        accessKeyId: creds.AccessKeyId!,
        secretAccessKey: creds.SecretAccessKey!,
        sessionToken: creds.SessionToken!,
      },
    });
  }

  async getCostAndUsage(startDate: string, endDate: string): Promise<CostRecord[]> {
    const response = await this.ceClient!.send(
      new GetCostAndUsageCommand({
        TimePeriod: { Start: startDate, End: endDate },
        Granularity: "DAILY",
        Metrics: ["UnblendedCost", "UsageQuantity"],
        GroupBy: [
          { Type: "DIMENSION", Key: "SERVICE" },
          { Type: "DIMENSION", Key: "REGION" },
          { Type: "TAG", Key: "team" },
          { Type: "TAG", Key: "owner" },
          { Type: "TAG", Key: "environment" },
        ],
      })
    );
    return this.normalize(response.ResultsByTime ?? []);
  }

  async healthCheck(): Promise<{ ok: boolean; error?: string }> {
    try {
      await this.getCostAndUsage(
        new Date(Date.now() - 86400000).toISOString().split("T")[0],
        new Date().toISOString().split("T")[0]
      );
      return { ok: true };
    } catch (err: any) {
      return { ok: false, error: err.message };
    }
  }

  private normalize(results: any[]): CostRecord[] {
    // Map AWS response → unified CostRecord[]
    // Tags: { "Teams$team": "engineering" } → { team: "engineering" }
    return results.flatMap(period =>
      (period.Groups ?? []).map((g: any) => ({
        time: new Date(period.TimePeriod.Start),
        provider: "aws",
        service: g.Keys[0],
        region: g.Keys[1],
        cost_usd: parseFloat(g.Metrics.UnblendedCost.Amount),
        cost_original: parseFloat(g.Metrics.UnblendedCost.Amount),
        original_currency: "USD",
        fx_rate: 1,
        tags: this.extractTags(g.Keys),
        is_estimate: period.Estimated ?? false,
      }))
    );
  }
}
```

#### **Azure Connector**

```typescript
import { ClientSecretCredential } from "@azure/identity";
import axios, { AxiosInstance } from "axios";

export class AzureConnector {
  private axiosClient: AxiosInstance;
  private fxRate: number;   // USD/original-currency rate; loaded from FX table at init

  constructor(private config: AzureConfig, fxRate: number = 1) {
    this.fxRate = fxRate;   // caller passes today's FX rate from Redis/DB cache
    const credential = new ClientSecretCredential(
      config.tenantId,
      config.clientId,
      config.clientSecret
    );
    this.axiosClient = axios.create({
      baseURL: "https://management.azure.com",
    });
    // Attach bearer token on each request
    this.axiosClient.interceptors.request.use(async (req) => {
      const token = await credential.getToken("https://management.azure.com/.default");
      req.headers.Authorization = `Bearer ${token.token}`;
      return req;
    });
  }

  async getCostAndUsage(startDate: string, endDate: string): Promise<CostRecord[]> {
    const scope = `/subscriptions/${this.config.subscriptionId}`;
    const query = {
      type: "Usage",
      timeframe: "Custom",
      timePeriod: {
        from: `${startDate}T00:00:00Z`,
        to: `${endDate}T23:59:59Z`,
      },
      dataset: {
        granularity: "Daily",
        aggregation: {
          totalCost: { name: "PreTaxCost", function: "Sum" },
        },
        grouping: [
          { type: "Dimension", name: "ServiceName" },
          { type: "Dimension", name: "ResourceGroup" },
          { type: "TagKey", name: "team" },
          { type: "TagKey", name: "owner" },
          { type: "TagKey", name: "environment" },
        ],
      },
    };

    const response = await this.axiosClient.post(
      `${scope}/providers/Microsoft.CostManagement/query?api-version=2021-10-01`,
      query
    );
    return this.normalize(response.data);
  }

  async healthCheck(): Promise<{ ok: boolean; error?: string }> {
    try {
      await this.getCostAndUsage(
        new Date(Date.now() - 86400000).toISOString().split("T")[0],
        new Date().toISOString().split("T")[0]
      );
      return { ok: true };
    } catch (err: any) {
      return { ok: false, error: err.response?.data?.error?.message ?? err.message };
    }
  }

  private normalize(data: any): CostRecord[] {
    // Parse Azure column-based response into CostRecord[]
    const cols: string[] = data.columns.map((c: any) => c.name);
    return (data.rows ?? []).map((row: any[]) => {
      const record: any = {};
      cols.forEach((col, i) => { record[col] = row[i]; });
      return {
        time: new Date(record.UsageDate),
        provider: "azure",
        service: record.ServiceName,
        region: record.ResourceGroup,
        cost_usd: parseFloat(record.PreTaxCost) * this.fxRate, // convert to USD
        cost_original: parseFloat(record.PreTaxCost),
        original_currency: this.config.currency ?? "USD",
        fx_rate: this.fxRate,
        tags: {
          team: record.team ?? null,
          owner: record.owner ?? null,
          environment: record.environment ?? null,
        },
        is_estimate: false,
      };
    });
  }
}
```

#### **GCP Connector**

```typescript
import { BigQuery } from "@google-cloud/bigquery";

export class GCPConnector {
  private bq: BigQuery;

  constructor(private config: GCPConfig) {
    this.bq = new BigQuery({
      projectId: config.projectId,
      credentials: config.serviceAccountKey, // parsed JSON key object
    });
  }

  async getCostFromBigQuery(startDate: string, endDate: string): Promise<CostRecord[]> {
    const { projectId, dataset } = this.config;
    // Use parameterized query — no string interpolation of user values
    const query = `
      SELECT
        DATE(usage_start_time) as date,
        service.description as service,
        location.region as region,
        SUM(CAST(cost AS FLOAT64)) as cost,
        currency,
        labels
      FROM \`${projectId}.${dataset}.gcp_billing_export_v1_*\`
      WHERE DATE(usage_start_time) BETWEEN @startDate AND @endDate
      GROUP BY date, service, region, currency, labels
      ORDER BY date DESC
    `;

    const [rows] = await this.bq.query({
      query,
      params: { startDate, endDate },
    });

    return rows.map((row: any) => ({
      time: new Date(row.date.value),
      provider: "gcp",
      service: row.service,
      region: row.region,
      cost_usd: parseFloat(row.cost) * this.fxRate,
      cost_original: parseFloat(row.cost),
      original_currency: row.currency,
      fx_rate: this.fxRate,
      tags: this.extractLabels(row.labels ?? []),
      is_estimate: false,
    }));
  }

  private extractLabels(labels: Array<{ key: string; value: string }>): Record<string, string> {
    const normalized: Record<string, string> = {};
    for (const label of labels) {
      // Normalize: "team", "owner", "environment", "project"
      if (["team", "owner", "environment", "project"].includes(label.key)) {
        normalized[label.key] = label.value;
      }
    }
    return normalized;
  }

  async healthCheck(): Promise<{ ok: boolean; error?: string }> {
    try {
      await this.getCostFromBigQuery(
        new Date(Date.now() - 86400000).toISOString().split("T")[0],
        new Date().toISOString().split("T")[0]
      );
      return { ok: true };
    } catch (err: any) {
      return { ok: false, error: err.message };
    }
  }
}
```

### **Cost Service (Orchestrator)**

```typescript
export class CostService {
  private connectors: Map<string, AWSConnector | AzureConnector | GCPConnector> = new Map();

  async initialize(accounts: CloudAccount[]): Promise<void> {
    for (const account of accounts) {
      const creds = await vault.getCredentials(account.id);
      if (account.provider === "aws") {
        const conn = new AWSConnector(creds);
        await conn.assumeRole();
        this.connectors.set(account.id, conn);
      } else if (account.provider === "azure") {
        this.connectors.set(account.id, new AzureConnector(creds));
      } else if (account.provider === "gcp") {
        this.connectors.set(account.id, new GCPConnector(creds));
      }
    }
  }

  async syncAccount(account: CloudAccount): Promise<SyncResult> {
    const connector = this.connectors.get(account.id);
    if (!connector) throw new Error(`No connector for account ${account.id}`);

    const yesterday = new Date(Date.now() - 86400000).toISOString().split("T")[0];
    const today = new Date().toISOString().split("T")[0];

    const startTime = Date.now();
    let records: CostRecord[] = [];
    let error: string | null = null;

    try {
      records = await withRetry(() => connector.getCostAndUsage(yesterday, today));
    await db.cost_records.insertMany(
        records.map(r => ({ ...r, org_id: account.org_id, account_id: account.id, ingested_at: new Date() }))
      );
      await db.cloud_accounts.update(account.id, {
        last_sync: new Date(),
        last_sync_status: "success",
        last_sync_error: null,
        last_sync_records: records.length,
        data_as_of: records.length > 0 ? records[0].time : null,
      });
    } catch (err: any) {
      error = err.message;
      await db.cloud_accounts.update(account.id, {
        last_sync: new Date(),
        last_sync_status: "failed",
        last_sync_error: error,
        last_sync_records: 0,
      });
      logger.error({ account_id: account.id, error }, "Sync failed");
    }

    return {
      account_id: account.id,
      records_synced: records.length,
      duration_ms: Date.now() - startTime,
      error,
    };
  }

  async dailySyncAll(orgId: string): Promise<void> {
    const accounts = await db.cloud_accounts.findAll({ org_id: orgId, is_active: true });
    const results = await Promise.allSettled(accounts.map(a => this.syncAccount(a)));
    logger.info({ org_id: orgId, results }, "Daily sync complete");

    // After sync, run cap threshold checks
    await capAlertService.checkAllCaps(orgId);
  }
}
```

### **Error Handling & Retries**

```typescript
async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries = 3
): Promise<T> {
  let lastError: Error = new Error("Unknown error");

  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error: any) {
      lastError = error;

      // Do not retry on auth errors — fail fast so the user sees the credential error
      if (
        error.message?.includes("Unauthorized") ||
        error.message?.includes("Invalid credentials") ||
        error.message?.includes("AccessDenied") ||
        error.$metadata?.httpStatusCode === 401 ||
        error.$metadata?.httpStatusCode === 403 ||
        error.status === 401 ||
        error.status === 403
      ) {
        throw error;
      }

      // Respect Retry-After header for rate limit (429) responses
      if (error.status === 429 || error.$metadata?.httpStatusCode === 429) {
        const retryAfterSec = parseInt(error.response?.headers?.["retry-after"] ?? "30", 10);
        const delay = Math.min(retryAfterSec * 1000, 120_000); // cap at 2 min
        logger.warn({ attempt: i + 1, delay_ms: delay, reason: "rate_limited" }, "Rate limited — waiting...");
        await new Promise(r => setTimeout(r, delay));
        continue;
      }

      // Exponential backoff for all other errors: 1s → 2s → 4s (max 30s)
      const delay = Math.min(1000 * Math.pow(2, i), 30000);
      logger.warn({ attempt: i + 1, delay_ms: delay, error: error.message }, "Retrying...");
      await new Promise(r => setTimeout(r, delay));
    }
  }

  throw lastError;
}
```

### **API Endpoints Summary**

| Platform | Endpoint | Auth | Rate Limit | Notes |
|----------|----------|------|-----------|-------|
| AWS | `ce:GetCostAndUsage` (SDK) | IAM role (STS) | 5 TPS | Current month = estimates |
| Azure | `POST .../query?api-version=2021-10-01` | OAuth2 bearer | 30 req/min | Daily granularity only |
| GCP | BigQuery SQL on billing export table | Service account JWT | Warehouse cost ~$0 | BigQuery export must be enabled in GCP |

---

## **Budget Cap System**

### **Overview**

Budget caps let users define spending limits at any scope — platform, service, or individual account. When spend crosses a defined threshold, Prism sends an email alert (and optionally a Teams message). Caps reset at the start of each calendar month.

### **Cap Scopes**

| Scope | Example | Description |
|-------|---------|-------------|
| **Platform-level** | AWS total: $5,000/mo | Alert when all AWS accounts combined cross threshold |
| **Service-level** | AWS EC2: $2,000/mo | Alert when a specific service crosses threshold |
| **Account-level** | AWS Dev Account: $500/mo | Alert when a specific account crosses threshold |

Caps can coexist — you can have a platform-level cap AND service-level caps simultaneously.

### **Alert Thresholds**

Each cap triggers alerts at these crossing points:

| Threshold | Email Subject | Severity |
|-----------|--------------|---------|
| **75%** | "⚠️ [AWS EC2] at 75% of $2,000 cap ($1,500 spent)" | Warning |
| **90%** | "⚠️ [AWS EC2] at 90% of $2,000 cap — approaching limit" | Warning |
| **100%** | "🚨 [AWS EC2] cap reached — $2,000 of $2,000 used" | Critical |
| **125%** | "🚨 [AWS EC2] exceeded cap by 25% — $2,500 spent ($500 over)" | Critical |
| **150%** | "🚨 [AWS EC2] exceeded cap by 50% — $3,000 spent ($1,000 over)" | Critical |

**Rules:**
- Each threshold fires **once per billing period** — no repeated emails for the same threshold
- If a service drops below a threshold then rises again: re-alert at next crossing
- Alerts go to all emails in "Alert Email Recipients" (configured in settings)
- Teams message sent at same thresholds **only if** Teams webhook is configured

### **Cap Alert Email Format**

```
Subject: ⚠️ AWS EC2 at 90% of $2,000 cap — Prism Alert

AWS EC2 Spend Alert
───────────────────
Cap:          $2,000 / month
Spent so far: $1,800 (90%)
Remaining:    $200
Days left in month: 8

At current burn rate, you will exceed the cap in ~2 days.

Top services contributing:
  • EC2 On-Demand Instances (us-east-1): $1,200
  • EC2 On-Demand Instances (eu-west-1): $400
  • Data Transfer: $200

Suggested actions:
  • Review on-demand instances — consider Reserved Instances
  • Check for idle instances (3 flagged in recommendations)
  • Increase the cap in Prism if this spend is expected

View Dashboard: https://app.prism.io/org/acme/dashboard
Manage Caps:    https://app.prism.io/org/acme/settings/caps
```

### **Cap Management Service**

```typescript
export class CapAlertService {
  async checkAllCaps(orgId: string): Promise<void> {
    const caps = await db.budget_caps.findAll({ org_id: orgId, is_active: true });
    const monthStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
    const now = new Date();

    for (const cap of caps) {
      const spent = await this.getSpendForCap(cap, monthStart, now);
      const pct = (spent / cap.cap_amount) * 100;
      await this.evaluateThresholds(cap, spent, pct, orgId);
    }
  }

  private async evaluateThresholds(
    cap: BudgetCap,
    spent: number,
    pct: number,
    orgId: string
  ): Promise<void> {
    const thresholds = [75, 90, 100, 125, 150];

    for (const threshold of thresholds) {
      if (pct >= threshold) {
        // Check if we already sent this alert this billing period
        const alreadySent = await db.alerts.findOne({
          cap_id: cap.id,
          threshold_percent: threshold,
          triggered_at: { gte: new Date(new Date().getFullYear(), new Date().getMonth(), 1) },
        });

        if (!alreadySent) {
          await this.fireAlert(cap, spent, pct, threshold, orgId);
        }
      }
    }
  }

  private async fireAlert(
    cap: BudgetCap,
    spent: number,
    pct: number,
    threshold: number,
    orgId: string
  ): Promise<void> {
    const org = await db.organizations.findById(orgId);
    const settings = await db.notification_settings.findByOrg(orgId);

    // Create alert record first (for audit trail even if notifications fail)
    const alert = await db.alerts.insert({
      org_id: orgId,
      cap_id: cap.id,
      type: "cap_threshold",
      scope_label: this.capScopeLabel(cap),
      threshold_percent: threshold,
      spend_at_trigger: spent,
      cap_amount: cap.cap_amount,
      severity: threshold >= 100 ? "critical" : "warning",
      triggered_at: new Date(),
      email_sent: false,
      teams_sent: false,
      slack_sent: false,
      webhook_sent: false,
    });

    // Fire all channels concurrently; failures in one don't block others
    const updates: Partial<Alert> = {};

    await Promise.allSettled([
      // Email (always, if recipients configured)
      settings.alert_emails.length > 0
        ? emailService.sendCapAlert({ to: settings.alert_emails, cap, spent, pct, threshold, org })
            .then(() => { updates.email_sent = true; })
            .catch(err => logger.error({ alert_id: alert.id, err }, "Email send failed"))
        : Promise.resolve(),

      // Teams (only if webhook configured)
      settings.teams_webhook_url
        ? teamsService.sendCapAlert({ webhookUrl: settings.teams_webhook_url, cap, spent, pct, threshold })
            .then(() => { updates.teams_sent = true; })
            .catch(err => logger.error({ alert_id: alert.id, err }, "Teams send failed"))
        : Promise.resolve(),

      // Slack (only if webhook configured)
      settings.slack_webhook_url
        ? slackService.sendCapAlert({ webhookUrl: settings.slack_webhook_url, cap, spent, pct, threshold })
            .then(() => { updates.slack_sent = true; })
            .catch(err => logger.error({ alert_id: alert.id, err }, "Slack send failed"))
        : Promise.resolve(),

      // Outbound webhooks (for Jira/custom)
      webhookService.dispatchEvent(orgId, "alert.fired", { alert_id: alert.id, type: "cap_threshold", scope: this.capScopeLabel(cap), threshold_percent: threshold, spend: spent, cap: cap.cap_amount })
        .then(() => { updates.webhook_sent = true; })
        .catch(err => logger.warn({ alert_id: alert.id, err }, "Outbound webhook dispatch failed")),
    ]);

    await db.alerts.update(alert.id, updates);
  }
}
```

### **Microsoft Teams Notification (Optional)**

Teams is an **optional** notification channel. If no webhook URL is configured, Teams notifications are skipped entirely. To enable:

1. In the connected Teams channel: **Manage Channel → Connectors → Incoming Webhook → Create**
2. Copy the webhook URL
3. Paste into Prism: Settings → Notifications → Teams Webhook URL

**Teams Adaptive Card for Cap Alert:**

```json
{
  "type": "message",
  "attachments": [{
      "contentType": "application/vnd.microsoft.card.adaptive",
      "content": {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
                      {
                        "type": "TextBlock",
          "text": "⚠️ AWS EC2 at 90% of $2,000 cap",
                        "weight": "bolder",
                        "size": "large",
                        "color": "warning"
                      },
              {
                "type": "FactSet",
                "facts": [
            { "title": "Spent:", "value": "$1,800" },
            { "title": "Cap:", "value": "$2,000" },
            { "title": "Remaining:", "value": "$200" },
            { "title": "Days left:", "value": "8" }
            ]
          }
        ],
        "actions": [
          {
            "type": "Action.OpenUrl",
          "title": "View Dashboard",
          "url": "https://app.prism.io/org/acme/dashboard"
        },
        {
          "type": "Action.OpenUrl",
          "title": "Manage Caps",
          "url": "https://app.prism.io/org/acme/settings/caps"
        }
      ]
    }
  }]
}
```

---

## **Alerts & Notifications**

### **Alert Types**

| Type | Trigger | Severity | Delivery |
|------|---------|---------|---------|
| Cap threshold | 75/90/100/125/150% of any budget cap | Warning/Critical | Email + Teams/Slack (if configured) |
| **Forecast breach** | Projected EOMonth spend will exceed cap | Warning | Email + Teams/Slack |
| **Spend acceleration** | Daily avg increased >30% week-over-week | Warning | Email |
| Sync failure | Cloud account sync fails 2+ times consecutively | Warning | Email |
| Credential expiry | Azure/GCP credential expires in <14 days | Warning | Email |
| **Commitment expiry** | RI/SP/CUD expires in 60/30/14 days | Warning | Email |
| **Unused commitment** | Purchased commitment running <80% utilization | Warning | Email (weekly digest) |
| Untagged resources | New resources detected with no owner/team tag | Info | Email (daily digest) |
| Idle resource | Resource with zero usage for 7+ days | Info | Email (daily digest) |

### **Notification Channels**

| Channel | Setup | When it fires |
|---------|-------|--------------|
| **Email** | Always active — recipients configured in Settings | All alert types |
| **Teams webhook** | Optional — paste webhook URL in Settings | All alert types |
| **Slack webhook** | Optional — paste webhook URL in Settings | All alert types |
| **Outbound webhook** | Optional — custom URL in Settings | All alert types (for Jira, ServiceNow, custom systems) |

Only one of Teams or Slack (or both) fires per alert — whichever is configured. If neither is configured, only email fires.

### **Slack Integration**

Setup (same pattern as Teams):

1. In Slack: Apps → Incoming Webhooks → Add to channel → Copy webhook URL
2. In Prism Settings → Notifications → Slack Webhook: paste URL → [Test]

**Slack message format:**

```
⚠️ AWS EC2 at 90% of $3,500 cap

Spent:     $3,200 / $3,500
Remaining: $300 · 8 days left

Top services:
  EC2 On-Demand (us-east-1): $2,100
  EC2 On-Demand (eu-west-1): $1,100

View dashboard → https://app.prism.io/org/acme/aws
Manage caps   → https://app.prism.io/org/acme/settings/caps
```

### **Outbound Webhook (for Jira / ServiceNow / Custom)**

When configured, Prism POSTs a structured JSON payload to the webhook URL on every alert. Useful for auto-creating Jira tickets, routing to ServiceNow, or feeding internal tools.

**Webhook payload format:**
```json
{
  "event": "alert.fired",
  "alert_type": "cap_threshold",
  "severity": "warning",
  "org_id": "uuid",
  "org_name": "Acme Corp",
  "timestamp": "2026-10-24T09:15:00Z",
  "data": {
    "scope": "AWS EC2",
    "provider": "aws",
    "threshold_pct": 90,
    "spend": 3200,
    "cap": 3500,
    "remaining": 300,
    "forecast_breach_date": "2026-10-28",
    "dashboard_url": "https://app.prism.io/org/acme/aws"
  }
}
```

Payload is signed with HMAC-SHA256 (`X-Prism-Signature` header) — receiver should validate before processing.

**Other event types:** `alert.acknowledged`, `recommendation.implemented`, `sync.failed`, `cap.created`, `member.invited`

### **Alert Delivery Rules**

- **Cap threshold alerts:** Immediate on threshold crossing; once per threshold per billing period
- **Forecast breach:** Once per day while projected to breach — suppressed if cap is raised
- **Spend acceleration:** Once per week — not repeated until rate drops then rises again
- **Sync failure alerts:** After 2 consecutive failures; then once per 24h until resolved
- **Credential expiry:** 14 days before, 7 days before, 1 day before
- **Commitment expiry:** 60 days before, 30 days before, 14 days before
- **Unused commitment:** Once per week, batched with other commitment alerts
- **Untagged/Idle:** Batched into a daily digest email at 9:00 AM org local time — not individual emails per resource

### **Alert Management (In-App)**

Users can:
- **Acknowledge** an alert — marks it as seen, removes from active alert list
- **Snooze** an alert — suppresses re-notification for N hours (4h, 24h, 7 days)
- **Dismiss** an alert — permanently closes it for this billing period
- View full **Alert History** (all time) with filters by type, severity, platform, date

---

## **Monthly Report System**

### **Overview**

One configurable monthly report covers everything a startup needs to know about their cloud costs. It is delivered by email on a user-chosen day each month to a configurable list of recipients. No AI — the report is a deterministic template rendering real data.

### **Report Schedule Configuration**

```
Send on day: [ 4 ▼ ] of each month
Recipients:  [ neeraj@acme.com    ] [×]
             [ finance@acme.com   ] [×]
             [ cto@acme.com       ] [×]
             [+ Add recipient]
Include per-account breakdown:  [✓]
Include recommendations:        [✓]
[Save]  [Send Test Report Now]
```

### **Report Structure**

**Section 1: Executive Summary**
```
PRISM Monthly Cloud Cost Report — October 2026
Acme Corp | Generated: Nov 4, 2026

TOTAL CLOUD SPEND THIS MONTH: $12,450
Previous month: $10,800  |  Change: +$1,650 (+15.3%)
Budget cap status: 83% of $15,000 org cap used
```

**Section 2: Spend by Platform**
```
Platform       This Month   Last Month   Change    Cap         % of Cap
─────────────────────────────────────────────────────────────────────
AWS            $7,200       $6,100       +$1,100   $8,000      90% ⚠️
Azure          $3,800       $3,500       +$300     $5,000      76%
GCP            $1,450       $1,200       +$250     $2,000      73%
─────────────────────────────────────────────────────────────────────
Total          $12,450      $10,800      +$1,650   $15,000     83%
```

**Section 3: Top Services by Spend**
```
#  Service               Platform   This Month   Change
1  EC2 Compute           AWS        $3,200       +$800
2  Azure Virtual Machines Azure      $2,100       +$200
3  RDS (PostgreSQL)      AWS        $1,800       –$100
4  S3 Storage            AWS        $900         +$50
5  Cloud Run             GCP        $750         +$300
```

**Section 4: Spend by Team (Tag-Based)**
```
Team           This Month   % of Total   Cap       Status
engineering    $6,800       55%          $8,000    85% ⚠️
data           $3,100       25%          $4,000    78%
infrastructure $1,900       15%          $2,500    76%
untagged       $650         5%           —         —
```

**Section 5: Budget Cap Status**
```
Cap                     Spent      Cap        %        Status
AWS Total               $7,200     $8,000     90%      ⚠️ Near limit
AWS EC2                 $3,200     $3,500     91%      ⚠️ Near limit
Azure Total             $3,800     $5,000     76%      ✅ On track
GCP Total               $1,450     $2,000     73%      ✅ On track
Engineering team        $6,800     $8,000     85%      ⚠️ Near limit
```

**Section 6: Recommendations (Top 5)**
```
#  Resource              Type               Est. Savings/mo   Confidence
1  prod-api-03 (EC2)     Rightsizing        $340              High
2  staging-db (RDS)      Idle termination   $180              High
3  m5.2xlarge fleet (5)  Reserved Instance  $1,200            High
4  s3-logs-archive       Storage tiering    $90               Medium
5  dev-vm-02 (Azure)     Idle termination   $45               High

Total potential savings: $1,855/month
```

**Section 7: Month-over-Month Trend (last 3 months)**
```
Month       AWS       Azure     GCP       Total     Change
August      $9,200    $3,100    $1,050    $13,350   —
September   $10,800   $3,500    $1,200    $15,500   +$2,150 (+16%)
October     $7,200    $3,800    $1,450    $12,450   -$3,050 (-20%)
```

**Section 8: Commitment Summary (if commitments exist)**
```
Commitment Coverage: 45% of eligible compute  ⚠️  (target: 60–80%)
Commitment Utilization: 91%  ✅
Effective Savings Rate (ESR): 18%  ⚠️  (target: >20%)
Savings from commitments this month: $1,380

Expiring soon:
  EC2 RI (m5.xlarge, us-east-1) — expires Dec 22, 2026 (58 days)
  → Action: Evaluate renewal or Compute Savings Plan replacement
```

**Section 9: FinOps Health Score**
```
FinOps Health Score: 64/100  ⚠️

Metric                  This Month   Last Month   Change
Tag Coverage            78%          71%          +7%  ↑
Allocation Coverage     95%          93%          +2%  ↑
Commitment Coverage     45%          45%          0%   →  ← biggest gap
Commitment Utilization  91%          94%          -3%  ↓
Effective Savings Rate  18%          15%          +3%  ↑
Idle Resource Rate      3%           4%           -1%  ↑
Recs Acted On           52%          44%          +8%  ↑
Forecast Accuracy       91%          88%          +3%  ↑

Action items to improve score:
1. Increase commitment coverage (buy Compute SP → save $1,020/mo)
2. Tag 3 untagged resources in AWS ($800/mo allocation gap)
```

**Section 10: Unit Economics (if business metrics configured)**
```
Cost per Active Customer:   $4.20/month  ↓ from $4.80  ✅  (-12.5%)
Cost per API Request:       $0.0023      ↓ from $0.0027 ✅  (-14.8%)
Cloud as % of Revenue:      12%          ↑ from 10%     ⚠️  (+2%)

Note: Business metrics sourced from Stripe (customers) and Datadog (API requests).
Last updated: Oct 31, 2026.
```

**Footer:**
```
This report was generated automatically by Prism.
View full dashboard:     https://app.prism.io/org/acme
View FinOps scorecard:   https://app.prism.io/org/acme/scorecard
Manage report settings:  https://app.prism.io/org/acme/settings/reports
To unsubscribe, visit your settings page.
```

### **Report Generation Service**

```typescript
export class MonthlyReportService {
  async generateAndSend(orgId: string, reportConfig: MonthlyReport): Promise<void> {
    const now = new Date();
    const monthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const monthEnd = new Date(now.getFullYear(), now.getMonth(), 1);

    // Gather all data deterministically — no AI
    const [
      currentSpend,
      lastMonthSpend,
      byPlatform,
      byService,
      byTeam,
      capStatus,
      recommendations,
      trend,
    ] = await Promise.all([
      this.getTotalSpend(orgId, monthStart, monthEnd),
      this.getTotalSpend(orgId, new Date(monthStart.getFullYear(), monthStart.getMonth() - 1, 1), monthStart),
      this.getSpendByPlatform(orgId, monthStart, monthEnd),
      this.getTopServices(orgId, monthStart, monthEnd, 10),
      this.getSpendByTeam(orgId, monthStart, monthEnd),
      this.getCapStatus(orgId, monthStart, monthEnd),
      this.getTopRecommendations(orgId, 5),
      this.getThreeMonthTrend(orgId),
    ]);

    const html = renderReportTemplate({
      orgName: (await db.organizations.findById(orgId)).name,
      reportMonth: monthStart.toLocaleString("default", { month: "long", year: "numeric" }),
      currentSpend,
      lastMonthSpend,
      byPlatform,
      byService,
      byTeam,
      capStatus,
      recommendations,
      trend,
    });

    await emailService.sendReport({
      to: reportConfig.recipient_emails,
      subject: `Prism Cloud Cost Report — ${monthStart.toLocaleString("default", { month: "long", year: "numeric" })}`,
      html,
      pdfAttachment: await renderPDF(html),
    });

    await db.monthly_reports.update(reportConfig.id, {
      last_sent: now,
      next_send: this.nextSendDate(reportConfig.send_day_of_month),
    });

    logger.info({ org_id: orgId, recipients: reportConfig.recipient_emails.length }, "Monthly report sent");
  }

  private nextSendDate(dayOfMonth: number): Date {
    const now = new Date();
    const next = new Date(now.getFullYear(), now.getMonth() + 1, dayOfMonth);
    return next;
  }
}
```

---

## **User Management & Access Control**

### **Roles**

| Role | Dashboard | Config | Budgets/Caps | Alerts | Reports | Team Members |
|------|-----------|--------|--------------|--------|---------|--------------|
| **Owner** | Full | Manage | Manage | Manage | Manage | Manage + Transfer ownership |
| **Admin** | Full | Manage | Manage | Manage | Manage | Invite/Remove (not Owner) |
| **Editor** | Full | View only | View + Request exception | Acknowledge/Snooze | View | View |
| **Viewer** | Read-only | View only | View only | View only | View only | View |

- **Owner** is assigned to the person who creates the org. Only one Owner at a time.
- Owner can transfer ownership to another Admin.
- Roles are set per-member per-org. A user can be Admin in Org A and Viewer in Org B.

### **Authentication**

**Primary: Email + Password**
- Registration: email + name + password (min 12 chars, 1 uppercase, 1 number)
- Email verification required before dashboard access
- Password reset via email link (expires 1 hour)
- Bcrypt hash (cost factor 12) — never store plaintext

**Alternative: Google OAuth**
- "Sign in with Google" button
- JIT provisioning on first login
- If email matches an existing password account → linked automatically

**Session:**
- Access token: JWT, valid 7 days
- Refresh token: valid 30 days, rotated on use
- On logout: invalidate refresh token server-side (stored in Redis)
- Concurrent sessions: allowed (mobile + desktop)

### **Team Invite Flow**

```
Owner/Admin → [Invite Member] → enter email + select role
→ Prism sends invite email with magic link (expires 48h)
→ New user: clicks link → sets password → lands on dashboard
→ Existing user: clicks link → logged in → added to org
→ If invite expires: [Resend Invite] button in team management
```

### **Authentication Flow**

```
1. User enters email + password (or clicks Google OAuth)
2. Backend validates credentials
3. If Google OAuth: validate id_token signature with Google
4. JIT provisioning: if first login, create User record
5. Check TeamMember record for org membership and role
6. Issue JWT (7-day access) + refresh token (30-day)
7. Store refresh token hash in Redis for invalidation
8. Frontend stores tokens in HttpOnly cookies (not localStorage)
```

### **API Key Authentication (For Integrations)**

```typescript
// User generates API key in settings → Integrations → API Keys
const rawKey = crypto.randomBytes(32).toString("hex");
const hashedKey = await bcrypt.hash(rawKey, 10);

await db.api_keys.insert({
  org_id: orgId,
  user_id: userId,
  key_hash: hashedKey,
  name: "My CI Integration",
  scopes: ["cost.read", "alerts.read", "reports.read"],
  created_at: new Date(),
  expires_at: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000),
  last_used: null,
});

// Show raw key to user ONCE — never again
// User adds to their CI/CD as: Authorization: Bearer {rawKey}
```

---

## **Security & Compliance**

### **Data Protection**
- **In Transit:** TLS 1.3 on all endpoints — no HTTP
- **At Rest:** AES-256 encryption for credentials, secrets, API keys
- **Database:** Row-level security in PostgreSQL (`org_id` scoped on all queries)
- **Cookies:** HttpOnly, Secure, SameSite=Strict for auth tokens

### **Multi-Tenant Isolation**
Every database query is scoped by `org_id`. The API middleware enforces:
```typescript
// Applied to every authenticated route
app.use(async (req, res, next) => {
  const org = await db.organizations.findById(req.user.org_id);
  if (!org) return res.status(403).json({ error: "Org not found" });
  req.org = org; // All downstream queries use req.org.id — never user-supplied org IDs
  next();
});
```

### **Credential Management**
- **Never store:** Permanent AWS access keys, Azure passwords
- **Use instead:** IAM roles (AWS), service principals (Azure), service accounts (GCP)
- **Vault:** HashiCorp Vault or AWS Secrets Manager — credentials fetched at sync time, not cached in app memory
- **Rotation:** 90-day schedule; Prism warns 14 days before expiry

### **API Versioning**
All public API routes are prefixed with `/v1/`. Breaking changes are introduced as `/v2/` with a 6-month deprecation period for `/v1/`. Internal service-to-service calls are exempt.

```
GET  /v1/orgs/{orgId}/costs
GET  /v1/orgs/{orgId}/alerts
POST /v1/orgs/{orgId}/caps
```

### **CSRF Protection**
All state-changing endpoints (POST/PUT/PATCH/DELETE) require:
- A valid JWT in the `Authorization: Bearer` header, OR
- A valid session cookie **plus** a `X-CSRF-Token` header (for browser-based calls)
- Requests with only a cookie and no CSRF token are rejected with `403`

### **Rate Limiting (Prism's Own API)**

| Endpoint Group | Limit | Window |
|---------------|-------|--------|
| Auth (login, reset password) | 10 req | 15 min per IP |
| Dashboard queries | 120 req | 1 min per org |
| Sync trigger (manual) | 5 req | 1 hour per account |
| LLM queries | 20 req | 1 hour per user |
| Webhook test | 10 req | 1 hour per org |
| All other endpoints | 300 req | 1 min per org |

Rate limit headers returned: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### **SSRF Protection (Outbound Webhooks)**
User-supplied webhook URLs must be validated before saving and before each dispatch:

```typescript
import { isIP } from "net";

function validateWebhookUrl(url: string): void {
  const parsed = new URL(url); // throws if malformed

  // Block private/loopback IP ranges — prevents SSRF attacks
  const blocked = ["localhost", "127.", "10.", "192.168.", "172.16.", "::1", "0.0.0.0"];
  if (blocked.some(b => parsed.hostname.startsWith(b))) {
    throw new Error("Webhook URL must not point to a private or loopback address");
  }

  // Resolve hostname to IP and re-check (DNS rebinding protection)
  // Done asynchronously at dispatch time via a DNS pre-resolve step
  // Only https:// is allowed — no http://, ftp://, file://, etc.
  if (parsed.protocol !== "https:") {
    throw new Error("Webhook URL must use HTTPS");
  }
}
```

### **Webhook Validation (Teams + Slack)**
Incoming action callbacks from Teams/Slack are validated via HMAC:
```typescript
app.post("/api/teams-actions", validateHMAC("teams"), handleTeamsAction);
app.post("/api/slack-actions", validateHMAC("slack"),  handleSlackAction);

function validateHMAC(provider: "teams" | "slack") {
  return (req: Request, res: Response, next: NextFunction) => {
    const sigHeader = provider === "teams"
      ? req.headers["x-ms-teams-signature"] as string
      : req.headers["x-slack-signature"] as string;
    const secret = provider === "teams"
      ? process.env.TEAMS_SIGNING_SECRET!
      : process.env.SLACK_SIGNING_SECRET!;
    const expected = "sha256=" + crypto
      .createHmac("sha256", secret)
      .update(JSON.stringify(req.body))
      .digest("hex");
    if (!sigHeader || !crypto.timingSafeEqual(Buffer.from(sigHeader), Buffer.from(expected))) {
      return res.status(401).json({ error: "Invalid signature" });
    }
    next();
  };
}
```

### **Input Validation**
- All request bodies validated with Zod schemas before reaching business logic
- VirtualTagRule regex patterns: compiled and timed on a 1000-char string; rejected if >50ms or fails to compile (ReDoS guard)
- Virtual tag split_config: pct values must sum exactly to 100; validated at save time
- Outbound webhook URLs: validated for HTTPS and non-private IPs at save time and dispatch time
- Email addresses: RFC 5322 validated before storing

### **Audit Logging**
- **Prism Audit Trail:** All user actions logged — login, permission changes, cap creation/deletion, report send, alert acknowledge
- **AWS CloudTrail:** All API calls to customer AWS accounts
- **Azure Activity Log:** Service principal actions in customer Azure subscriptions
- **GCP Cloud Audit Logs:** Service account billing access
- Audit logs are **immutable** — append-only, no update/delete API

### **Data Retention**
- **Hot data (TimescaleDB):** 13 months (current + 12 historical)
- **Cold data:** After 13 months, archived to S3 in compressed Parquet format
- **Audit logs:** 7 years (compliance requirement)
- **Right-to-erasure (GDPR):** Customer data deletion within 30 days of account closure; includes backups

---

## **Pricing Model**

| Tier | Monthly | Users | Cloud Accounts | Key Features | Target |
|------|---------|-------|---------------|--------------|--------|
| **Starter** | $99 | 5 | Up to 3 (1 per platform) | AWS + Azure + GCP; email alerts; monthly report; basic caps | Solo founders / small teams |
| **Professional** | $299 | 25 | Unlimited | Multi-account; org-level; Teams alerts; per-service caps; per-team allocation | Growing startups |
| **Enterprise** | $999+ | Unlimited | Unlimited | Multi-org workspace; dedicated support; SLA; compliance exports | Larger companies |

**Startup Program:** 50% off for 6 months for companies with <$1M ARR.  
**Free Trial:** 14-day trial of Professional plan, no credit card required.

### **Billing**
- Monthly subscription via Stripe
- Annual billing available (2 months free)
- Usage-based add-on: additional cloud accounts beyond plan limit ($15/account/month)

### **Pricing Rationale**
- Cost of goods sold: ~$40/month (AWS hosting, email delivery, database)
- Gross margin: 85–90%
- CAC payback: <3 months

---

## **Implementation Roadmap**

### **Phase 1: MVP (Months 1–3) — AWS, Azure, GCP**

**Week 1–2:**
- [ ] AWS, Azure, GCP connectors with parameterized queries (follow API Implementation Guide)
- [ ] IAM roles in test accounts for all 3 platforms
- [ ] Cost normalization pipeline (PostgreSQL + TimescaleDB, daily aggregates only)
- [ ] Tag normalization (AWS tags → Azure tags → GCP labels → unified schema)
- [ ] Currency conversion with daily FX rate fetch
- [ ] Resource inventory table (`Resource` model — name, type, region, created_at, last_activity)

**Week 3–4:**
- [ ] Overall + Per-Platform dashboards (React) — wireframes in Dashboard Specification section
- [ ] Cost View toggle: Unblended / Amortized / Blended
- [ ] Data freshness indicators per account; partial data state
- [ ] Tagging coverage % metric on dashboard
- [ ] Spend Forecasting — end-of-month linear projection widget
- [ ] Email alert system (AWS SES or SendGrid)
- [ ] Forecast breach alert type

**Week 5–8:**
- [ ] Budget cap system — platform, service, account level
- [ ] Cap threshold alerts at 75/90/100/125/150%
- [ ] Teams webhook (optional), Slack webhook (optional), Outbound webhook (optional)
- [ ] Virtual Tag rule builder — set_tag and split actions; retroactive re-tag
- [ ] Onboarding checklist — first-run wizard
- [ ] Monthly report generation and scheduled email delivery

**Week 9–12:**
- [ ] Email + Google OAuth authentication
- [ ] Team member management (invite, roles, remove)
- [ ] Configuration setup wizard for each platform with copy-paste IAM blocks
- [ ] Single account / multi-account / organization scope support
- [ ] Rule-based recommendations (rightsizing, idle, storage tiering, RI opportunity)
- [ ] Resource age shown on recommendation cards
- [ ] Realized savings tracker (after `implemented`, track actual vs. projected for 30 days)
- [ ] Network/Egress cost breakdown in Per-Platform dashboard
- [ ] LLM configuration UI (OpenRouter key, model picker, budget cap)
- [ ] LLM: recommendation explanations, report narrative, alert context, NL query (all with fallback)
- [ ] CSV/PDF export; untagged resource detection; daily digest email
- [ ] FinOps Health Scorecard page (all 9 metrics)
- [ ] Executive KPI View

**Launch:** 100 beta customers, $15K MRR target

---

### **Phase 2: Scale + Additional Platforms (Months 4–6)**

- [ ] GitHub Actions billing integration
- [ ] Snowflake Account Usage integration
- [ ] Commitment Management dashboard (RI/SP/CUD coverage, utilization, ESR, expiry calendar)
- [ ] Commitment expiry alerts (60/30/14 days)
- [ ] AWS IAM permission additions for commitment APIs
- [ ] Unit Economics: business metric ingestion (webhook, CSV, Stripe, Datadog)
- [ ] Cost per customer / cost per request calculation + dashboard widget
- [ ] Unit economics section in monthly report
- [ ] Shared cost allocation (split shared resources by equal/fixed %/usage ratio)
- [ ] Comparison mode (current period vs. previous period side-by-side)
- [ ] Forecast accuracy tracking — month-end comparison + 3-month rolling average
- [ ] Resource Explorer view (every discovered resource with full detail)
- [ ] AI API cost tracking (OpenAI, Anthropic billing integration)

**Target:** 500 customers, $75K MRR

---

### **Phase 3: Enterprise + Compliance (Months 7–9)**

- [ ] SAML 2.0 SSO / Microsoft Entra ID integration
- [ ] Multi-org workspace (MSP / agency use case)
- [ ] SOC 2 Type II audit
- [ ] Compliance report exports (GDPR, HIPAA basics)
- [ ] Datadog cost integration
- [ ] Azure DevOps / GitLab CI cost attribution
- [ ] FinOps scorecard benchmarking (anonymous peer comparison)

**Target:** 1,000 customers, $200K MRR

---

### **Phase 4: Advanced (Months 10–12)**

- [ ] Terraform/CloudFormation IaC cost scanning on PRs (pre-deploy cost gating)
- [ ] Kubernetes (OpenCost + Prometheus) cost allocation
- [ ] Carbon footprint tracking (AWS/Azure/GCP emissions APIs)
- [ ] Cost simulation / what-if analysis ("What if we move this to Spot?")
- [ ] Automated commitment purchasing recommendations (Compute SP auto-buy with approval)
- [ ] Driver-based forecasting (LLM-assisted, considering planned workloads)

**Target:** 2,000 customers, $400K MRR

---

## **Success Metrics**

### **Month 12 Targets**

| Metric | Target | Notes |
|--------|--------|-------|
| MAU | 2,000+ | Monthly active users |
| MRR | $150K | Monthly recurring revenue |
| ARR | $1.8M | Annual recurring revenue |
| Customers | 500+ | Paying customers |
| Conversion | 20% | Free trial → paid |
| Churn | <5% | Monthly churn rate |
| NPS | >50 | Net Promoter Score |
| Uptime | 99.9% | Service availability |
| API p95 | <200ms | Dashboard API latency |
| Sync success rate | >98% | Daily syncs completing without error |
| Cost Savings | 25% avg | Per customer vs. pre-Prism baseline |

### **Engagement Metrics**

- **Dashboard DAU/MAU:** >60%
- **Monthly report open rate:** >70%
- **Cap alert email click-through:** >50%
- **Recommendations acted on:** >30% (target Phase 2: >60%)
- **Virtual tag rules created:** >1 per org by month 2
- **Commitment management viewed:** >40% of orgs with active commitments
- **FinOps scorecard viewed:** >50% of orgs monthly
- **Forecast accuracy (avg):** <15% variance by month 6

### **FinOps Outcome KPIs (Customer Health)**

These measure whether customers are *actually improving* — the core retention signal:

| KPI | Target by Month 6 | Measurement |
|-----|------------------|-------------|
| Tag Coverage % | >75% per org | Average across active orgs |
| Allocation Coverage % | >90% per org | % of spend attributed to a team |
| Recommendations implemented | >3 per org/month | Count in `Recommendation.status` |
| Realized savings vs. projected | >80% accuracy | Tracked in `Recommendation.actual_savings` |
| Commitment Coverage % | >40% (starter), >60% (professional) | From `CommitmentRecord` |
| ESR (Effective Savings Rate) | >15% | From commitment data |

---

## **Debug & Observability**

### **Sync Logs (Admin-visible in Configuration page)**

Per-account sync history table:

| Timestamp | Status | Records | Duration | Error |
|-----------|--------|---------|---------|-------|
| Oct 24, 2026 06:01 AM | ✅ Success | 1,243 | 4.2s | — |
| Oct 23, 2026 06:00 AM | ✅ Success | 1,187 | 3.8s | — |
| Oct 22, 2026 06:03 AM | ❌ Failed | 0 | 1.1s | AccessDenied: IAM role expired |

- **"Sync Now" button** — triggers immediate sync for a specific account; shows live progress
- **Exportable:** Download sync log as CSV

### **Alert Audit Trail**

Full history of every alert fired:

| Time | Type | Scope | Threshold | Spend | Email Sent | Teams Sent | Action |
|------|------|-------|-----------|-------|-----------|-----------|--------|
| Oct 24 9:15 AM | Cap | AWS EC2 | 90% | $1,800 | ✅ | ✅ | Snoozed by neeraj@acme.com |
| Oct 20 2:40 PM | Cap | AWS Total | 75% | $6,000 | ✅ | ❌ (no webhook) | Acknowledged |

### **Connector Health Dashboard**

Summary card per connected account:

```
AWS — Production Account
  Status:         ✅ Healthy
  Last sync:      2h ago (06:01 AM UTC)
  Data as of:     Oct 23, 2026 (24h lag — normal)
  Records today:  1,243
  API calls used: 3 of 5 TPS limit

Azure — Dev Subscription
  Status:         🔴 Credential expired
  Last sync:      6h ago (failed)
  Error:          AADSTS70011: The provided value for scope is not valid.
  Action:         [Reconnect]

GCP — Main Project
  Status:         ✅ Healthy
  Last sync:      3h ago
  Data as of:     Oct 22, 2026 (48h lag — normal for BigQuery export)
  Records today:  892
```

### **Application-Level Logging**

All logs structured as JSON with these standard fields:

```typescript
logger.info({
  event: "sync.complete",
  org_id: "uuid",
  account_id: "uuid",
  provider: "aws",
  records: 1243,
  duration_ms: 4200,
  data_as_of: "2026-10-23T23:00:00Z",
});

logger.error({
  event: "sync.failed",
  org_id: "uuid",
  account_id: "uuid",
  provider: "azure",
  error: "AADSTS70011: scope invalid",
  attempt: 3,
});

logger.warn({
  event: "cap.alert.fired",
  org_id: "uuid",
  cap_id: "uuid",
  scope: "AWS EC2",
  threshold_pct: 90,
  spend: 1800,
  cap: 2000,
  email_sent: true,
  teams_sent: false,
});
```

Log aggregation: CloudWatch Logs (default) or any ELK/Datadog-compatible sink.  
Retention: 90 days hot, then S3 archive.

### **Monitoring Alerts (Internal)**

Internal Prism health checks (not customer-facing):

| Check | Threshold | Action |
|-------|-----------|--------|
| API error rate | >1% over 5 min | PagerDuty on-call |
| Sync job queue lag | >2h behind | Slack #oncall alert |
| DB connection pool exhausted | >90% used | Auto-scale trigger |
| Email delivery failure rate | >5% | Investigate SES/SendGrid |
| p95 API latency | >1s | Performance investigation |

---

## **Deployment Checklist**

### **Pre-Launch (Week 1)**

**Infrastructure:**
- [ ] Kubernetes cluster (EKS on AWS)
- [ ] PostgreSQL 15 + TimescaleDB extension (RDS or self-managed)
- [ ] Redis (ElastiCache for sessions, job queues)
- [ ] S3 for report exports + CDN (CloudFront)
- [ ] SQS queues: `prism-daily-sync`, `prism-report-generation`, `prism-alerts`

**Secrets & Security:**
- [ ] HashiCorp Vault or AWS Secrets Manager provisioned
- [ ] AES-256 encryption key generated and stored in Vault
- [ ] SSL/TLS certificates provisioned (ACM auto-renewal)
- [ ] WAF rules enabled (OWASP Top 10)
- [ ] Row-level security confirmed in PostgreSQL (test cross-org query blocked)

**Email:**
- [ ] SES or SendGrid domain verified and DKIM configured
- [ ] Transactional email templates (invite, reset, alert, report) QA'd
- [ ] Monthly report scheduler job registered in SQS/cron

**Monitoring:**
- [ ] CloudWatch dashboards + alert rules
- [ ] Structured log aggregation pipeline
- [ ] Health check endpoints for all services (`/health`, `/ready`)

### **Customer Onboarding (Week 2)**

- [ ] Configuration wizard tested end-to-end for AWS, Azure, GCP
- [ ] IAM role setup validated in fresh test accounts
- [ ] "Test Connection" endpoint working and returning meaningful errors
- [ ] "Sync Now" manual trigger tested
- [ ] Invite flow tested (email invite → accept → role assigned)
- [ ] Monthly report "Send Test" button works
- [ ] Cap alert emails rendering correctly in Gmail, Outlook, Apple Mail

### **Launch (Week 3)**

- [ ] Health checks passing on all connectors (test accounts)
- [ ] Staging environment tests (happy path + sad paths: bad credentials, expired tokens, no data)
- [ ] Load testing: 100 concurrent orgs doing daily sync without DB contention
- [ ] Security scan: OWASP Top 10, SQL injection on all inputs, CSRF on state-changing endpoints
- [ ] Backup and restore tested (RDS snapshot restore)
- [ ] Runbook written for: sync failures, credential expiry, report send failure, DB disk full

**Go-Live:**
- [ ] Announce to beta cohort (20–50 customers)
- [ ] Daily sync running at 06:00 UTC for all accounts
- [ ] Cap alerts firing correctly in test org
- [ ] Support email/channel staffed
- [ ] Error budget: <0.1% failed syncs acceptable in first week

### **Post-Launch (Weeks 4–12)**

- [ ] Monitor sync error rate daily
- [ ] Collect feedback via in-app NPS survey (30-day post-signup)
- [ ] Critical bugs fixed within 24h, non-critical within 7 days
- [ ] Feature requests triaged weekly
- [ ] Credential expiry warning emails working (test with 14-day and 7-day windows)

---

## **Appendix: Environment Variables**

```bash
# ─── Database ───────────────────────────────────────────────
DATABASE_URL="postgresql://user:pass@host:5432/prism"
REDIS_URL="redis://host:6379"

# ─── Auth ───────────────────────────────────────────────────
JWT_SECRET="min-32-char-random-string"
JWT_ACCESS_EXPIRY="7d"
JWT_REFRESH_EXPIRY="30d"
GOOGLE_CLIENT_ID="xxxxxxxx.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="xxxxxxxxxxxxxxxxxxxx"

# ─── Email ──────────────────────────────────────────────────
EMAIL_PROVIDER="ses"               # "ses" | "sendgrid"
AWS_SES_REGION="us-east-1"
SENDGRID_API_KEY="SG.xxxxxxxxx"   # if using SendGrid
EMAIL_FROM="noreply@prism.io"
EMAIL_FROM_NAME="Prism"

# ─── Secrets Vault ──────────────────────────────────────────
VAULT_URL="https://vault.internal"
VAULT_TOKEN="hvs.xxxxxxxxx"
ENCRYPTION_KEY="32-byte-aes-key-base64-encoded"   # for credential encryption at rest

# ─── AWS (Prism's own account for hosting) ──────────────────
AWS_REGION="us-east-1"
PRISM_AWS_ACCOUNT_ID="123456789012"               # Prism's account — used in IAM trust policy shown to customers

# ─── Teams (Optional) ───────────────────────────────────────
TEAMS_SIGNING_SECRET="xxxxxxxxxxxxxxxxxxxx"       # for HMAC validation on incoming actions

# ─── Slack (Optional) ────────────────────────────────────────
# Per-org Slack webhook URLs stored in DB (NotificationSettings.slack_webhook_url)
# No global env var needed — each org configures their own webhook in Settings

# ─── Outbound Webhooks ───────────────────────────────────────
# Per-org webhook configs in DB (OutboundWebhook table)
# Signing secrets stored encrypted in Vault per webhook

# ─── LLM / OpenRouter (Optional) ────────────────────────────
# Each org's OpenRouter key is stored encrypted in Vault per-org,
# configured by the user in Settings → LLM. Not a global env var.
# Below is for local dev/test only — never commit a real key.
OPENROUTER_API_KEY_DEV="sk-or-v1-xxxxxxxxx"      # dev/test only; never prod
OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"

# ─── FX Rates ───────────────────────────────────────────────
FX_RATE_API_URL="https://api.exchangerate-api.com/v4/latest/USD"
FX_RATE_API_KEY="xxxxxxxx"

# ─── App ────────────────────────────────────────────────────
PORT=3000
NODE_ENV="production"
LOG_LEVEL="info"
APP_URL="https://app.prism.io"
```

---

## **Document History**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Sep 2026 | Initial product specification |
| 1.1 | Sep 2026 | Added market research, gamification, weekly reports |
| 2.0 | Oct 1, 2026 | Integrated IAM roles, API implementation, Teams notifications |
| 3.0 | Oct 25, 2026 | Major revision: Startup-focused scope. Removed AI/ML, gamification, GitHub/Snowflake (Phase 1). Added configuration wizard with IAM copy-paste blocks, single/multi/org account support, budget cap system with 75/90/100/125/150% thresholds, monthly email report, simplified RBAC (Owner/Admin/Editor/Viewer), email-primary notifications with Teams as optional, USD-default currency with FX conversion, debug/observability section, data freshness indicators. Fixed SQL injection (BigQuery parameterized queries), fixed withRetry lastError bug, added Teams webhook HMAC validation. |
| 3.1 | Oct 25, 2026 | Added: Optional LLM integration via OpenRouter (user-configured, graceful fallback). LLM surfaces: report executive narrative, recommendation explanations, alert context, natural language queries, untagged resource ownership suggestions. Added full Dashboard Specification (overall + per-platform wireframes). Added Data Storage Philosophy (store only necessary aggregates). Added LLMConfig data model. |
| 3.2 | Oct 25, 2026 | Added: Virtual Tagging (in-Prism rule builder, retroactive re-tag, split allocation, audit log). Spend Forecasting (end-of-month linear projection, forecast breach alert, accuracy tracking). Commitment Management (RI/SP/CUD coverage, utilization, ESR, expiry calendar, expiry alerts). FinOps Health Scorecard (9 metrics, 0–100 score, weekly trend, Executive KPI View). Network/Egress breakdown in per-platform dashboard. Slack webhook as optional notification channel. Outbound webhook (Jira/custom, HMAC-signed). Shared cost allocation (equal/fixed%/usage-ratio split). Resource lifecycle tracking (created_at, last_activity, created_by). Unit Economics with business metric ingestion (Stripe/Datadog/CSV/webhook). Onboarding checklist (first-run wizard). Amortized/Blended/Unblended cost view toggle. Tagging coverage % on dashboard. FinOps outcome KPIs in success metrics. Updated data models: VirtualTagRule, CommitmentRecord, SpendForecast, BusinessMetric, BusinessMetricValue, OutboundWebhook, NotificationSettings, Resource. Roadmap revised across all 4 phases. |
| 3.4 | Oct 25, 2026 | **End-to-End User Journey section added** (9 stages): Stage 0 Sign Up & Org Creation (screens, email, error states). Stage 1 Empty State dashboard. Stage 2 Connect Cloud Account (4-step AWS wizard with IAM copy-paste, background sync job sequence). Stage 3 Invite Team Members (modal UI, invite email template, accept flow, expired-invite handling). Stage 4 Set Budget Caps (UI + what triggers on create). Stage 5 Configure Monthly Report (UI with all include toggles). Stage 6 Ongoing Autopilot Operations (daily job schedule timeline). Stage 7 Alerts (in-app banner + full email template + threshold table). Stage 8 Monthly Report email template. Stage 9 Settings tab reference. Complete end-to-end flow diagram. |
| 3.3 | Oct 25, 2026 | **Hardening pass — production readiness:** Fixed Azure connector `this.fxRate` undefined bug (NaN cost_usd). Added `withRetry` 429 rate-limit handling with `retry-after` header. Added DB indexes (cost_records idempotency, alerts dedup partial index, resource unique constraint, commitment expiry index, forecast index, vtag priority index). Added Redis dashboard query caching strategy (6 cache keys, org-scoped). Added WebSocket event schema (5 event types with typed payloads). Added Dead Letter Queue (DLQ) spec for background jobs. Added API versioning (`/v1/` prefix, 6-month deprecation). Added CSRF protection spec. Added rate limiting table. Added SSRF protection for outbound webhook URLs (private IP blocklist, HTTPS-only). Added Slack HMAC validation (paired with Teams HMAC). Added `validateWebhookUrl` utility. Added input validation section (Zod, regex ReDoS guard, split_config pct sum validation). Fixed `CapAlertService.fireAlert` to set `slack_sent` and `webhook_sent`, fire Slack and outbound webhooks concurrently via `Promise.allSettled`. Fixed `MonthlyReport` model (added `include_commitments`, `include_unit_economics`, `include_finops_scorecard`). Fixed `VirtualTagRule` model (added `updated_at`, `updated_by`, ReDoS guard comment, split_config validation note). Fixed `Resource` model (added `idle_since`, `virtual_tags`, upsert note, unique constraint). Fixed `TeamMember` model (added `email`, `invite_expires_at`, token hashing note). Fixed `Alert` expanded types + added `metadata`. Fixed `Recommendation` expanded types + `llm_explanation`, `llm_risk_note`, `actual_savings_updated_at`. Fixed `BudgetCap` (added `name`, `updated_at`). Fixed `Organization` (added `timezone`, `feature_flags`). Fixed `CostRecord` (added `cost_unblended_usd`, `cost_amortized_usd`, `virtual_tags`). Added forecast edge case table (3-day minimum, mid-month onboarding, weekend zero-spend). Added `rolling_7d_avg` and `data_coverage` to `SpendForecast`. Added commitment sync frequency table. Added retroactive re-tag background job note with progress indicator. Added VPC Flow Logs prerequisite for network egress detailed breakdown. Fixed onboarding checklist (deduped to 5 non-overlapping steps). Added Day-1 empty state design. |

---

**Status:** ✅ **APPROVED FOR DEVELOPMENT**

**Next Steps:**
1. Spin up AWS/Azure/GCP test accounts
2. Create IAM roles (follow Configuration & Setup Guide → Section 8)
3. Implement connectors (follow API Implementation Guide)
4. Deploy infrastructure (Kubernetes, PostgreSQL + TimescaleDB, Redis, SQS)
5. Begin Phase 1 development (Weeks 1–12)
