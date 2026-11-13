/** PRISM FinOps — platform health types. */

export type HealthStatus = 'ok' | 'degraded' | 'down';

export interface HealthComponentStatus {
  status: HealthStatus;
  detail?: string;
}

export interface HealthResponse {
  status: HealthStatus;
  db: HealthComponentStatus;
  redis: HealthComponentStatus;
  ts?: string;
}
