'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { getBacktestErrors, getBacktestSeries, getBacktestSummary } from '@/lib/api';
import type {
  BacktestErrorBin,
  BacktestErrors,
  BacktestEventMark,
  BacktestSeries,
  BacktestSummary,
} from '@/types/intelligence';

interface BacktestPanelProps {
  target?: string;
}

interface MetricCard {
  label: string;
  value: string;
  helper: string;
}

interface ErrorBinChartPoint extends BacktestErrorBin {
  label: string;
}

const EVENT_MARK_DATE = '2022-02-24';
const CHART_COLORS = ['#D4AF37', '#F3E5AB', '#B8860B', '#CD7F32', '#FFD700'];

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
  const intervalCards = Object.entries(metrics?.interval_hit_rate ?? {}).map(([interval, hitRate]) => ({
    label: `${interval} Hit Rate`,
    value: formatPercent(hitRate),
    helper: 'Prediction interval coverage',
  }));

  return [
    {
      label: 'Direction Accuracy',
      value: formatPercent(metrics?.direction_accuracy),
      helper: 'Directional hit rate',
    },
    {
      label: 'RMSE',
      value: formatDecimal(metrics?.rmse),
      helper: 'Root mean squared error',
    },
    {
      label: 'MAPE',
      value: formatPercent(metrics?.mape),
      helper: 'Mean absolute percentage error',
    },
    ...intervalCards,
  ];
}

function findEventLabel(eventMarks: BacktestEventMark[]): string {
  return eventMarks.find((mark) => mark.date === EVENT_MARK_DATE)?.label || '2022-02-24 event';
}

export default function BacktestPanel({ target = 'Brent' }: BacktestPanelProps) {
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
          getBacktestSummary(target),
          getBacktestSeries(target),
          getBacktestErrors(target),
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
  }, [target]);

  const metricCards = useMemo(() => buildMetricCards(summary), [summary]);

  const errorDistribution = useMemo<ErrorBinChartPoint[]>(() => {
    return (errors?.bins || []).map((bin) => ({
      ...bin,
      label: bin.range,
    }));
  }, [errors]);

  const eventMarks = series?.events || [];
  const eventLabel = findEventLabel(eventMarks);
  const stageRows = summary?.stage_metrics || [];
  const hasBacktestData = (series?.points?.length ?? 0) > 0;

  if (loading) {
    return (
      <section className="w-full max-w-7xl mx-auto p-4">
        <div className="bg-gray-900 p-8 rounded-lg border border-gray-800 text-center">
          <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-accent-primary border-t-transparent" />
          <p className="text-gray-200 font-medium">Loading backtest validation results...</p>
          <p className="text-gray-500 text-sm mt-2">Fetching summary, series, and error distribution for {target}.</p>
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
      <div className="text-center">
        <p className="text-sm uppercase tracking-[0.25em] text-accent-primary">Model validation</p>
        <h2 className="text-3xl font-bold mt-2 text-white">Backtest Results: {summary?.target || target}</h2>
        <p className="text-gray-400 mt-2">
          Historical actual-vs-predicted validation{summary?.window ? ` for ${summary.window}` : ''} and error diagnostics.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-6 gap-4">
        {metricCards.map((metric) => (
          <div key={metric.label} className="bg-gray-900 p-4 rounded-lg border border-gray-800">
            <p className="text-xs uppercase tracking-wide text-gray-500">{metric.label}</p>
            <p className="text-2xl font-bold text-white mt-2">{metric.value}</p>
            <p className="text-xs text-gray-400 mt-2">{metric.helper}</p>
          </div>
        ))}
      </div>

      <div className="bg-gray-900 p-6 rounded-lg border border-gray-800">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 mb-4">
          <div>
            <h3 className="text-xl font-bold text-accent-primary">Actual vs Predicted Series</h3>
            <p className="text-sm text-gray-400">Reference markers annotate high-impact historical events, including {EVENT_MARK_DATE}.</p>
          </div>
          <span className="text-xs text-gray-400 border border-gray-700 rounded-full px-3 py-1">{eventLabel}</span>
        </div>
        <div className="h-96">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series?.points || []} margin={{ top: 20, right: 32, left: 8, bottom: 12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="date" stroke="#EAEAEA" minTickGap={32} />
              <YAxis stroke="#EAEAEA" tickFormatter={(value: number) => value.toFixed(2)} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                formatter={(value: number | string | undefined, name: string | undefined) => [formatDecimal(Number(value)), name ?? '']}
                labelStyle={{ color: '#EAEAEA' }}
              />
              <Legend />
              <Line type="monotone" dataKey="actual_price" name="Actual Price" stroke="#F3E5AB" strokeWidth={2} dot={false} activeDot={{ r: 6 }} />
              <Line type="monotone" dataKey="predicted_price" name="Predicted Price" stroke="#D4AF37" strokeWidth={2} strokeDasharray="5 5" dot={false} />
              <Line type="monotone" dataKey="lower_price" name="Lower Price" stroke="#CD7F32" strokeWidth={1.5} strokeDasharray="3 3" dot={false} />
              <Line type="monotone" dataKey="upper_price" name="Upper Price" stroke="#CD7F32" strokeWidth={1.5} strokeDasharray="3 3" dot={false} />
              {eventMarks.map((mark) => (
                <ReferenceLine
                  key={`${mark.date}-${mark.label}`}
                  x={mark.date}
                  stroke={mark.date === EVENT_MARK_DATE ? '#FF6B6B' : '#CD7F32'}
                  strokeDasharray="4 4"
                  label={{ value: mark.label, fill: '#EAEAEA', fontSize: 12, position: 'top' }}
                />
              ))}
            </LineChart>
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
    </section>
  );
}
