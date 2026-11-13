/** PRISM FinOps — platform health API module. */

import axios from 'axios';

import type { HealthComponentStatus, HealthResponse, HealthStatus } from '@/types/health';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface RawHealthResponse {
  status: HealthStatus;
  db?: boolean | HealthComponentStatus;
  redis?: boolean | HealthComponentStatus;
  ts?: string;
}

function normalizeComponent(
  value: boolean | HealthComponentStatus | undefined,
): HealthComponentStatus {
  if (typeof value === 'boolean') {
    return { status: value ? 'ok' : 'down' };
  }
  if (value) {
    return value;
  }
  return { status: 'down' };
}

/** Polls the unauthenticated health endpoint. */
export async function check(): Promise<HealthResponse> {
  const { data } = await axios.get<RawHealthResponse>(`${API_BASE}/health`, {
    timeout: 10_000,
  });
  return {
    status: data.status,
    db: normalizeComponent(data.db),
    redis: normalizeComponent(data.redis),
    ts: data.ts,
  };
}
