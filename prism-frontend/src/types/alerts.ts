/** PRISM FinOps — alert types (aligned to live backend). */

export type AlertType = string;

export type AlertStatus = 'active' | 'acknowledged' | 'snoozed';

export interface Alert {
  id: string;
  type: AlertType;
  status: AlertStatus;
  scope?: string;
  scope_value?: string;
  severity?: string;
  message?: string;
  cap_id?: string;
  threshold_pct?: number;
  triggered_at: string;
  snoozed_until?: string | null;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  email_sent?: boolean;
  teams_sent?: boolean;
  slack_sent?: boolean;
  webhook_sent?: boolean;
}

export interface BackendAlert {
  id: string;
  type: string;
  scope?: string | null;
  scope_value?: string | null;
  severity?: string;
  threshold_percent?: number | null;
  message?: string;
  triggered_at: string;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  snoozed_until?: string | null;
  cap_id?: string | null;
}

export interface SnoozeRequest {
  until: string;
}

export interface AlertListParams {
  status?: AlertStatus;
  page?: number;
  size?: number;
  type?: string;
  acknowledged?: boolean;
}

export interface AlertCountResponse {
  active: number;
}
