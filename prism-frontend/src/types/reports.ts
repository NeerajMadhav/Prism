/** PRISM FinOps — monthly report configuration. */

export interface ReportConfig {
  is_active: boolean;
  recipient_emails: string[];
  send_day: number;
  next_send: string | null;
  last_sent: string | null;
  include_recommendations: boolean;
  include_finops_scorecard: boolean;
  include_commitments: boolean;
  include_unit_economics: boolean;
}

export type UpdateReportConfig = Partial<
  Omit<ReportConfig, 'next_send' | 'last_sent'>
>;

export interface SendReportNowResponse {
  message: string;
  task_id: string;
}
