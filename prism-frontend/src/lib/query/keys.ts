/** PRISM FinOps — TanStack Query key factories. */

import type { AlertListParams } from '@/types/alerts';
import type { CostQueryParams } from '@/types/costs';
import type { RecommendationListParams } from '@/types/recommendations';
import type { ResourceListParams } from '@/types/resources';

export const queryKeys = {
  root: ['prism'] as const,
  me: () => [...queryKeys.root, 'me'] as const,
  health: () => [...queryKeys.root, 'health'] as const,
  org: (orgId: string) => [...queryKeys.root, 'org', orgId] as const,
  team: {
    all: (orgId: string) => [...queryKeys.root, 'team', orgId] as const,
    members: (orgId: string) =>
      [...queryKeys.team.all(orgId), 'members'] as const,
  },
  accounts: {
    all: (orgId: string) => [...queryKeys.root, 'accounts', orgId] as const,
    list: (orgId: string) => [...queryKeys.accounts.all(orgId), 'list'] as const,
    detail: (orgId: string, accountId: string) =>
      [...queryKeys.accounts.all(orgId), 'detail', accountId] as const,
    syncLogs: (orgId: string, accountId: string) =>
      [...queryKeys.accounts.detail(orgId, accountId), 'sync-logs'] as const,
  },
  costs: {
    all: (orgId: string) => [...queryKeys.root, 'costs', orgId] as const,
    summary: (orgId: string, params?: CostQueryParams) =>
      [...queryKeys.costs.all(orgId), 'summary', params ?? {}] as const,
    byDay: (orgId: string, params?: CostQueryParams) =>
      [...queryKeys.costs.all(orgId), 'by-day', params ?? {}] as const,
    byService: (orgId: string, params?: CostQueryParams) =>
      [...queryKeys.costs.all(orgId), 'by-service', params ?? {}] as const,
    byTag: (orgId: string, tagKey: string, params?: CostQueryParams) =>
      [...queryKeys.costs.all(orgId), 'by-tag', tagKey, params ?? {}] as const,
    topServices: (orgId: string, params?: CostQueryParams) =>
      [...queryKeys.costs.all(orgId), 'top-services', params ?? {}] as const,
  },
  caps: {
    all: (orgId: string) => [...queryKeys.root, 'caps', orgId] as const,
    list: (orgId: string) => [...queryKeys.caps.all(orgId), 'list'] as const,
    detail: (orgId: string, capId: string) =>
      [...queryKeys.caps.all(orgId), 'detail', capId] as const,
  },
  alerts: {
    all: (orgId: string) => [...queryKeys.root, 'alerts', orgId] as const,
    list: (orgId: string, params?: AlertListParams) =>
      [...queryKeys.alerts.all(orgId), 'list', params ?? {}] as const,
    count: (orgId: string) =>
      [...queryKeys.alerts.all(orgId), 'count'] as const,
  },
  notifications: (orgId: string) =>
    [...queryKeys.root, 'notifications', orgId] as const,
  reports: (orgId: string) => [...queryKeys.root, 'reports', orgId] as const,
  recommendations: {
    all: (orgId: string) =>
      [...queryKeys.root, 'recommendations', orgId] as const,
    list: (orgId: string, params?: RecommendationListParams) =>
      [...queryKeys.recommendations.all(orgId), 'list', params ?? {}] as const,
  },
  forecasts: {
    all: (orgId: string) => [...queryKeys.root, 'forecasts', orgId] as const,
    current: (orgId: string) =>
      [...queryKeys.forecasts.all(orgId), 'current'] as const,
    history: (orgId: string) =>
      [...queryKeys.forecasts.all(orgId), 'history'] as const,
  },
  commitments: {
    all: (orgId: string) => [...queryKeys.root, 'commitments', orgId] as const,
    list: (orgId: string) =>
      [...queryKeys.commitments.all(orgId), 'list'] as const,
    summary: (orgId: string) =>
      [...queryKeys.commitments.all(orgId), 'summary'] as const,
    expiring: (orgId: string) =>
      [...queryKeys.commitments.all(orgId), 'expiring'] as const,
  },
  scorecard: {
    all: (orgId: string) => [...queryKeys.root, 'scorecard', orgId] as const,
    detail: (orgId: string) =>
      [...queryKeys.scorecard.all(orgId), 'detail'] as const,
    executive: (orgId: string) =>
      [...queryKeys.scorecard.all(orgId), 'executive'] as const,
  },
  resources: {
    all: (orgId: string) => [...queryKeys.root, 'resources', orgId] as const,
    list: (orgId: string, params?: ResourceListParams) =>
      [...queryKeys.resources.all(orgId), 'list', params ?? {}] as const,
    idle: (orgId: string) =>
      [...queryKeys.resources.all(orgId), 'idle'] as const,
    detail: (orgId: string, resourceId: string) =>
      [...queryKeys.resources.all(orgId), 'detail', resourceId] as const,
  },
  virtualTags: {
    all: (orgId: string) => [...queryKeys.root, 'virtual-tags', orgId] as const,
    rules: (orgId: string) =>
      [...queryKeys.virtualTags.all(orgId), 'rules'] as const,
    audit: (orgId: string) =>
      [...queryKeys.virtualTags.all(orgId), 'audit'] as const,
  },
  metrics: {
    all: (orgId: string) => [...queryKeys.root, 'metrics', orgId] as const,
    list: (orgId: string) => [...queryKeys.metrics.all(orgId), 'list'] as const,
    values: (orgId: string, metricId: string) =>
      [...queryKeys.metrics.all(orgId), 'values', metricId] as const,
    unitEconomics: (orgId: string) =>
      [...queryKeys.metrics.all(orgId), 'unit-economics'] as const,
  },
  webhooks: {
    all: (orgId: string) => [...queryKeys.root, 'webhooks', orgId] as const,
    list: (orgId: string) =>
      [...queryKeys.webhooks.all(orgId), 'list'] as const,
  },
  llm: {
    all: (orgId: string) => [...queryKeys.root, 'llm', orgId] as const,
    config: (orgId: string) =>
      [...queryKeys.llm.all(orgId), 'config'] as const,
  },
  apiKeys: {
    all: (orgId: string) => [...queryKeys.root, 'api-keys', orgId] as const,
    list: (orgId: string) =>
      [...queryKeys.apiKeys.all(orgId), 'list'] as const,
  },
} as const;

/** Short alias used by hooks. */
export const qk = queryKeys;
