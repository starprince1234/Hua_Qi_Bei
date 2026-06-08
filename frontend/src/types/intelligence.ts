export interface NewsEvent {
  event_id: string;
  published_at: string;
  source: 'gdelt' | 'newsapi' | 'demo';
  provider_event_id: string;
  title: string;
  summary: string;
  url: string;
  impact_direction: 'bullish' | 'bearish' | 'neutral';
  impact_level: 'high' | 'medium' | 'low';
  impact_score: number;
  confidence: number;
  affected_industries: string[];
  tags: string[];
  llm_model_id: string;
  analysis_version: string;
}

export interface NewsEventList {
  items: NewsEvent[];
  updated_at: string;
  provider_status: string;
}

export interface BacktestMetrics {
  direction_accuracy: number;
  rmse: number;
  mape: number;
  interval_hit_rate: Record<string, number>;
}

export interface BacktestStageMetric {
  stage: string;
  direction_accuracy: number;
  rmse: number;
}

export interface BacktestSummary {
  target: string;
  window: string;
  metrics: BacktestMetrics;
  stage_metrics: BacktestStageMetric[];
  provider_status: string;
  required_fields: string[];
  message: string | null;
}

export interface BacktestSeriesPoint {
  date: string;
  actual_price: number;
  predicted_price: number;
  lower_price: number;
  upper_price: number;
}

export interface BacktestEventMark {
  date: string;
  label: string;
  hit_interval: boolean;
  actual_return_7d: number;
  predicted_return_7d: number;
}

export interface BacktestSeries {
  points: BacktestSeriesPoint[];
  events: BacktestEventMark[];
}

export interface BacktestErrorBin {
  range: string;
  count: number;
}

export interface BacktestErrors {
  bins: BacktestErrorBin[];
}

export interface FactorHistoryPoint {
  date: string;
  inventory: number;
  geo: number;
  macro: number;
  supply_demand: number;
  technical: number;
  event_label: string | null;
  predicted_return_7d: number;
  lower_return_7d: number;
  upper_return_7d: number;
  actual_return_7d: number | null;
  hit_interval: boolean | null;
}

export interface FactorHistory {
  categories: string[];
  points: FactorHistoryPoint[];
  provider_status: string;
}

export interface OverviewEventSummary {
  title: string;
  impact_direction: string;
  impact_level: string;
  published_at: string | null;
  source: string | null;
}

export interface OverviewPredictionSummary {
  available: boolean;
  updated_at: string | null;
  model_version: string | null;
  risk_level: string | null;
  horizon: number | null;
  confidence_score: number | null;
  median_return: number | null;
}

export interface OverviewDominantFactor {
  category: string | null;
  contribution: number | null;
  label: string | null;
}

export interface OverviewBacktestStatus {
  provider_status: string;
  available: boolean;
  point_count: number;
  required_fields: string[];
}

export interface OverviewData {
  updated_at: string;
  news_provider_status: string;
  news_event_count: number;
  high_impact_event: OverviewEventSummary | null;
  latest_prediction: OverviewPredictionSummary;
  dominant_factor: OverviewDominantFactor;
  factor_history_points: number;
  backtest: OverviewBacktestStatus;
}

export type APIResponse<T> = {
  success: boolean;
  code: number;
  message: string;
  data: T;
  request_id: string | null;
};
