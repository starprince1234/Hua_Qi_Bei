'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { getFactorHistory } from '@/lib/api';
import type { FactorHistory, FactorHistoryPoint } from '@/types/intelligence';

type Target = 'Brent' | 'WTI';
type Granularity = 'month' | 'quarter';
type FactorKey = 'inventory' | 'geo' | 'macro' | 'supply_demand' | 'technical';
type FactorCategory = {
  key: FactorKey;
  label: string;
  color: string;
};

type ChartPoint = {
  date: string;
  predicted_return_7d: number;
  lower_return_7d: number;
  upper_return_7d: number;
  event_label: string | null;
  actual_return_7d: number | null;
  hit_interval: boolean | null;
} & Record<FactorKey, number>;

interface FactorTooltipPayload {
  payload?: ChartPoint;
}

interface FactorTooltipProps {
  active?: boolean;
  label?: string | number;
  payload?: FactorTooltipPayload[];
  categories: FactorCategory[];
}

const FACTOR_KEYS: FactorKey[] = ['inventory', 'geo', 'macro', 'supply_demand', 'technical'];

const FALLBACK_CATEGORIES: Record<FactorKey, { label: string; color: string }> = {
  inventory: { label: 'Inventory', color: '#8884d8' },
  geo: { label: 'Geopolitical', color: '#82ca9d' },
  macro: { label: 'Macro', color: '#ffc658' },
  supply_demand: { label: 'Supply / Demand', color: '#ff7300' },
  technical: { label: 'Technical', color: '#00C49F' },
};

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return 'Failed to load factor history.';
}

function toChartPoint(point: FactorHistoryPoint): ChartPoint {
  return {
    date: point.date,
    predicted_return_7d: point.predicted_return_7d,
    lower_return_7d: point.lower_return_7d,
    upper_return_7d: point.upper_return_7d,
    actual_return_7d: point.actual_return_7d,
    event_label: point.event_label,
    hit_interval: point.hit_interval,
    inventory: point.inventory,
    geo: point.geo,
    macro: point.macro,
    supply_demand: point.supply_demand,
    technical: point.technical,
  };
}

function formatDateLabel(date: string): string {
  return date.slice(0, 10);
}

function formatContribution(value: number): string {
  return value.toFixed(3);
}

function formatReturn(value: number): string {
  if (Number.isNaN(value)) {
    return '-';
  }
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(1)}%`;
}

function formatNullableReturn(value: number | null): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 'Pending actual';
  }
  return formatReturn(value);
}

function FactorTooltip({ active, label, payload, categories }: FactorTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const point = payload[0]?.payload;
  if (!point) {
    return null;
  }

  const dateLabel = typeof label === 'string' || typeof label === 'number' ? formatDateLabel(String(label)) : formatDateLabel(point.date);

  return (
    <div className="min-w-64 rounded-lg border border-gray-700 bg-gray-950 p-4 text-sm text-gray-200 shadow-xl shadow-black/30">
      <p className="font-semibold text-white">Date: {dateLabel}</p>
      {point.event_label && <p className="mt-2 text-xs text-amber-200">Event: {point.event_label}</p>}

      <div className="mt-3 space-y-1">
        {categories.map((category) => (
          <div key={category.key} className="flex items-center justify-between gap-4">
            <span className="inline-flex items-center gap-2 text-gray-300">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: category.color }} />
              {category.label}
            </span>
            <span className="font-mono text-gray-100">{formatContribution(point[category.key])}</span>
          </div>
        ))}
      </div>

      <div className="mt-3 border-t border-gray-800 pt-3 text-xs text-gray-300">
        <p>
          Predicted 7D: <span className="text-gray-100">{formatReturn(point.predicted_return_7d)}</span>
        </p>
        <p>
          Interval:{' '}
          <span className="text-gray-100">
            {formatReturn(point.lower_return_7d)} - {formatReturn(point.upper_return_7d)}
          </span>
        </p>
        <p>
          Actual 7D: <span className="text-gray-100">{formatNullableReturn(point.actual_return_7d)}</span>
        </p>
        <p className={point.hit_interval === null ? 'font-semibold text-gray-400' : point.hit_interval ? 'font-semibold text-green-300' : 'font-semibold text-red-300'}>
          {point.hit_interval === null ? 'Awaiting actual return' : point.hit_interval ? 'Hit interval' : 'Missed interval'}
        </p>
      </div>
    </div>
  );
}

export default function FactorPanel() {
  const [target, setTarget] = useState<Target>('Brent');
  const [granularity, setGranularity] = useState<Granularity>('month');
  const [history, setHistory] = useState<FactorHistory | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadFactorHistory(): Promise<void> {
      setLoading(true);
      setError(null);

      try {
        const data = await getFactorHistory({ target, granularity });
        if (!cancelled) {
          setHistory(data);
        }
      } catch (caughtError: unknown) {
        if (!cancelled) {
          setError(getErrorMessage(caughtError));
          setHistory(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadFactorHistory();

    return () => {
      cancelled = true;
    };
  }, [target, granularity]);

  const chartData = useMemo<ChartPoint[]>(() => {
    return (history?.points ?? []).map(toChartPoint);
  }, [history]);

  const categories = useMemo<FactorCategory[]>(() => {
    const fromBackend = new Set(history?.categories ?? []);

    return FACTOR_KEYS.map((key) => {
      return {
        key,
        label: FALLBACK_CATEGORIES[key].label,
        color: FALLBACK_CATEGORIES[key].color,
      };
    }).filter((category) => fromBackend.size === 0 || fromBackend.has(category.key));
  }, [history]);

  return (
    <section className="w-full max-w-7xl mx-auto p-4">
      <div className="bg-gray-900 p-6 rounded-lg border border-gray-800">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between mb-6">
          <div>
            <p className="text-sm uppercase tracking-[0.25em] text-gray-500">Factor History</p>
            <h2 className="text-2xl font-bold text-accent-primary mt-1">Contribution Timeline</h2>
            <p className="text-sm text-gray-400 mt-2">
              Backend-normalized factor contributions for the selected crude benchmark and period grouping.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <label className="text-sm text-gray-300">
              <span className="block mb-1 text-gray-400">Target</span>
              <select
                value={target}
                onChange={(event) => setTarget(event.target.value as Target)}
                className="bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-accent-primary"
              >
                <option value="Brent">Brent</option>
                <option value="WTI">WTI</option>
              </select>
            </label>

            <label className="text-sm text-gray-300">
              <span className="block mb-1 text-gray-400">Granularity</span>
              <select
                value={granularity}
                onChange={(event) => setGranularity(event.target.value as Granularity)}
                className="bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-accent-primary"
              >
                <option value="month">Month</option>
                <option value="quarter">Quarter</option>
              </select>
            </label>
          </div>
        </div>

        {loading && (
          <div className="h-80 flex items-center justify-center rounded-lg border border-gray-800 bg-gray-950 text-gray-300">
            Loading factor history...
          </div>
        )}

        {!loading && error && (
          <div className="rounded-lg border border-red-900/60 bg-red-950/40 p-4 text-red-200">
            <p className="font-semibold">Unable to load factor history</p>
            <p className="text-sm mt-1 text-red-100/80">{error}</p>
          </div>
        )}

        {!loading && !error && chartData.length === 0 && (
          <div className="h-80 flex items-center justify-center rounded-lg border border-gray-800 bg-gray-950 text-gray-300">
            No factor history data available.
          </div>
        )}

        {!loading && !error && chartData.length > 0 && (
          <>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="date" stroke="#EAEAEA" tickFormatter={formatDateLabel} />
                  <YAxis stroke="#EAEAEA" tickFormatter={(value) => Number(value).toFixed(2)} />
                  <Tooltip content={<FactorTooltip categories={categories} />} />
                  <Legend />
                  {categories.map((category) => (
                    <Area
                      key={category.key}
                      type="monotone"
                      dataKey={category.key}
                      name={category.label}
                      stackId="factor-contribution"
                      stroke={category.color}
                      fill={category.color}
                      fillOpacity={0.72}
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-6 overflow-x-auto">
              <table className="w-full text-sm text-gray-200">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-3 pr-4">Date</th>
                    {categories.map((category) => (
                      <th key={category.key} className="text-left py-3 pr-4">
                        <span className="inline-flex items-center gap-2">
                          <span
                            className="h-2.5 w-2.5 rounded-full"
                            style={{ backgroundColor: category.color }}
                          />
                          {category.label}
                        </span>
                      </th>
                    ))}
                    <th className="text-left py-3 pr-4">Event</th>
                    <th className="text-left py-3 pr-4">Predicted 7D</th>
                    <th className="text-left py-3 pr-4">Actual 7D</th>
                    <th className="text-left py-3">Interval</th>
                  </tr>
                </thead>
                <tbody>
                  {chartData.map((point) => (
                    <tr key={point.date} className="border-b border-gray-800/80">
                      <td className="py-3 pr-4 whitespace-nowrap">{formatDateLabel(point.date)}</td>
                      {categories.map((category) => (
                        <td key={`${point.date}-${category.key}`} className="py-3 pr-4">
                          {formatContribution(point[category.key])}
                        </td>
                      ))}
                      <td className="py-3 pr-4 text-gray-400">{point.event_label ?? '-'}</td>
                      <td className="py-3 pr-4">{formatReturn(point.predicted_return_7d)}</td>
                      <td className="py-3 pr-4">{formatNullableReturn(point.actual_return_7d)}</td>
                      <td className={point.hit_interval === null ? 'py-3 text-gray-400 font-semibold' : point.hit_interval ? 'py-3 text-green-400 font-semibold' : 'py-3 text-red-400 font-semibold'}>
                        {point.hit_interval === null ? 'Pending' : point.hit_interval ? 'Hit' : 'Miss'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
