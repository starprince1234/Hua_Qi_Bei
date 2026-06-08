'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { getBacktestErrors, getBacktestSeries, getBacktestSummary } from '@/lib/api';
import FactorPanel from './FactorPanel';
import type {
  BacktestErrorBin,
  BacktestErrors,
  BacktestEventMark,
  BacktestSeries,
  BacktestSummary,
} from '@/types/intelligence';

interface BacktestPanelProps {
  target?: string;
  includeFactorHistory?: boolean;
}

interface MetricCard {
  label: string;
  value: string;
  helper: string;
  detail?: string;
}

interface ErrorBinChartPoint extends BacktestErrorBin {
  label: string;
}

type SeriesChartPoint = {
  date: string;
  actual_price: number;
  predicted_price: number;
  lower_price: number;
  upper_price: number;
  interval_range: number;
};

const EVENT_MARK_DATE = '2022-02-24';
const CHART_COLORS = ['#D4AF37', '#60A5FA', '#F87171', '#34D399', '#FBBF24'];
const KEY_EVENT_LABELS = new Set(['俄乌战争爆发', '俄油制裁冲击', '巴以冲突爆发', '中东冲突升级']);

function formatDecimal(value: number | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-';
  }

  return value.toFixed(2);
}

function formatPercent(value: number | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-';
  }

  return `${(value * 100).toFixed(1)}%`;
}

function formatSignedPercent(value: number | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-';
  }

  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(1)}%`;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return 'Unable to load backtest validation data.';
}

function buildMetricCards(summary: BacktestSummary | null): MetricCard[] {
  const metrics = summary?.metrics;
  const intervalHitRate = metrics?.interval_hit_rate ?? {};
  const directionAccuracy = metrics?.direction_accuracy;
  const randomEdge =
    typeof directionAccuracy === 'number'
      ? `${((directionAccuracy - 0.5) * 100).toFixed(1)}pp above random 50%`
      : 'Benchmark: random 50%';
  const riskCoverage = [
    `High ${formatPercent(intervalHitRate.high)}`,
    `Medium ${formatPercent(intervalHitRate.medium)}`,
    `Low ${formatPercent(intervalHitRate.low)}`,
  ].join(' / ');

  return [
    {
      label: 'Direction Accuracy',
      value: formatPercent(directionAccuracy),
      helper: 'Higher is better',
      detail: randomEdge,
    },
    {
      label: 'RMSE',
      value: formatDecimal(metrics?.rmse),
      helper: 'Lower is better',
      detail: 'Root mean squared price error',
    },
    {
      label: 'MAPE',
      value: formatPercent(metrics?.mape),
      helper: 'Lower is better',
      detail: 'Mean absolute percentage error',
    },
    {
      label: 'Risk Interval Hit Rate',
      value: formatPercent(intervalHitRate.all),
      helper: 'Coverage by risk bucket',
      detail: riskCoverage,
    },
  ];
}

function describeKeyEvents(eventMarks: BacktestEventMark[]): string {
  const keyCount = eventMarks.filter((mark) => KEY_EVENT_LABELS.has(mark.label)).length;
  return keyCount > 0 ? `${keyCount} key event markers` : 'No key event markers';
}

function formatTimestamp(timestamp?: string | null): string {
  if (!timestamp) {
    return '-';
  }
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export default function BacktestPanel({ target = 'Brent', includeFactorHistory = true }: BacktestPanelProps) {
  const [selectedTarget, setSelectedTarget] = useState(target);
  const [summary, setSummary] = useState<BacktestSummary | null>(null);
  const [series, setSeries] = useState<BacktestSeries | null>(null);
  const [errors, setErrors] = useState<BacktestErrors | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadBacktestData(): Promise<void> {
      setLoading(true);
      setErrorMessage(null);

      try {
        const [summaryData, seriesData, errorsData] = await Promise.all([
          getBacktestSummary(selectedTarget),
          getBacktestSeries(selectedTarget),
          getBacktestErrors(selectedTarget),
        ]);

        if (!active) {
          return;
        }

        setSummary(summaryData);
        setSeries(seriesData);
        setErrors(errorsData);
      } catch (error: unknown) {
        if (!active) {
          return;
        }

        setErrorMessage(getErrorMessage(error));
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadBacktestData();

    return () => {
      active = false;
    };
  }, [selectedTarget]);

  const metricCards = useMemo(() => buildMetricCards(summary), [summary]);

  const errorDistribution = useMemo<ErrorBinChartPoint[]>(() => {
    return (errors?.bins || []).map((bin) => ({
      ...bin,
      label: bin.range,
    }));
  }, [errors]);

  const seriesChartData = useMemo<SeriesChartPoint[]>(() => {
    return (series?.points || []).map((point) => ({
      ...point,
      interval_range: Math.max(0, point.upper_price - point.lower_price),
    }));
  }, [series]);

  const eventMarks = series?.events || [];
  const keyEventMarks = eventMarks.filter((mark) => KEY_EVENT_LABELS.has(mark.label));
  const eventLabel = describeKeyEvents(eventMarks);
  const stageRows = summary?.stage_metrics || [];
  const hasBacktestData = (series?.points?.length ?? 0) > 0;

  if (loading) {
    return (
      <section className="w-full max-w-7xl mx-auto p-4">
        <div className="bg-gray-900 p-8 rounded-lg border border-gray-800 text-center">
          <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-accent-primary border-t-transparent" />
          <p className="text-gray-200 font-medium">Loading backtest validation results...</p>
          <p className="text-gray-500 text-sm mt-2">Fetching summary, series, and error distribution for {selectedTarget}.</p>
        </div>
      </section>
    );
  }

  if (errorMessage) {
    return (
      <section className="w-full max-w-7xl mx-auto p-4">
        <div className="bg-red-950/40 p-6 rounded-lg border border-red-900 text-red-100">
          <h2 className="text-xl font-bold mb-2">Backtest validation unavailable</h2>
          <p className="text-sm text-red-200">{errorMessage}</p>
        </div>
      </section>
    );
  }

  if (!hasBacktestData) {
    return (
      <section className="w-full max-w-7xl mx-auto p-4">
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-6">
          <p className="text-sm uppercase tracking-[0.25em] text-accent-primary">Model validation</p>
          <h2 className="mt-2 text-3xl font-bold text-white">Backtest validation awaiting online history</h2>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-gray-300">
            The API is online and no longer reads demo_backtest.json. A real backtest needs historical rows that pair
            model predictions with later actual outcomes, so this panel will stay empty until that dataset is uploaded
            or imported.
          </p>
          <div className="mt-5 rounded-md border border-gray-800 bg-gray-950 p-4">
            <p className="text-sm font-semibold text-gray-100">Missing fields required for validation</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {(summary?.required_fields ?? []).map((field) => (
                <span key={field} className="rounded-full border border-gray-700 px-3 py-1 text-xs text-gray-300">
                  {field}
                </span>
              ))}
            </div>
            <p className="mt-3 text-xs text-gray-500">Provider status: {summary?.provider_status ?? 'online_empty'}</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="w-full max-w-7xl mx-auto p-4 space-y-8">
      <div className="rounded-lg border border-gray-800 bg-gray-900 p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.25em] text-accent-primary">Model validation</p>
            <h2 className="text-3xl font-bold mt-2 text-white">Backtest Results: {summary?.target || selectedTarget}</h2>
            <p className="text-gray-400 mt-2">
              Historical actual-vs-predicted validation{summary?.window ? ` for ${summary.window}` : ''} and error diagnostics.
            </p>
          </div>
          <label className="text-sm text-gray-300">
            <span className="mb-1 block text-gray-400">Target</span>
            <select
              value={selectedTarget}
              onChange={(event) => setSelectedTarget(event.target.value)}
              className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-accent-primary"
            >
              <option value="Brent">Brent</option>
              <option value="WTI">WTI</option>
            </select>
          </label>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 text-sm md:grid-cols-4">
          <div className="rounded-md border border-gray-800 bg-gray-950 px-4 py-3">
            <p className="text-xs uppercase tracking-wide text-gray-500">Provider</p>
            <p className="mt-1 font-semibold text-gray-100">{summary?.provider_status ?? 'unavailable'}</p>
          </div>
          <div className="rounded-md border border-gray-800 bg-gray-950 px-4 py-3">
            <p className="text-xs uppercase tracking-wide text-gray-500">Run ID</p>
            <p className="mt-1 break-all font-mono text-xs text-gray-100">{summary?.run_id ?? '-'}</p>
          </div>
          <div className="rounded-md border border-gray-800 bg-gray-950 px-4 py-3">
            <p className="text-xs uppercase tracking-wide text-gray-500">Model Version</p>
            <p className="mt-1 font-semibold text-gray-100">{summary?.model_version ?? '-'}</p>
          </div>
          <div className="rounded-md border border-gray-800 bg-gray-950 px-4 py-3">
            <p className="text-xs uppercase tracking-wide text-gray-500">Updated</p>
            <p className="mt-1 font-semibold text-gray-100">{formatTimestamp(summary?.updated_at)}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {metricCards.map((metric) => (
          <div key={metric.label} className="bg-gray-900 p-4 rounded-lg border border-gray-800">
            <p className="text-xs uppercase tracking-wide text-gray-500">{metric.label}</p>
            <p className="text-2xl font-bold text-white mt-2">{metric.value}</p>
            <p className="text-xs text-gray-400 mt-2">{metric.helper}</p>
            {metric.detail && <p className="text-xs text-accent-primary mt-1">{metric.detail}</p>}
          </div>
        ))}
      </div>

      <div className="bg-gray-900 p-6 rounded-lg border border-gray-800">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 mb-4">
          <div>
            <h3 className="text-xl font-bold text-accent-primary">Actual vs Predicted Series</h3>
            <p className="text-sm text-gray-400">Gray line is actual price, blue dashed line is the model backtest, and the light-blue band is the prediction interval.</p>
          </div>
          <span className="text-xs text-gray-400 border border-gray-700 rounded-full px-3 py-1">{eventLabel}</span>
        </div>
        <div className="h-96">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={seriesChartData} margin={{ top: 20, right: 32, left: 8, bottom: 12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="date" stroke="#EAEAEA" minTickGap={32} />
              <YAxis stroke="#EAEAEA" tickFormatter={(value: number) => value.toFixed(2)} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                formatter={(value: number | string | undefined, name: string | undefined) => [formatDecimal(Number(value)), name ?? '']}
                labelStyle={{ color: '#EAEAEA' }}
              />
              <Legend />
              <Area type="monotone" dataKey="lower_price" stackId="interval" stroke="none" fill="transparent" name="Interval Lower" />
              <Area type="monotone" dataKey="interval_range" stackId="interval" stroke="none" fill="#60A5FA" fillOpacity={0.18} name="Prediction Interval" />
              <Line type="monotone" dataKey="actual_price" name="Actual Price" stroke="#A3A3A3" strokeWidth={2.2} dot={false} activeDot={{ r: 6 }} />
              <Line type="monotone" dataKey="predicted_price" name="Predicted Price" stroke="#60A5FA" strokeWidth={2.2} strokeDasharray="6 5" dot={false} />
              {keyEventMarks.map((mark) => (
                <ReferenceLine
                  key={`${mark.date}-${mark.label}`}
                  x={mark.date}
                  stroke={mark.date === EVENT_MARK_DATE ? '#FF6B6B' : '#CD7F32'}
                  strokeDasharray="4 4"
                  label={{ value: mark.label, fill: '#EAEAEA', fontSize: 12, position: 'top' }}
                />
              ))}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div className="xl:col-span-2 bg-gray-900 p-6 rounded-lg border border-gray-800">
          <h3 className="text-xl font-bold mb-4 text-accent-primary">Error Distribution</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={errorDistribution} margin={{ top: 5, right: 30, left: 8, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="label" stroke="#EAEAEA" angle={-20} textAnchor="end" height={64} interval={0} />
                <YAxis stroke="#EAEAEA" allowDecimals={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                  formatter={(value: number | string | undefined, name: string | undefined) => {
                    if (name === 'count') {
                      return [String(value), 'Count'];
                    }

                    return [String(value), name ?? ''];
                  }}
                  labelStyle={{ color: '#EAEAEA' }}
                />
                <Bar dataKey="count" name="Count">
                  {errorDistribution.map((bin, index) => (
                    <Cell key={bin.range} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-gray-900 p-6 rounded-lg border border-gray-800">
          <h3 className="text-xl font-bold mb-4 text-accent-primary">Event Markers</h3>
          <div className="space-y-3">
            {eventMarks.map((mark) => (
              <div key={`${mark.date}-${mark.label}`} className="bg-gray-800 px-4 py-3 rounded-md">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-semibold text-white">{mark.label}</span>
                  <span className={mark.hit_interval ? 'text-green-400 text-sm' : 'text-red-400 text-sm'}>
                    {mark.hit_interval ? 'Hit' : 'Miss'}
                  </span>
                </div>
                <p className="mt-1 text-xs text-gray-400">{mark.date}</p>
                <p className="mt-2 text-sm text-gray-300">
                  Actual {formatSignedPercent(mark.actual_return_7d)} · Predicted {formatSignedPercent(mark.predicted_return_7d)}
                </p>
              </div>
            ))}
            {eventMarks.length === 0 && <p className="text-sm text-gray-400">No event markers returned.</p>}
          </div>
        </div>
      </div>

      <div className="bg-gray-900 p-6 rounded-lg border border-gray-800">
        <h3 className="text-xl font-bold mb-4 text-accent-primary">Stage Performance</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-gray-200">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-3 pr-4">Stage</th>
                <th className="text-left py-3 pr-4">Direction Accuracy</th>
                <th className="text-left py-3">RMSE</th>
              </tr>
            </thead>
            <tbody>
              {stageRows.map((stage) => (
                <tr key={stage.stage} className="border-b border-gray-800/80">
                  <td className="py-3 pr-4 text-gray-300">{stage.stage}</td>
                  <td className="py-3 pr-4">{formatPercent(stage.direction_accuracy)}</td>
                  <td className="py-3">{formatDecimal(stage.rmse)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {includeFactorHistory && <FactorPanel initialTarget={selectedTarget} embedded />}
    </section>
  );
}
