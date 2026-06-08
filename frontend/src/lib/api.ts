import { getApiBasePath } from '@/components/apiBase';
import type {
  APIResponse,
  NewsEventList,
  BacktestSummary,
  BacktestSeries,
  BacktestErrors,
  FactorHistory,
  OverviewData,
} from '@/types/intelligence';

const API_BASE = getApiBasePath();

async function get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000');
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
  }
  const response = await fetch(url.toString(), { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  const envelope: APIResponse<T> = await response.json();
  if (!envelope.success) {
    throw new Error(envelope.message || `API error: ${envelope.code}`);
  }
  return envelope.data;
}

export async function getEvents(filters?: {
  impact_direction?: string;
  impact_level?: string;
  source?: string;
  limit?: number;
  offset?: number;
  from_date?: string;
  to_date?: string;
  keyword?: string;
}): Promise<NewsEventList> {
  return get<NewsEventList>('/events', filters);
}

export async function getBacktestSummary(target = 'Brent'): Promise<BacktestSummary> {
  return get<BacktestSummary>('/backtest/summary', { target });
}

export async function getBacktestSeries(target = 'Brent'): Promise<BacktestSeries> {
  return get<BacktestSeries>('/backtest/series', { target });
}

export async function getBacktestErrors(target = 'Brent'): Promise<BacktestErrors> {
  return get<BacktestErrors>('/backtest/errors', { target });
}

export async function getFactorHistory(params?: {
  target?: string;
  from_date?: string;
  to_date?: string;
  granularity?: string;
}): Promise<FactorHistory> {
  return get<FactorHistory>('/factors/history', params);
}

export async function getOverview(): Promise<OverviewData> {
  return get<OverviewData>('/overview');
}
