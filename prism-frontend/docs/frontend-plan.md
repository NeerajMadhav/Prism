# PRISM Frontend — Complete Implementation Plan
> **Version 2 — End-to-End, No Gaps**
>
> **Stack:** Next.js 15 (App Router) · TypeScript · Tailwind CSS · shadcn/ui · Recharts · TanStack Query v5 · Zustand v4 · React Hook Form + Zod · Lucide React · date-fns + date-fns-tz · native WebSocket · Sonner toasts
>
> **Backend:** FastAPI (`NEXT_PUBLIC_API_URL`) — all 23 route groups, WebSocket, health endpoint
>
> **Principles:** real-user first · minimal · premium · real-time · role-gated · extendable · maintainable · accessible

---

## TABLE OF CONTENTS

1. [Project Bootstrap & Configuration](#1-project-bootstrap--configuration)
2. [Complete Folder Structure](#2-complete-folder-structure)
3. [Design System & Global Styles](#3-design-system--global-styles)
4. [Type System (all entities)](#4-type-system)
5. [API Client Layer (all modules)](#5-api-client-layer)
6. [Custom Hooks (all)](#6-custom-hooks)
7. [State Management](#7-state-management)
8. [Auth Layer & Route Guards](#8-auth-layer--route-guards)
9. [App Shell Components](#9-app-shell-components)
10. [WebSocket & Real-time Layer](#10-websocket--real-time-layer)
11. [Shared / Reusable Components](#11-shared--reusable-components)
12. [All Screen Implementations](#12-all-screen-implementations)
13. [Form Patterns & Validation](#13-form-patterns--validation)
14. [Data Flow & Backend Integration](#14-data-flow--backend-integration)
15. [Error Handling & Edge Cases](#15-error-handling--edge-cases)
16. [Transitions & Animations](#16-transitions--animations)
17. [Performance & Caching](#17-performance--caching)
18. [Accessibility](#18-accessibility)
19. [Security](#19-security)
20. [Mobile Responsiveness](#20-mobile-responsiveness)
21. [Testing Strategy](#21-testing-strategy)
22. [Build, Environment & Deployment](#22-build-environment--deployment)
23. [Implementation Order (5-Phase Sprint Map)](#23-implementation-order)

---

## 1. Project Bootstrap & Configuration

### Step 1.1 — Scaffold
- `npx create-next-app@latest prism-frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"`

### Step 1.2 — Dependencies
**UI:** `shadcn/ui` (init), all Radix primitives, `tailwindcss-animate`, `next-themes`, `sonner`, `cmdk`

**Data:** `@tanstack/react-query` v5, `@tanstack/react-query-devtools`, `axios`, `zustand`, `date-fns`, `date-fns-tz`

**Forms:** `react-hook-form`, `@hookform/resolvers`, `zod`

**Charts:** `recharts`

**Utils:** `lucide-react`, `clsx`, `tailwind-merge`, `class-variance-authority`

**Calendar:** `react-day-picker@8.x` — install via `npx shadcn@latest add calendar` (not manually, to get the compatible version)

**Drag-and-drop:** `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities` (virtual tag rule reordering)

**Dev:** `vitest`, `@vitejs/plugin-react`, `jsdom`, `@testing-library/react`, `@testing-library/user-event`, `msw`, `prettier`, `prettier-plugin-tailwindcss`, `@next/bundle-analyzer`

### Step 1.3 — shadcn/ui components to add
`button card input label badge dialog drawer sheet tooltip dropdown-menu popover select tabs table progress separator switch checkbox textarea alert skeleton avatar command scroll-area calendar`

### Step 1.4 — Environment variables

| Variable | Dev | Prod |
|----------|-----|------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | `https://api.yourprism.com` |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000` | `wss://api.yourprism.com` |
| `NEXT_PUBLIC_APP_URL` | `http://localhost:3000` | `https://app.yourprism.com` |

### Step 1.5 — `next.config.ts`
- Rewrite `/api/:path*` → `NEXT_PUBLIC_API_URL/:path*` (dev proxy, eliminates CORS)
- `images.remotePatterns`: `lh3.googleusercontent.com` (Google avatars)
- `headers()`: add `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=()`, `Strict-Transport-Security` (prod only)

### Step 1.6 — `tsconfig.json`
- `strict: true`
- `noUncheckedIndexedAccess: true`
- Path alias `@/*` → `./src/*`

### Step 1.7 — `prettier.config.js`
- `plugins: ['prettier-plugin-tailwindcss']` — auto-sorts Tailwind classes

### Step 1.8 — `.eslintrc.json`
- Extends `next/core-web-vitals`, `prettier`
- Rule: `no-console: warn` (use structured logger in prod)

---

## 2. Complete Folder Structure

```
prism-frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx                       ← Root: redirect('/dashboard')
│   │   │
│   │   ├── (auth)/                        ← Route group: NO sidebar, NO auth guard
│   │   │   ├── login/page.tsx
│   │   │   ├── signup/page.tsx
│   │   │   ├── verify-email/page.tsx
│   │   │   ├── forgot-password/page.tsx
│   │   │   ├── reset-password/page.tsx
│   │   │   ├── accept-invite/page.tsx
│   │   │   └── oauth-callback/page.tsx    ← Google OAuth exchange + redirect
│   │   │
│   │   ├── (app)/                         ← Route group: HAS sidebar + auth guard
│   │   │   ├── layout.tsx                 ← App shell
│   │   │   ├── loading.tsx                ← App-wide fallback skeleton
│   │   │   ├── onboarding/page.tsx        ← Full-screen wizard, no sidebar
│   │   │   ├── dashboard/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   ├── costs/
│   │   │   │   ├── page.tsx               ← Tab-based cost explorer (useSearchParams in Suspense)
│   │   │   │   └── loading.tsx
│   │   │   ├── accounts/
│   │   │   │   ├── page.tsx               ← Account list
│   │   │   │   ├── loading.tsx
│   │   │   │   ├── connect/page.tsx       ← Connect wizard
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx           ← Account detail + sync logs
│   │   │   │       └── loading.tsx
│   │   │   ├── forecasts/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   ├── commitments/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   ├── recommendations/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   ├── scorecard/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   ├── resources/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   ├── caps/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   ├── alerts/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   ├── virtual-tags/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   ├── metrics/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   ├── assistant/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   ├── reports/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   └── settings/
│   │   │       ├── layout.tsx             ← Settings secondary sidebar
│   │   │       ├── loading.tsx            ← Covers all settings sub-routes
│   │   │       ├── team/page.tsx
│   │   │       ├── notifications/page.tsx
│   │   │       ├── webhooks/page.tsx
│   │   │       ├── api-keys/page.tsx
│   │   │       ├── org/page.tsx
│   │   │       ├── profile/page.tsx
│   │   │       └── llm/page.tsx           ← Admin only
│   │   │
│   │   ├── layout.tsx                     ← Root layout (providers + fonts)
│   │   ├── providers.tsx                  ← All React context providers
│   │   ├── globals.css
│   │   ├── not-found.tsx                  ← 404 page
│   │   └── error.tsx                      ← Root error boundary
│   │
│   ├── components/
│   │   ├── ui/                            ← shadcn/ui (DO NOT edit manually)
│   │   │
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── SidebarItem.tsx
│   │   │   ├── TopBar.tsx
│   │   │   ├── UserMenu.tsx
│   │   │   ├── NotificationsPanel.tsx
│   │   │   ├── CommandPalette.tsx
│   │   │   ├── HealthBanner.tsx
│   │   │   ├── OfflineBanner.tsx          ← navigator.onLine + online/offline events
│   │   │   ├── SettingsSubNav.tsx
│   │   │   └── AppSkeleton.tsx
│   │   │
│   │   ├── auth/
│   │   │   ├── AuthBootstrap.tsx
│   │   │   ├── AuthSplitLayout.tsx
│   │   │   ├── LoginForm.tsx
│   │   │   ├── SignupForm.tsx
│   │   │   ├── SignupStep1.tsx            ← Account details
│   │   │   ├── SignupStep2.tsx            ← Org details
│   │   │   ├── SignupStep3.tsx            ← Verify email
│   │   │   ├── GoogleOAuthButton.tsx
│   │   │   └── PasswordStrengthBar.tsx
│   │   │
│   │   ├── onboarding/
│   │   │   ├── OnboardingWizard.tsx
│   │   │   ├── OnboardingStep.tsx
│   │   │   └── StepIndicator.tsx
│   │   │
│   │   ├── dashboard/
│   │   │   ├── KpiCardRow.tsx
│   │   │   ├── SyncStatusBar.tsx
│   │   │   ├── SpendByDayChart.tsx
│   │   │   ├── TopServicesTable.tsx
│   │   │   ├── BudgetCapsSummary.tsx
│   │   │   ├── ForecastSummary.tsx
│   │   │   ├── ScorecardSummary.tsx
│   │   │   └── RecommendationsList.tsx
│   │   │
│   │   ├── costs/
│   │   │   ├── CostFilters.tsx
│   │   │   ├── ByDayChart.tsx
│   │   │   ├── ByServiceTable.tsx
│   │   │   ├── ByTagChart.tsx
│   │   │   ├── TopServicesChart.tsx
│   │   │   └── ExportCsvButton.tsx
│   │   │
│   │   ├── accounts/
│   │   │   ├── AccountCard.tsx
│   │   │   ├── AccountDetailHeader.tsx
│   │   │   ├── ConnectWizard.tsx
│   │   │   ├── ProviderSelector.tsx
│   │   │   ├── CredentialForm/
│   │   │   │   ├── index.tsx
│   │   │   │   ├── AwsCredentialForm.tsx
│   │   │   │   ├── AzureCredentialForm.tsx
│   │   │   │   └── GcpCredentialForm.tsx
│   │   │   ├── TestConnectionButton.tsx
│   │   │   └── SyncLogsTimeline.tsx
│   │   │
│   │   ├── caps/
│   │   │   ├── CapRow.tsx
│   │   │   ├── CapProgressBar.tsx
│   │   │   ├── CapFormDrawer.tsx
│   │   │   └── CapDetailPanel.tsx
│   │   │
│   │   ├── alerts/
│   │   │   ├── AlertRow.tsx
│   │   │   ├── AlertDetailDrawer.tsx
│   │   │   ├── AlertBadge.tsx
│   │   │   └── SnoozeMenu.tsx
│   │   │
│   │   ├── scorecard/
│   │   │   ├── ScoreGauge.tsx
│   │   │   ├── ScoreMetricRow.tsx
│   │   │   └── ExecutiveView.tsx
│   │   │
│   │   ├── commitments/
│   │   │   └── CommitmentRow.tsx
│   │   │
│   │   ├── recommendations/
│   │   │   ├── RecCard.tsx
│   │   │   └── ExplainDrawer.tsx
│   │   │
│   │   ├── virtual-tags/
│   │   │   ├── RuleRow.tsx
│   │   │   ├── RuleEditorDrawer.tsx
│   │   │   └── ApplyProgressDrawer.tsx
│   │   │
│   │   ├── metrics/
│   │   │   ├── MetricCard.tsx
│   │   │   ├── IngestValueModal.tsx
│   │   │   └── UnitEconomicsTable.tsx
│   │   │
│   │   ├── assistant/
│   │   │   ├── ChatMessage.tsx
│   │   │   └── ChatInput.tsx
│   │   │
│   │   ├── settings/
│   │   │   ├── InviteMemberDrawer.tsx
│   │   │   ├── MemberRow.tsx
│   │   │   ├── WebhookFormDrawer.tsx
│   │   │   └── ApiKeyCreateModal.tsx
│   │   │
│   │   ├── charts/
│   │   │   ├── AreaChart.tsx
│   │   │   ├── BarChart.tsx
│   │   │   ├── LineChart.tsx
│   │   │   ├── DonutChart.tsx
│   │   │   ├── RadialGauge.tsx
│   │   │   ├── Sparkline.tsx
│   │   │   └── ChartTooltip.tsx
│   │   │
│   │   └── common/
│   │       ├── DataCard.tsx
│   │       ├── DeltaBadge.tsx
│   │       ├── ProviderBadge.tsx
│   │       ├── StatusDot.tsx
│   │       ├── DataFreshness.tsx
│   │       ├── EstimatedBadge.tsx
│   │       ├── EmptyState.tsx
│   │       ├── ErrorState.tsx
│   │       ├── PageHeader.tsx
│   │       ├── SectionHeader.tsx
│   │       ├── RoleGate.tsx
│   │       ├── ConfirmDialog.tsx
│   │       ├── CopyBlock.tsx
│   │       ├── SortableTable.tsx
│   │       ├── DateRangePicker.tsx
│   │       ├── Pagination.tsx
│   │       └── LoadingSkeleton.tsx
│   │
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts              ← Axios + 401 silent-refresh interceptor
│   │   │   ├── auth.ts
│   │   │   ├── org.ts
│   │   │   ├── team.ts
│   │   │   ├── accounts.ts
│   │   │   ├── costs.ts
│   │   │   ├── caps.ts
│   │   │   ├── alerts.ts
│   │   │   ├── notifications.ts
│   │   │   ├── reports.ts
│   │   │   ├── recommendations.ts
│   │   │   ├── forecasts.ts
│   │   │   ├── commitments.ts
│   │   │   ├── scorecard.ts
│   │   │   ├── resources.ts
│   │   │   ├── virtual-tags.ts
│   │   │   ├── webhooks.ts
│   │   │   ├── llm.ts
│   │   │   ├── metrics.ts
│   │   │   ├── api-keys.ts
│   │   │   └── health.ts
│   │   │
│   │   ├── ws/
│   │   │   ├── wsClient.ts            ← Singleton, exponential reconnect
│   │   │   └── wsEvents.ts            ← Event type union
│   │   │
│   │   ├── auth/
│   │   │   ├── tokens.ts              ← In-memory access + sessionStorage refresh
│   │   │   └── guards.ts              ← Programmatic route protection helpers
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAuth.ts             ← useMe, useLogin, useLogout, useSignup
│   │   │   ├── useOrg.ts              ← useOrg, useUpdateOrg
│   │   │   ├── useRole.ts             ← useRole, useHasRole, useIsAtLeast
│   │   │   ├── useAccounts.ts         ← useAccounts, useAccount, useSyncLogs
│   │   │   ├── useCosts.ts            ← useCostSummary, useCostsByDay, etc.
│   │   │   ├── useCaps.ts             ← useCaps, useCap, useCreateCap, etc.
│   │   │   ├── useAlerts.ts           ← useAlerts, useAlertsCount, useAcknowledge
│   │   │   ├── useForecasts.ts
│   │   │   ├── useCommitments.ts
│   │   │   ├── useRecommendations.ts
│   │   │   ├── useScorecard.ts
│   │   │   ├── useResources.ts
│   │   │   ├── useVirtualTags.ts
│   │   │   ├── useMetrics.ts
│   │   │   ├── useNotifications.ts
│   │   │   ├── useReports.ts
│   │   │   ├── useWebhooks.ts
│   │   │   ├── useApiKeys.ts
│   │   │   ├── useLlm.ts
│   │   │   ├── useTeam.ts
│   │   │   ├── useWebSocket.ts
│   │   │   ├── useHealth.ts
│   │   │   ├── useCommandPalette.ts
│   │   │   └── useDebounce.ts
│   │   │
│   │   ├── utils/
│   │   │   ├── cn.ts                  ← clsx + twMerge
│   │   │   ├── currency.ts            ← formatCurrency(amount, currency, compact?)
│   │   │   ├── dates.ts               ← formatDate, formatRelative, toOrgTz
│   │   │   ├── delta.ts               ← formatDelta, getDeltaDirection
│   │   │   ├── providers.ts           ← getProviderColor, getProviderLabel
│   │   │   ├── errors.ts              ← handleApiError, extractErrorMessage
│   │   │   └── download.ts            ← triggerCsvDownload
│   │   │
│   │   ├── store/
│   │   │   ├── authStore.ts           ← user, org, role
│   │   │   ├── wsStore.ts             ← connected, lastSyncEvent
│   │   │   └── uiStore.ts             ← sidebarCollapsed, commandPaletteOpen
│   │   │
│   │   ├── query/
│   │   │   ├── queryClient.ts
│   │   │   └── keys.ts                ← All query key factories
│   │   │
│   │   └── constants/
│   │       ├── routes.ts
│   │       ├── providers.ts
│   │       └── roles.ts
│   │
│   ├── types/
│   │   ├── api.ts                     ← Generic wrappers (ApiError, Paginated<T>)
│   │   ├── auth.ts
│   │   ├── org.ts
│   │   ├── team.ts
│   │   ├── accounts.ts
│   │   ├── costs.ts
│   │   ├── caps.ts
│   │   ├── alerts.ts
│   │   ├── notifications.ts
│   │   ├── reports.ts
│   │   ├── forecasts.ts
│   │   ├── commitments.ts
│   │   ├── recommendations.ts
│   │   ├── scorecard.ts
│   │   ├── resources.ts
│   │   ├── virtual-tags.ts
│   │   ├── metrics.ts
│   │   ├── webhooks.ts
│   │   ├── llm.ts
│   │   ├── api-keys.ts
│   │   └── ws.ts
│   │
│   ├── middleware.ts                  ← Edge middleware (session guard)
│   │
│   └── test/
│       ├── setup.ts
│       ├── handlers.ts                ← MSW request handlers
│       └── utils.tsx                  ← renderWithProviders helper
│
├── public/
│   ├── providers/
│   │   ├── aws.svg
│   │   ├── azure.svg
│   │   └── gcp.svg
│   └── logo.svg
│
├── tailwind.config.ts
├── tsconfig.json
├── next.config.ts
├── vitest.config.ts
├── prettier.config.js
├── .eslintrc.json
├── .env.local
└── .env.example
```

---

## 3. Design System & Global Styles

### Step 3.1 — Color tokens (Tailwind extend)

| Token | Hex | Use |
|-------|-----|-----|
| `brand-50` | `#EEF2FF` | Active nav bg, badge bg |
| `brand-100` | `#E0E7FF` | Hover ring |
| `brand-500` | `#6366F1` | Primary buttons, active nav, links |
| `brand-600` | `#4F46E5` | Button hover |
| `brand-700` | `#4338CA` | Button active/pressed |
| `gray-50` | `#F9FAFB` | Page canvas |
| `gray-100` | `#F3F4F6` | Table row hover, input bg |
| `gray-200` | `#E5E7EB` | Card border, divider |
| `gray-300` | `#D1D5DB` | Input border, disabled |
| `gray-400` | `#9CA3AF` | Placeholder text |
| `gray-500` | `#6B7280` | Muted text, sidebar sections |
| `gray-600` | `#4B5563` | Secondary text |
| `gray-700` | `#374151` | Body text |
| `gray-900` | `#111827` | Sidebar bg, headings |
| `aws` | `#FF9900` | AWS provider color |
| `azure` | `#0078D4` | Azure provider color |
| `gcp` | `#34A853` | GCP provider color |
| success `500` | `#22C55E` | Positive delta, healthy status |
| warning `500` | `#F59E0B` | 75–99% cap, degraded |
| danger `500` | `#EF4444` | Error, failed sync, 100%+ cap |

### Step 3.2 — Typography

**Font:** Inter (Google Fonts) — weights 400/500/600/700/800

**Mono font:** JetBrains Mono — weight 400 (credentials, API keys, code blocks)

**Scale:** 11px (xs) → 13px (sm) → 14px (base) → 15px (md) → 18px (lg) → 20px (xl) → 24px (2xl) → 30px (3xl) → 36px (4xl) → 48px (5xl)

**Rules:**
- Weight 400 — body, table rows
- Weight 500 — labels, nav items, card headers
- Weight 600 — section headings, card titles, buttons
- Weight 700 — page headings
- Weight 800 — big KPI numbers only
- Class `tabular` (`font-variant-numeric: tabular-nums`) on all numeric columns and money values

### Step 3.3 — Spacing system
4px base unit. Cards: 24px internal padding. Card grid gap: 24px. Page padding: 24px desktop, 16px tablet.

### Step 3.4 — Border radius
4px (badges/chips), 8px (buttons/inputs), 12px (cards/panels), 16px (large cards/drawers), `full` (avatar/status dot/pill)

### Step 3.5 — Shadow scale
xs (input), sm (default card), md (card hover, dropdown), lg (popover), xl (modal/command palette)

### Step 3.6 — Animations to define
- `shimmer` (skeleton loading)
- `slide-up` (toast, page mount)
- `slide-in-right` (drawer open)
- `spin-slow` (sync icon while syncing)
- `pulse-status` (healthy status dot)

### Step 3.7 — shadcn/ui CSS variables
Map all shadcn variables (`--background`, `--foreground`, `--primary`, `--border`, `--ring`, etc.) to PRISM tokens in `globals.css`. This themes all shadcn components automatically without per-component overrides.

### Step 3.8 — Dark mode tokens
Defined for `.dark` class on `<html>`. Activate via `next-themes` ThemeProvider. Dark mode: slate-900 canvas, slate-800 cards, slate-700 borders. Ship light mode first; add dark mode toggle in profile settings.

---

## 4. Type System

### Step 4.1 — `types/api.ts` (generic wrappers)
- `ApiError` — `{ detail: string | ValidationError[] }`
- `ValidationError` — `{ loc: string[]; msg: string; type: string }`
- `Paginated<T>` — `{ items: T[]; total: number; page: number; size: number }`
- `DateRange` — `{ start: string; end: string }` (ISO date strings)

### Step 4.2 — `types/auth.ts`
- `Role` — union: `'viewer' | 'editor' | 'admin' | 'owner'`
- `User` — `id, name, email, avatar_url?, email_verified, created_at`
- `Org` — `id, name, currency, timezone, feature_flags`
- `MeResponse` — `{ user: User; org: Org; role: Role }`
- `LoginRequest` — `{ email, password }`
- `LoginResponse` — `{ access_token, refresh_token, user, org, role }`
- `SignupRequest` — `{ name, email, password, org_name, currency, timezone }`

### Step 4.3 — `types/accounts.ts`
- `Provider` — `'aws' | 'azure' | 'gcp'`
- `SyncStatus` — `'pending' | 'running' | 'success' | 'failed' | 'never'`
- `CloudAccount` — `{ id, name, provider, status, last_sync_at, last_sync_status, records_synced, data_as_of, error_message?, created_at }`
- `SyncLog` — `{ id, account_id, started_at, completed_at?, status, records_synced?, error_message?, duration_ms? }`
- `ConnectRequest` — provider-specific credential shapes:
  - AWS: `{ provider: 'aws', name, role_arn, external_id, region }`
  - Azure: `{ provider: 'azure', name, tenant_id, client_id, client_secret, subscription_id }`
  - GCP: `{ provider: 'gcp', name, project_id, dataset_id, table_prefix, service_account_json }`
- `ConnectResponse` — `{ account: CloudAccount; sync_task_id: string; sync_mode: 'queued' | 'inline' }`
- `TestConnectionResponse` — `{ ok: boolean; message: string; latency_ms?: number }`

### Step 4.4 — `types/costs.ts`
- `CostView` — `'unblended' | 'amortized'`
- `CostSummary` — `{ total, mom_pct, mom_abs, is_estimate, data_as_of, currency, provider? }`
- `CostByDay` — `{ date, total, by_provider: Record<Provider, number>, is_estimate }`
- `CostByService` — `{ service, provider, total, mom_pct, mom_abs, trend: number[] }`
- `CostByTag` — `{ tag_key, tag_value, total, pct_of_total }`
- `TopService` — `{ service, provider, total, mom_pct, rank }`

### Step 4.5 — `types/caps.ts`
- `CapScope` — `'platform' | 'service' | 'account'`
- `BudgetCap` — `{ id, name, provider?, scope, service?, account_id?, amount, currency, period, thresholds: number[], current_spend, pct_used, next_threshold, last_alert_at?, created_at }`
- `CreateCapRequest` — `{ name, provider?, scope, service?, account_id?, amount, thresholds }`

### Step 4.6 — `types/alerts.ts`
- `AlertType` — `'cap_threshold' | 'sync_failure' | 'forecast_breach'`
- `AlertStatus` — `'active' | 'acknowledged' | 'snoozed'`
- `Alert` — `{ id, type, status, cap_id?, threshold_pct?, current_pct?, current_spend?, cap_amount?, provider?, scope?, triggered_at, snoozed_until?, acknowledged_at?, email_sent, teams_sent, slack_sent, webhook_sent }`
- `SnoozeRequest` — `{ until: string }` (ISO datetime)

### Step 4.7 — `types/notifications.ts`
- `NotificationSettings` — `{ alert_emails: string[], teams_webhook_url?, slack_webhook_url?, thresholds: { t75, t90, t100, t125, t150 } }`

### Step 4.8 — `types/forecasts.ts`
- `Forecast` — `{ provider, projected_total, cap_amount?, pct_of_cap?, days_elapsed, days_in_month, daily_avg, will_breach, currency, computed_at }`
- `ForecastHistory` — `{ month, provider, projected, actual?, variance_pct?, accuracy_pct?, cap_amount? }`

### Step 4.9 — `types/commitments.ts`
- `CommitmentType` — `'reserved_instance' | 'savings_plan' | 'cud'`
- `CommitmentStatus` — `'active' | 'expiring' | 'expired'`
- `Commitment` — `{ id, provider, type, resource_type, coverage_pct, utilization_pct, start_date, end_date, days_to_expiry, status, monthly_cost }`
- `CommitmentSummary` — `{ coverage_pct, utilization_pct, expiring_count, total_monthly_cost }`

### Step 4.10 — `types/recommendations.ts`
- `RecStatus` — `'open' | 'implemented' | 'rejected' | 'archived'`
- `RecConfidence` — `'high' | 'medium' | 'low'`
- `Recommendation` — `{ id, title, description, provider, region?, service, type, estimated_savings_monthly, confidence, status, created_at, resolved_at? }`

### Step 4.11 — `types/scorecard.ts`
- `ScoreGrade` — `'A' | 'B' | 'C' | 'D' | 'F'`
- `ScorecardMetric` — `{ key, label, weight_pct, score, status: 'good' | 'warning' | 'critical' }`
- `Scorecard` — `{ total_score, grade, metrics: ScorecardMetric[], computed_at, prev_score? }`
- `ScorecardExecutive` — `{ mtd_spend, forecast, scorecard_grade, savings_realized, currency }`

### Step 4.12 — `types/resources.ts`
- `Resource` — `{ id, name, type, provider, region, account_id, is_idle, idle_since?, last_active_at?, cost_per_day, tags: Record<string, string>, discovered_at }`

### Step 4.13 — `types/virtual-tags.ts`
- `ConditionType` — `'service_contains' | 'tag_equals' | 'account_is' | 'provider_is'`
- `VirtualTagRule` — `{ id, priority, tag_key, tag_value, condition_type, condition_value, created_at }`
- `VirtualTagAudit` — `{ id, rule_id, rule_tag_key, applied_by, applied_at, rows_processed, rows_updated, status, duration_ms? }`

### Step 4.14 — `types/metrics.ts`
- `MetricSource` — `'manual' | 'webhook'`
- `BusinessMetric` — `{ id, name, unit, source, description?, created_at }`
- `MetricValue` — `{ id, metric_id, value, date, note? }`
- `UnitEconomics` — `{ metric: BusinessMetric; mtd_value: number; mtd_cost: number; cost_per_unit: number; mom_unit_pct? }`

### Step 4.15 — `types/webhooks.ts`
- `OutboundWebhook` — `{ id, url, events: string[], active, signing_secret_prefix, created_at, last_delivery_at?, last_delivery_status? }`
- `CreateWebhookRequest` — `{ url, events: string[] }`

### Step 4.16 — `types/llm.ts`
- `LlmProvider` — `'openai' | 'azure_openai'`
- `LlmConfig` — `{ configured: boolean; provider?, model?, monthly_budget?, current_spend?, budget_pct? }`
- `LlmQueryRequest` — `{ question: string; context_id?: string }`
- `LlmQueryResponse` — `{ answer: string; tokens_used: number; remaining_queries_this_hour: number }`

### Step 4.17 — `types/api-keys.ts`
- `ApiKeyScope` — `'cost.read' | 'alerts.read' | 'reports.read' | 'webhooks.write'`
- `ApiKey` — `{ id, name, prefix, scopes: ApiKeyScope[], created_at, last_used_at? }`
- `CreateApiKeyResponse` — `{ key: ApiKey; raw_key: string }` (raw_key shown ONCE)

### Step 4.18 — `types/team.ts`
- `TeamMember` — `{ id, user_id, name, email, avatar_url?, role: Role, joined_at }`
- `Invite` — `{ id, email, role, invited_by, expires_at }`

### Step 4.19 — `types/ws.ts`
- `WsEventType` — `'connected' | 'ping' | 'sync.complete'`
- `WsEvent` — `{ event: WsEventType; org_id: string; timestamp: string; data: Record<string, unknown> }`
- `SyncCompleteData` — `{ provider: Provider; account_id: string; account_name: string; records: number; duration_ms: number }`

---

## 5. API Client Layer

### Step 5.1 — `lib/api/client.ts`
Axios instance: baseURL = `NEXT_PUBLIC_API_URL/v1`, timeout 30s, `Content-Type: application/json`

**Request interceptor:** Attach `Authorization: Bearer <access_token>` from in-memory token store

**Response interceptor (401 → silent refresh):**
1. If response is 401 AND request was not already retried:
2. If a refresh is already in-flight, queue the request and wait
3. POST `/auth/refresh` with refresh token from sessionStorage
4. On success: update in-memory access token, replay all queued requests
5. On failure: `clearTokens()`, clear Zustand auth, redirect to `/login?from=<current_path>`

**Rate limit interceptor (429):**
- Read `Retry-After` header
- If present, wait that many seconds then retry once automatically
- If still 429, surface `toast.error("Rate limit reached. Try again in Xs.")`

### Step 5.2 — `lib/api/auth.ts`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `signup(body)` | POST `/auth/signup` | Create user + org |
| `verifyEmail(token)` | POST `/auth/verify-email` | Confirm email |
| `resendVerification(email)` | POST `/auth/resend-verification` | Resend link |
| `login(body)` | POST `/auth/login` | Returns tokens |
| `refresh(refreshToken)` | POST `/auth/refresh` | Rotate tokens |
| `logout(refreshToken)` | POST `/auth/logout` | Revoke refresh |
| `getMe()` | GET `/auth/me` | Current user + org + role |
| `updateMe(body)` | PUT `/auth/me` | Update name/avatar |
| `changePassword(body)` | POST `/auth/change-password` | Needs current password |
| `forgotPassword(email)` | POST `/auth/forgot-password` | Sends reset email |
| `resetPassword(body)` | POST `/auth/reset-password` | token + new password |
| `startGoogleOAuth()` | GET `/auth/google` | Redirects to Google |
| `exchangeOAuthCode(code,state)` | POST `/auth/oauth/exchange` | Returns tokens |

### Step 5.3 — `lib/api/org.ts`

| Method | Endpoint | Min role |
|--------|----------|----------|
| `getOrg(orgId)` | GET `/orgs/:orgId` | viewer |
| `updateOrg(orgId, body)` | PUT `/orgs/:orgId` | admin |

### Step 5.4 — `lib/api/team.ts`

| Method | Endpoint | Min role |
|--------|----------|----------|
| `listMembers(orgId)` | GET `/orgs/:orgId/team` | viewer |
| `inviteMember(orgId, body)` | POST `/orgs/:orgId/team/invite` | admin |
| `acceptInvite(orgId, token)` | POST `/orgs/:orgId/team/accept-invite` | none (token) |
| `changeRole(orgId, memberId, role)` | PUT `/orgs/:orgId/team/:id/role` | admin |
| `removeMember(orgId, memberId)` | DELETE `/orgs/:orgId/team/:id` | admin |

### Step 5.5 — `lib/api/accounts.ts`

| Method | Endpoint | Min role |
|--------|----------|----------|
| `list(orgId)` | GET `/orgs/:orgId/accounts` | viewer |
| `get(orgId, accountId)` | GET `/orgs/:orgId/accounts/:id` | viewer |
| `connect(orgId, body)` | POST `/orgs/:orgId/accounts` | admin |
| `update(orgId, accountId, body)` | PUT `/orgs/:orgId/accounts/:id` | admin |
| `remove(orgId, accountId)` | DELETE `/orgs/:orgId/accounts/:id` | admin |
| `test(orgId, accountId)` | POST `/orgs/:orgId/accounts/:id/test` | admin |
| `sync(orgId, accountId)` | POST `/orgs/:orgId/accounts/:id/sync` | admin |
| `getSyncLogs(orgId, accountId)` | GET `/orgs/:orgId/accounts/:id/sync-logs` | viewer |

### Step 5.6 — `lib/api/costs.ts`

| Method | Endpoint |
|--------|----------|
| `getSummary(orgId, params)` | GET `/orgs/:orgId/costs` |
| `getByDay(orgId, params)` | GET `/orgs/:orgId/costs/by-day` |
| `getByService(orgId, params)` | GET `/orgs/:orgId/costs/by-service` |
| `getByTag(orgId, tagKey, params)` | GET `/orgs/:orgId/costs/by-tag` |
| `getTopServices(orgId, params)` | GET `/orgs/:orgId/costs/top-services` |

Params (all optional): `start` (ISO date), `end` (ISO date), `provider`, `view` (`unblended`/`amortized`), `account_id`

### Step 5.7 — `lib/api/caps.ts`
`list(orgId)`, `get(orgId, capId)`, `create(orgId, body)`, `update(orgId, capId, body)`, `remove(orgId, capId)`

### Step 5.8 — `lib/api/alerts.ts`
`list(orgId, params: { status?, page?, size? })`, `acknowledge(orgId, alertId)`, `snooze(orgId, alertId, { until: string })`, `count(orgId)` — returns `{ active: number }`

### Step 5.9 — `lib/api/notifications.ts`
`get(orgId)`, `update(orgId, body)`, `testEmail(orgId)`, `testTeams(orgId)`, `testSlack(orgId)`

### Step 5.10 — `lib/api/reports.ts`
`get(orgId)`, `update(orgId, body)`, `sendNow(orgId)`

### Step 5.11 — `lib/api/recommendations.ts`
`list(orgId, params: { status?, provider?, min_savings?, confidence? })`, `updateStatus(orgId, recId, status)`

### Step 5.12 — `lib/api/forecasts.ts`
`getCurrent(orgId)`, `getHistory(orgId)`

### Step 5.13 — `lib/api/commitments.ts`
`list(orgId)`, `getSummary(orgId)`, `getExpiring(orgId)`

### Step 5.14 — `lib/api/scorecard.ts`
`get(orgId)`, `getExecutive(orgId)`

### Step 5.15 — `lib/api/resources.ts`
`list(orgId, params: { provider?, region?, type? })`, `listIdle(orgId)`, `get(orgId, resourceId)`

### Step 5.16 — `lib/api/virtual-tags.ts`
`list(orgId)`, `create(orgId, body)`, `update(orgId, ruleId, body)`, `remove(orgId, ruleId)`, `reorder(orgId, orderedIds)`, `apply(orgId, ruleId)`, `getAuditLog(orgId)`

### Step 5.17 — `lib/api/webhooks.ts`
`list(orgId)`, `create(orgId, body)`, `update(orgId, webhookId, body)`, `remove(orgId, webhookId)`, `test(orgId, webhookId)`

### Step 5.18 — `lib/api/llm.ts`
`getConfig(orgId)`, `setConfig(orgId, body)`, `deleteConfig(orgId)`, `query(orgId, body: LlmQueryRequest)`

### Step 5.19 — `lib/api/metrics.ts`
`list(orgId)`, `create(orgId, body)`, `remove(orgId, metricId)`, `ingestValue(orgId, metricId, body)`, `getValues(orgId, metricId)`, `getUnitEconomics(orgId)`

### Step 5.20 — `lib/api/api-keys.ts`
`list(orgId)`, `create(orgId, body)`, `revoke(orgId, keyId)`

### Step 5.21 — `lib/api/health.ts`
`check()` — GET `/health` (no auth required). Poll every 60s. Backend returns `{ status: 'ok' | 'degraded' | 'down', db: ..., redis: ... }`

---

## 6. Custom Hooks

### Step 6.1 — `hooks/useAuth.ts`
- `useMe()` — `useQuery` for `/auth/me`, staleTime 10min
- `useLogin()` — mutation: on success → setTokens + setAuth store + redirect `/dashboard`
- `useLogout()` — mutation: always (onSettled) → clearTokens + clear store + redirect `/login`
- `useSignup()` — mutation: 3-step form orchestration
- `useVerifyEmail(token)` — mutation: on success → redirect to login
- `useForgotPassword()` — mutation
- `useResetPassword()` — mutation: on success → redirect to login with success toast
- `useUpdateMe()` — mutation + invalidates `me` query
- `useChangePassword()` — mutation

### Step 6.2 — `hooks/useRole.ts`
- `useRole()` — returns current role string from authStore
- `useIsAtLeast(role)` — boolean; uses `ROLE_RANK` map (`viewer=1, editor=2, admin=3, owner=4`)
- Usage: `const canEdit = useIsAtLeast('editor')` — cleaner than `<RoleGate>` for conditional logic

### Step 6.3 — `hooks/useOrg.ts`
- `useOrg()` — returns org from authStore (already loaded via `useMe`)
- `useUpdateOrg()` — mutation: invalidates `org` and `me` query

### Step 6.4 — `hooks/useAccounts.ts`
- `useAccounts(orgId)` — `useQuery` staleTime 60s
- `useAccount(orgId, id)` — `useQuery`
- `useSyncLogs(orgId, accountId)` — `useQuery` with `refetchInterval: 10_000` while drawer open
- `useConnectAccount(orgId)` — mutation: on success → invalidate accounts + toast
- `useTriggerSync(orgId)` — mutation: optimistically sets account status to 'syncing'
- `useTestConnection(orgId)` — mutation: returns `TestConnectionResponse`

### Step 6.5 — `hooks/useCosts.ts`
- `useCostSummary(orgId, params)` — `useQuery` staleTime 5min
- `useCostsByDay(orgId, params)` — `useQuery`
- `useCostsByService(orgId, params)` — `useQuery`
- `useCostsByTag(orgId, tagKey, params)` — `useQuery`
- `useTopServices(orgId, params)` — `useQuery`

All cost hooks: params passed as dependency to query key so filter changes trigger new fetch.

### Step 6.6 — `hooks/useCaps.ts`
- `useCaps(orgId)` — list
- `useCreateCap(orgId)` — mutation + invalidate caps
- `useUpdateCap(orgId, capId)` — mutation + optimistic update
- `useDeleteCap(orgId, capId)` — mutation + optimistic removal

### Step 6.7 — `hooks/useAlerts.ts`
- `useAlerts(orgId, params)` — `useQuery` staleTime 60s
- `useAlertsCount(orgId)` — `useQuery` polling every 60s — feeds TopBar badge
- `useAcknowledge(orgId)` — mutation + optimistic update
- `useSnooze(orgId)` — mutation + optimistic update

**Real-time:** `useWebSocket` invalidates `['alerts', orgId]` on `sync.complete` event → `useAlerts` auto-refetches.

### Step 6.8 — `hooks/useHealth.ts`
- `useHealth()` — `useQuery` with `refetchInterval: 60_000` (poll health every 60s)
- Feeds `HealthBanner` and `StatusDot` in TopBar

### Step 6.9 — `hooks/useWebSocket.ts`
- Connects WS on mount using current access token
- **On token refresh:** WS client must disconnect and reconnect with new token (token expiry during open connection)
- Subscribes to all WS events, dispatches to:
  - `sync.complete` → toast + cache invalidation (costs, accounts, alerts, caps)
  - `connected` → update wsStore
  - `ping` → no-op
- Cleans up on unmount (disconnect + unsubscribe)
- Exposes `isConnected: boolean` from wsStore

### Step 6.10 — `hooks/useCommandPalette.ts`
- Opens/closes command palette via `uiStore`
- Registers `⌘K` / `Ctrl+K` keyboard shortcut globally
- Provides search results from local cache (accounts names, alert titles, routes)

### Step 6.11 — Domain hooks (all follow same pattern)
Each domain hook wraps its API module with TanStack Query:

| Hook file | Key hooks exported |
|-----------|-------------------|
| `useForecasts.ts` | `useForecasts(orgId)`, `useForecastHistory(orgId)` |
| `useCommitments.ts` | `useCommitments(orgId)`, `useCommitmentSummary(orgId)`, `useExpiringCommitments(orgId)` |
| `useRecommendations.ts` | `useRecommendations(orgId, params)`, `useUpdateRecStatus(orgId)` |
| `useScorecard.ts` | `useScorecard(orgId)`, `useScorecardExecutive(orgId)` |
| `useResources.ts` | `useResources(orgId, params)`, `useIdleResources(orgId)` |
| `useVirtualTags.ts` | `useVirtualTags(orgId)`, `useVtagAudit(orgId)`, `useCreateRule`, `useApplyRule` |
| `useMetrics.ts` | `useMetrics(orgId)`, `useUnitEconomics(orgId)`, `useIngestValue` |
| `useNotifications.ts` | `useNotifications(orgId)`, `useUpdateNotifications`, `useTestChannel` |
| `useReports.ts` | `useReport(orgId)`, `useUpdateReport`, `useSendNow` |
| `useWebhooks.ts` | `useWebhooks(orgId)`, `useCreateWebhook`, `useTestWebhook` |
| `useApiKeys.ts` | `useApiKeys(orgId)`, `useCreateApiKey`, `useRevokeApiKey` |
| `useLlm.ts` | `useLlmConfig(orgId)`, `useSetLlmConfig`, `useDeleteLlmConfig`, `useLlmQuery` |
| `useTeam.ts` | `useTeam(orgId)`, `useInviteMember`, `useChangeRole`, `useRemoveMember` |

---

## 7. State Management

### Step 7.1 — `store/authStore.ts` (Zustand)
Fields: `user: User | null`, `org: Org | null`, `role: Role | null`, `isReady: boolean`
Actions: `setAuth(user, org, role)`, `clear()`
**No persistence** — rehydrated on every page load via `useMe()` query.

### Step 7.2 — `store/wsStore.ts` (Zustand)
Fields: `connected: boolean`, `lastSyncEvent: SyncCompleteData | null`
Actions: `setConnected(bool)`, `setLastSync(data)`

### Step 7.3 — `store/uiStore.ts` (Zustand + persist)
Fields:
- `sidebarCollapsed: boolean` — persisted
- `commandPaletteOpen: boolean` — session only
- `costView: 'unblended' | 'amortized'` — persisted (default: `'unblended'`)
- `defaultDateRangePreset: '7d' | '30d' | 'month'` — persisted (default: `'month'`)
- `recentPages: string[]` — persisted, last 5 visited paths (for CommandPalette Recent group)
- `pageSize: 20 | 50 | 100` — persisted (default: `20`), user's preferred table page size

Actions: `toggleSidebar()`, `openCommandPalette()`, `closeCommandPalette()`, `setCostView(view)`, `setDatePreset(preset)`, `addRecentPage(path)`, `setPageSize(size)`

Persisted: `sidebarCollapsed`, `costView`, `defaultDateRangePreset`, `recentPages`, `pageSize` — all via localStorage key `prism-ui`

### Step 7.4 — Rule: TanStack Query for all server data
Zustand stores only 3 things: auth identity, WS state, UI preferences.
All server data (costs, accounts, caps, etc.) lives in TanStack Query cache.
**Never copy server data into Zustand.**

### Step 7.5 — Optimistic updates
Every `useMutation` that modifies a list uses `onMutate` to update cache immediately, with `onError` rollback.

Pattern for all mutations:
1. `onMutate`: snapshot current cache data, apply optimistic change via `queryClient.setQueryData`
2. `onError`: restore from snapshot
3. `onSettled`: `queryClient.invalidateQueries` to sync with server truth

---

## 8. Auth Layer & Route Guards

### Step 8.1 — Token storage strategy
- **Access token:** in-memory only (`let _accessToken`). Never in localStorage. Lost on page refresh (intentional — triggers silent refresh on next request).
- **Refresh token:** `sessionStorage.setItem('prism_rt', token)`. Cleared on tab close. Not httpOnly (browser-only app). Trade-off documented.
- **Session cookie hint:** Backend sets `prism_session` cookie (non-httpOnly, used only for edge middleware check). Contains no secrets.

### Step 8.2 — `middleware.ts` (Next.js Edge)
Runs on every request except `_next`, `api`, `public`, `favicon`.

Logic:
1. Check `prism_session` cookie
2. If unauthenticated and accessing protected route → redirect `/login?from=<path>`
3. If authenticated and accessing `/login` → redirect `/dashboard`
4. `/onboarding` is protected (need auth) but no sidebar — handled by page-level check

### Step 8.3 — `components/auth/AuthBootstrap.tsx`
Client component, wraps entire app inside providers.

Behavior on mount:
1. Check if `prism_rt` exists in sessionStorage
2. If yes: call `authApi.refresh()` to get fresh access token (page refresh recovery)
3. On success: call `authApi.getMe()` to hydrate `authStore`
4. On failure: `clearTokens()` → user flows to login naturally
5. While bootstrapping: render `<AppSkeleton />` to prevent flicker

This is the critical bridge between page refresh (tokens lost from memory) and authenticated state.

### Step 8.4 — `lib/auth/guards.ts`
- `requireAuth()` — throws/redirects if not authenticated (use in server components)
- `requireRole(role)` — checks `authStore.role` rank; for use in page-level hooks
- `ROLE_RANK` — `{ viewer: 1, editor: 2, admin: 3, owner: 4 }`

### Step 8.5 — Google OAuth flow
1. User clicks `[Continue with Google]`
2. Frontend: redirect to `GET /auth/google` (backend starts OAuth, sets state in `app_kv`)
3. Google redirects back to backend callback: `GET /auth/google/callback`
4. Backend generates one-time exchange code, redirects to `FRONTEND_URL/auth/oauth-callback?code=X&state=Y`
5. Frontend page at `/auth/oauth-callback` calls `POST /auth/oauth/exchange?code=X&state=Y`
6. Backend returns tokens — frontend handles same as normal login
7. Page: `src/app/(auth)/oauth-callback/page.tsx` — loading spinner → `exchangeOAuthCode()` → `setTokens()` → `/dashboard`

### Step 8.6 — Accept Invite flow
1. User receives email with link: `FRONTEND_URL/accept-invite?token=X`
2. Page calls `GET /auth/me` to check if already authenticated
3. **New user path:** Show name + password form → `POST /team/accept-invite` with token + password → auto-login with returned tokens
4. **Existing user path:** Show "Join [OrgName]" confirm → `POST /team/accept-invite` with token (no password needed) → update org context
5. Edge case: expired token → show "This invite has expired. Ask your admin to resend."

### Step 8.7 — Invite expiry handling
Backend invite tokens expire. Frontend:
- On 400/404 from `accept-invite`: show "Invite expired or invalid" state with CTA to contact admin
- Never show generic error — this is a known expected failure

---

## 9. App Shell Components

### Step 9.1 — `components/layout/AppSkeleton.tsx`
Shown during `AuthBootstrap` initialization and `useMe` loading.
Structure: dark sidebar-width block on left + right area with shimmer bars in TopBar position and content area. Exact same layout proportions as real shell to prevent layout shift.

### Step 9.2 — Root layout (`app/layout.tsx`)
- Loads Inter + JetBrains Mono via `next/font/google`
- Wraps with `<Providers>`
- Sets metadata title template `%s | PRISM`

### Step 9.3 — `app/providers.tsx`
Wraps in this order (outer → inner):
1. `QueryClientProvider` (TanStack Query)
2. `ThemeProvider` (next-themes, default light)
3. `TooltipProvider` (Radix, delayDuration 300ms)
4. `AuthBootstrap`
5. `Toaster` (Sonner, position bottom-right, richColors)
6. `ReactQueryDevtools` (dev only)

### Step 9.4 — App layout (`app/(app)/layout.tsx`)
- Calls `useMe()` — if loading → `<AppSkeleton />`, if no user → redirect `/login`
- Calls `useWebSocket()` — starts WS connection
- Calls `useHealth()` — starts 60s health polling
- Layout: `flex h-screen overflow-hidden` → sidebar fixed left + flex-1 column right
- Right column: `OfflineBanner` (navigator.onLine) → `HealthBanner` (conditional) → `TopBar` → `main` (overflow-y-auto)
- Passes `orgId` via URL context (org ID comes from `authStore.org.id`)
- Renders `<CommandPalette />` (always mounted, hidden until ⌘K)

### Step 9.5 — `components/layout/Sidebar.tsx`
- Fixed left, `z-40`, dark background (`gray-900`)
- Width: 240px expanded, 64px collapsed — CSS transition `width 200ms ease-in-out`
- Logo area: "PRISM" text expanded, "P" icon collapsed
- 3 nav sections: OVERVIEW / MANAGE / SETTINGS — section labels hidden when collapsed
- Nav items: icon + label (collapsed: icon only with tooltip)
- Active state: `bg-brand-500 text-white`
- Hover state: `bg-gray-800 text-gray-100`
- Bottom: user avatar + name (collapsed: avatar only) + collapse toggle button
- Scroll: `overflow-y-auto scrollbar-thin` for long nav lists
- **Responsive:** below `lg (1024px)` → auto-collapse; below `md (768px)` → off-canvas (hamburger)

### Step 9.6 — `components/layout/SidebarItem.tsx`
- Reusable nav item: `href, icon, label, active, collapsed, badge?`
- `badge` prop: shows unread count (alerts, notifications)
- Alerts nav item shows active alert count badge

### Step 9.7 — `components/layout/TopBar.tsx`
- Sticky top-0, `z-30`, `bg-gray-50/90 backdrop-blur-sm`
- Height: 60px
- Left: Page title (derived from pathname map)
- Center: Search button (triggers `CommandPalette` via `uiStore`) with `⌘K` hint
- Right (left → right): `StatusDot` → notification bell (with active alert count badge) → `UserMenu`
- Notification bell: clicking opens `NotificationsPanel` slide-in

### Step 9.8 — `components/layout/NotificationsPanel.tsx`
- Slide-in sheet from right (Radix Sheet)
- Lists active alerts (up to 10 most recent)
- Each: type, scope, time, [Acknowledge] button inline
- "View all alerts →" link at bottom
- Real-time: invalidates when WS `sync.complete` fires
- Badge count from `useAlertsCount()`

### Step 9.9 — `components/layout/UserMenu.tsx`
- Avatar (Google photo or initial fallback)
- Dropdown: Profile | Change Password | Dark Mode toggle | Sign Out
- Shows user name + email at top
- Shows role badge

### Step 9.10 — `components/layout/CommandPalette.tsx`
- Triggered by `⌘K` / `Ctrl+K` (global keydown listener)
- Uses `cmdk` library
- Groups: Pages | Accounts | Actions | Recent
- Pages: all 22 app routes with icons — navigate on select
- Accounts: search cloud account names → navigate to account detail
- Actions: "Connect account", "Create cap", "Sync now" (most recent account), "View alerts"
- Recent: last 5 visited pages (tracked in `uiStore`)
- Closes on selection, Escape, or backdrop click

### Step 9.11 — `components/layout/HealthBanner.tsx`
- Only renders when `health.status !== 'ok'`
- `degraded`: amber background — "Dashboard data may be stale — cache service unavailable"
- `down`: red background — "Backend is unreachable — please check your connection"
- Dismissible (X button) for single session — reappears if status persists

### Step 9.12 — Settings sub-layout (`app/(app)/settings/layout.tsx`)
- Left column: secondary vertical nav (200px)
  - Profile, Organisation, Team, Notifications, Webhooks, API Keys, (LLM — admin only)
- Right column: page content
- Same pattern as main sidebar but lighter styling (white bg instead of dark)

---

## 10. WebSocket & Real-time Layer

### Step 10.1 — WS client singleton (`lib/ws/wsClient.ts`)

**Connection lifecycle:**
1. `connect(token)` — opens `WS_URL/ws?token=<access_jwt>`. Guard: skip if already OPEN.
2. `onopen` — reset `reconnectAttempts`, start ping timer, update `wsStore.connected = true`
3. `onmessage` — parse JSON, dispatch to all listeners
4. `onclose` — stop ping, `wsStore.connected = false`, schedule reconnect
5. `onerror` — close socket (triggers `onclose`)

**Exponential reconnect:** delays 1s, 2s, 4s, 8s, 16s, max 30s. Reset on successful open.

**Ping timer:** Send `{ type: 'ping' }` every 25s to keep connection alive through proxies.

**Token refresh integration:**
- `updateToken(newToken: string)` method: closes current connection and immediately reconnects with new token (uses same exponential backoff as normal reconnect)
- On `useWebSocket`, after Axios interceptor successfully refreshes: call `wsClient.updateToken(newToken)`
- **55-minute connection ceiling timer:** After 55 min, proactively close and reconnect with fresh token. Prevents long-lived connections with stale token contexts. (Access token is refreshed every ~13 min by proactive refresh, so token is always current.)
- **Tab visibility:** `document.addEventListener('visibilitychange')` — pause ping when tab hidden, reconnect if connection dropped while hidden

**Subscribe/unsubscribe:** returns cleanup function. `useWebSocket` hook calls cleanup on unmount.

### Step 10.2 — `useWebSocket` hook behavior

On `sync.complete` event:
1. Show Sonner toast: `"✓ {provider} synced · {records.toLocaleString()} records · {account_name}"`
2. Invalidate `['costs', orgId]` — dashboard updates
3. Invalidate `['accounts', orgId]` — account card refreshes
4. Invalidate `['alerts', orgId]` — new alerts may have fired
5. Invalidate `['caps', orgId]` — cap spend percentages may change
6. Invalidate `['forecasts', orgId]` — forecast may update
7. Update `wsStore.lastSyncEvent`

On `connected` event:
- Update `wsStore.connected = true`

### Step 10.3 — Real-time patterns per screen

| Screen | Trigger | Action |
|--------|---------|--------|
| Dashboard | `sync.complete` | Auto-refetch all dashboard queries |
| Accounts list | `sync.complete` | Account card shows updated last_sync_at |
| Account detail | `sync.complete` for this account | Sync logs drawer refetches |
| Alerts | `sync.complete` | Alert list refetches (new alerts may exist) |
| Budget Caps | `sync.complete` | Cap spend pct updates |
| TopBar bell | Any alert change | `useAlertsCount` refetches (60s polling) |
| Sync logs drawer | While open | Poll `GET /accounts/:id/sync-logs` every 10s |
| VTag apply progress | While drawer open | Poll `GET /virtual-tags/audit-log` every 3s |
| Health banner | — | Poll `GET /health` every 60s |

### Step 10.4 — `lib/ws/wsEvents.ts`
- Export all WS event type definitions
- Export `isSyncCompleteEvent(e): e is SyncCompleteEvent` type guard
- Each event's `data` property is typed via discriminated union

---

## 11. Shared / Reusable Components

### Step 11.1 — `common/DataCard.tsx`
Props: `label, value (ReactNode), delta? (number), deltaLabel?, sparkline?, freshness?, estimated? (bool), className?, onClick?`
- Large value with `tabular` class
- `DeltaBadge` inline right of value
- `EstimatedBadge` top-right when estimated=true
- `Sparkline` below value
- Freshness text at bottom in gray-400
- Hover shadow when onClick is provided

### Step 11.2 — `common/DeltaBadge.tsx`
Props: `delta: number, label?: string, size?: 'sm' | 'md'`
- Positive (cost increase): red bg + TrendingUp icon
- Negative (cost decrease): green bg + TrendingDown icon
- Zero: gray bg + Minus icon
- Always includes sign (`+12.4%`)

### Step 11.3 — `common/ProviderBadge.tsx`
Props: `provider: Provider, size?: 'sm' | 'md'`
- Shows provider logo + label
- Uses provider color as border or bg tint
- Consistent across all tables and cards

### Step 11.4 — `common/StatusDot.tsx`
Props: `status: 'healthy' | 'warning' | 'error' | 'unknown', pulse?: bool, tooltip?: string`
- 8×8px colored circle
- `pulse` = animated ring for healthy/active
- Wrapped in `<Tooltip>` when tooltip provided

### Step 11.5 — `common/DataFreshness.tsx`
Props: `dataAsOf: string (ISO), className?`
- Renders: `"Data as of Nov 13"` or `"Updated 2h ago"`
- Relative time using `date-fns/formatDistanceToNow`
- Org timezone applied via `toOrgTz()`

### Step 11.6 — `common/EstimatedBadge.tsx`
- Small amber badge: `⚠ estimated`
- Tooltip: "Today's figures are estimated and will update when finalized"
- Used wherever `is_estimate: true`

### Step 11.7 — `common/EmptyState.tsx`
Props: `icon?, title, message?, action?: { label, onClick }`
- Centered, py-20
- Icon in gray-300, large
- One CTA button (optional)

### Step 11.8 — `common/ErrorState.tsx`
Props: `title?, message?, retry?: () => void`
- For query `isError` states
- Shows error message from `error.message` or fallback
- [Retry] button calls `refetch()`

### Step 11.9 — `common/PageHeader.tsx`
Props: `title, description?, actions?: ReactNode`
- Left: title (text-2xl font-bold) + description (gray-500)
- Right: action buttons slot
- Separator below
- Used at top of every page

### Step 11.10 — `common/SectionHeader.tsx`
Props: `title, action?: ReactNode`
- Smaller header within a page section
- text-lg font-semibold
- Optional right-aligned action

### Step 11.11 — `common/RoleGate.tsx`
Props: `require: Role, children, fallback?: 'hide' | 'disable'`
- `hide` (default): renders nothing for insufficient role
- `disable`: renders children wrapped in disabled tooltip
- Tooltip text: "Requires [role] or above"
- Checks `ROLE_RANK[currentRole] >= ROLE_RANK[require]`

**Owner protections:**
- Changing an owner's role: disabled with "Cannot change owner role"
- Removing yourself: disabled with "Cannot remove yourself"
- These are additional checks beyond basic RBAC

### Step 11.12 — `common/ConfirmDialog.tsx`
Props: `open, onOpenChange, title, description, confirmLabel?, confirmVariant?, onConfirm, loading?`
- Radix Dialog
- Two buttons: [Cancel] [Confirm] (confirm = destructive variant by default)
- `loading` = spinner + disabled state on confirm button
- Closes on Escape key automatically

### Step 11.13 — `common/CopyBlock.tsx`
Props: `content, label?`
- Monospaced pre block with copy button
- Copy button shows Check icon for 2s after copy
- Uses `navigator.clipboard.writeText`
- Label (optional): displayed in gray header bar above content

### Step 11.14 — `common/SortableTable.tsx`
Props: `columns: Column<T>[], data: T[], keyField, onRowClick?, loading?, emptyState?`
- Column: `{ key, label, sortable?, align?, render? }`
- Client-side sort on sortable columns (↑/↓ arrows)
- Loading: shows 5-row skeleton
- Empty: renders `emptyState` prop or default EmptyState
- `onRowClick`: cursor-pointer + hover bg

### Step 11.15 — `common/DateRangePicker.tsx`
Props: `value: DateRange, onChange`
- Popover with preset buttons: "This month", "Last 7 days", "Last 30 days", "Last 90 days"
- Calendar below presets for custom range
- Displays selected range formatted: "Nov 1 – Nov 13, 2026"
- When changed, updates URL params (not internal state)

### Step 11.16 — `common/Pagination.tsx`
Props: `page, size, total, onPageChange`
- Shows "Showing 1–20 of 143"
- [← Prev] [1] [2] [3] [...] [Next →]
- Disabled when at limits
- Calls `onPageChange(newPage)` → page stored in URL params

### Step 11.17 — `common/LoadingSkeleton.tsx`
Variants: `card`, `table`, `kpi-row`, `chart`
- Used in Suspense fallbacks and `isLoading` states
- Exact shape matches the loaded component (prevents layout shift)

### Step 11.18 — `charts/` (all wrapped for SSR safety)
Every chart component:
- Wrapped with `dynamic(() => import(...), { ssr: false })` at usage site
- Wrapped in `<ResponsiveContainer width="100%" height={height}>` internally
- Loading state: shimmer skeleton div matching height
- Props always include: `data`, `height` (default per chart type)

Chart types:
- `AreaChart` — time series with gradient fill, provider color prop
- `BarChart` — vertical/horizontal, stacked variant, rounded top corners
- `LineChart` — multi-series, strokeWidth 2.5, no dots
- `DonutChart` — innerRadius 60%, custom center label
- `RadialGauge` — for scorecard score, color gradient based on value
- `Sparkline` — 32px tall, no axes, inline in cards
- `ChartTooltip` — shared custom tooltip component (white bg, shadow, clean type)

---

## 12. All Screen Implementations

### Step 12.1 — Auth screens

#### `/login`
Layout: `AuthSplitLayout` (left: hero illustration + tagline; right: form)
Components:
- `LoginForm` — email, password, [Sign in] primary button
- `GoogleOAuthButton` — [Continue with Google] outline button
- Forgot password link → `/forgot-password`
- Sign up link → `/signup`

Behavior:
- Form validation: email (valid format), password (min 8)
- On submit: `useLogin()` mutation → success → `/dashboard`, error → inline message (never specify which field)
- Google: redirect to `/auth/google` backend endpoint
- Mount animation: form slides in from right (`animate-slide-up`)
- If `?from=` param present → redirect there after login

#### `/signup`
3-step stepper inside `AuthSplitLayout`

**Step 1 — Account details:**
- Full name (required)
- Email (required, valid format)
- Password (required, min 8) + `PasswordStrengthBar` (weak/fair/strong/very strong)
- Google OAuth button as alternative
- Next → validates step 1 fields only

**Step 2 — Organisation:**
- Organisation name (required)
- Default currency (select: USD/EUR/GBP/INR + others)
- Timezone (searchable select, grouped by region)
- Back button
- Create Account → `useSignup()` mutation

**Step 3 — Verify email:**
- Static "Check your inbox" with animated email icon
- "Resend email" link (calls `resendVerification`)
- "Already verified? Sign in" link

#### `/verify-email?token=X`
- On mount: auto-submit `verifyEmail(token)` mutation
- Loading: spinner
- Success: "Email verified! Redirecting..." → `/login?verified=1`
- Error: "Invalid or expired link" + resend form

#### `/forgot-password`
- Email input
- [Send reset link] → `forgotPassword(email)` mutation
- On success (always, even for unknown emails): "If that email exists, we've sent a link"
- Link back to login

#### `/reset-password?token=X`
- New password + confirm password inputs
- [Set new password] → `resetPassword({ token, password })` mutation
- On success: redirect `/login?reset=1` with success toast

#### `/accept-invite?token=X`
- On mount: attempt `GET /auth/me`
- **New user:** Name field + Password + confirm → "Accept Invite" button
- **Existing user:** "Join [OrgName]" confirm button (no password needed)
- On success: tokens returned → auto login → `/dashboard`
- Error (token invalid/expired): clear error page with "Contact your admin"

#### `/oauth-callback?code=X`
- On mount: call `exchangeOAuthCode(code, state)` mutation
- Loading: spinner ("Completing sign in...")
- Success: setTokens + redirect `/dashboard`
- Error: redirect `/login?oauth_error=1` with toast

---

### Step 12.2 — Onboarding (`/onboarding`)

Shown when: authenticated + zero cloud accounts + role is admin/owner

Full-screen (no sidebar). Progress indicator at top (steps 1–4 with animated fill).

**Step 1 — Connect first cloud account**
Embeds `ConnectWizard` component (same as `/accounts/connect`)
On success → auto-advance to Step 2

**Step 2 — Set a budget cap (optional)**
Simplified cap form: provider, amount, threshold preset (90% default)
[Skip →] link in top-right. [Set Cap] → `useCreateCap` mutation → advance

**Step 3 — Invite your team (optional)**
Email input + role select + [Add to list]. Shows staged invites list below.
[Skip →] link. [Send Invites] → fires all invite mutations → advance

**Step 4 — Notifications**
Alert email input (pre-filled from current user's email)
5 threshold toggle switches (default: 75% and 90% enabled)
[Done → Go to Dashboard] → `updateNotifications` → redirect `/dashboard`

---

### Step 12.3 — Dashboard (`/dashboard`)

**All queries run in parallel on mount.** Layout renders immediately with skeletons.

**Greeting bar:**
`"Good morning, Neeraj"` (time-aware: morning/afternoon/evening based on org timezone)

**Sync Status Bar:**
One `StatusDot` + text per connected account: `"AWS · synced 2h ago"`, `"Azure · failed 6h ago ⚠"`, `"GCP · syncing..."` (live spinner from `wsStore.lastSyncEvent`)

**KPI Row (4 cards):**
1. MTD Spend — total + sparkline (last 14 days) + `EstimatedBadge` if today
2. MoM Change — `DeltaBadge` large display + "vs last month" label
3. Month Forecast — projected + "X% of cap" if cap exists
4. Active Alerts — count + "X unacknowledged" subtext, clicking → `/alerts`

**Main 2-col row:**
- Left 2/3: `SpendByDayChart` — area chart, 30 days, stacked by provider, today marked with dashed line + `⚠ est.`, provider filter + cost view toggle
- Right 1/3: `TopServicesTable` — 5 rows: service name, provider badge, MTD, MoM delta. "View all →" link

**Lower 3-col row:**
- `BudgetCapsSummary` — 2-3 caps with progress bars, "1 at 90%+ ⚠" summary, "Manage caps →"
- `ForecastSummary` — by-provider projected amounts, breach warning badges
- `ScorecardSummary` — big score number + grade letter, "↑ from X last month", "View full scorecard →"

**Recommendations row:**
3 open recs: title, savings, [Review] button each. "View all recommendations →" link.

**Empty state:** If 0 accounts → redirect to `/onboarding`. If accounts but 0 cost data → "Data syncing — check back shortly" with last sync time.

---

### Step 12.4 — Costs Explorer (`/costs`)

**Filter bar (URL params — all deep-linkable):**
`DateRangePicker` | Provider select (All/AWS/Azure/GCP) | Cost view (Unblended/Amortized) | `ExportCsvButton`

**Data freshness bar:** `DataFreshness` component + `EstimatedBadge` if any current-day data

**Tabs:** By Day | By Service | By Tag | Top Services (tab selection also in URL param `?tab=`)

**By Day tab:**
- `ByDayChart`: vertical bar chart, stacked by provider, 30-day default
- Zero-fill days shown as ghost bars (gray-100)
- Today bar: lighter opacity + estimated badge in tooltip
- Hover tooltip: date + per-provider breakdown + total

**By Service tab:**
- `ByServiceTable`: `SortableTable`, sortable by MTD and MoM%
- Columns: Service | Provider badge | MTD | MoM % | Trend (sparkline 14d)
- Default sort: MTD descending

**By Tag tab:**
- Tag key `Select` dropdown (populated from unique tags in org)
- `DonutChart` right + summary table left
- "Untagged" segment always shown with pct

**Top Services tab:**
- Horizontal `BarChart` — top 10 by MTD
- MoM% column alongside bars

**Export CSV:** calls API with `format=csv` param → triggers blob download via `triggerCsvDownload()`

---

### Step 12.5 — Accounts (`/accounts`)

**Header:** `PageHeader` with "+ Connect Account" button (admin only via `RoleGate`)

**Account cards grid (2 or 3 columns responsive):**
Each `AccountCard` shows:
- Provider logo + name + account ID/subscription
- `StatusDot` + status text: synced Xh ago / failed / syncing... (spinner)
- Data freshness + records count
- Error message in amber alert box (when failed)
- Action buttons: `[Sync Now]` (admin, rate-limited) | `[Test]` (admin) | `[···]` menu (edit, delete)
- **WS real-time:** card updates when `sync.complete` fires for this account's provider

**Connect Account flow** → routes to `/accounts/connect`

---

### Step 12.6 — Connect Account (`/accounts/connect`)

Reuses `ConnectWizard` component in full-page layout.

**Step 1 — Provider selection:**
3 large cards: AWS | Azure | GCP — each with provider logo, name, description of what data is pulled

**Step 2 — Credentials:**
- Account name (all providers)
- Dynamic form per provider:
  - **AWS:** `role_arn` text, `external_id` text (optional), `region` select. Below: IAM policy JSON in `CopyBlock` with instructions.
  - **Azure:** `tenant_id`, `client_id`, `client_secret` (password input), `subscription_id`
  - **GCP:** `project_id`, `dataset_id`, `table_prefix`, `service_account_json` (textarea with monospace)
  - All inputs: `autocomplete="off"`, `autocorrect="off"`, `spellcheck="false"`
  - Credentials never shown again after save

**Step 3 — Test Connection:**
- `[Test Connection]` button → `useTestConnection()` mutation
- Loading: spinner + "Testing..."
- Success: green checkmark + latency badge + "✓ Connection successful"
- Error: red X + exact error message from backend
- Must pass test before proceeding (block "Next" until tested)

**Step 4 — Confirm + initial sync:**
- Summary card of what will be connected
- Shows sync estimate: "Backfilling ~395 days of data may take 5–15 minutes"
- `[Connect & Start Sync]` → `useConnectAccount()` mutation
- Response: `{ sync_mode }` shown in success state
  - `queued`: "✓ Connected! Syncing in background — we'll notify you when complete"
  - `inline`: "✓ Connected! Syncing now (Celery unavailable — running inline)"
- Auto-redirect to `/accounts` after 3s

---

### Step 12.7 — Account Detail (`/accounts/[id]`)

**Header:** Provider logo + account name + status badge + sync mode badge

**Two-column layout:**
Left: Account details (provider, name, credentials status "configured ✓", created by, created at)
Right: Latest sync stats (last sync time, records synced, data_as_of, duration)

**Sync Logs section:**
- `SyncLogsTimeline` component
- Timeline of runs (newest first)
- Each entry: status dot + time + duration + records + expand for error details
- Polled every 10s when page is active
- Load more (pagination)

**Actions:** `[Sync Now]` | `[Test Connection]` | `[Edit Credentials]` | `[Disconnect Account]` (delete confirm)

---

### Step 12.8 — Budget Caps (`/caps`)

**Header:** "+ Add Cap" button (editor+)

**Cap list:**
Each `CapRow`:
- `ProviderBadge` + scope badge + name
- `$current / $limit` (formatted with org currency)
- `CapProgressBar` with color by pct
- Percentage label: "83%" in matching color
- `"Next threshold: 90% · $X away"` or `"⚠ At 100% — exceeded"`
- `"Last alert: Nov 12"` if any
- `[Edit]` (editor+) `[Delete]` (admin) buttons

**Add/Edit Cap Drawer:**
Fields: Name | Provider (optional) | Scope | Service/Account (conditional on scope) | Amount | Threshold checkboxes (75/90/100/125/150%) | [Save] [Cancel]

**Detail Panel:**
Click any cap → right slide-in with spend history chart + alert history table

**Real-time:** `sync.complete` → invalidates caps query → pct values update

---

### Step 12.9 — Alerts (`/alerts`)

**Filter tabs:** Active (N) | Acknowledged | Snoozed

**Alert list:**
Each `AlertRow`:
- Left border: amber (< 100%) or red (≥ 100%) or gray (ack'd/snoozed)
- Icon: `AlertTriangle` (warning) or `AlertOctagon` (critical)
- Cap name + scope description + threshold %
- Spend at time of alert: `$13,500 / $15,000`
- Delivery channels: `Email ✓ · Teams ✓ · Slack ✗` (green/gray check/cross)
- Triggered at (relative time)
- Actions: `[Acknowledge]` button | `[Snooze ▾]` dropdown menu
  - Snooze options: 1 hour / 4 hours / 24 hours / 7 days / Until resolved
- Clicking row → `AlertDetailDrawer` (full history of this alert, acknowledgement trail)

**Optimistic update:** Acknowledge/snooze immediately moves item from Active tab with animation

---

### Step 12.10 — Forecasts (`/forecasts`)

**Provider cards row (1 card per active provider):**
- Provider logo + name
- `Projected: $14,210`
- `CapProgressBar`: days elapsed / total days
- `"13 of 30 days elapsed · Daily avg: $X"`
- Breach badge when >90% of cap: amber "Will approach cap" / red "Breach projected"
- "No cap set" pill when no cap configured (show forecast without bar)

**Trend chart:** Line chart showing daily projected spend through month-end

**History table:** `SortableTable`
Columns: Month | Provider | Projected | Actual | Variance | Accuracy % | Status badge

---

### Step 12.11 — Commitments (`/commitments`)

**Summary banner:** "Coverage: 68% · Utilization: 84% · 2 expiring within 30 days"

**Tabs:** All | Expiring Soon

**All Commitments table:**
Columns: Provider | Type | Resource/Scope | Coverage % | Utilization % | End Date | Days left | Status badge

**Expiring Soon tab:**
- Same table, pre-filtered to `days_to_expiry ≤ 30`
- Sorted by `days_to_expiry` ascending (soonest first)
- Countdown badges: `< 7d` = red, `< 30d` = amber

---

### Step 12.12 — Recommendations (`/recommendations`)

**Filter bar:** Provider | Min savings (number input) | Confidence (All/High/Medium/Low)

**Tabs with count badges:** Open | Implemented | Rejected

**Rec cards:**
Each `RecCard`:
- Left accent: confidence color (green/yellow/gray)
- Title + description (truncated to 2 lines, expand on click)
- `ProviderBadge` + region + service
- `"Saves $94/mo"` in green + `"High confidence"`
- Status badge (for non-open tabs)
- Actions (open tab only): `[Implement]` (editor+) | `[Reject]` | `[Explain →]`

`[Explain →]`: slide-in `ExplainDrawer` calling `useLlmQuery` with recommendation ID as context. If LLM not configured: shows "Configure AI Assistant to get explanations"

**Status update:** Optimistic update — card moves to correct tab immediately with animation

---

### Step 12.13 — FinOps Scorecard (`/scorecard`)

**Toggle:** `[Detailed View]` ↔ `[Executive View]`

**Detailed View:**
- Large `RadialGauge`: 0–100 score with gradient (red→amber→green), centered score number
- Grade badge: A/B/C/D/F with matching color
- `"↑ 7 points from last month"` delta text
- 7 `ScoreMetricRow`s (one per metric):
  - Metric name + weight %
  - `CapProgressBar` for metric score
  - Status icon: ✓ (≥80), ⚠ (50–79), ✗ (<50)
  - Metric value label (e.g., "88% tagged")
- Computed at timestamp

**Executive View:**
4 `DataCard`s: MTD Spend | Month Forecast | Scorecard Grade | Savings Realized (from implemented recs)

---

### Step 12.14 — Resources (`/resources`)

**Filter bar:** Provider | Region (text search) | Type (text search)

**Tabs:** All Resources | Idle (N)

**All Resources table:**
Columns: Name | Type | Provider | Region | Last Active | Cost/day | Tags

**Idle Resources tab:**
- Pre-filtered to `is_idle: true`
- Additional column: "Idle Since" with colored badge:
  - `< 7 days`: amber `Idle 3d`
  - `>= 7 days`: red `Idle 14d`
- Sorted by idle duration (longest first)

---

### Step 12.15 — Virtual Tags (`/virtual-tags`)

**Tabs:** Rules | Audit Log

**Rules tab:**
- Priority-ordered list, drag handle for reorder (mobile: up/down arrows fallback)
- Each `RuleRow`:
  - `# {priority}` number
  - `Tag: "{key}" = "{value}"`
  - `When: {condition_type} contains "{condition_value}"`
  - `[Edit]` `[Apply]` `[Delete]` buttons (editor+)
- `[+ New Rule]` button opens `RuleEditorDrawer`

**Rule Editor Drawer:**
- Tag Key (text), Tag Value (text)
- Condition Type (select): Service contains / Tag equals / Account is / Provider is
- Condition Value (text)
- Preview: "Will apply to resources where service contains 'ec2'"
- `[Save]`

**Apply flow:**
1. `[Apply]` → confirm dialog "Re-tag all historical cost records matching this rule?"
2. On confirm: `useApplyRule()` mutation
3. Opens `ApplyProgressDrawer` automatically
4. Drawer polls `GET /virtual-tags/audit-log` every 3s
5. Shows: "Re-tagging... 23,451 / 45,231 records (67%)" with progress bar
6. On complete: "✓ 45,231 rows processed, 12,432 updated"

**Audit Log tab:**
`SortableTable` — Rule name | Applied by | Date | Rows processed | Rows updated | Duration | Status badge

---

### Step 12.16 — Business Metrics (`/metrics`)

**Header:** `PageHeader` + `[+ Add Metric]` button (admin+)

**Metric cards grid:**
Each `MetricCard`:
- Name + unit
- Source badge (manual / webhook)
- Current month value + MoM unit cost delta
- `[Ingest Value]` (editor+, manual only) | `[···]` (delete — admin+)

**Ingest Value Modal:** Date (defaults today) + value number + note (optional) + [Save]

**Unit Economics section (bottom):**
Section header: "Unit Economics — Cost per [metric]"
`SortableTable` — Metric | MTD Value | Cloud Cost | Cost/Unit | MoM Unit Trend (DeltaBadge) | Currency

---

### Step 12.17 — AI Assistant (`/assistant`)

**Two-column layout:**
- Left sidebar (200px): conversation history list (last 10 questions, by date, truncated)
- Right main area: active conversation

**Main area:**
- Scrollable chat history
- User messages: right-aligned, brand-50 bg, gray-700 text
- PRISM messages: left-aligned, white card with shadow
- Each message: timestamp + user/PRISM label

**Input area:**
- Auto-growing textarea (max 4 rows) with [Send →] button
- Rate limit indicator: `"20/hour remaining · LLM budget: $4.20 / $20.00 used"`
- Progress bar for budget usage
- Hit rate limit: input disabled + "Rate limit reached. Resets in Xm"

**Unconfigured state:**
Full-page `EmptyState`: "AI Assistant not configured" + description + `[Configure in Settings →]` CTA (admin only)

---

### Step 12.18 — Reports (`/reports`)

**Single-page form:**
- Active toggle (switch)
- Recipients: tag-style email input (add via Enter/comma, remove via ×)
- Send on: Day [1–28] select of each month
- Include sections: Recommendations ✓ | Scorecard ✓ | Commitments ✓ | Unit Economics ☐
- `[Save Changes]` | `[Send Now →]` (sends to configured recipients immediately)
- Last sent: timestamp + delivery status badge

---

### Step 12.19 — Settings screens

**Sub-layout:** Secondary sidebar nav on left (200px), page content right.
Nav items: Profile | Organisation | Team | Notifications | Webhooks | API Keys | (AI — admin only)

#### Profile (`/settings/profile`)
- Avatar (clickable to upload — if not Google auth)
- Name field (editable)
- Email (readonly if Google OAuth, editable if password auth)
- Password section: `[Change Password]` → expands inline: current + new + confirm fields
- Google OAuth: connection badge — "Connected ✓" or "Connect Google account →"
- Delete account: danger zone at bottom (requires typing "DELETE" to confirm)
- `[Save Profile]`

#### Organisation (`/settings/org`)
- Org name (admin+)
- Default currency (admin+): select
- Timezone (admin+): searchable select
- `[Save Changes]`

#### Team (`/settings/team`)
**Active members table:**
Columns: Avatar + Name | Email | Role badge | Joined | Actions

Actions per row:
- Change role dropdown (inline select, admin+, cannot change own role, cannot change owner)
- Remove button with confirm dialog (admin+, cannot remove self, cannot remove owner)

**[Invite Member]** drawer (admin+):
- Email input
- Role select (admin/editor/viewer — cannot invite as owner)
- [Send Invite]
- Shows staged list of pending invites below (if any)

**Pending invites section:** separate table — Email | Role | Sent by | Expires | [Revoke]

**Owner protections (UI enforced):**
- Owner row: role column shows locked "Owner" badge, no change allowed
- Cannot demote the last owner
- Tooltip on locked controls: "Cannot change the owner's role"

#### Notifications (`/settings/notifications`)
- Alert emails: tag input (add/remove)
- Teams webhook URL: text input + `[Test Teams]` button
- Slack webhook URL: text input + `[Test Slack]` button
- Alert email: `[Test Email]` button
- Threshold toggles: 5 switches labeled `75% / 90% / 100% / 125% / 150%`
- Test buttons: show success/fail toast + inline result
- `[Save]`

#### Webhooks (`/settings/webhooks`)
**Table:** URL | Events (comma list) | Active (dot) | Last delivery | Actions

**Add/Edit Webhook Drawer:**
- URL (text, validated on backend for SSRF)
- Events: multi-checkbox: `alert.fired | sync.complete | cap_created | ...`
- Signing secret: auto-generated UUID, shown in `CopyBlock`, can regenerate
- Active toggle
- `[Save]`

**Test Delivery:** `[Test]` → fires test event → shows delivery result inline on row

#### API Keys (`/settings/api-keys`)
**Table:** Name | Key prefix (`prism_...`) | Scopes | Created | Last used | [Revoke]

**Create Key modal:**
- Name field
- Scopes checkboxes: `cost.read | alerts.read | reports.read | webhooks.write`
- [Create Key] → response shows raw key ONCE in `CopyBlock` with warning
- Closing modal: "Have you copied your key?" confirm

**Revoke:** confirm dialog "Revoke this key? Apps using it will stop working immediately."

#### AI (`/settings/llm`) — admin only via `RoleGate require="admin"`
- Provider select: OpenAI | Azure OpenAI
- API Key: password input (write-only — backend never returns key value)
- Model: text input (e.g., `gpt-4o`)
- Monthly budget ($): number input
- Current spend: progress bar (pct of budget)
- `[Save]` | `[Disable AI]` (danger, with confirm)

---

## 13. Form Patterns & Validation

### Step 13.1 — Universal form setup
All forms use: `react-hook-form` + `zodResolver` + typed Zod schemas.
Every form field: label + input + inline error message (from `formState.errors`).

### Step 13.2 — Zod schema rules
- Strings: `.min(1, 'Required').max(limit, 'Too long')`
- Emails: `z.string().email('Invalid email')`
- URLs: `z.string().url('Invalid URL')`
- Currency amounts: `z.number().positive('Must be greater than 0')`
- Passwords: `z.string().min(8, 'At least 8 characters')`
- Confirm password: `z.refine(data => data.password === data.confirm, { message: 'Passwords must match', path: ['confirm'] })`
- Optional fields: `.optional()` or `.nullable()`

### Step 13.3 — Mutation pattern
1. `mutationFn`: API call
2. `onSuccess`: invalidate relevant queries + success toast + close drawer/modal
3. `onError`: `handleApiError(error)` — surfaces backend message via `toast.error()`
4. Submit button: `disabled={isPending}`, shows "Saving..." during pending

### Step 13.4 — Multi-step forms (wizard)
- Use `useForm` with mode `'onBlur'`
- Each step validates only its own fields via `trigger(['field1', 'field2'])`
- State persists across steps (single form instance)
- Back button: no validation required

### Step 13.5 — Credential forms specifically
- `autocomplete="off"` on all inputs
- `type="password"` for secrets
- Show/hide toggle for secret fields
- Never pre-fill from API response (write-only pattern)
- Never log form values in error boundaries

---

## 14. Data Flow & Backend Integration

### Step 14.1 — Request/Response flow
```
User action
  → React component calls hook (e.g., useCostsByDay)
    → TanStack Query checks cache
      → Cache hit (not stale): return cached data immediately
      → Cache miss / stale: call API module function
        → Axios client attaches Bearer token
          → 200: data stored in cache, component re-renders
          → 401: silent refresh → retry → succeed or logout
          → 429: wait Retry-After → retry once → surface error
          → 4xx: surface error message from response body
          → 5xx: surface generic error + allow retry
```

### Step 14.2 — Cache invalidation strategy

| Trigger | Invalidates |
|---------|------------|
| `sync.complete` WS event | costs, accounts, alerts, caps, forecasts |
| Create/delete cap | caps, alerts |
| Acknowledge/snooze alert | alerts, `useAlertsCount` |
| Recommend status change | recommendations |
| Connect account | accounts |
| Update notifications | notifications |
| Update org | org, me |
| Change role | team, me |
| Apply virtual tag rule | virtual-tags audit log |
| Ingest metric value | metrics, unit-economics |

### Step 14.3 — Backend connection points per screen

| Screen | Backend endpoints consumed |
|--------|--------------------------|
| Dashboard | `/costs`, `/costs/by-day`, `/costs/top-services`, `/forecasts`, `/scorecard`, `/caps`, `/recommendations`, `/accounts` |
| Costs | `/costs`, `/costs/by-day`, `/costs/by-service`, `/costs/by-tag`, `/costs/top-services` |
| Accounts | `/accounts`, `/accounts/:id`, `/accounts/:id/test`, `/accounts/:id/sync`, `/accounts/:id/sync-logs` |
| Caps | `/caps`, `/caps/:id` |
| Alerts | `/alerts`, `/alerts/:id/acknowledge`, `/alerts/:id/snooze` |
| Forecasts | `/forecasts`, `/forecasts/history` |
| Commitments | `/commitments`, `/commitments/summary`, `/commitments/expiring` |
| Recommendations | `/recommendations`, `/recommendations/:id/status`, `/llm/query` |
| Scorecard | `/scorecard`, `/scorecard/executive` |
| Resources | `/resources`, `/resources/idle`, `/resources/:id` |
| Virtual Tags | `/virtual-tags`, `/virtual-tags/:id/apply`, `/virtual-tags/audit-log`, `/virtual-tags/reorder` |
| Metrics | `/metrics`, `/metrics/:id/values`, `/metrics/unit-economics` |
| Assistant | `/llm`, `/llm/query` |
| Reports | `/reports`, `/reports/send-now` |
| Team | `/orgs/:id/team`, `/orgs/:id/team/invite`, `/orgs/:id/team/:id/role`, `/orgs/:id/team/:id` |
| Notifications | `/orgs/:id/notifications`, `/orgs/:id/notifications/test/*` |
| Webhooks | `/orgs/:id/webhooks`, `/orgs/:id/webhooks/:id/test` |
| API Keys | `/orgs/:id/api-keys` |
| Org | `/orgs/:id` |
| Auth | `/auth/*` |
| Health | `/health` |
| WS | `WS /ws?token=` |

### Step 14.4 — URL-param driven filter state

All cost and list filter state stored in URL search params (not component state):
- `useSearchParams()` to read
- `router.push` / `router.replace` to update (replace for filter changes, push for page changes)
- This makes browser back/forward work correctly and enables deep links

**⚠ Next.js 15 build requirement:** Any client component calling `useSearchParams()` MUST be isolated in its own Client Component and its parent must wrap it in `<Suspense>`. Failing to do so causes a build error or full-page CSR bailout. Pattern: `page.tsx` (Server Component) → `<Suspense fallback={<LoadingSkeleton />}>` → `<CostExplorerClient />` (Client Component with `useSearchParams`). Applies to: costs, alerts, resources, recommendations, virtual-tags pages.

### Step 14.5 — Pagination strategy
All list endpoints that may return large sets use page-based pagination:
- `page=1&size=20` default
- `Pagination` component reads/writes `page` from URL params
- `pageSize` stored in `uiStore` as user preference (20/50/100) — add `pageSize: 20` to `uiStore` persisted fields

### Step 14.6 — `org_id` in all requests
`orgId` always comes from `authStore.org.id`. Never hardcoded.
All API module functions accept `orgId` as first parameter.
Backend validates org membership on every request (multi-tenant isolation).

---

## 15. Error Handling & Edge Cases

### Step 15.1 — Error hierarchy

| Level | Handler | What it catches |
|-------|---------|----------------|
| Axios interceptor | 401 → silent refresh, 429 → retry | Network/auth errors before component sees them |
| Mutation `onError` | `handleApiError()` → `toast.error()` | Mutation failures |
| Query `isError` | `ErrorState` component | Data fetch failures |
| Route `error.tsx` | `Error` page | Unhandled render errors |
| Root `error.tsx` | Fallback page | Catastrophic errors |

### Step 15.2 — `lib/utils/errors.ts`
- `extractErrorMessage(error)`: pulls `detail` from FastAPI errors, handles both string and array
- `handleApiError(error, fallback?)`: calls `toast.error(extractErrorMessage(error))`
- `isAuthError(error)`: returns true for 401 (used to skip toast — silent refresh handles it)

### Step 15.3 — All edge cases

| Scenario | Frontend behavior |
|----------|------------------|
| Access token expires | Axios interceptor: silent refresh → retry. User never sees this. |
| Refresh token expires | `clearTokens()` → redirect `/login?from=<path>` → after login redirect back |
| WS token expires | `wsClient.reconnect(newToken)` triggered by authStore change listener |
| Celery down | `sync_mode: 'inline'` shown in connect response and sync logs |
| Redis degraded | `GET /health → degraded` → `HealthBanner` shows |
| Backend unreachable | `GET /health → error` → HealthBanner shows error variant |
| 0 accounts | Dashboard redirects to `/onboarding` |
| 0 cost data (accounts connected, sync not done) | EmptyState: "Syncing your first data — check back shortly" |
| LLM not configured | Assistant shows setup CTA; Explain button in Recs shows tooltip |
| No cap set for a provider | Forecast card shows "No cap set" pill, no progress bar |
| Invite expired | Accept-invite page shows specific "Invite expired" state |
| Rate limit (429) | Auto-retry once after `Retry-After` seconds; then `toast.error` |
| Webhook SSRF validation | Backend returns 400 with detail — surface to form field error |
| Owner protection | Backend returns 403 — surface `toast.error("Cannot change the owner's role")` |
| Remove self | Disabled in UI + backend validation |
| Duplicate cap | Backend 400 → surface as form-level error |
| Credentials after save | Never pre-filled from GET response; form starts empty |
| Sync rate limit (5/hr) | Backend 429 with specific message → "Sync limit reached. Try again after X" |

### Step 15.4 — `app/(app)/error.tsx`
- Shows "Something went wrong" with [Try again] (calls `reset()`)
- Shows error message in dev mode only
- In prod: generic message + link to dashboard

### Step 15.5 — `app/not-found.tsx`
- "Page not found" message
- Link back to `/dashboard`
- Matches app shell style

---

## 16. Transitions & Animations

### Step 16.1 — Page transitions
Next.js App Router doesn't have built-in page transitions. Strategy:
- Each `(app)` route's `page.tsx` root div gets `className="animate-slide-up"` (from Tailwind keyframe)
- Animation: `opacity: 0 + translateY(16px)` → `opacity: 1 + translateY(0)` in 200ms
- This gives each page a subtle "rise in" on navigate

### Step 16.2 — Drawer/sheet transitions
- Radix Sheet built-in: `slide-in-right` 250ms
- Backdrop: `fade-in` 150ms

### Step 16.3 — Modal transitions
- Radix Dialog built-in: `scale(0.95) + opacity(0)` → `scale(1) + opacity(1)` 150ms

### Step 16.4 — Toast transitions
Sonner handles: slide up from bottom-right, fade out on dismiss

### Step 16.5 — Tab transitions
Radix Tabs built-in content switch. No animation needed (instant is fine here).

### Step 16.6 — Sidebar collapse
`width 200ms ease-in-out` via CSS transition. Content shifts right/left smoothly.

### Step 16.7 — Progress bar fill
`transition: width 500ms ease` on cap progress bar fills — animated on first render.

### Step 16.8 — Chart mount
Recharts `isAnimationActive={true}` for all charts — bars/lines animate in on first render. Set `isAnimationActive={false}` on refetch (data update) to prevent jarring re-animation.

### Step 16.9 — Optimistic update animation
When an alert is acknowledged: row fades out (`opacity 0, translateY(-4px)`) over 200ms before being removed from active list.

### Step 16.10 — Skeleton → content transition
Skeleton components fade out when replaced by real content (`transition-opacity 200ms`).

---

## 17. Performance & Caching

### Step 17.1 — TanStack Query stale times

| Data type | staleTime | Reasoning |
|-----------|-----------|-----------|
| `/auth/me`, role | 10 min | Role changes are rare and immediately applied by backend |
| Health | 60 sec | Poll frequently to catch degraded state |
| Cost data | 5 min | Day-grain data — doesn't change until next sync |
| Accounts, sync status | 60 sec | Need reasonably fresh sync state |
| Alerts, alert count | 60 sec | Active alerts change after sync |
| Settings (team, webhooks, API keys) | 10 min | Low-change data |
| Forecasts | 5 min | Updated by daily job |
| Scorecard | 10 min | Updated by daily job |
| Recommendations | 5 min | Updated by daily job |

### Step 17.2 — Code splitting
Every chart component: `dynamic(() => import(...), { ssr: false })`
Reason: Recharts imports are heavy (~300KB) and don't support SSR.
Loading fallback: `.skeleton` div matching chart height.

### Step 17.3 — Route-level code splitting
Next.js App Router does this automatically per route segment. No manual splitting needed.

### Step 17.4 — Image optimization
- Use `next/image` for all images (provider logos, user avatars)
- Provider SVGs: use `<img>` (SVGs don't need optimization)
- Google avatars: `width={28} height={28}` on `<Image>` with `remotePatterns` configured

### Step 17.5 — Filter state in URL
Prevents double-fetch when user navigates back (cached page URL = cached query key).

### Step 17.6 — Virtualization
For large lists (resources, recommendations with 100+ items): consider `@tanstack/react-virtual` if performance issues arise. Not needed for typical FinOps orgs.

### Step 17.7 — Avoid unnecessary re-renders
- `useCallback` and `useMemo` only where profiling shows issues
- Avoid putting large data arrays in Zustand (use TanStack Query instead)
- `SortableTable` uses local sort state — doesn't trigger query refetch

---

## 18. Accessibility

### Step 18.1 — Semantic HTML
- Use correct heading hierarchy: h1 (page title) → h2 (section) → h3 (card header)
- Tables: proper `<thead>`, `<tbody>`, `<th scope="col">`, `<td>`
- Forms: each `<input>` has `<label>` with matching `htmlFor/id` or `aria-label`
- Buttons vs links: navigation = `<Link>` (or `<a>`), action = `<button>`

### Step 18.2 — Keyboard navigation
- All interactive elements reachable via Tab
- Modal/drawer: Radix handles focus trap + Escape close automatically
- Dropdown menus: Radix handles keyboard navigation (Arrow keys)
- Custom components: ensure `tabIndex={0}` + `onKeyDown` for Space/Enter

### Step 18.3 — Color contrast
- Text on white: gray-700 (`#374151`) on white = 7.4:1 (AAA)
- Muted text: gray-500 (`#6B7280`) on white = 4.6:1 (AA)
- Brand button: white on brand-500 = 3.0:1 (AA large text only → use on 16px+ text)
- Error text: danger-600 on white = 4.5:1 (AA)

### Step 18.4 — ARIA attributes
- Icon-only buttons: `aria-label="Sync now"` / `aria-label="Delete cap"`
- Toast container: `aria-live="polite"` for non-urgent, `aria-live="assertive"` for errors
- Loading skeletons: `aria-busy="true"` on container, `aria-label="Loading..."`
- Charts: `role="img"` with `aria-label="Spend by day chart: total $12,453 this month"`
- Status dots: `aria-label="Sync status: healthy"`
- Progress bars: `role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}`

### Step 18.5 — Focus rings
All focusable elements: `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2`
Never remove outline entirely (`outline: none` → replace with ring, not remove)

### Step 18.6 — Reduced motion
Respect `prefers-reduced-motion`:
```css
@media (prefers-reduced-motion: reduce) {
  .animate-shimmer, .animate-slide-up, .animate-slide-in { animation: none; }
  .transition-all, .transition-colors { transition: none; }
}
```

---

## 19. Security

### Step 19.1 — Token security
- Access token: in-memory only (not in localStorage, not in cookies from frontend)
- Refresh token: `sessionStorage` (cleared on tab close, not persisted across sessions)
- Never log tokens — `tokens.ts` exports opaque functions, never export raw token string

### Step 19.2 — Credential forms
- `autocomplete="off"` on all credential inputs (prevent browser autofill)
- `type="password"` for all secrets (even text-looking ones like `client_secret`)
- Never pre-fill from API GET response (all credential fields return masked)
- Error boundaries: never log form values in error reports

### Step 19.3 — Content Security Policy
In `next.config.ts` headers:
- `default-src 'self'`
- `script-src 'self' 'unsafe-eval'` (Next.js requires unsafe-eval in dev)
- `connect-src 'self' NEXT_PUBLIC_API_URL wss://NEXT_PUBLIC_WS_URL`
- `img-src 'self' data: https://lh3.googleusercontent.com`

### Step 19.4 — CORS
Backend `CORS_ORIGINS` = `NEXT_PUBLIC_APP_URL` (exact match). Frontend dev proxy means no CORS in development.

### Step 19.5 — API key display
Raw API key shown ONCE after creation in `CopyBlock`. Closing modal: "Have you copied your key?" confirm dialog. After close: only prefix shown, no recover path.

### Step 19.6 — XSS prevention
- Never use `dangerouslySetInnerHTML` except for sanitized markdown in LLM responses
- If LLM responses render HTML: use `DOMPurify.sanitize()` before rendering
- All user input rendered as text nodes, not HTML

### Step 19.7 — CSRF
- Backend uses `SameSite=Strict` on session cookies (if used)
- State parameter validated in OAuth flow (backend handles)
- All state-changing requests use POST/PUT/DELETE (never GET)

---

## 20. Mobile Responsiveness

### Step 20.1 — Breakpoints
Tailwind defaults: sm (640px), md (768px), lg (1024px), xl (1280px), 2xl (1536px)

### Step 20.2 — Sidebar responsive behavior
- `>= lg (1024px)`: sidebar visible, expanded by default
- `md–lg (768–1024px)`: sidebar auto-collapsed to icon-only
- `< md (768px)`: sidebar hidden, hamburger menu in TopBar → slide-in overlay

### Step 20.3 — Dashboard responsive grid
- `>= xl`: 4-col KPI row, 2+1 main row, 3-col lower row
- `lg–xl`: 2-col KPI row, 2-col main row (stacked), 2-col lower row
- `< lg`: 1-col all (stacked)

### Step 20.4 — Tables on mobile
- Tables wrap in `overflow-x-auto`
- Key columns pinned left (name/service)
- Less critical columns hidden on small screens via `hidden sm:table-cell`

### Step 20.5 — Drawers/modals on mobile
- Drawers: full-width on mobile (not 480px fixed)
- Modals: `max-w-[calc(100vw-32px)]` on mobile with `mx-4`
- Sheets (Radix Sheet): naturally full-width on mobile

### Step 20.6 — TopBar on mobile
- Collapse search button to icon-only (⌘K hint hidden)
- Keep: health dot + bell + avatar
- Add: hamburger menu icon (leftmost)

---

## 21. Testing Strategy

### Step 21.1 — `src/test/setup.ts`
- `import '@testing-library/jest-dom'` — DOM matchers
- MSW server lifecycle: `server.listen({ onUnhandledRequest: 'warn' })` / `server.resetHandlers()` / `server.close()`
- `console.error` filtered: suppress React `act()` warnings in test output
- `global.IntersectionObserver` mock — required by Radix Select, Popover
- `global.ResizeObserver` mock — required by Recharts `ResponsiveContainer`
- `window.matchMedia` mock — required by `next-themes`

### Step 21.2 — `src/test/handlers.ts` (MSW)
One handler per API endpoint. All handlers return realistic mock data matching the type definitions. Group by API module. Used for both unit and integration tests.

### Step 21.3 — `src/test/utils.tsx`
`renderWithProviders(ui, options?)`: renders with QueryClientProvider + fresh QueryClient + ThemeProvider + TooltipProvider. Fresh QueryClient per test (no cross-test cache pollution).

### Step 21.4 — What to test

**Unit tests (pure functions):**
- `formatCurrency()` — various currencies, compact mode
- `formatDelta()` — positive/negative/zero
- `extractErrorMessage()` — string detail, array detail, unknown error
- `cn()` — class merging correctness
- `ROLE_RANK` — ordering invariant
- `_azure_daily_windows()` equivalents in frontend date utils

**Hook tests (renderHook + MSW):**
- `useMe()` — returns user, handles 401
- `useLogin()` — sets tokens on success, redirects
- `useLogout()` — clears tokens, clears cache
- `useAlertsCount()` — polling, returns correct count
- `useWebSocket()` — cache invalidation on sync.complete

**Component tests:**
- `DataCard` — renders value, delta badge, estimated badge
- `CapProgressBar` — correct color at each threshold
- `DeltaBadge` — green for negative delta, red for positive
- `RoleGate` — hides for insufficient role, shows tooltip for disable mode
- `EmptyState` — renders action button when provided
- `SortableTable` — sorts correctly on column click
- `ConfirmDialog` — calls onConfirm, closes on cancel

**Integration tests (component + MSW):**
- Login form: submit → success → redirect
- Login form: submit → 401 → shows error
- Cap form: submit → creates cap → table updates
- Alert acknowledge: click → optimistic update → server confirm
- WS sync.complete: cost queries invalidated → new data shown

**E2E (Playwright — optional, Phase 5):**
- Full login → connect account → view dashboard flow
- Cap creation → alert trigger simulation

### Step 21.5 — Test coverage targets
- Utils: 100%
- Hooks: >80%
- Components: >70% (critical ones only)
- Forms: 100% validation paths

---

## 22. Build, Environment & Deployment

### Step 22.1 — Scripts
`dev` | `build` | `start` | `lint` | `typecheck (tsc --noEmit)` | `test` | `test:watch` | `format`

### Step 22.2 — Build verification
Before every deploy:
1. `npm run typecheck` — zero TypeScript errors
2. `npm run lint` — zero ESLint errors
3. `npm run test` — all tests pass
4. `npm run build` — successful build output

### Step 22.3 — Environment variables — full list

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | Backend FastAPI URL |
| `NEXT_PUBLIC_WS_URL` | Yes | WebSocket URL (`wss://` in prod) |
| `NEXT_PUBLIC_APP_URL` | Yes | This app's URL (for OAuth callback) |

### Step 22.4 — Backend environment alignment

| Frontend sets | Backend must have |
|---------------|------------------|
| `NEXT_PUBLIC_API_URL` | — |
| `NEXT_PUBLIC_APP_URL` | `FRONTEND_URL` (must match for CORS) |
| OAuth redirect | `GOOGLE_REDIRECT_URI = NEXT_PUBLIC_APP_URL/auth/oauth-callback` (register this exact URL in Google Console) |

### Step 22.5 — Deployment checklist

- [ ] `NEXT_PUBLIC_WS_URL` uses `wss://` (not `ws://` — TLS required in prod)
- [ ] Backend `CORS_ORIGINS` includes exact `NEXT_PUBLIC_APP_URL`
- [ ] Google OAuth: callback URL registered in Google Console = `NEXT_PUBLIC_APP_URL/auth/oauth-callback`
- [ ] Security headers configured in `next.config.ts`
- [ ] Remove `ReactQueryDevtools` in production build (auto-removed in prod mode)
- [ ] `NEXT_PUBLIC_*` vars are public — never put secrets in them

### Step 22.6 — Recommended deployment: Vercel
- Connect GitHub repo → Vercel auto-deploys on push
- Preview deployments per PR
- Environment variables set per environment (preview/production)
- Edge runtime for `middleware.ts` (auto-detected)

---

## 23. Implementation Order

### Phase 1 — Foundation (Week 1)
Everything that must exist before a single page can render.

| Task | Files |
|------|-------|
| 1. Project scaffold + all dependencies | `package.json`, `tailwind.config.ts`, `tsconfig.json` |
| 2. Design system + globals | `globals.css`, `tailwind.config.ts` |
| 3. All type definitions | `src/types/*.ts` (22 files) |
| 4. API client + all API modules | `lib/api/*.ts` (21 files) |
| 5. Query client + all query keys | `lib/query/queryClient.ts`, `lib/query/keys.ts` |
| 6. Token storage + auth guards | `lib/auth/tokens.ts`, `lib/auth/guards.ts` |
| 7. All Zustand stores | `lib/store/*.ts` |
| 8. All custom hooks | `lib/hooks/*.ts` (25 files) |
| 9. Constants (routes, roles, providers) | `lib/constants/*.ts` |
| 10. Utility functions | `lib/utils/*.ts` |
| 11. Root layout + providers | `app/layout.tsx`, `app/providers.tsx` |
| 12. AuthBootstrap + AppSkeleton | `components/auth/AuthBootstrap.tsx`, `components/layout/AppSkeleton.tsx` |
| 13. Edge middleware | `middleware.ts` |
| 14. WS client + wsEvents | `lib/ws/wsClient.ts`, `lib/ws/wsEvents.ts` |
| 15. Shared components (all common/) | `components/common/*.tsx` (16 components) |
| 16. All chart components | `components/charts/*.tsx` (7 components) |
| 17. All `loading.tsx` route files | 17 files — one per app route (see folder structure) |
| 18. `OfflineBanner.tsx` | `components/layout/OfflineBanner.tsx` |

### Phase 2 — Auth + Shell + Core (Week 2)

| Task | Why this order |
|------|---------------|
| Auth pages (login, signup, verify, forgot, reset, accept-invite, oauth-callback) | Can't enter app |
| App shell (sidebar, topbar, health banner, notifications panel, user menu, command palette) | Shell needed before any page |
| `useWebSocket` + HealthBanner integration | Real-time from day 1 |
| Dashboard page (all sub-components) | Daily anchor — validates entire data flow |
| Accounts page + Account detail + Connect wizard | No data without accounts |

### Phase 3 — Cost Management Core (Week 3)

| Task |
|------|
| Costs explorer (all 4 tabs) |
| Budget Caps (list + drawer) |
| Alerts (list + acknowledge/snooze + notifications panel) |
| Forecasts |
| FinOps Scorecard |

### Phase 4 — Power Features (Week 4)

| Task |
|------|
| Commitments |
| Recommendations (with LLM explain) |
| Resources (all + idle) |
| Virtual Tags (rules + apply + audit log) |
| Business Metrics + unit economics |
| AI Assistant |
| Reports |
| Onboarding wizard |

### Phase 5 — Settings + Polish (Week 5)

| Task |
|------|
| All settings pages (profile, org, team, notifications, webhooks, api-keys, llm) |
| `not-found.tsx` and `error.tsx` pages |
| Settings sub-layout secondary nav |
| Skeleton loaders on every async component |
| Empty states on every page |
| Command palette full implementation |
| Responsive layout (mobile sidebar hamburger) |
| Dark mode toggle in profile |
| Page transition animations |
| Reduced motion support |
| Accessibility audit (all ARIA attrs, contrast, keyboard nav) |
| Dynamic imports for all charts |
| All unit tests (utils, hooks, components) |
| MSW integration tests (auth flow, cost flow, alert flow) |
| `npm run typecheck` — zero errors |
| `npm run lint` — zero warnings |
| Lighthouse CI ≥ 90 performance |
| Deployment checklist completion |

---

## Appendix A — Route Constants

```
/login | /signup | /verify-email | /forgot-password | /reset-password
/accept-invite | /auth/oauth-callback
/onboarding
/dashboard
/costs
/accounts | /accounts/connect | /accounts/[id]
/forecasts | /commitments | /recommendations | /scorecard | /resources
/caps | /alerts | /virtual-tags | /metrics | /assistant | /reports
/settings/profile | /settings/org | /settings/team
/settings/notifications | /settings/webhooks | /settings/api-keys | /settings/llm
```
Total: 25 routes — all backed by existing backend APIs.

## Appendix B — RBAC Reference

| Action | Min Role |
|--------|----------|
| View any data | viewer |
| Acknowledge/snooze alert | viewer |
| Submit LLM query | viewer |
| Create/edit caps | editor |
| Update recommendation status | editor |
| Ingest metric value | editor |
| Create/edit virtual tag rules | editor |
| Connect/update/test/sync accounts | admin |
| Update org settings | admin |
| Invite/remove team members | admin |
| Update notifications | admin |
| Create/delete API keys | admin |
| Create/delete webhooks | admin |
| Configure LLM | admin |
| Send report now | admin |
| Delete account (soft) | admin |
| Delete cap | admin |
| Change role (not owner) | admin |
| All owner actions | owner |

## Appendix C — Component Rendering Contract

Every data-fetching component MUST handle all 4 states:
1. **Loading:** `<LoadingSkeleton variant="..." />` matching component shape
2. **Error:** `<ErrorState message={} retry={refetch} />`
3. **Empty:** `<EmptyState title="" message="" action={} />`
4. **Data:** render the actual component

No component may throw or render blank for any of these states.

---

*Build in Phase order. Each phase is independently deployable and testable. Never skip a phase — every phase's output is the foundation for the next.*

---

## 24. Gap Fixes & Critical Corrections

> This section documents every gap found in the plan above and the precise fix for each.

---

### Gap 1 — Next.js Middleware Bypass (CVE-2025-29927) [SECURITY CRITICAL]

**Problem:** The middleware in `src/middleware.ts` checks for a session cookie and redirects unauthenticated users. However, CVE-2025-29927 allows attackers on self-hosted/Docker deployments to bypass middleware entirely by sending the `x-middleware-subrequest` header. Middleware-only auth = broken auth in self-hosted setups.

**Fix — Two-layer auth (middleware is defense-in-depth only, NOT the sole gate):**

**Layer 1 (middleware):** Keep session cookie check for fast redirect at edge. Never treat it as proof of valid session.

**Layer 2 (app layout server-side):** `src/app/(app)/layout.tsx` — After rendering, the client-side `useMe()` call to `GET /auth/me` is the TRUE auth gate. If the backend returns 401 (token invalid/expired), the Axios interceptor attempts refresh. If refresh fails, redirects to `/login`. This cannot be bypassed by any HTTP header.

**Additional fix:** Pin Next.js version to `>= 15.2.3` in `package.json` with `engines` field:
```json
"engines": { "node": ">=20" },
"dependencies": { "next": ">=15.2.3" }
```

**Rule:** Middleware handles redirects for UX speed. Backend token validation handles actual security. Never rely on middleware alone.

---

### Gap 2 — Missing `date-fns-tz` dependency

**Problem:** Plan says "format dates with org timezone" but `date-fns` does not handle IANA timezone conversions. Org has `timezone: "America/New_York"` etc.

**Fix — Add to dependencies:**
```
npm install date-fns-tz
```

**`lib/utils/dates.ts` full specification:**
- `import { formatInTimeZone, toZonedTime, fromZonedTime } from 'date-fns-tz'`
- `formatDate(isoString, tz, fmt = 'MMM d, yyyy')` → converts ISO string to org timezone, formats with date-fns
- `formatRelative(isoString)` → `"2 hours ago"`, `"3 days ago"` (no timezone adjustment needed)
- `toOrgTz(date, tz)` → returns Date in org's timezone
- `getOrgNow(tz)` → current time in org's timezone (used for greeting "Good morning/afternoon/evening")
- `formatDateForApi(date)` → `"2026-11-13"` UTC ISO date string (for API params)
- `formatDateTimeForApi(date)` → `"2026-11-13T00:00:00Z"` (for snooze until)
- All format tokens: use `date-fns` format strings (`'MMM d'`, `'MMM d, yyyy'`, `'h:mm a'`)

---

### Gap 3 — Missing Utility Function Specifications

**`lib/utils/currency.ts`:**
- `formatCurrency(amount: number, currency: string, compact = false): string`
  - Uses `Intl.NumberFormat(undefined, { style: 'currency', currency, notation: compact ? 'compact' : 'standard', maximumFractionDigits: compact ? 1 : 2 })`
  - Compact: `$1.2M`, `$14.2k`, `$890.00` (no compact below 10k)
  - Standard: `$12,453.20`
  - Rule: always pass `org.currency` from authStore — never hardcode `'USD'`
- `parseCurrencyInput(str: string): number` — strips symbols, parses float
- `getCurrencySymbol(currency: string): string` — `'$'`, `'€'`, `'£'`, `'₹'` etc.

**`lib/utils/delta.ts`:**
- `formatDelta(pct: number | null, opts?: { label?: string }): string` — `"+12.4% vs last month"` or `"−3.2%"`
- `getDeltaDirection(pct: number): 'up' | 'down' | 'neutral'`
- `isDeltaPositive(pct: number): boolean` — NOTE: for COST, positive delta = bad (more spend). Components should handle this semantic (DeltaBadge already does: positive = red, negative = green).

**`lib/utils/providers.ts`:**
- `getProviderColor(provider: string): string` — returns hex, falls back to `'#6B7280'`
- `getProviderLabel(provider: string): string` — `'AWS'`, `'Azure'`, `'Google Cloud'`, fallback `provider`
- `getProviderLogo(provider: string): string` — returns `/providers/aws.svg` etc.
- `ALL_PROVIDERS: Provider[]` — `['aws', 'azure', 'gcp']`
- `isValidProvider(str: string): str is Provider` — type guard

**`lib/utils/download.ts`:**
- `triggerCsvDownload(data: string | Blob, filename: string): void`
  - Creates object URL → creates `<a>` element with `download` attribute → clicks it → revokes URL
  - For API CSV: `GET /costs/by-service?format=csv` returns blob → pass directly
  - Filename format: `prism-costs-by-service-2026-11-13.csv`

**`lib/utils/errors.ts`:** (already has spec but add this)
- `isRateLimitError(error: unknown): boolean` — checks `error.response?.status === 429`
- `getRetryAfterSeconds(error: unknown): number` — reads `Retry-After` header, defaults 60

---

### Gap 4 — Proactive Token Refresh (Don't Wait for 401)

**Problem:** Current plan only refreshes tokens reactively on 401. But:
1. JWT expires every 15 minutes
2. If user is idle and then acts, all queued requests will fail simultaneously and trigger concurrent refresh attempts (the queue in the interceptor handles this but it's still reactive)
3. Better: refresh proactively 2 minutes before expiry

**Fix — Add to `lib/auth/tokens.ts`:**
- `decodeTokenExpiry(token: string): number` — decode JWT payload (base64), return `exp` field (epoch seconds). Use `atob(token.split('.')[1])` — no library needed.
- `scheduleProactiveRefresh(accessToken: string, refreshFn: () => void): () => void` — schedules `setTimeout` to call `refreshFn` at `(exp - 120) * 1000 - Date.now()` ms. Returns cleanup function.

**Add to `AuthBootstrap.tsx`:**
- After successfully setting tokens, call `scheduleProactiveRefresh(accessToken, () => authApi.refresh(refreshToken))`
- On cleanup (unmount): cancel the timer
- After every token refresh (in Axios interceptor): reschedule the timer with new access token

---

### Gap 5 — Multi-Tab Session Sync

**Problem:** User logs out in tab A. Tab B still shows the authenticated app (tokens in memory). If they click anything, Axios interceptor will try to use the in-memory token, fail, then try to refresh from `sessionStorage` — but `sessionStorage` is tab-isolated, so refresh token is still present. Net result: other tabs don't log out.

**Fix — `lib/auth/tokens.ts`:**
Use a `localStorage` sentinel (not the token itself — the token stays in sessionStorage):
- On `setTokens(access, refresh)`: write `localStorage.setItem('prism_session_active', '1')`
- On `clearTokens()`: write `localStorage.setItem('prism_session_active', '0')` then `localStorage.removeItem('prism_session_active')`

**Add listener in `AuthBootstrap.tsx`:**
- `window.addEventListener('storage', (e) => { if (e.key === 'prism_session_active' && e.newValue === '0') { clearTokens(); authStore.clear(); router.push('/login'); } })`
- This fires in all OTHER tabs when one tab calls `clearTokens()`
- Remove listener on unmount

---

### Gap 6 — `useSearchParams` Suspense Boundary (Next.js 15 Build Requirement)

**Problem:** Next.js 15 App Router **builds will fail** (or bail out to full CSR) if any component calls `useSearchParams()` without being wrapped in `<Suspense>`. The costs page uses `useSearchParams` extensively.

**Fix — Pattern for every page using `useSearchParams`:**

For `costs/page.tsx` and any other page using URL-param filters:
1. The `page.tsx` is a Server Component (no `'use client'`)
2. Extract all `useSearchParams` logic into a separate Client Component: `CostExplorerClient.tsx`
3. In `page.tsx`: wrap `<CostExplorerClient />` in `<Suspense fallback={<LoadingSkeleton variant="chart" />}>`

**Affects these pages:** costs, resources, recommendations, alerts, resources, virtual-tags (any that use URL filter params)

**Rule:** Any client component using `useSearchParams` MUST be isolated and its parent must wrap it in `<Suspense>`.

---

### Gap 7 — Missing `loading.tsx` Files

**Problem:** Without `loading.tsx`, navigating to a dynamic route in Next.js App Router shows a blank screen until the server responds. Instant navigation requires these files.

**Fix — Add these files to folder structure and Phase 1 build list:**

```
src/app/(app)/
├── loading.tsx                    ← Covers all app routes
├── dashboard/loading.tsx          ← Dashboard-specific skeleton
├── costs/loading.tsx
├── accounts/loading.tsx
├── accounts/[id]/loading.tsx
├── forecasts/loading.tsx
├── commitments/loading.tsx
├── recommendations/loading.tsx
├── scorecard/loading.tsx
├── resources/loading.tsx
├── caps/loading.tsx
├── alerts/loading.tsx
├── virtual-tags/loading.tsx
├── metrics/loading.tsx
├── assistant/loading.tsx
├── reports/loading.tsx
└── settings/
    └── loading.tsx                ← Covers all settings sub-routes
```

Each `loading.tsx` exports a default function returning `<LoadingSkeleton variant="X" />` matching the page shape. This creates a Suspense boundary automatically.

---

### Gap 8 — Missing Route: `/auth/oauth-callback`

**Problem:** Plan describes the OAuth callback flow in Section 8.5 and Section 12.1, but `src/app/(auth)/oauth-callback/page.tsx` is not in the folder structure.

**Fix — Add to folder structure:**
```
src/app/
├── (auth)/
│   ├── login/page.tsx
│   ├── signup/page.tsx
│   ├── verify-email/page.tsx
│   ├── forgot-password/page.tsx
│   ├── reset-password/page.tsx
│   ├── accept-invite/page.tsx
│   └── oauth-callback/page.tsx   ← ADD THIS
```

**Route behavior:**
- Google redirects to `FRONTEND_URL/auth/oauth-callback?code=X&state=Y`
- Page calls `POST /auth/oauth/exchange?code=X&state=Y`
- Loading: spinner centered, "Completing sign in..."
- Success: `setTokens()` + redirect to `?from` param or `/dashboard`
- Error: redirect to `/login?oauth_error=1` → login page shows toast "Google sign-in failed. Please try again."

---

### Gap 9 — WebSocket: Graceful Degradation + Security + Token Expiry

**9a — Graceful degradation when WS unavailable:**
If WS never connects after 3 attempts, frontend must still work. All critical data has polling via TanStack Query. Document this in `useWebSocket`:
- After 3 failed reconnect attempts: set `wsStore.wsUnavailable = true`
- Show no visible error — just rely on stale TanStack Query refetch
- Dashboard data: `refetchOnWindowFocus: true` when wsUnavailable (more aggressive refresh)
- After 30 min without WS: auto-retry connection reset (clear reconnect counter)

**9b — WS token refresh during open connection:**
Access token expires every 15 minutes. The WS connection opened at minute 0 becomes invalid at minute 15.

Fix sequence in `wsClient.ts`:
- Add `updateToken(newToken: string)` method
- When Axios interceptor successfully refreshes (gets new access token): call `wsClient.updateToken(newToken)`
- `updateToken` closes the current WS connection cleanly and reconnects with the new token
- Reconnect uses the same exponential backoff as normal reconnect

**9c — WS origin check:**
Backend MUST validate the `Origin` header on WS upgrade against `FRONTEND_URL`. This is a backend concern but document that frontend never needs to work around it — if connection fails due to origin mismatch, it shows up as a failed WS connection and falls back gracefully.

**9d — WS maximum connection lifetime:**
Set a 55-minute ceiling timer in `wsClient`. After 55 minutes, proactively close and reconnect with fresh token (tokens are refreshed every 13 min by proactive refresh, so token is always fresh). Prevents long-lived connections from going stale.

---

### Gap 10 — Polling Stop Conditions

**Problem:** Plan says "poll every 10s" but doesn't specify when to stop. Polling forever wastes resources.

**Fix — Specify stop conditions for all polling:**

**Sync Logs Drawer (`useSyncLogs`):**
```
refetchInterval: (query) => {
  const logs = query.state.data
  if (!logs?.length) return 5_000  // keep polling if no logs yet
  const latest = logs[0]
  if (latest.status === 'success' || latest.status === 'failed') return false  // STOP
  return 10_000  // still running → keep polling
}
```

**Virtual Tag Apply Progress (`useVtagAudit`):**
```
refetchInterval: (query) => {
  const audit = query.state.data
  if (!audit?.length) return 3_000
  const latest = audit[0]
  if (latest.status === 'completed' || latest.status === 'failed') return false  // STOP
  return 3_000
}
```

**Health polling:** Always poll every 60s — health can change at any time, no stop condition.

**Alert count polling:** Always poll every 60s — new alerts can arrive at any time.

**Drawer unmount cleanup:** When SyncLogsDrawer or ApplyProgressDrawer closes, the query's `enabled` prop should be set to `false` to disable the interval. Use `enabled: isDrawerOpen` in the query options.

---

### Gap 11 — LLM Streaming Implementation

**Problem:** Plan says "stream response if backend supports" but doesn't describe how.

**Fix — Two cases:**

**Case A — Backend does NOT stream (current FastAPI implementation returns full response):**
1. Submit question via `POST /llm/query`
2. Show loading spinner in chat bubble
3. On response: render full answer, animate text in with `typing` CSS animation (not real streaming)
4. Animation: show answer character by character via `setInterval` + substring slice — cosmetic only

**Case B — If backend adds SSE streaming in the future:**
1. Use `fetch()` directly (not Axios) with `Accept: text/event-stream`
2. `const reader = response.body.getReader()`
3. Decode chunks with `TextDecoder`, parse `data: {...}` SSE frames
4. Append each token to chat message state
5. When stream ends (`data: [DONE]`), mark message complete

**Default behavior: Case A.** Add `NEXT_PUBLIC_LLM_STREAMING=false` env flag to switch to Case B when ready.

---

### Gap 12 — TanStack Query v5 Optimistic Update Pattern (Corrected)

**Problem:** Previous description was for TanStack Query v4. The API changed in v5.

**v5 Correct pattern** (applies to ALL mutations with optimistic update):

```
onMutate: async (variables, context) => {
  // 1. Cancel in-flight refetches (prevent overwriting our optimistic write)
  await context.client.cancelQueries({ queryKey: qk.alerts(orgId, {}) })
  
  // 2. Snapshot current data
  const previous = context.client.getQueryData(qk.alerts(orgId, {}))
  
  // 3. Apply optimistic update
  context.client.setQueryData(qk.alerts(orgId, {}), (old) => applyChange(old, variables))
  
  // 4. Return snapshot for potential rollback
  return { previous }
},
onError: (error, variables, onMutateResult) => {
  // Restore from snapshot
  if (onMutateResult?.previous) {
    queryClient.setQueryData(qk.alerts(orgId, {}), onMutateResult.previous)
  }
},
onSettled: (data, error, variables, onMutateResult, context) => {
  // Always reconcile with server truth
  context.client.invalidateQueries({ queryKey: qk.alerts(orgId, {}) })
}
```

**Key v5 differences from v4:**
- `context.client` is the QueryClient (not imported separately)
- `onMutate(variables, context)` — 2nd arg is `MutationFunctionContext`
- `onError(error, variables, onMutateResult, context)` — 4th arg for rollback data

**Applies to:** alert acknowledge/snooze, recommendation status update, cap edit, virtual tag reorder, metric ingest value.

---

### Gap 13 — Network Offline Handling

**Problem:** If the user loses internet connection, all API calls fail. No feedback shown.

**Fix — Add `OfflineBanner` component:**

**`components/layout/OfflineBanner.tsx`:**
- Uses `navigator.onLine` initial state + `window.addEventListener('online'/'offline')`
- When offline: amber banner above HealthBanner — "No internet connection — changes won't be saved"
- When back online: auto-dismiss with "Back online" toast + `queryClient.invalidateQueries()` to refresh stale data

**TanStack Query config addition in `queryClient.ts`:**
```
networkMode: 'offlineFirst'
```
This makes queries return cached data while offline instead of immediately erroring. Mutations queue and retry when network returns.

**Add to `app/(app)/layout.tsx`:** Render `<OfflineBanner />` above `<HealthBanner />`

---

### Gap 14 — GCP Service Account JSON File Upload

**Problem:** GCP credential form shows a textarea for `service_account_json`. Users have a `.json` file downloaded from Google Console. Making them copy-paste JSON is a poor UX.

**Fix — `AwsCredentialForm.tsx` / `GcpCredentialForm.tsx`:**
GCP `service_account_json` field:
1. Show file input button: `[📎 Upload service account JSON]`
2. `accept=".json"` — browser file picker, JSON files only
3. `FileReader.readAsText(file)` → validates it's valid JSON → populates the textarea
4. Textarea still visible (editable fallback for paste)
5. Show filename badge: `"service-account.json ✓"` after upload
6. Clear button to reset

---

### Gap 15 — `uiStore` Additional Persisted Preferences

**Problem:** User switches cost view to "Amortized" then navigates away — preference is lost. Same for date range default.

**Fix — Add to `uiStore.ts`:**
```
// Persisted user preferences
costView: 'unblended' | 'amortized'          // default: 'unblended'
defaultDateRangePreset: '7d' | '30d' | 'month' // default: 'month'
recentPages: string[]                          // last 5 visited paths for CommandPalette
```

**How used:**
- `CostFilters.tsx` reads `costView` from `uiStore` as default, URL param overrides it
- When user changes cost view: update both URL param AND `uiStore`
- `DateRangePicker` reads `defaultDateRangePreset` as default selection
- `recentPages` updated in `app/(app)/layout.tsx` on route change

---

### Gap 16 — Empty States for Every Screen

**Problem:** Plan describes `EmptyState` component but doesn't specify what each page shows.

| Page | Empty condition | Title | Message | CTA |
|------|----------------|-------|---------|-----|
| Dashboard | 0 accounts | "Connect your first cloud account" | "PRISM needs at least one account to start tracking costs." | "Connect Account →" → `/accounts/connect` |
| Dashboard | Accounts connected, no cost data yet | "Data syncing..." | "Your first sync is in progress. Come back in a few minutes." | "View sync status →" → `/accounts` |
| Costs | No cost records | "No cost data for this period" | "Try a different date range or wait for your next sync." | "Trigger sync →" |
| Accounts | 0 accounts | "No cloud accounts connected" | "Connect AWS, Azure, or GCP to start tracking your cloud spend." | "Connect Account →" |
| Caps | 0 caps | "No budget caps set" | "Set caps to get alerts when your cloud spend exceeds your budget." | "Create Cap →" |
| Alerts | 0 alerts (active) | "No active alerts" | "All your budget thresholds are within range." | null |
| Alerts | 0 alerts (ack'd) | "No acknowledged alerts" | null | null |
| Forecasts | No data | "No forecast data yet" | "Forecasts are generated after 7 days of cost data." | null |
| Commitments | 0 commitments | "No commitments tracked" | "Reserved Instances, Savings Plans, and CUDs will appear here after sync." | null |
| Recommendations | 0 open | "No open recommendations" | "PRISM will suggest cost savings opportunities after analyzing your spend." | null |
| Recommendations | 0 implemented | "No implemented recommendations" | "Mark a recommendation as implemented to track your savings." | null |
| Scorecard | No data | "Scorecard unavailable" | "The scorecard needs at least 14 days of cost data." | null |
| Resources | 0 resources | "No resources discovered" | "Resources are populated after your first sync." | null |
| Resources (idle) | 0 idle | "No idle resources found" | "Great! All your resources appear to be active." | null |
| Virtual Tags | 0 rules | "No virtual tag rules" | "Create rules to categorize resources that lack proper cloud tags." | "New Rule →" |
| Metrics | 0 metrics | "No business metrics" | "Add metrics like MAU or API requests to calculate unit economics." | "Add Metric →" |
| Assistant | LLM not configured | "AI Assistant not configured" | "Configure your LLM API key in Settings to enable AI-powered cost analysis." | "Configure →" (admin only) |
| Reports | — | (config form always shows, never empty) | — | — |
| Team | 1 member only | "Just you so far" | "Invite your team to collaborate on cloud cost management." | "Invite Member →" |
| Webhooks | 0 webhooks | "No webhooks configured" | "Connect PRISM events to your systems via outbound webhooks." | "Add Webhook →" |
| API Keys | 0 keys | "No API keys" | "Create API keys for programmatic access to PRISM data." | "Create Key →" |
| Sync logs | No logs | "No sync history" | "Trigger a sync to populate this list." | null |

---

### Gap 17 — Virtual Tag Rule Priority Drag-to-Reorder Spec

**Problem:** Plan says "drag-to-reorder" but doesn't specify when the API call fires.

**Fix:**
- Use `@dnd-kit/core` and `@dnd-kit/sortable` for drag-and-drop (lighter than react-beautiful-dnd, works in React 18+)
- Add to dependencies: `npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities`
- **On drag end:** Optimistically reorder the list in state + immediately call `PUT /virtual-tags/reorder` with the new ordered `rule_ids` array
- On error: rollback to previous order + toast "Failed to save order"
- Mobile fallback: Up/Down arrow buttons on each row (no drag library needed on mobile)

---

### Gap 18 — `src/test/setup.ts` Contents

**Problem:** Plan mentions this file but doesn't specify what goes in it.

**Fix — Full contents:**
```typescript
// 1. jest-dom matchers
import '@testing-library/jest-dom'

// 2. MSW server lifecycle
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
afterEach(() => server.resetHandlers())   // reset per-test overrides
afterAll(() => server.close())

// 3. Silence expected console.error in tests (e.g. React act() warnings)
const originalConsoleError = console.error
beforeAll(() => {
  console.error = (...args: unknown[]) => {
    if (typeof args[0] === 'string' && args[0].includes('act(')) return
    originalConsoleError(...args)
  }
})
afterAll(() => { console.error = originalConsoleError })

// 4. Mock IntersectionObserver (used by Radix Select, Popover)
global.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} }

// 5. Mock ResizeObserver (used by Recharts ResponsiveContainer)
global.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }

// 6. Mock window.matchMedia (used by next-themes)
Object.defineProperty(window, 'matchMedia', {
  value: (query: string) => ({ matches: false, media: query, onchange: null,
    addListener: () => {}, removeListener: () => {}, addEventListener: () => {},
    removeEventListener: () => {}, dispatchEvent: () => false })
})
```

---

### Gap 19 — `lib/utils/cn.ts` Already Correct + `lib/utils/providers.ts` Chart Colors Map

**Add to `lib/utils/providers.ts`:**
```
// Chart series palette — for non-provider charts (recommendations, resources)
export const CHART_COLORS = [
  '#6366F1', // brand
  '#22C55E', // success
  '#F59E0B', // warning
  '#3B82F6', // info
  '#EC4899', // pink
  '#8B5CF6', // violet
  '#14B8A6', // teal
  '#F97316', // orange
]
```

---

### Gap 20 — Number Formatting for Large Currency Values

**Problem:** Dashboard will show values like `$1,243,521.40` — too verbose for KPI cards.

**Fix — `formatCurrency` compact rules:**
- `< $1,000`: show full — `$843.20`
- `$1,000 – $9,999`: show full with comma — `$4,231.00`
- `$10,000 – $999,999`: compact — `$14.2k`
- `>= $1,000,000`: compact — `$1.2M`
- In tables and tooltips: always use full format for precision
- In KPI cards and chart axes: use compact format

---

### Gap 21 — Font Loading Optimization

**Problem:** Inter loaded via `next/font/google` is correctly optimized but default `font-display` behavior should be verified.

**Fix — In `app/layout.tsx`:**
```typescript
const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',  // prevent FOIT (flash of invisible text)
})
const mono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  weight: '400',
  display: 'swap',
})
```

---

### Gap 22 — Provider Logos Image Optimization

**Problem:** Provider logos in `AccountCard`, `ProviderBadge`, etc. are SVGs. Next.js `<Image>` doesn't add value for SVGs (no optimization). But avatar images from Google need proper `Image` usage.

**Fix:**
- Provider logos (`.svg`): use regular `<img>` tag with explicit `width` and `height`. SVG is vector — no optimization needed.
- Google avatar URLs: use `next/image` `<Image>` with `width={28} height={28}` and `loading="eager"` (they appear in layout on every page)
- User-uploaded avatars (future): use `next/image` with `fill` prop

---

### Gap 23 — Tab Visibility API for WS Ping Optimization

**Problem:** Browser tabs send WS pings every 25s even when the tab is hidden. Wastes resources and may cause proxy timeouts.

**Fix — Add to `wsClient.ts`:**
```
// Pause ping when tab is hidden, resume when visible
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') {
    this._stopPing()
  } else {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this._startPing()
    } else {
      this._open()  // reconnect if connection dropped while hidden
    }
  }
})
```

---

### Gap 24 — `react-day-picker` Version Compatibility

**Problem:** shadcn/ui `calendar` component requires a specific version of `react-day-picker`. As of shadcn/ui latest, it uses `react-day-picker` v8. Installing v9 breaks it.

**Fix — Pin version:**
```
npm install react-day-picker@8.x
```
Or use shadcn's `add calendar` command which installs the correct version automatically:
```
npx shadcn@latest add calendar
```
Do NOT manually install `react-day-picker` — always install via shadcn to get the compatible version.

---

### Gap 25 — `CommandPalette` Full Keyboard Behavior Spec

**Problem:** Plan mentions `⌘K` opens it but doesn't fully specify keyboard behavior.

**Fix — Complete keyboard spec using `cmdk`:**
- `⌘K` / `Ctrl+K`: open
- `Escape`: close (Radix Dialog handles this automatically)
- `↑` / `↓`: navigate items
- `Enter`: select item, navigate/execute action, close palette
- `Backspace` (when input empty): clear group filter
- Typing: filters all groups simultaneously
- If 0 results: show "No results found" message

**Data sources for search:**
1. Static: all 25 route labels with their icons
2. Dynamic (from TanStack Query cache — no extra API calls):
   - `useAccounts` cache: account names
   - `useAlerts` cache: "X active alerts"
3. Actions: "Connect account", "Create cap", "Invite team member", "Sync now"

**Result rendering:** Group headers + item rows. Max 5 items per group. Keyboard focus indicated by brand-100 bg.

---

### Gap 26 — `PasswordStrengthBar` Rules

**Problem:** Listed in folder structure but not specified.

**Fix:**
- Accepts `password: string`
- 4 strength levels: Weak / Fair / Strong / Very Strong
- Scoring: length ≥8 (+1), ≥12 (+1), has number (+1), has special char (+1), has uppercase (+1)
- Score 1 = Weak (red), 2 = Fair (amber), 3 = Strong (green), 4 = Very Strong (brand-500)
- Visual: row of 4 segment bars with color fill
- Text: strength label below bars
- Never block submission — visual hint only

---

### Gap 27 — Webhook Signing Secret UX

**Problem:** Plan mentions "signing secret: auto-generated UUID" but doesn't specify when/how to show/regenerate it.

**Fix:**
- On webhook CREATE: auto-generate UUID server-side. Show in `CopyBlock` in the create drawer. Warn: "Save this secret — it won't be shown again."
- On webhook LIST/EDIT: show only the prefix (`prism_wh_abc123...`) in table
- Regenerate button: `[Regenerate Secret]` → confirm dialog → generates new secret → shows once in modal

---

### Gap 28 — Settings Profile: Delete Account Danger Zone

**Problem:** Plan mentions "delete account with 'DELETE' confirm" but doesn't specify the full flow.

**Fix:**
- Section at bottom of Profile page: "Danger Zone" (red border card)
- `[Delete Account]` button (red, outline)
- Modal: "This action is permanent. Type DELETE to confirm."
  - Text input: validates exact string "DELETE"
  - Confirm button disabled until input matches
  - On confirm: `DELETE /v1/auth/me` → clears all tokens → redirects to `/login`
  - Backend deletes: user record, memberships, owned orgs (if last owner)
  - If not last owner: removes from org only

---

### Gap 29 — Alerts Page: Pagination and Infinite Scroll Clarification

**Problem:** Original plan in `frontend.md` mentioned infinite scroll for alerts, but `frontend-plan.md` says cursor pagination. Need to reconcile.

**Fix — Use cursor-based infinite scroll for alerts ONLY:**
Rationale: alerts are a feed (read top-to-bottom, load more as you scroll), not a data table.

Implementation:
- Use TanStack Query `useInfiniteQuery` for alerts
- `GET /alerts?cursor=<last_id>&limit=20`
- `IntersectionObserver` on last row → `fetchNextPage()`
- Each "page" of 20 alerts appended to list (not replaced)
- **All other lists (caps, resources, team, etc.):** use regular page-based pagination with `Pagination` component

---

### Gap 30 — Route Group: `(app)` Layout Should Redirect `/` to `/dashboard`

**Problem:** When user visits `https://app.prism.com/` (root), nothing handles the route. No redirect specified.

**Fix — Add `src/app/page.tsx` (root):**
```
// Server Component — just redirect
import { redirect } from 'next/navigation'
export default function Home() {
  redirect('/dashboard')
}
```
This handles the root URL. Middleware also catches it, but explicit redirect is cleaner.

---

### Gap 31 — Missing `team.ts` from API Folder Structure

**Problem:** `lib/api/team.ts` is mentioned in hooks (Step 6.2) but was missing from the original folder structure listing.

**Fix — Confirm `lib/api/` contains these files (complete list):**
```
lib/api/
├── client.ts
├── auth.ts
├── org.ts          ← orgs/:orgId CRUD
├── team.ts         ← orgs/:orgId/team CRUD  ← WAS MISSING
├── accounts.ts
├── costs.ts
├── caps.ts
├── alerts.ts
├── notifications.ts
├── reports.ts
├── recommendations.ts
├── forecasts.ts
├── commitments.ts
├── scorecard.ts
├── resources.ts
├── virtual-tags.ts
├── webhooks.ts
├── llm.ts
├── metrics.ts
├── api-keys.ts
└── health.ts
```
Total: 21 API modules. All have typed methods with correct endpoint paths.

---

### Gap 32 — Chart SSR Safety: `dynamic()` Import Pattern for Each Chart

**Problem:** Plan says "wrap with `dynamic()` at usage site" but doesn't specify which files do the wrapping.

**Fix — Rule:** Each `components/charts/*.tsx` file exports the raw Recharts component. The wrapping is done in the **consumer** component.

**Files that must use `dynamic()` for chart imports:**
- `components/dashboard/SpendByDayChart.tsx` → imports `AreaChart` with `dynamic()`
- `components/dashboard/TopServicesTable.tsx` → imports `Sparkline` with `dynamic()`
- `components/costs/ByDayChart.tsx` → imports `BarChart`
- `components/costs/ByServiceTable.tsx` → imports `Sparkline`
- `components/costs/ByTagChart.tsx` → imports `DonutChart`
- `components/costs/TopServicesChart.tsx` → imports `BarChart`
- `components/scorecard/ScoreGauge.tsx` → imports `RadialGauge`
- `components/metrics/UnitEconomicsTable.tsx` → imports `Sparkline`

**Pattern for all of the above:**
```typescript
// In the component file itself:
import dynamic from 'next/dynamic'
const AreaChart = dynamic(() => import('@/components/charts/AreaChart'), {
  ssr: false,
  loading: () => <div className="skeleton" style={{ height: chartHeight }} />,
})
```

---

### Gap 33 — Missing: `src/app/(app)/page.tsx` for Root App Route

**Problem:** The `(app)` route group doesn't have a root page. If user navigates to `/`, they get a 404 within the app group.

**Fix:** Already covered in Gap 30 above (`src/app/page.tsx` redirects to `/dashboard`). No additional file needed inside `(app)/`.

---

### Gap 34 — Bundle Size & Performance Budgets

**Targets:**
| Metric | Target |
|--------|--------|
| First Load JS (shared chunks) | < 200 KB gzipped |
| Page JS (each route) | < 50 KB gzipped |
| Largest Contentful Paint | < 2.5s |
| Time to Interactive | < 3.5s |
| Cumulative Layout Shift | < 0.1 |

**Monitoring:** Add `next.config.ts` bundle analyzer:
```
npm install -D @next/bundle-analyzer
```
Run with `ANALYZE=true npm run build` to inspect bundle sizes before deploy.

**Key size concerns:**
- Recharts: ~300KB raw → mitigated by `dynamic()` imports (only loaded on pages that show charts)
- date-fns: ~80KB tree-shaken → only import specific functions, never `import * from 'date-fns'`
- cmdk: ~15KB — OK
- TanStack Query: ~40KB — OK

---

### Gap 35 — Form `mode` Default

**Problem:** Plan only mentions `mode: 'onBlur'` for multi-step forms.

**Fix — Default for ALL forms:** `mode: 'onSubmit'` with `reValidateMode: 'onChange'`.

This means:
- Errors only shown after first submit attempt (not while user is typing)
- After first submit, errors update in real-time as user corrects them
- Better UX than aggressive `'onChange'` mode

**Exception:** Login and password-related forms use `mode: 'onBlur'` (password strength bar needs it).

---

### Gap 36 — `AuthBootstrap` Loading State Details

**Problem:** Plan says "show `<AppSkeleton />`" during bootstrap but doesn't specify how to prevent flicker from the brief delay between `AppSkeleton` and actual content.

**Fix:**
- `AuthBootstrap` state: `'initializing' | 'authenticated' | 'unauthenticated'`
- Initial state: `'initializing'` — render `<AppSkeleton />`
- If no refresh token in sessionStorage: set `'unauthenticated'` → middleware redirects
- If refresh token exists: attempt `/auth/refresh` → on success: set `'authenticated'`
- After `'authenticated'`: the actual page renders with pre-hydrated auth state
- CSS: AppSkeleton uses `opacity: 0 → 1` fade-in (100ms) to avoid harsh flash

---

### Corrected Folder Structure Additions (Summary)

The following files were MISSING from the folder structure and must be added:

```
src/
├── app/
│   ├── page.tsx                             ← ADD: redirect to /dashboard
│   ├── (auth)/
│   │   └── oauth-callback/
│   │       └── page.tsx                     ← ADD: Google OAuth callback
│   └── (app)/
│       ├── loading.tsx                      ← ADD
│       ├── dashboard/loading.tsx            ← ADD
│       ├── costs/loading.tsx                ← ADD
│       ├── accounts/loading.tsx             ← ADD
│       ├── accounts/[id]/loading.tsx        ← ADD
│       ├── forecasts/loading.tsx            ← ADD
│       ├── commitments/loading.tsx          ← ADD
│       ├── recommendations/loading.tsx      ← ADD
│       ├── scorecard/loading.tsx            ← ADD
│       ├── resources/loading.tsx            ← ADD
│       ├── caps/loading.tsx                 ← ADD
│       ├── alerts/loading.tsx               ← ADD
│       ├── virtual-tags/loading.tsx         ← ADD
│       ├── metrics/loading.tsx              ← ADD
│       ├── assistant/loading.tsx            ← ADD
│       ├── reports/loading.tsx              ← ADD
│       └── settings/loading.tsx             ← ADD
└── components/
    └── layout/
        └── OfflineBanner.tsx                ← ADD
```

### Corrected Dependencies (Summary)

Add these to Step 1.2:
```bash
npm install date-fns-tz           # timezone-aware date formatting
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities  # virtual tags drag-to-reorder
npm install -D @next/bundle-analyzer  # bundle size inspection
```
Pin: `react-day-picker@8.x` (use shadcn `add calendar` command, don't install manually)

### Corrected `next.config.ts` (Summary)

Add to Step 1.5:
- `Next.js >= 15.2.3` pinned (CVE-2025-29927)
- Bundle analyzer integration (`@next/bundle-analyzer`)
- Keep existing security headers

---

## 25. Final Integration Checklist (Before Each Phase Ends)

### After Phase 1
- [ ] `npm run typecheck` — 0 errors
- [ ] `npm run lint` — 0 errors
- [ ] All 21 API modules have typed method signatures matching backend routes
- [ ] All 22 type files match backend response shapes
- [ ] Query key factory covers all endpoints
- [ ] Token flow: setTokens → getAccessToken → Axios interceptor → 401 → refresh → retry
- [ ] WS client: connects, pings, reconnects, handles token update

### After Phase 2
- [ ] Login → Dashboard full flow works end-to-end
- [ ] Google OAuth: redirect → callback → tokens → dashboard
- [ ] Logout: clears tokens, clears cache, redirects
- [ ] Logout in one tab → other tabs log out (StorageEvent)
- [ ] 401 → silent refresh → retry → success (verify with devtools network tab)
- [ ] WS connects on login, shows "sync.complete" toast after triggering a sync
- [ ] HealthBanner shows when backend health is degraded
- [ ] Sidebar collapses, persists preference across page refreshes
- [ ] CommandPalette opens with ⌘K, navigates correctly, closes on Escape
- [ ] Onboarding redirects happen correctly (0 accounts → /onboarding)

### After Phase 3
- [ ] Dashboard data freshness: all 7 parallel queries shown with correct stale times
- [ ] sync.complete WS event → all dashboard cards auto-update
- [ ] Costs: date range changes update URL params → back button works
- [ ] Costs: export CSV downloads correct file
- [ ] Caps: optimistic update → progress bar moves immediately
- [ ] Alerts: acknowledge → item moves from Active to Acknowledged immediately
- [ ] Alerts: snooze → snooze_until shows correctly
- [ ] Forecast breach: correct badge shows (amber/red)
- [ ] Scorecard: radial gauge renders correct grade and score

### After Phase 4
- [ ] Commitments expiry countdown correct per timezone
- [ ] Recommendations: LLM explain shows (or setup CTA if LLM not configured)
- [ ] Resources idle sort: longest idle first
- [ ] VTag: drag reorder fires API, optimistic update works
- [ ] VTag apply: progress polling stops when status is final
- [ ] Business metrics: unit economics table calculates correctly
- [ ] Assistant: rate limit counter decrements, disables input at 0
- [ ] Reports: send-now fires, toast shows delivery status

### After Phase 5
- [ ] All `loading.tsx` files render correct skeleton shapes
- [ ] All pages with `useSearchParams` wrapped in `<Suspense>`
- [ ] `npm run build` succeeds with no warnings
- [ ] Lighthouse Performance ≥ 90 (verify with real network throttling)
- [ ] Lighthouse Accessibility ≥ 95
- [ ] All charts render after dynamic import (no SSR errors in console)
- [ ] Mobile: sidebar hamburger works, tables scroll horizontally
- [ ] Dark mode toggle works (optional — can ship light only)
- [ ] Empty states: verified for all 20 screen states
- [ ] `OfflineBanner` shows when navigator.onLine = false
- [ ] Multi-tab logout verified manually (open 2 tabs, logout from one)
- [ ] WS reconnects after 30s offline (verify by blocking WS in devtools)
- [ ] No `console.error` in production build

---

*This plan is now complete. All 36 gaps have been addressed. The 25-item checklist per phase ensures nothing ships broken.*

---

## 26. Backend Changes Required for Frontend Compatibility

> Cross-reference of every frontend expectation vs. what the backend currently provides.
> Each item is [MISSING], [NEEDS CHANGE], or [VERIFY] — work through these before or alongside frontend Phase 2+.

---

### B1 — [MISSING] `DELETE /v1/auth/me` — Delete user account

**Frontend needs:** Profile page → Danger Zone → user types "DELETE" → `DELETE /v1/auth/me`

**Backend today:** Has `GET /me`, `PUT /me`, `POST /change-password` — no delete endpoint.

**Add to backend:**
- `DELETE /v1/auth/me` (authenticated, any role)
- Behavior:
  1. If user is last owner of an org: delete org + all org data (or return 409 "Transfer ownership first")
  2. If user has other members in org: remove membership only
  3. Revoke all refresh tokens for user
  4. Soft-delete user record (set `deleted_at`, anonymize email/name)
- Returns: `204 No Content`
- Frontend: on success → `clearTokens()` → redirect `/login`

---

### B2 — [MISSING] `GET /v1/orgs/{org_id}/alerts/count` — Alert badge polling

**Frontend needs:** TopBar badge shows `useAlertsCount()` polled every 60s — calls `GET /alerts/count` → `{ active: number }`

**Backend today:** Only `GET /` for list (returns full alert objects). Polling the full list just for a count is wasteful.

**Add to backend:**
- `GET /v1/orgs/{org_id}/alerts/count` (viewer)
- Returns: `{ active: number }` (count of `status = 'active'` alerts for the org)
- Cheap DB query: `SELECT COUNT(*) FROM alerts WHERE org_id = $1 AND status = 'active'`
- No pagination, no joins needed

---

### B3 — [MISSING] Cursor pagination on `GET /v1/orgs/{org_id}/alerts`

**Frontend needs:** Alerts page uses `useInfiniteQuery` with cursor pagination: `GET /alerts?cursor=<last_id>&limit=20`

**Backend today:** Alerts list likely uses page-based pagination (`page` + `size`).

**Change backend:**
- Add `cursor: str | None` (last seen alert ID) + `limit: int = 20` params to `GET /alerts`
- When `cursor` provided: `WHERE id < cursor ORDER BY triggered_at DESC LIMIT limit`
- Response shape: `{ items: Alert[], next_cursor: string | null }`
  - `next_cursor` = last item's ID if `len(items) == limit`, else `null`
- Keep backward compatibility: `page` + `size` params still work for other uses
- Alert ID should be sortable/comparable (UUID v7 or created_at-based ID recommended; if UUID v4, use `triggered_at` as cursor instead)

---

### B4 — [MISSING] CSV export on cost endpoints

**Frontend needs:** `ExportCsvButton` calls `GET /costs/by-service?format=csv` → receives `Content-Type: text/csv` blob → `triggerCsvDownload()`

**Backend today:** Cost endpoints return JSON only. No `format` param.

**Add to backend (all 5 cost endpoints):**
- Accept query param `format: 'json' | 'csv'` (default `'json'`)
- When `format=csv`:
  - Build CSV string from the same data
  - Return `Response(content=csv_string, media_type='text/csv', headers={'Content-Disposition': 'attachment; filename="prism-costs-{date}.csv"'})`
- Endpoints to add CSV export: `GET /costs`, `/costs/by-day`, `/costs/by-service`, `/costs/by-tag`, `/costs/top-services`
- Priority: `/costs/by-service` and `/costs/by-day` are the most used for export

---

### B5 — [MISSING] Pending invites list + revoke

**Frontend needs:** `settings/team` shows "Pending Invites" table with `[Revoke]` button per invite.

**Backend today:** `POST /invite` creates an invite, `POST /accept-invite` accepts it — but no way to list or revoke pending invites.

**Add to backend:**
- `GET /v1/orgs/{org_id}/team/invites` (admin) → returns `Invite[]` (pending, non-expired)
  - `Invite: { id, email, role, invited_by_name, created_at, expires_at }`
- `DELETE /v1/orgs/{org_id}/team/invites/{invite_id}` (admin) → revoke (delete invite record)
  - Returns `204 No Content`

---

### B6 — [MISSING] Webhook signing secret regeneration

**Frontend needs:** Settings → Webhooks → Edit → `[Regenerate Secret]` button

**Backend today:** Webhook create generates a secret. Update (`PUT`) may not regenerate it.

**Add to backend:**
- `POST /v1/orgs/{org_id}/webhooks/{webhook_id}/regenerate-secret` (admin)
- Generates new UUID signing secret, stores HMAC/encrypted, returns new raw secret ONCE
- Returns: `{ signing_secret: string }` (shown once, then never returned again)
- Frontend: shows new secret in `CopyBlock` modal

---

### B7 — [NEEDS CHANGE] WS `sync.complete` event — missing `account_name` and `duration_ms`

**Frontend needs:** Toast reads `"✓ {provider} synced · {records} records · {account_name}"`. Type `SyncCompleteData` has `account_name` and `duration_ms`.

**Backend today (backend.md §27):** `sync.complete` sends `{ provider, account_id, records }` — missing `account_name` and `duration_ms`.

**Change backend:**
- In `src/workers/sync.py` (or wherever WS broadcast is called after sync): look up account name from DB (already in memory during sync), include in broadcast payload
- Updated event data: `{ provider, account_id, account_name, records, duration_ms }`
- `duration_ms`: time from sync start to completion (already tracked in `sync_logs.duration_ms`)

---

### B8 — [NEEDS CHANGE] Recommendations filter params

**Frontend needs:** `GET /recommendations?status=open&provider=aws&min_savings=100&confidence=high`

**Backend today:** Section 13 says "filter by status" only. Other params not documented.

**Verify/add to backend:**
- Confirm `GET /recommendations` supports these query params:
  - `status: 'open' | 'implemented' | 'rejected' | 'archived'` (may already exist)
  - `provider: 'aws' | 'azure' | 'gcp'` (filter by cloud provider)
  - `min_savings: float` (filter by `estimated_savings_monthly >= min_savings`)
  - `confidence: 'high' | 'medium' | 'low'` (filter by confidence level)
- If any are missing: add as optional `Query` params with `None` default (no filter when absent)

---

### B9 — [NEEDS CHANGE] LLM query response — confirm `remaining_queries_this_hour`

**Frontend needs:** `LlmQueryResponse = { answer, tokens_used, remaining_queries_this_hour }` — rate limit counter shown in UI, disables input at 0.

**Backend today:** Section 20 says "20/hour rate limit, spend tracked (Redis preferred)" — unclear if `remaining_queries_this_hour` is in response body.

**Verify/change backend:**
- `POST /llm/query` response MUST include `remaining_queries_this_hour: int` (how many queries left this hour for this org)
- Calculated as: `max(0, 20 - current_hour_count)`
- When rate limit hit (429): response body includes `{ detail: "Rate limit reached", retry_after_seconds: N, remaining_queries_this_hour: 0 }`

---

### B10 — [MISSING] `GET /v1/orgs/{org_id}/reports` — `last_sent_at` + `last_send_status`

**Frontend needs:** Reports page shows "Last sent: {timestamp} · {status badge}"

**Backend today:** `GET /reports` returns config. No mention of last delivery info.

**Change backend:**
- Add `last_sent_at: datetime | None` and `last_send_status: 'delivered' | 'failed' | None` to the report config response (GET `/reports`)
- These fields already exist in DB table `monthly_reports` (or should be added)
- `POST /send-now` response should also return `{ queued: bool, status: 'queued' | 'sent' | 'failed' }` so frontend can show appropriate toast

---

### B11 — [NEEDS CHANGE] `Cache-Control` headers on auth responses

**Frontend needs (security):** Auth endpoint responses (`/auth/login`, `/auth/refresh`, `/auth/me`, `/auth/oauth/exchange`) must NOT be cached by CDN/proxy.

**Backend today:** No explicit `Cache-Control` on auth responses.

**Add to backend:**
- In auth router or middleware: add `Cache-Control: private, no-cache, no-store, must-revalidate` header to all `/auth/*` responses
- Also add `Pragma: no-cache` for HTTP/1.0 proxy compatibility
- Easiest: add response middleware that sets this header on all paths starting with `/v1/auth/`

---

### B12 — [VERIFY] `GET /health` response shape

**Frontend needs:** `{ status: 'ok' | 'degraded' | 'down', db: { status }, redis: { status } }`

**Backend today:** Returns `ok/degraded/down` with component details — verify exact JSON shape.

**Required shape:**
```json
{
  "status": "ok",
  "db": { "status": "ok" },
  "redis": { "status": "degraded", "detail": "connection timeout" }
}
```
If shape differs, frontend `useHealth` hook needs adjustment OR backend shape should match this contract. **Decide one and document it.** Frontend `types/health.ts` must match exactly.

---

### B13 — [VERIFY] `GET /v1/orgs/{org_id}/alerts` — `status` filter param

**Frontend needs:** Tabs Active / Acknowledged / Snoozed each pass `status=active|acknowledged|snoozed`

**Backend today:** GET `/` for list — `status` filter not explicitly documented in backend.md.

**Verify:** Confirm `status` query param is supported. If not, add it. This is a core feature — tabs are broken without it.

---

### B14 — [VERIFY] `GET /v1/orgs/{org_id}/llm` — `configured` boolean in response

**Frontend needs:** `LlmConfig = { configured: boolean, provider?, model?, monthly_budget?, current_spend?, budget_pct? }`

**Backend today:** Section 20 says "key never returned plain" — but does the response include `configured: bool`?

**Verify/change backend:**
- `GET /llm` response MUST include `configured: bool` (true if an API key is stored)
- Must NOT return the actual API key value
- Should return: `{ configured: true, provider: 'openai', model: 'gpt-4o', monthly_budget: 20.00, current_spend: 4.21, budget_pct: 21.1 }` or `{ configured: false }` (all other fields absent)

---

### B15 — [VERIFY] Paginated response shape consistency

**Frontend needs:** All list endpoints return `{ items: T[], total: int, page: int, size: int }` (the `Paginated<T>` type)

**Backend today:** Pagination exists but exact shape not documented.

**Confirm all list endpoints return this shape:**
```json
{
  "items": [...],
  "total": 143,
  "page": 1,
  "size": 20
}
```
**Exception:** Alerts uses cursor pagination (B3 above) → `{ items: [...], next_cursor: "..." }`

**Endpoints that MUST return Paginated<T>:**
- caps, resources, recommendations, virtual-tags, audit-log, sync-logs, webhooks, api-keys, team members, metrics

---

### B16 — [VERIFY] `GET /v1/orgs/{org_id}/sync-logs` — sync status values

**Frontend uses:** `SyncStatus = 'pending' | 'running' | 'success' | 'failed' | 'never'`

**Verify backend `sync_logs.status` enum matches exactly these values.** If the backend uses different strings (e.g., `'completed'` instead of `'success'`), either:
- Frontend adapts its type, OR
- Backend normalizes to match the documented type

**Decide one — document in `types/accounts.ts`.**

---

### B17 — [MISSING] Rate limit error response consistency

**Frontend needs:** All 429 responses include `Retry-After: N` header (seconds to wait). Frontend Axios interceptor reads this and auto-waits.

**Backend today:** Auth and LLM endpoints are rate-limited. It's unclear if all return `Retry-After`.

**Confirm/add:**
- ALL 429 responses include `Retry-After: N` header (integer seconds)
- Sync rate limit 429: `{ detail: "Sync rate limit reached. Try again after {N} minutes." }` with `Retry-After: N*60`
- LLM rate limit 429: `{ detail: "Query limit reached. Resets in {N} minutes.", retry_after_seconds: N, remaining_queries_this_hour: 0 }`
- Auth rate limit 429: `{ detail: "Too many requests. Try again after {N} seconds." }` + `Retry-After: N`

---

### B18 — [MISSING] WS origin validation

**Backend today:** WS connects on `GET /ws?token=` — unclear if `Origin` header is validated.

**Add to backend:**
- In `src/ws/ws_manager.py` or the WS endpoint: validate the `Origin` header against `FRONTEND_URL`
- Reject connections from unauthorized origins with `403 Forbidden` during the HTTP upgrade
- In development: also allow `http://localhost:3000`
- This prevents unauthorized domains from connecting to org-scoped WS events

---

### B19 — [VERIFY] Recommendation type has `confidence` field

**Frontend type:** `Recommendation = { ..., confidence: 'high' | 'medium' | 'low', ... }`

**Backend today:** Section 13 mentions recommendations exist but doesn't detail the response shape.

**Confirm recommendation response includes:**
`{ id, title, description, provider, region?, service, type, estimated_savings_monthly, confidence, status, created_at, resolved_at? }`

---

### B20 — [VERIFY] `POST /v1/orgs/{org_id}/accounts/{id}/sync` — `Retry-After` when rate limited

**Frontend needs:** When sync is rate-limited (5/hour max), frontend shows specific message: "Sync limit reached. Try again after X"

**Verify:**
- When 429: response includes both `Retry-After` header AND body `{ detail: "..." }` with time info
- When Redis is down (no rate limiting): sync fires normally — frontend never gets 429 in this case

---

### B21 — [NEEDS CHANGE] `POST /v1/orgs/{org_id}/reports/send-now` response

**Frontend needs:** After firing "Send Now", toast shows delivery result status.

**Backend today:** `POST /send-now` queues or forces send — return value not documented.

**Change backend:** Return `{ queued: bool, message: string }`:
- Celery available: `{ queued: true, message: "Report queued for delivery" }`
- Celery unavailable / sent inline: `{ queued: false, message: "Report sent to N recipients" }`
- Error (no recipients configured): `400 { detail: "No recipients configured. Update notification settings first." }`

---

### B22 — [VERIFY] `DELETE /v1/orgs/{org_id}/accounts/{id}` — response on soft-delete

**Frontend needs:** After disconnect, card is immediately removed via optimistic update. Toast shows success.

**Verify:** `DELETE /accounts/{id}` returns `204 No Content` (not 200 with body) so frontend optimistic remove works without parsing a response.

---

### B23 — [MISSING] `POST /v1/orgs/{org_id}/notifications/test/email` — test result in body

**Frontend needs:** Test email/Teams/Slack buttons show inline success/fail on the button after test.

**Backend today:** Test endpoints exist. Return value not documented.

**Verify/change:**
- `POST /notifications/test/email` returns `{ ok: bool, message: string }` (not just 2xx/4xx)
- Same for `test/teams` and `test/slack`
- `ok: false` with `200 OK` status (not 5xx) so frontend can show the specific error inline without triggering error boundaries

---

### B24 — [VERIFY] `GET /v1/orgs/{org_id}/forecasts` — breach detection fields

**Frontend needs:** `Forecast = { ..., will_breach: bool, pct_of_cap?, ... }`

**Backend today:** Forecast endpoint exists. Fields not fully documented.

**Confirm response includes:**
- `will_breach: bool` (is projected total > cap amount for this provider?)
- `pct_of_cap: float | None` (projected / cap_amount * 100; `null` if no cap set)
- `days_elapsed: int`, `days_in_month: int`, `daily_avg: float`
- `computed_at: datetime`

---

### B25 — [VERIFY] Error response format consistency

**Frontend `extractErrorMessage` handles two formats:**
1. `{ detail: "string" }` — simple error
2. `{ detail: [{ loc, msg, type }] }` — Pydantic validation errors

**All backend 4xx responses MUST use one of these two formats.** No other formats (e.g., `{ error: "..." }` or `{ message: "..." }`).

**FastAPI default Pydantic validation errors already use format #2.** Custom exceptions must use format #1. Confirm all custom `HTTPException` calls use `detail="..."` (string) only.

---

### B26 — [VERIFY] `GET /v1/orgs/{org_id}/commitments` — expiry fields

**Frontend needs:** Commitments show `days_to_expiry`, `status: 'active' | 'expiring' | 'expired'`

**Verify:**
- `days_to_expiry: int` — calculated from `end_date - today`
- `status` derived from `days_to_expiry`: `> 30` = active, `≤ 30` = expiring, `< 0` = expired
- Either computed in backend before returning, or document that frontend computes from `end_date`
- **Recommended: compute in backend** to avoid timezone edge cases

---

### B27 — [NEEDS CHANGE] `GET /v1/orgs/{org_id}/scorecard` — confirm all 7 metric fields

**Frontend needs:** `Scorecard = { total_score, grade, metrics: ScorecardMetric[], computed_at, prev_score? }`
Where `ScorecardMetric = { key, label, weight_pct, score, status: 'good' | 'warning' | 'critical' }`

**Backend today:** 7 weights documented. Confirm response includes `status` per metric (not just `score`).

**Add if missing:** `status` derived from `score`:
- `score >= 80` → `'good'`
- `score >= 50` → `'warning'`
- `score < 50` → `'critical'`

Also confirm `prev_score` (previous month's total score) is included for delta display.

---

### B28 — [VERIFY] CORS handles `OPTIONS` preflight for all routes

**Frontend needs:** Axios sends `Content-Type: application/json` → triggers preflight `OPTIONS` request.

**Backend today:** CORS middleware exists, locked to `FRONTEND_URL`. Confirm:
- `allow_methods=["*"]` or at minimum `["GET", "POST", "PUT", "DELETE", "OPTIONS"]`
- `allow_headers=["*"]` or at minimum `["Authorization", "Content-Type", "X-Request-Id"]`
- `allow_credentials=False` (tokens in Authorization header, not cookies)

---

### Summary Table — Backend Work Required

| ID | Type | Effort | Blocking? | Description |
|----|------|--------|-----------|-------------|
| B1 | Add endpoint | Small | No (Phase 5) | `DELETE /auth/me` — delete user account |
| B2 | Add endpoint | Small | Phase 2 | `GET /alerts/count` — TopBar badge |
| B3 | Change endpoint | Medium | Phase 3 | Cursor pagination on alerts list |
| B4 | Add feature | Medium | Phase 3 | CSV export (`format=csv`) on cost endpoints |
| B5 | Add endpoints | Small | Phase 5 | Pending invites list + revoke |
| B6 | Add endpoint | Small | Phase 5 | Webhook regenerate-secret |
| B7 | Change data | Small | **Phase 2** | WS `sync.complete` add `account_name`, `duration_ms` |
| B8 | Change endpoint | Small | Phase 4 | Recommendations filter params |
| B9 | Verify/change | Small | Phase 4 | LLM `remaining_queries_this_hour` in response |
| B10 | Change endpoint | Small | Phase 5 | Reports `last_sent_at` + send-now response |
| B11 | Add middleware | Small | **Phase 2** | `Cache-Control: private` on `/auth/*` |
| B12 | Verify | Tiny | Phase 2 | Health response exact JSON shape |
| B13 | Verify | Tiny | **Phase 2** | Alerts `status` filter param |
| B14 | Verify | Tiny | Phase 4 | LLM config `configured` boolean |
| B15 | Verify | Small | Phase 2 | Paginated<T> shape consistency |
| B16 | Verify | Tiny | Phase 2 | Sync log status enum values |
| B17 | Add headers | Small | Phase 2 | `Retry-After` on all 429 responses |
| B18 | Add validation | Small | Phase 2 | WS Origin header validation |
| B19 | Verify | Tiny | Phase 4 | Recommendation `confidence` field |
| B20 | Verify | Tiny | Phase 3 | Sync rate limit `Retry-After` |
| B21 | Change endpoint | Tiny | Phase 5 | `send-now` response body |
| B22 | Verify | Tiny | Phase 3 | Soft-delete returns `204` |
| B23 | Change endpoint | Small | Phase 5 | Notification test returns `{ ok, message }` |
| B24 | Verify | Small | Phase 3 | Forecast `will_breach`, `pct_of_cap` fields |
| B25 | Verify | Small | **Phase 2** | Error response format consistency |
| B26 | Verify | Small | Phase 4 | Commitment `days_to_expiry` + `status` computed |
| B27 | Verify | Small | Phase 4 | Scorecard metric `status` + `prev_score` |
| B28 | Verify | Tiny | **Phase 2** | CORS OPTIONS preflight config |

**Phase 2 blockers** (must be done before frontend auth/shell works): B7, B11, B12, B13, B15, B16, B17, B18, B25, B28

**Phase 3 blockers** (must be done before core cost management works): B2, B4, B20, B22, B24

**Can defer to Phase 4–5**: B1, B3, B5, B6, B8, B9, B10, B14, B19, B21, B23, B26, B27

---

### Validation Matrix — Every Form ↔ Backend Validation

| Form | Fields validated frontend (Zod) | Fields validated backend | Backend error format needed |
|------|--------------------------------|--------------------------|-----------------------------|
| Signup | name ≥1, email format, password ≥8, org_name ≥1 | email uniqueness, org_name uniqueness | `{ detail: "Email already registered" }` |
| Login | email format, password ≥1 | credentials check | `{ detail: "Invalid email or password" }` (never specify which) |
| Forgot password | email format | always 200 (no enumeration) | n/a |
| Reset password | password ≥8, passwords match | token validity, expiry | `{ detail: "Reset link expired or invalid" }` |
| Connect account (all) | all fields required | credential validity (live test) | `{ detail: "Role ARN not found or not assumable" }` etc. |
| Test connection | — | live connectivity | `{ ok: bool, message: str, latency_ms?: int }` |
| Create cap | name ≥1, amount > 0 | duplicate name per org | `{ detail: "A cap with this name already exists" }` |
| Snooze alert | until datetime in future | datetime format | `{ detail: "Snooze time must be in the future" }` |
| Invite member | email format, role not owner | email already member | `{ detail: "User is already a member of this org" }` |
| Webhook URL | url format | SSRF validation | `{ detail: "URL not allowed: private IP ranges are blocked" }` |
| LLM config | api_key ≥1, model ≥1 | key validity (optional live check) | `{ detail: "Invalid API key" }` |
| Virtual tag rule | tag_key ≥1, tag_value ≥1, condition_value ≥1 | duplicate priority | auto-assign next priority (no error) |
| Change password | current ≥1, new ≥8, match | current password correct | `{ detail: "Current password is incorrect" }` |
| Accept invite | name ≥1 (new user), password ≥8 | token valid, not expired | `{ detail: "Invite expired or invalid" }` |
| Org settings | name ≥1, valid currency, valid timezone | — | standard validation errors |
| Notifications | valid emails, valid URLs | SSRF on webhook URLs | `{ detail: "Teams webhook URL not reachable" }` |

---

### Real-time Guarantees — What Must Always Work

| Scenario | Frontend behavior | Backend guarantee needed |
|----------|-------------------|--------------------------|
| Sync completes → dashboard refreshes | WS `sync.complete` → TanStack Query invalidate | Backend MUST broadcast `sync.complete` after EVERY successful sync (Celery or inline) |
| Sync fails → account card shows error | `useAccounts` polls every 60s + WS invalidates | Backend MUST update `cloud_accounts.last_sync_status = 'failed'` and `error_message` immediately on failure |
| Cap threshold crossed → alert appears | `useAlerts` invalidated on `sync.complete` | Backend MUST run alert check (`prism-alerts.check_org`) synchronously after sync, before broadcasting WS event |
| Alert count badge increments | `useAlertsCount` polls every 60s | B2 (alerts/count) must exist |
| Health degrades → banner shows | `useHealth` polls every 60s | Backend health endpoint must reflect Redis/DB state within 1 poll cycle (60s) |
| VTag apply completes → progress drawer closes | Poll audit log every 3s, stop on `completed`/`failed` | Backend `virtual_tag_audit_log.status` must update from `'running'` to `'completed'`/`'failed'` when worker finishes |
| Token expires → transparent refresh | Axios interceptor retries on 401 | Backend refresh endpoint must work reliably; atomic token rotation must not cause race conditions with concurrent requests |
| LLM rate limit reached → input disables | `remaining_queries_this_hour` in response body | B9: backend MUST return this count in every `/llm/query` response |

---

*Backend changes in this section are required for the frontend to work correctly end-to-end. Prioritize Phase 2 blockers before starting frontend implementation.*
