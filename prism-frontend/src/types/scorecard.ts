/** PRISM FinOps — FinOps health scorecard types. */

export type ScoreGrade = 'A' | 'B' | 'C' | 'D' | 'F';

export type ScoreMetricStatus = 'good' | 'warning' | 'critical';

export interface ScorecardMetric {
  key: string;
  label: string;
  weight_pct: number;
  score: number;
  status: ScoreMetricStatus;
}

export interface Scorecard {
  total_score: number;
  grade: ScoreGrade;
  metrics: ScorecardMetric[];
  computed_at: string;
  prev_score?: number;
}

export interface ScorecardExecutive {
  mtd_spend: number;
  forecast: number;
  scorecard_grade: ScoreGrade;
  savings_realized: number;
  currency: string;
}
