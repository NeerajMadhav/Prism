/** PRISM FinOps — business metrics API (normalized pagination). */

import { apiClient } from '@/lib/api/client';
import { normalizePaginated } from '@/lib/api/normalize';
import type { Paginated } from '@/types/api';
import type {
  BusinessMetric,
  CreateMetricRequest,
  IngestMetricValueRequest,
  MetricValue,
  UnitEconomics,
} from '@/types/metrics';

/** Lists business metrics. */
export async function list(orgId: string): Promise<Paginated<BusinessMetric>> {
  const { data } = await apiClient.get<BusinessMetric[] | Paginated<BusinessMetric>>(
    `/orgs/${orgId}/metrics`,
  );
  return normalizePaginated(data);
}

/** Creates a business metric definition. */
export async function create(
  orgId: string,
  body: CreateMetricRequest,
): Promise<BusinessMetric> {
  const { data } = await apiClient.post<BusinessMetric>(
    `/orgs/${orgId}/metrics`,
    body,
  );
  return data;
}

/** Deletes a business metric. */
export async function remove(orgId: string, metricId: string): Promise<void> {
  await apiClient.delete(`/orgs/${orgId}/metrics/${metricId}`);
}

/** Ingests a metric value for a date. */
export async function ingestValue(
  orgId: string,
  metricId: string,
  body: IngestMetricValueRequest,
): Promise<MetricValue> {
  const { data } = await apiClient.post<MetricValue>(
    `/orgs/${orgId}/metrics/${metricId}/values`,
    body,
  );
  return data;
}

/** Lists values for a metric. */
export async function getValues(
  orgId: string,
  metricId: string,
): Promise<MetricValue[]> {
  const { data } = await apiClient.get<MetricValue[]>(
    `/orgs/${orgId}/metrics/${metricId}/values`,
  );
  return Array.isArray(data) ? data : [];
}

/** Fetches unit economics across metrics. */
export async function getUnitEconomics(orgId: string): Promise<UnitEconomics[]> {
  const { data } = await apiClient.get<UnitEconomics[]>(
    `/orgs/${orgId}/metrics/unit-economics`,
  );
  return Array.isArray(data) ? data : [];
}
