/** PRISM FinOps — virtual tag rule types. */

export type ConditionType =
  | 'service_contains'
  | 'tag_equals'
  | 'account_is'
  | 'provider_is';

export interface VirtualTagRule {
  id: string;
  priority: number;
  tag_key: string;
  tag_value: string;
  condition_type: ConditionType;
  condition_value: string;
  created_at: string;
}

export interface VirtualTagAudit {
  id: string;
  rule_id: string;
  rule_tag_key: string;
  applied_by: string;
  applied_at: string;
  rows_processed: number;
  rows_updated: number;
  status: string;
  duration_ms?: number;
}

export interface CreateVirtualTagRuleRequest {
  priority: number;
  tag_key: string;
  tag_value: string;
  condition_type: ConditionType;
  condition_value: string;
}

export type UpdateVirtualTagRuleRequest = Partial<CreateVirtualTagRuleRequest>;

export interface ReorderVirtualTagRulesRequest {
  ordered_ids: string[];
}
