/** PRISM FinOps — outbound webhook types. */

export interface OutboundWebhook {
  id: string;
  url: string;
  events: string[];
  active: boolean;
  signing_secret_prefix: string;
  created_at: string;
  last_delivery_at?: string;
  last_delivery_status?: string;
}

export interface CreateWebhookRequest {
  url: string;
  events: string[];
}

export type UpdateWebhookRequest = Partial<CreateWebhookRequest> & {
  active?: boolean;
};
