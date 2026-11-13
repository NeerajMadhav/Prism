/** PRISM FinOps — notification channel settings. */

export interface NotificationThresholds {
  t75: boolean;
  t90: boolean;
  t100: boolean;
  t125: boolean;
  t150: boolean;
}

export interface NotificationSettings {
  alert_emails: string[];
  teams_webhook_url?: string;
  slack_webhook_url?: string;
  thresholds: NotificationThresholds;
}

export type UpdateNotificationSettings = Partial<NotificationSettings>;
