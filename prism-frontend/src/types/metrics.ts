/** PRISM FinOps — business metric types. */

export type MetricSource = 'manual' | 'webhook';

export interface BusinessMetric {
  id: string;
  name: string;
  unit: string;
  source: MetricSource;
  description?: string;
  created_at: string;
}

export interface MetricValue {
  id: string;
  metric_id: string;
  value: number;
  date: string;
  note?: string;
}

export interface UnitEconomics {
  metric: BusinessMetric;
  mtd_value: number;
  mtd_cost: number;
  cost_per_unit: number;
  mom_unit_pct?: number;
}

export interface CreateMetricRequest {
  name: string;
  unit: string;
  source: MetricSource;
  description?: string;
}

export interface IngestMetricValueRequest {
  value: number;
  date: string;
  note?: string;
}
