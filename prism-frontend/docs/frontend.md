Now I have everything I need. Let me synthesize all 15 reference images, the FinOps design research, and the full backend contract into a complete frontend plan.

---

# PRISM Frontend Plan

## What I drew from the UI references

| Reference | Unique signal to borrow |
|-----------|------------------------|
| **Donezo** (Media 2) | Dark sidebar + white canvas, grouped nav sections (MENU/GENERAL), metric cards with inline deltas |
| **Crextio** (Media 3) | Bento grid widgets, inline progress bars in stat cards, warm welcome greeting |
| **Analytics dash** (Media 4) | Bold dollar numbers, bar chart with percentage labels floating above, dense but clean KPI row |
| **Minimal dash** (Media 5) | Icon-only sidebar, full-width gradient progress bar, radial spider chart for multi-metric health |
| **Finance widgets** (Media 6) | Dark card / light card contrast within the same view, gauge + mini-chart combos |
| **URBN** (Media 8) | Zero-clutter white UI, line chart with barely-visible gridlines, section header "Smart score 82/100" |
| **Fundex dark** (Media 9) | Dark mode with two-tone bar charts, horizontal data table with status dots, premium feel |
| **Realty hub** (Media 10) | Icon-only left rail, neutral beige accents, metric + dial pairs |
| **Revenue cards** (Media 11) | Modular card system (each card = one question answered), export CSV button in overview card |
| **Oppo Device** (Media 12) | Prominent CTA ("+ Add Asset"), scorecard dial 79%, "Areas to Address" actionable list, day bar chart |
| **Zarss** (Media 14) | Dark sidebar + white area dual-tone, monochrome charts with tooltip, activity feed right column |
| **Dappr** (Media 15) | Icon-only dark side rail, KPI row (4 cards), line chart with tooltip, to-do action items |
| **Crowz** (Media 16) | Warm sidebar with user profile card at top, clean area line chart, channel breakdown row |

**What NOT to use:** Media 7 (Phoenix) is too technical/hardware-specific for a SaaS product.

---

## Real user model — who opens PRISM and how often

| Persona | Frequency | What they open first | Critical need |
|---------|-----------|----------------------|---------------|
| **FinOps Engineer** | Daily | Dashboard → Alerts → Recommendations | "Any anomalies overnight? Any caps about to fire?" |
| **Engineering Manager** | 2–3×/week | Costs by-service → Forecast | "Is my team's AWS spend trending up?" |
| **CTO / CFO** | Weekly/monthly | Scorecard → Executive view → Reports | "One number: are we on budget?" |
| **DevOps Admin** | On-demand | Accounts → Sync logs → Notifications | "Why did sync fail? Fix IAM role." |
| **New user (first day)** | Once | Onboarding wizard | "How do I connect AWS without breaking prod?" |

This shapes every layout decision: **the dashboard must answer the FinOps engineer's daily question in <5 seconds**. Settings pages are secondary.

---

## Tech Stack

```
Next.js 15 (App Router) + TypeScript
Tailwind CSS + shadcn/ui (Radix primitives)
Recharts — charts (bar, line, area, radial, donut)
TanStack Query (React Query) — all API data fetching + cache
Zustand — auth state, org context, WS connection
React Hook Form + Zod — forms + validation
next-auth (or custom) — JWT / Google OAuth
native WebSocket — sync.complete toasts
Lucide React — icons (consistent, clean)
date-fns — date formatting
```

[Certain] This exact stack appears in the top real-world FinOps dashboards built in 2025–2026, pairs perfectly with the FastAPI backend, and directly aligns with PRISM's backend contract.

---

## Design Language

**Palette (from references + FinOps premium standard):**

```
Sidebar:         #111827  (near-black)   — from Donezo, Zarss, Dappr
Canvas:          #F9FAFB  (off-white)    — from URBN, Oppo Device
Card:            #FFFFFF  border #E5E7EB
Accent:          #6366F1  (indigo)       — "PRISM" = spectrum/light
Success:         #22C55E  green
Warning:         #F59E0B  amber
Danger:          #EF4444  red
Muted text:      #6B7280
Heading text:    #111827
```

**Typography:** Inter (Google Fonts) — same as most references. `font-semibold` for numbers, `font-normal` for labels.

**Component language:**
- Rounded corners everywhere (`rounded-xl` for cards, `rounded-lg` for buttons)
- Subtle shadows `shadow-sm hover:shadow-md`
- Skeleton loaders on all async components (never spinners)
- Status dots: green pulse = healthy/syncing, amber = degraded, red = error
- Badges for roles, MoM deltas (+12% ↑ green, -3% ↓ red)

---

## Application Shell

```
┌─────────────────────────────────────────────────────────────────┐
│ Dark Sidebar (240px / collapse to 64px)  │  Top Bar              │
│                                           │  Content Area         │
│ Logo: PRISM                              │                       │
│ ─────────────────────────────             │                       │
│ OVERVIEW                                  │                       │
│  ● Dashboard                             │                       │
│  ○ Costs                                 │                       │
│  ○ Accounts                              │                       │
│  ○ Forecast                              │                       │
│  ○ Commitments                           │                       │
│  ○ Recommendations                       │                       │
│  ○ Scorecard                             │                       │
│  ○ Resources                             │                       │
│ ─────────────────────────────             │                       │
│ MANAGE                                    │                       │
│  ○ Budget Caps                           │                       │
│  ○ Alerts                                │                       │
│  ○ Virtual Tags                          │                       │
│  ○ Business Metrics                      │                       │
│  ○ Assistant (LLM)                       │                       │
│  ○ Reports                               │                       │
│ ─────────────────────────────             │                       │
│ SETTINGS                                  │                       │
│  ○ Team                                  │                       │
│  ○ Notifications                         │                       │
│  ○ Webhooks                              │                       │
│  ○ API Keys                              │                       │
│  ○ Org                                   │                       │
│ ─────────────────────────────             │                       │
│  [Avatar]  Neeraj K  (Owner)  [←]        │                       │
└─────────────────────────────────────────────────────────────────┘
```

**Top Bar:**
- Left: Page title + breadcrumb
- Center: Global search `⌘K` — fuzzy search across accounts, services, recommendations, alerts
- Right: Health indicator dot → Notifications bell (badge count) → User avatar dropdown (profile, change password, logout)

**WebSocket:** Persistent connection. When `sync.complete` fires → toast bottom-right: *"✓ AWS synced · 1,243 records · just now"*. When health = degraded → sticky amber banner: *"Dashboard data may be stale — Redis unavailable"*

---

## Screens (ordered by user journey)

---

### 1. Auth Flow — `/auth/*`

**Pages:** login, signup (3-step), verify-email, forgot-password, reset-password, accept-invite

**Login page design (from references: Donezo sidebar feel + clean URBN white):**
```
Left half: Product illustration + "PRISM — See every cloud dollar"
Right half: 
  Logo
  "Welcome back"
  Email + Password
  [Sign in] button (indigo, full width)
  ─── or ───
  [Continue with Google] (white, border)
  "No account? Sign up"
```

**Signup:** 3-step stepper (like Oppo Device's clear section headers)
- Step 1: Email + Name + Password
- Step 2: Organisation name + Currency
- Step 3: Check inbox (animated email icon)

**Key detail:** Accept-invite page sets password for new users, skips password for existing ones — handle both cases.

---

### 2. First-run Onboarding Wizard

Shown if `accounts.length === 0` after login. Full-screen stepper (not inside the sidebar shell).

```
Step 1 of 4: Connect your first cloud account
  [AWS] [Azure] [GCP]  (card selector)
  → credential form with copy-paste IAM block (like the backend plan)
  → "Test connection" live button
  → On pass: "✓ Connection successful"

Step 2 of 4: Set a budget cap (optional skip)
  Provider, Scope, Amount

Step 3 of 4: Invite your team (optional skip)
  Email + Role

Step 4 of 4: Set up notifications
  Alert email, Thresholds
  → "Go to dashboard" CTA
```

---

### 3. Dashboard — `/dashboard`

This is the **most important screen**. Layout (from Media 2 Donezo + Media 12 Oppo + FinOps research):

```
"Good morning, Neeraj 👋"
"November 2026 · AWS synced 2h ago · Azure synced 3h ago · GCP ⚠️ failed"

┌────────────────────────────────────────────────────────────────┐
│ KPI CARD ROW (4 cards)                                         │
│ [MTD Spend $12,453] [MoM △+8%] [Forecast $18.2k] [⚠ 3 Alerts]│
│  sparkline ↓          badge        vs cap $20k    unread      │
└────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────┐  ┌───────────────────────────┐
│ SPEND BY DAY (area chart 30d)    │  │ TOP 5 SERVICES            │
│ [All Providers ▾] [Unblended ▾]  │  │ EC2        $4,231  +12% ↑ │
│                                  │  │ S3         $1,840  -3%  ↓ │
│  area chart with provider colors │  │ RDS        $1,210  +5%  ↑ │
│  today marked ⚠ estimated        │  │ Azure VMs  $890   +1%  ↑ │
│                                  │  │ GCP BQ     $430   +20% ↑ │
└──────────────────────────────────┘  └───────────────────────────┘

┌────────────────────────┐  ┌────────────────────┐  ┌────────────┐
│ BUDGET CAPS            │  │ FORECAST            │  │ SCORECARD  │
│ AWS Total              │  │ Nov month-end:      │  │            │
│ $12.4k / $15k          │  │ $18,200             │  │  83/100    │
│ [████████░░░] 83%      │  │ [█████████░] 91%    │  │    B       │
│ 1 at 90%+ ⚠            │  │ vs cap $20k         │  │  ↑ from 76 │
└────────────────────────┘  └────────────────────┘  └────────────┘

┌──────────────────────────────────────────────────────────────┐
│ RECOMMENDATIONS (top 3)         [View all →]                 │
│ 💡 Downsize ec2 t3.large → t3.medium  Save $94/mo  [Review] │
│ 💡 Delete 3 unused EBS volumes        Save $23/mo  [Review] │
│ 💡 Enable S3 Intelligent Tiering      Save $41/mo  [Review] │
└──────────────────────────────────────────────────────────────┘
```

---

### 4. Costs — `/costs`

Tab bar: **Overview | By Day | By Service | By Tag | Top Services**

Controls row: `[Date range picker]  [Provider: All ▾]  [Cost view: Unblended ▾]  [Export CSV]`

Data freshness: `"Data as of Nov 12 · Today's figures are estimated ⚠"`

**By Day tab:** Area/bar chart (like Media 4's bold bars with percentage labels). Zero-filled days shown as grey.

**By Service tab:** Table with sortable columns (service, provider, MTD, MoM %, trend sparkline). Like Media 8 (URBN table) — clean, no clutter.

**By Tag tab:** Tag key dropdown → stacked bar or donut. Untagged % shown prominently.

---

### 5. Accounts — `/accounts`

```
┌────────────────────────────────────┐  [+ Connect Account]
│ 🟢 AWS – Production                │
│    Account: 123456789012            │
│    Last synced: 2h ago · 1,243 rec  │
│    Data as of: Nov 12               │
│    [Sync Now]  [Test]  [···]        │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│ 🔴 Azure – Dev Subscription        │
│    Error: AADSTS70011 scope invalid  │
│    Last synced: 6h ago (failed)     │
│    [Reconnect]  [Sync Logs]         │
└────────────────────────────────────┘
```

**Connect wizard:** Stepper with credential forms. AWS shows pre-filled IAM policy JSON in a copy block (from backend plan). "Test Connection" calls `/test` endpoint live.

**Sync Logs drawer:** Timeline list of sync runs — status badge, records count, duration, error message if failed.

---

### 6. Budget Caps — `/caps`

```
[+ Add Cap]

AWS Total              $12,453 / $15,000      [████████░░░] 83%  ⚠ 90% threshold
AWS EC2                $4,231  / $6,000       [███████░░░░] 71%  ✓
Azure All              $890    / $2,000       [████░░░░░░░] 44%  ✓
```

Progress bar colors: green (<75%), amber (75–99%), red (100%+), dark red (>125%).

Clicking any row → detail panel: threshold history, alert history, edit form.

---

### 7. Alerts — `/alerts`

Filter tabs: **Active (3) | Acknowledged | Snoozed**

```
⚠ Cap threshold · AWS Total · 90% · $13,500/$15,000
  Triggered Nov 13 09:15 · Email ✓ · Teams ✓ · Slack ✗
  [Acknowledge]  [Snooze until ▾]

⚠ Cap threshold · AWS EC2 · 75% · $4,231/$5,000
  Triggered Nov 12 · Email ✓
  [Acknowledge]  [Snooze until ▾]
```

Severity color-coding on left border (amber=warning, red=critical).

---

### 8. Forecasts — `/forecasts`

```
┌────────────────────┐  ┌────────────────────┐  ┌──────────────────┐
│ AWS                │  │ Azure              │  │ GCP              │
│ Projected: $14,210 │  │ Projected: $3,100  │  │ Projected: $890  │
│ [██████████░] 95%  │  │ [████░░░░░░] 55%   │  │ [███░░░░░░] 44%  │
│ vs cap $15k        │  │ vs cap $5k         │  │ No cap set       │
│ ⚠ 95% — will hit!  │  │ ✓ On track         │  │ —                │
│ Days elapsed: 13   │  │ Daily avg: $103    │  │                  │
└────────────────────┘  └────────────────────┘  └──────────────────┘

Forecast History (table): month, provider, projected, actual, variance %, accuracy
```

---

### 9. Commitments — `/commitments`

```
Summary: Coverage 68% · Utilization 84% · 2 expiring in 30 days

Tabs: [All Commitments] [Expiring Soon]

Table:
Provider  Type       Resource  Coverage  Utilization  End Date      Status
AWS       Savings Plan  EC2    72%       91%          Mar 2027     Active
AWS       Reserved Inst t3.m  54%       78%          Dec 2026     Expiring ⚠
GCP       CUD           VM     80%       88%          Jun 2027     Active
```

Expiring Soon — dedicated tab with countdown badges.

---

### 10. Recommendations — `/recommendations`

```
Tabs: [Open (8)] [Implemented (3)] [Rejected (1)]

Filter: [Provider ▾] [Min savings ▾] [Confidence ▾]

┌────────────────────────────────────────────────────────────────┐
│ 🟡 Medium  Downsize ec2 t3.large → t3.medium               │
│    AWS · us-east-1 · Saves $94/mo  High confidence          │
│    [Implement]  [Reject]  [Explain →]                        │
└────────────────────────────────────────────────────────────────┘
```

"Explain →" triggers LLM explanation if configured. This directly maps to Media 12's "Areas to Address" pattern.

---

### 11. FinOps Scorecard — `/scorecard`

Inspired by **Media 5's radial chart** + **Media 12's dial** — this is the most visually impactful page:

```
┌─────────────────────────────────────────────────────────────────┐
│ FinOps Health Score                      [Executive View toggle]│
│                                                                  │
│    83                 Grade: B                                   │
│   / 100              ↑ from 76 last week                        │
│  [large radial dial]                                             │
│                                                                  │
│  Tagging Coverage    88%  ████████░   ✓ Green                   │
│  Idle Resource Rate  72%  ███████░░   ⚠ Yellow                  │
│  Commitment Coverage 65%  ██████░░░   ⚠ Yellow                  │
│  Budget Cap Coverage 90%  █████████   ✓ Green                   │
│  Forecast Accuracy   78%  ███████░░   ⚠ Yellow                  │
│  Alert Response Time 95%  █████████   ✓ Green                   │
│  Rec Action Rate     40%  ████░░░░░   🔴 Red                    │
└─────────────────────────────────────────────────────────────────┘

Executive View: 4 KPI cards for CFO level (MTD, forecast, scorecard grade, savings realized)
```

---

### 12. Resources — `/resources`

```
Tabs: [All Resources] [Idle (12)]

Filters: [Provider] [Region] [Type]

Table with:
  resource name | type | provider | region | last active | idle since | last cost/day | tags
  
Idle tab highlights with orange "Idle X days" badge.
```

---

### 13. Virtual Tags — `/virtual-tags`

```
Tabs: [Rules] [Audit Log]

[+ New Rule]

Drag-to-reorder list (priority order):
  ⠿ #1  Environment  →  "prod" (regex: service contains "prod")  [Edit] [Apply] [Delete]
  ⠿ #2  Team        →  "platform" (tag: team = platform)        [Edit] [Apply] [Delete]

Apply drawer: shows progress "Re-tagging 45,231 records... 67%"
Audit log tab: table with run date, rule, rows processed, rows updated, status
```

---

### 14. Business Metrics — `/metrics`

```
[+ Add Metric]

Metric cards:
  Monthly Active Users  source: manual  unit: users  [Ingest value]
  API Requests          source: webhook unit: requests

Unit Economics table (bottom):
  Metric            MTD value    MTD cloud cost    Cost per unit
  MAU               12,450       $14,200           $1.14/user   ↑ 0.08
  API Requests      8.2M         $14,200           $0.0017/req  ↓ 0.0002
```

---

### 15. AI Assistant — `/assistant`

```
┌────────────────────────────────────────────────────────────────┐
│ Ask anything about your cloud costs                            │
│                                                                │
│ [chat history]                                                 │
│                                                                │
│ You: Which service drove the most cost increase last week?     │
│ PRISM: EC2 increased by $1,240 (+18%) vs the prior week,       │
│        primarily from r5.xlarge instances in us-east-1.        │
│        You have 3 open recommendations for this service →      │
│                                                                │
│ [Ask your question...                        ] [Send →]        │
│ 20/hour · Monthly LLM budget: $4.20 / $20.00 used             │
└────────────────────────────────────────────────────────────────┘
```

Admin can configure API key, model, budget in `/settings` → LLM section.

---

### 16. Reports — `/reports`

```
Monthly Report Configuration

Toggle: [Active / Inactive]
Recipients: [email1, email2 + Add]
Send on: Day [1] of each month
Sections: [✓] Recommendations  [✓] Scorecard  [✓] Commitments  [ ] Unit Economics

[Send Now →]  Last sent: Nov 1, 2026
```

---

### 17–22. Settings

Grouped under `/settings/*` with a secondary side-nav:

| Path | Content |
|------|---------|
| `/settings/notifications` | Alert emails, Teams/Slack URLs, threshold toggles (75/90/100/125/150%), test buttons |
| `/settings/webhooks` | Webhook list, add/edit/test/delete, event checkboxes, signing secret |
| `/settings/team` | Members table with role badges, invite drawer, change role, remove |
| `/settings/api-keys` | Key list (prefix only), create (shown once in a copy-box), revoke |
| `/settings/org` | Name, currency, timezone, plan |
| `/settings/profile` | Name, avatar, change password, Google OAuth connection |

---

## Cross-cutting UX patterns (apply everywhere)

| Pattern | Implementation |
|---------|---------------|
| **Data freshness** | Every data card shows `"Updated X mins ago"` from `data_as_of` |
| **Estimated flag** | Amber `⚠ estimated` badge on current-day figures (backend `is_estimate=true`) |
| **Role gating** | Viewer sees buttons disabled with tooltip "Requires Editor+". Admin-only sections hidden entirely for viewers |
| **Realtime WS toast** | `sync.complete` → slide-in toast bottom-right, auto-dismiss 5s |
| **Health degraded banner** | `GET /health` returns degraded → amber sticky banner `"Data may be stale — cache unavailable"` |
| **Skeleton loaders** | Every `useQuery` loading state uses a matching skeleton, never a spinner |
| **Empty states** | Each page has an illustrated empty state + single CTA (e.g., "Connect your first account →") |
| **Global search ⌘K** | Command palette: search accounts, services, recommendations, alerts, settings pages |
| **Export** | Costs and sync logs have CSV download |
| **Confirm dangerous actions** | Delete account, revoke API key → modal confirm dialog |
| **Credential security** | Never show `credentials_enc`. Credential forms are always write-only. |
| **Pagination** | All lists use cursor/page-based pagination. No infinite scroll except alerts feed. |
| **MoM delta badges** | `+12% ↑` green, `-3% ↓` red, inline with every cost figure |
| **Provider color coding** | AWS = orange, Azure = blue, GCP = green (consistent across all charts) |
| **Token refresh** | Silent refresh on 401 using the refresh endpoint. On refresh failure → logout |

---

## Page/Route Map Summary

```
/login
/signup
/verify-email
/forgot-password
/reset-password
/accept-invite

/onboarding                    (first-run wizard)

/dashboard                     (home)
/costs                         (by-day, by-service, by-tag, top)
/accounts                      (list)
/accounts/connect              (wizard)
/accounts/[id]                 (detail + sync logs)
/forecasts
/commitments
/recommendations
/scorecard
/resources
/caps
/alerts
/virtual-tags
/metrics
/assistant
/reports

/settings/team
/settings/notifications
/settings/webhooks
/settings/api-keys
/settings/org
/settings/profile
/settings/llm                  (admin only)
```

**Total: 22 pages / route groups**, all backed by existing API endpoints with no frontend-only pages.

---

## What to build first (priority order)

1. **Auth shell + token management** — everything depends on this
2. **App shell** (sidebar + top bar + WS connection)
3. **Dashboard** — the daily-use anchor
4. **Accounts + Connect wizard** — data doesn't exist without this
5. **Costs** (by-day, by-service)
6. **Budget Caps + Alerts** — core value prop
7. **Scorecard** — high visual impact, impresses stakeholders
8. **Forecasts + Commitments + Recommendations**
9. **Settings** (notifications, team, webhooks, API keys)
10. **Resources, Virtual Tags, Business Metrics, Assistant, Reports**

---

## Factors to consider before building

| Factor | Decision needed |
|--------|----------------|
| **Dark mode** | References show both. Light default + dark toggle recommended. Ship light first. |
| **Mobile** | Real FinOps users are desktop-first. Responsive but not mobile-first. Sidebar collapses to hamburger on <768px. |
| **i18n** | Backend supports currency + timezone per org. Frontend should format numbers/dates per org currency/timezone from `/me`. |
| **Onboarding for invitees** | Invitee email arrives → accept-invite page → they may need to set a password (new user) or just join (existing). Two flows needed. |
| **Token refresh strategy** | 15m access token. Use TanStack Query's `onError` + `retry` with a refresh call before retry. Store refresh token in `httpOnly` cookie ideally, or `localStorage` with the tradeoff noted. |
| **Chart library** | Recharts is sufficient. Don't use heavyweight D3 for the KPI-style charts you have. |
| **Sensitive credential forms** | AWS/Azure/GCP credential inputs should use `autocomplete="off"` and not be logged/stored in browser history. |
| **Redis degraded UX** | Health endpoint returns `degraded` without 503. Frontend must check the `status` field, not just HTTP code. |
| **Cost view toggle** | Unblended vs Amortized affects all cost numbers. Store selection in URL params so deep links work. |
| **Date range** | Default: current month. Allow custom range. Backend `by-day` fills zero days so no gaps in charts. |























Here's the complete PRISM design system — every token, rule, and decision you need before writing a single component.

---

# PRISM Design System

## 1. Color Tokens

### Core Palette

```css
/* Brand */
--color-brand-50:    #EEF2FF   /* tinted bg for active states */
--color-brand-100:   #E0E7FF   /* hover bg on sidebar items */
--color-brand-200:   #C7D2FE
--color-brand-300:   #A5B4FC
--color-brand-400:   #818CF8
--color-brand-500:   #6366F1   /* PRIMARY — buttons, links, active nav */
--color-brand-600:   #4F46E5   /* hover state on primary button */
--color-brand-700:   #4338CA   /* pressed/active */
--color-brand-800:   #3730A3
--color-brand-900:   #312E81

/* Neutrals */
--color-gray-0:      #FFFFFF
--color-gray-50:     #F9FAFB   /* page canvas */
--color-gray-100:    #F3F4F6   /* table row hover, input bg */
--color-gray-200:    #E5E7EB   /* card border, divider */
--color-gray-300:    #D1D5DB   /* disabled input border */
--color-gray-400:    #9CA3AF   /* placeholder text */
--color-gray-500:    #6B7280   /* muted / helper text */
--color-gray-600:    #4B5563   /* secondary text */
--color-gray-700:    #374151   /* body text */
--color-gray-800:    #1F2937   /* dark heading */
--color-gray-900:    #111827   /* sidebar bg, near-black heading */

/* Semantic */
--color-success-50:  #F0FDF4
--color-success-100: #DCFCE7
--color-success-500: #22C55E   /* success icon, positive delta */
--color-success-600: #16A34A   /* success button/badge */
--color-success-700: #15803D

--color-warning-50:  #FFFBEB
--color-warning-100: #FEF3C7
--color-warning-400: #FBBF24
--color-warning-500: #F59E0B   /* warning icon, 75-99% cap */
--color-warning-600: #D97706

--color-danger-50:   #FEF2F2
--color-danger-100:  #FEE2E2
--color-danger-400:  #F87171
--color-danger-500:  #EF4444   /* error, >100% cap, failed sync */
--color-danger-600:  #DC2626

--color-info-50:     #EFF6FF
--color-info-500:    #3B82F6
--color-info-600:    #2563EB
```

### Semantic Role Mapping

| Role | Token | Use |
|------|-------|-----|
| Page background | `gray-50` | `#F9FAFB` |
| Card background | `gray-0` | `#FFFFFF` |
| Card border | `gray-200` | `#E5E7EB` |
| Sidebar background | `gray-900` | `#111827` |
| Sidebar active item bg | `brand-500` | `#6366F1` |
| Sidebar hover item bg | `gray-800` | `#1F2937` |
| Sidebar section label | `gray-500` | `#6B7280` |
| Sidebar text | `gray-300` | `#D1D5DB` |
| Heading text | `gray-900` | `#111827` |
| Body text | `gray-700` | `#374151` |
| Muted text | `gray-500` | `#6B7280` |
| Primary button | `brand-500` bg, white text | — |
| Primary button hover | `brand-600` bg | — |
| Secondary button | white bg, `gray-700` text, `gray-200` border | — |
| Destructive button | `danger-500` bg, white text | — |
| Input border | `gray-300` | — |
| Input border focus | `brand-500` | — |
| Input background | `gray-0` | — |
| Positive delta | `success-500` | +12% ↑ |
| Negative delta | `danger-500` | -3% ↓ |
| Neutral delta | `gray-500` | 0% → |

### Provider Color Coding (consistent across all charts)

```css
--color-aws:   #FF9900   /* AWS orange */
--color-azure: #0078D4   /* Azure blue */
--color-gcp:   #34A853   /* GCP green */
```

### Cap Progress Bar Colors

```css
/* < 75%  */ --cap-healthy: #22C55E
/* 75-89% */ --cap-warning: #F59E0B
/* 90-99% */ --cap-critical: #EF4444
/* ≥ 100% */ --cap-breach:  #991B1B   /* dark red */
```

---

## 2. Typography

### Font Family

```css
/* Primary — all UI text */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

/* Monospace — credentials, API keys, code blocks */
font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
```

**Load:** Google Fonts — `Inter` weights 400, 500, 600, 700. `JetBrains Mono` weight 400.

### Type Scale

| Token | Size | Line height | Weight | Use |
|-------|------|-------------|--------|-----|
| `text-xs` | 11px | 16px | 400/500 | Table meta, timestamps, badges |
| `text-sm` | 13px | 20px | 400 | Table body, helper text, labels |
| `text-base` | 14px | 20px | 400/500 | Default body, form labels |
| `text-md` | 15px | 24px | 500 | Card labels, nav items |
| `text-lg` | 18px | 28px | 600 | Card section headings |
| `text-xl` | 20px | 28px | 600 | Page sub-headings |
| `text-2xl` | 24px | 32px | 700 | Page titles |
| `text-3xl` | 30px | 36px | 700 | KPI numbers (MTD spend etc.) |
| `text-4xl` | 36px | 44px | 700 | Scorecard dial number |
| `text-5xl` | 48px | 56px | 800 | Hero numbers on overview |

### Font Weight Rules

```
400 — descriptive text, table rows, helper/muted
500 — interactive elements, card labels, nav items
600 — section headings, card titles, button text
700 — page headings, KPI labels
800 — big money numbers only (dashboard KPIs)
```

### Number Formatting

- Currency: `$12,453.20` — always use org's currency symbol from `/me`
- Large: `$1.2M` for ≥ 1M, `$14.2k` for ≥ 10k, full below 10k
- Delta: `+12.4%` (always include sign), `−3.2%` (use minus sign not hyphen)
- Dates: `Nov 13, 2026` for display, `2026-11-13` for data attrs

---

## 3. Spacing System

Tailwind's default scale mapped to meaning:

```
4px   (space-1)  — icon padding, dense badge spacing
8px   (space-2)  — icon-to-label gap, tight list items
12px  (space-3)  — input padding, compact rows
16px  (space-4)  — card internal padding (default)
20px  (space-5)  — card section gap
24px  (space-6)  — section spacing within a page
32px  (space-8)  — card-to-card gap in a grid
48px  (space-12) — section-to-section gap
64px  (space-16) — page-level padding (desktop)
```

**Rule:** Never use arbitrary pixel values. Always map to this scale.

---

## 4. Border Radius

```css
--radius-sm:   4px    /* badges, chips, tooltips */
--radius-md:   8px    /* buttons, inputs, dropdowns */
--radius-lg:   12px   /* cards, panels, modals */
--radius-xl:   16px   /* large feature cards, drawers */
--radius-full: 9999px /* avatar, status dot, pill badge */
```

---

## 5. Shadow Scale

```css
--shadow-xs: 0 1px 2px rgba(0,0,0,0.05);               /* input, badge */
--shadow-sm: 0 1px 3px rgba(0,0,0,0.08),               /* default card */
             0 1px 2px rgba(0,0,0,0.04);
--shadow-md: 0 4px 6px rgba(0,0,0,0.07),               /* card hover */
             0 2px 4px rgba(0,0,0,0.05);
--shadow-lg: 0 10px 15px rgba(0,0,0,0.08),             /* dropdown, popover */
             0 4px 6px rgba(0,0,0,0.04);
--shadow-xl: 0 20px 25px rgba(0,0,0,0.10),             /* modal, command palette */
             0 10px 10px rgba(0,0,0,0.04);
```

Cards get `shadow-sm` by default, `shadow-md` on hover.

---

## 6. Layout Grid

### Sidebar

```
Width expanded:   240px   (fixed, not scrollable)
Width collapsed:  64px    (icon-only mode)
Transition:       width 200ms ease-in-out
Breakpoint:       <1024px → auto-collapse
                  <768px  → hidden (hamburger menu)
```

### Top Bar

```
Height:     60px
Position:   sticky top-0, z-50
Background: rgba(249,250,251,0.9) backdrop-blur-sm
Border:     1px solid gray-200 bottom
```

### Content Area

```
Margin-left:    240px (or 64px collapsed)
Padding:        24px (desktop), 16px (tablet)
Max-width:      none (full width up to 1600px)
```

### Card Grid (dashboard)

```
KPI row:       4 columns  (1fr 1fr 1fr 1fr)
Main area:     2/3 chart + 1/3 table
Lower row:     3 equal columns
Responsive:    <1280px → 2-col KPI, 1-col below
               <768px  → 1-col all
Gap:           24px
```

---

## 7. Component Specifications

### Card

```
background:    white
border:        1px solid gray-200
border-radius: radius-lg (12px)
shadow:        shadow-sm
padding:       24px
hover:         shadow-md (on interactive cards)

Card Header:
  font:        text-sm, weight-500, gray-600
  margin-bottom: 4px

Card Value:
  font:        text-3xl, weight-700, gray-900

Card Delta:
  font:        text-sm, weight-500
  success:     success-500
  danger:      danger-500
```

### KPI Card (specific)

```
Structure:
  ┌──────────────────────────────┐
  │  Label (gray-500, text-sm)   │
  │  $12,453  +8.2% ↑            │
  │  ░░░░░░░░░░░░ (sparkline)    │
  │  "vs last month"  (gray-400) │
  └──────────────────────────────┘

Sparkline: 20px height, brand-500 color, no axes
Delta badge: inline right of value
             green bg (success-50) if positive
             red bg (danger-50) if negative
```

### Button

```
/* Primary */
bg: brand-500 | hover: brand-600 | active: brand-700
text: white, weight-500, text-sm
padding: 8px 16px
radius: radius-md (8px)
height: 36px

/* Secondary */
bg: white | hover: gray-100 | active: gray-200
text: gray-700, weight-500
border: 1px solid gray-200
Same sizing

/* Destructive */
bg: danger-500 | hover: danger-600
text: white

/* Ghost */
bg: transparent | hover: gray-100
text: gray-700
No border

/* Icon Button */
width: 36px, height: 36px, padding: 8px
radius: radius-md

/* Sizes */
sm: height 28px, padding 6px 10px, text-xs
md: height 36px, padding 8px 16px, text-sm  ← DEFAULT
lg: height 44px, padding 10px 20px, text-base

/* Disabled state */
opacity: 0.4, cursor: not-allowed
```

### Input / Form

```
/* Input */
height:        36px
padding:       8px 12px
border:        1px solid gray-300
border-radius: radius-md (8px)
background:    white
font:          text-sm, gray-900

focus:
  border-color: brand-500
  outline: 2px solid brand-100 (focus ring)
  
error:
  border-color: danger-500
  outline: 2px solid danger-100

/* Label */
text-sm, weight-500, gray-700
margin-bottom: 4px

/* Helper text */
text-xs, gray-500
margin-top: 4px

/* Error text */
text-xs, danger-500
margin-top: 4px
```

### Badge

```
/* Status */
Healthy / Active:   success-100 bg, success-700 text
Warning:            warning-100 bg, warning-700 text
Error / Failed:     danger-100  bg, danger-700  text
Neutral / Inactive: gray-100    bg, gray-600    text

/* Role */
Owner:  brand-100 bg, brand-700 text
Admin:  gray-800  bg, white     text  (dark)
Editor: gray-100  bg, gray-700  text
Viewer: gray-50   bg, gray-500  text

Font:    text-xs, weight-500
Padding: 2px 8px
Radius:  radius-sm (4px)
```

### Table

```
Header row:
  background: gray-50
  text: text-xs, weight-600, gray-500, UPPERCASE
  padding: 12px 16px
  border-bottom: 1px solid gray-200

Body row:
  background: white
  hover: gray-50
  padding: 12px 16px
  border-bottom: 1px solid gray-100
  font: text-sm, gray-700

Sortable column:
  cursor: pointer
  Show ↑↓ arrows on hover, filled arrow on active sort

Striped variant (optional):
  Every other row: gray-50/50
```

### Progress Bar (Budget Cap)

```
Container:
  height: 8px
  background: gray-100
  border-radius: radius-full

Fill:
  border-radius: radius-full
  transition: width 400ms ease
  
  < 75%:   success-500 (#22C55E)
  75-89%:  warning-500 (#F59E0B)
  90-99%:  danger-400  (#F87171)
  ≥ 100%:  danger-600  (#DC2626)
  > 125%:  #7F1D1D     (very dark red, overflow)
```

### Status Dot (animated pulse)

```
/* Healthy / Syncing */
width: 8px, height: 8px
border-radius: full
background: success-500
animation: pulse 2s infinite

/* Degraded / Warning */
background: warning-500 (no pulse)

/* Error */
background: danger-500 (no pulse)

/* Unknown / Offline */
background: gray-400 (no pulse)
```

### Toast / Notification

```
Position:   fixed bottom-right, 24px margin
Width:      360px
Padding:    16px
Radius:     radius-lg
Shadow:     shadow-xl
Animation:  slide-up 200ms ease + fade-in

Types:
  success: success-50 bg, success-700 border-left 4px, success icon
  warning: warning-50 bg, warning-500 border-left
  error:   danger-50  bg, danger-500  border-left
  info:    info-50    bg, info-500    border-left

Auto-dismiss: 5s (success/info), never (error — user must close)
```

### Sidebar Nav Item

```
/* Default */
padding: 8px 12px
border-radius: radius-md
font: text-sm, weight-500
color: gray-400
icon color: gray-500
cursor: pointer

/* Hover */
background: gray-800
color: gray-100
icon: gray-300

/* Active */
background: brand-500 (or brand-600 for darker depth)
color: white
icon: white

/* Section Label */
text-xs, weight-600, gray-500, UPPERCASE
padding: 16px 12px 4px
letter-spacing: 0.05em
```

### Modal / Dialog

```
Overlay:    rgba(0,0,0,0.4) backdrop-blur-sm
Container:  white bg, radius-xl (16px), shadow-xl
Width:      480px (small), 640px (medium), 768px (large)
Padding:    24px
Animation:  scale(0.95)→scale(1) + fade 150ms

Header:     text-lg weight-600 + X close button
Divider:    1px gray-200
Footer:     right-aligned: [Cancel] [Confirm] buttons
```

### Drawer (slide-in panel)

```
Position: fixed right-0, full height
Width:    480px (default), 640px (large variant)
Shadow:   shadow-xl left side
Animation: translateX(100%)→translateX(0) 250ms ease
Overlay:  same as modal
```

### Skeleton Loader

```
Background:  linear-gradient(90deg, gray-100, gray-200, gray-100)
Animation:   shimmer left-to-right 1.5s infinite
Border-radius: match the element it replaces

KPI skeleton: 
  - line 1: h-4 w-20 (label)
  - line 2: h-8 w-32 (value)
  - line 3: h-3 w-24 (delta)
```

---

## 8. Icon System

**Library:** Lucide React (consistent stroke weight, matches the minimal aesthetic of all references)

**Sizes:**
```
16px — inline in text, table cells
20px — sidebar nav icons, button icons
24px — card action icons, top bar
32px — empty state illustrations (use Lucide + custom tint)
48px — onboarding wizard step icons
```

**Provider logos:** Use official SVG logos (`aws.svg`, `azure.svg`, `gcp.svg`) at 20×20px with rounded borders. Store in `/public/providers/`.

**Key icons per section:**
```
Dashboard:        LayoutDashboard
Costs:            DollarSign
Accounts:         Cloud
Forecast:         TrendingUp
Commitments:      BadgePercent
Recommendations:  Lightbulb
Scorecard:        Award
Resources:        Server
Budget Caps:      Target
Alerts:           Bell / BellRing (unread)
Virtual Tags:     Tag
Metrics:          BarChart2
Assistant:        Sparkles
Reports:          FileText
Team:             Users
Notifications:    Settings2
Webhooks:         Webhook
API Keys:         Key
Org Settings:     Building2
Profile:          UserCircle
Sync:             RefreshCw (animate rotate on syncing)
Export:           Download
Error:            AlertCircle
Success:          CheckCircle2
Warning:          AlertTriangle
Info:             Info
```

---

## 9. Chart Design Rules

**Library:** Recharts

### Colors

```js
// All charts — provider series
const PROVIDER_COLORS = {
  aws:   '#FF9900',
  azure: '#0078D4',
  gcp:   '#34A853',
  all:   '#6366F1',  // combined/total = brand
}

// Generic series palette (non-provider)
const CHART_PALETTE = [
  '#6366F1', // brand
  '#22C55E', // success
  '#F59E0B', // warning
  '#3B82F6', // info
  '#EC4899', // pink
  '#8B5CF6', // violet
]
```

### Style rules

```
Grid lines:     stroke gray-100, strokeDasharray "4 4" (subtle)
Axis labels:    text-xs, gray-500, Inter
Tooltip:        white bg, shadow-lg, border gray-200, radius-md
                font: text-sm, gray-700
Animated:       isAnimationActive={true} (all charts)
Responsive:     Wrap every chart in <ResponsiveContainer>

Bar charts:
  radius: [4,4,0,0] (rounded top)
  fill: provider color or chart palette
  hover: opacity 0.8

Line charts:
  strokeWidth: 2.5
  dot: false (no dots on line, only on hover)
  activeDot: radius 5, fill brand-500

Area charts:
  strokeWidth: 2
  fill: gradient — top 20% opacity, bottom 0%
  
Donut/Pie:
  innerRadius: 55-65% (donut, not full pie)
  stroke: none
  
Radial (scorecard):
  startAngle: 180, endAngle: -180
  Custom label centered: score number
```

---

## 10. Dark Mode Tokens (optional — ship later)

```css
/* When dark mode is active (.dark class on <html>) */
--bg-page:   #0F172A     /* slate-900 */
--bg-card:   #1E293B     /* slate-800 */
--bg-hover:  #334155     /* slate-700 */
--border:    #334155
--text-head: #F1F5F9
--text-body: #CBD5E1
--text-mute: #64748B
/* Accent colors stay the same — they already work on dark */
```

---

## 11. Animation & Transition Rules

```css
/* Default transitions */
--transition-fast:    100ms ease-in-out   /* hover states */
--transition-normal:  200ms ease-in-out   /* sidebar collapse, button states */
--transition-slow:    350ms ease-in-out   /* modal/drawer open */
--transition-chart:   400ms ease          /* progress bars, chart mounts */

/* Specific */
Sidebar collapse:    width 200ms ease
Card hover shadow:   box-shadow 150ms ease
Toast slide-up:      transform + opacity 200ms ease
Skeleton shimmer:    background-position 1.5s ease infinite
Sync icon spin:      transform rotate(360deg) 1s linear infinite
Status pulse:        opacity 1→0.4→1 2s ease infinite
```

---

## 12. Z-Index Scale

```
z-0    — base content
z-10   — cards, raised elements
z-20   — sticky table headers
z-30   — top bar (sticky)
z-40   — sidebar (fixed)
z-50   — dropdowns, popovers, tooltips
z-60   — drawers, side panels
z-70   — modal overlay
z-80   — modal content
z-90   — toasts
z-100  — command palette (⌘K)
```

---

## 13. Tailwind Config (`tailwind.config.ts`)

```ts
import type { Config } from 'tailwindcss'

export default {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#EEF2FF',
          100: '#E0E7FF',
          500: '#6366F1',
          600: '#4F46E5',
          700: '#4338CA',
        },
        aws:   '#FF9900',
        azure: '#0078D4',
        gcp:   '#34A853',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        'xs':  ['11px', '16px'],
        'sm':  ['13px', '20px'],
        'base':['14px', '20px'],
        'md':  ['15px', '24px'],
        'lg':  ['18px', '28px'],
        'xl':  ['20px', '28px'],
        '2xl': ['24px', '32px'],
        '3xl': ['30px', '36px'],
        '4xl': ['36px', '44px'],
        '5xl': ['48px', '56px'],
      },
      borderRadius: {
        'sm': '4px',
        'md': '8px',
        'lg': '12px',
        'xl': '16px',
      },
      boxShadow: {
        'xs': '0 1px 2px rgba(0,0,0,0.05)',
        'sm': '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04)',
        'md': '0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.05)',
        'lg': '0 10px 15px rgba(0,0,0,0.08), 0 4px 6px rgba(0,0,0,0.04)',
        'xl': '0 20px 25px rgba(0,0,0,0.10), 0 10px 10px rgba(0,0,0,0.04)',
      },
      animation: {
        'shimmer':    'shimmer 1.5s infinite',
        'spin-slow':  'spin 1s linear infinite',
        'pulse-slow': 'pulse 2s ease-in-out infinite',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
} satisfies Config
```

---

## 14. `globals.css` (essentials)

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --sidebar-width: 240px;
    --sidebar-collapsed: 64px;
    --topbar-height: 60px;
  }

  * { box-sizing: border-box; }

  html {
    font-family: 'Inter', sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
  }

  body {
    background: #F9FAFB;  /* gray-50 */
    color: #374151;        /* gray-700 */
    font-size: 14px;
    line-height: 20px;
  }

  /* Number / currency — tabular nums so columns align */
  .tabular { font-variant-numeric: tabular-nums; }

  /* Monospace for credentials, API keys */
  .mono { font-family: 'JetBrains Mono', monospace; }
}

@layer utilities {
  .scrollbar-thin {
    scrollbar-width: thin;
    scrollbar-color: #E5E7EB transparent;
  }

  @keyframes shimmer {
    0%   { background-position: -400px 0; }
    100% { background-position: 400px 0; }
  }
}
```

---

## 15. Quick Reference Card

```
COLORS          |  FONTS              |  SPACING
────────────────|─────────────────────|──────────
Page bg  F9FAFB | Sans: Inter         | Base unit: 4px
Card     FFFFFF | Mono: JetBrains     | Card pad: 24px
Sidebar  111827 | Weights: 400–800    | Gap: 24px
Accent   6366F1 | Numbers: tabular    | Section: 32px
Success  22C55E | Base size: 14px     |
Warning  F59E0B | Headings: 24–48px   | RADIUS
Danger   EF4444 | KPI nums: 30–48px   | Btn/Input: 8px
AWS      FF9900 |                     | Card: 12px
Azure    0078D4 | ICONS               | Large: 16px
GCP      34A853 | Lucide React        | Pill: 9999px
                | 16/20/24/32/48px    |
```

---

Everything above maps directly to shadcn/ui's CSS variable system — when you init the project with `npx shadcn@latest init`, paste these tokens into `globals.css` as `--background`, `--foreground`, `--primary`, etc. and you get the entire component library pre-themed with zero overrides needed per-component.