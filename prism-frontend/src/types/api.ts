/** PRISM FinOps — shared API wrapper types. */

export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ApiError {
  detail: string | ValidationError[];
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface DateRange {
  start: string;
  end: string;
}

export type Role = 'viewer' | 'editor' | 'admin' | 'owner';

export type Provider = 'aws' | 'azure' | 'gcp';

export type SyncStatus = 'pending' | 'running' | 'success' | 'failed' | 'never';
