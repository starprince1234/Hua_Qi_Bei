/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { getApiBasePath } from './apiBase';

interface ResultDisplayProps {
  result: any;
}

const COLORS = ['#D4AF37', '#F3E5AB', '#B8860B', '#CD7F32', '#FFD700'];

type StepPoint = {
  step: number;
  median: number;
  upper: number;
  lower: number;
  predictedReturn: number;
};

const API_BASE = getApiBasePath();

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function fitPointByHorizon(points: StepPoint[], horizon: number): StepPoint | null {
  if (!points.length) {
    return null;
  }

  const sorted = [...points].sort((a, b) => a.step - b.step);
  if (sorted.length === 1) {
    return { ...sorted[0], step: horizon };
  }

  const exact = sorted.find((item) => item.step === horizon);
  if (exact) {
    return exact;
  }

  let left = sorted[0];
  let right = sorted[1];

  if (horizon <= sorted[0].step) {
    left = sorted[0];
    right = sorted[1];
  } else if (horizon >= sorted[sorted.length - 1].step) {
    left = sorted[sorted.length - 2];
    right = sorted[sorted.length - 1];
  } else {
    for (let idx = 0; idx < sorted.length - 1; idx += 1) {
      const cur = sorted[idx];
      const nxt = sorted[idx + 1];
      if (cur.step <= horizon && horizon <= nxt.step) {
        left = cur;
        right = nxt;
        break;
      }
    }
  }

  const span = Math.max(right.step - left.step, 1e-6);
  const t = (horizon - left.step) / span;

  return {
    step: horizon,
    median: lerp(left.median, right.median, t),
    upper: lerp(left.upper, right.upper, t),
    lower: lerp(left.lower, right.lower, t),
    predictedReturn: lerp(left.predictedReturn, right.predictedReturn, t),
  };
}

function normalizeRiskLevel(value: unknown): 'LOW' | 'MEDIUM' | 'HIGH' | 'EXTREME' | 'UNKNOWN' {
  const text = String(value ?? '').trim();
  const upper = text.toUpperCase();
  if (['LOW', 'MEDIUM', 'HIGH', 'EXTREME'].includes(upper)) {
    return upper as 'LOW' | 'MEDIUM' | 'HIGH' | 'EXTREME';
  }
  if (text.includes('低')) return 'LOW';
  if (text.includes('中')) return 'MEDIUM';
  if (text.includes('高') || text.includes('极')) return 'HIGH';
  return 'UNKNOWN';
}

function normalizeKgLevel(value: unknown): string {
  const text = String(value ?? '').trim();
  const lower = text.toLowerCase();
  const mapping: Record<string, string> = {
    critical: 'CRITICAL',
    high: 'HIGH',
    medium: 'MEDIUM',
    low: 'LOW',
    minor: 'MINOR',
    none: 'NONE',
    '最严重': 'CRITICAL',
    '严重': 'HIGH',
    '中': 'MEDIUM',
    '较轻微': 'LOW',
    '轻微': 'MINOR',
    '无': 'NONE',
  };
  return mapping[lower] || mapping[text] || 'MEDIUM';
}

function escapePdfText(text: string): string {
  return text
    .replace(/\\/g, '\\\\')
    .replace(/\(/g, '\\(')
    .replace(/\)/g, '\\)')
    .replace(/\r?\n/g, ' ')
    .replace(/[^\x20-\x7E]/g, '?');
}

function wrapText(text: string, maxChars: number): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  if (!words.length) {
    return [''];
  }

  const lines: string[] = [];
  let current = words[0];

  for (let i = 1; i < words.length; i += 1) {
    const candidate = `${current} ${words[i]}`;
    if (candidate.length <= maxChars) {
      current = candidate;
    } else {
      lines.push(current);
      current = words[i];
    }
  }
  lines.push(current);
  return lines;
}

function buildSimplePdfText(title: string, body: string, modelId?: string): string {
  const allLines = [title, modelId ? `Model: ${modelId}` : '', '', ...wrapText(body, 92)];
  const safeLines = allLines.map((line) => escapePdfText(line));

  const streamParts = ['BT', '/F1 11 Tf', '50 800 Td'];
  let first = true;
  for (const line of safeLines) {
    if (first) {
      streamParts.push(`(${line}) Tj`);
      first = false;
    } else {
      streamParts.push(`0 -14 Td (${line}) Tj`);
    }
  }
  streamParts.push('ET');
  const stream = `${streamParts.join('\n')}\n`;

  const objects = [
    '1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n',
    '2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n',
    '3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >> endobj\n',
    `4 0 obj << /Length ${stream.length} >> stream\n${stream}endstream\nendobj\n`,
    '5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n',
  ];

  const header = '%PDF-1.4\n';
  const offsets: number[] = [0];
  let bodyText = '';
  for (const obj of objects) {
    offsets.push(header.length + bodyText.length);
    bodyText += obj;
  }
  const xrefStart = header.length + bodyText.length;

  let xref = `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (let i = 1; i < offsets.length; i += 1) {
    xref += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`;
  }
  const trailer = `trailer << /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF\n`;
  return header + bodyText + xref + trailer;
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function ResultDisplay({ result }: ResultDisplayProps) {
  const [modal, setModal] = useState<{ title: string; content: string; modelId?: string } | null>(null);
  const { prediction, future_path, shock_signal, explainability, knowledge_graph } = result;
  const aiInsights = useMemo(() => result?.ai_insights || {}, [result]);
  const steps = Array.isArray(future_path?.steps) ? future_path.steps : [];

  // Build forecast path data
  const pathData = steps.map((step: any) => ({
    step: step.step,
    label: `${step.step}d`,
    median: step.median_price,
    upper: step.upper_price,
    lower: step.lower_price,
  }));

  const multiCycleRows = steps.map((step: any) => ({
    cycle: `${step.step}d`,
    predictedReturn: Number(step.predicted_return || 0),
    medianPrice: Number(step.median_price || 0),
    lowerPrice: Number(step.lower_price || 0),
    upperPrice: Number(step.upper_price || 0),
  }));

  const normalizedRiskLevel = normalizeRiskLevel(prediction?.risk_level);

  const latestStep = steps.length > 0 ? steps[steps.length - 1] : null;
  const summaryHorizon = Math.max(1, Number(prediction?.horizon || latestStep?.step || 30));

  const fitSource: StepPoint[] = steps
    .map((step: any) => ({
      step: Number(step.step || 0),
      median: Number(step.median_price || 0),
      upper: Number(step.upper_price || 0),
      lower: Number(step.lower_price || 0),
      predictedReturn: Number(step.predicted_return || 0),
    }))
    .filter((item: StepPoint) => item.step > 0);
  const fittedSummaryPoint = fitPointByHorizon(fitSource, summaryHorizon);

  // Build factor contribution data
  const factorData = (explainability?.top_factors || []).map((factor: any) => ({
    name: factor.factor,
    value: factor.contribution,
  }));

  const factorContributionPercentData = useMemo(() => {
    const totalAbs = factorData.reduce((sum: number, item: { value: number }) => sum + Math.abs(Number(item.value || 0)), 0);
    return factorData
      .map((item: { name: string; value: number }) => {
        const raw = Number(item.value || 0);
        const pct = totalAbs > 0 ? (Math.abs(raw) / totalAbs) * 100 : 0;
        return {
          name: item.name,
          value: Number(pct.toFixed(2)),
          raw,
          direction: raw >= 0 ? 'Positive' : 'Negative',
        };
      })
      .sort((a: { value: number }, b: { value: number }) => b.value - a.value);
  }, [factorData]);

  // Build industry shock data
  const industryData = (shock_signal?.top_affected_industries || []).map((item: any) => ({
    name: item.industry,
    value: item.magnitude,
  }));

  const insightContent = useMemo(
    () => ({
      risk: {
        title: 'Risk Insight Details',
        content: aiInsights?.risk?.detail || 'No risk insight available.',
        modelId: aiInsights?.risk?.model_id,
      },
      industry: {
        title: 'Industry Impact Details',
        content: aiInsights?.industry?.detail || 'No industry insight available.',
        modelId: aiInsights?.industry?.model_id,
      },
      kg: {
        title: 'Knowledge Graph Details',
        content: aiInsights?.knowledge_graph?.detail || 'No knowledge graph insight available.',
        modelId: aiInsights?.knowledge_graph?.model_id,
      },
      report: {
        title: 'Report Insight Details',
        content: aiInsights?.report?.detail || 'No report insight available.',
        modelId: aiInsights?.report?.model_id,
      },
      financing: {
        title: 'Financing Recommendation Report',
        content: aiInsights?.financing?.detail || 'No financing recommendation generated.',
        modelId: aiInsights?.financing?.model_id,
      },
    }),
    [aiInsights]
  );

  const openModal = (key: 'risk' | 'industry' | 'kg' | 'report' | 'financing') => {
    setModal(insightContent[key]);
  };

  const downloadInsightPdf = (key: 'risk' | 'industry' | 'kg' | 'report' | 'financing') => {
    const target = insightContent[key];
    const pdfText = buildSimplePdfText(target.title, target.content, target.modelId);
    downloadBlob(
      new Blob([pdfText], { type: 'application/pdf' }),
      `${key}-insight.pdf`
    );
  };

  const downloadStructuredReportPdf = async () => {
    const reportId = result?.report?.report_id;
    if (!reportId) {
      downloadInsightPdf('report');
      return;
    }

    try {
      const resp = await fetch(`${API_BASE}/report/${encodeURIComponent(reportId)}/pdf`);
      if (!resp.ok) {
        throw new Error('server pdf download failed');
      }
      const blob = await resp.blob();
      downloadBlob(blob, `risk-report-${reportId}.pdf`);
    } catch {
      downloadInsightPdf('report');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="w-full max-w-7xl mx-auto p-4"
    >
      <h2 className="text-3xl font-bold mb-8 text-center metal-gradient">Prediction Results</h2>

      {/* Prediction Summary */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="bg-gray-900 p-6 rounded-lg border border-gray-800 mb-8"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-accent-primary">Prediction Summary</h3>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => openModal('risk')}
              className="text-sm text-accent-primary border border-accent-primary/50 px-3 py-1 rounded-md hover:bg-accent-primary hover:text-black transition-colors"
            >
              Details
            </button>
            <button
              type="button"
              onClick={() => downloadInsightPdf('risk')}
              className="text-sm text-accent-primary border border-accent-primary/50 px-3 py-1 rounded-md hover:bg-accent-primary hover:text-black transition-colors"
            >
              PDF
            </button>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-800 p-4 rounded-md">
            <p className="text-gray-400 text-sm">Expected Return ({summaryHorizon}d)</p>
            <p className="text-2xl font-bold text-white">
              {((fittedSummaryPoint?.predictedReturn || 0) * 100).toFixed(2)}%
            </p>
          </div>
          <div className="bg-gray-800 p-4 rounded-md">
            <p className="text-gray-400 text-sm">Price Range ({summaryHorizon}d)</p>
            <p className="text-2xl font-bold text-white">
              {fittedSummaryPoint
                ? `${Number(fittedSummaryPoint.lower || 0).toFixed(2)} - ${Number(fittedSummaryPoint.upper || 0).toFixed(2)}`
                : '-'}
            </p>
          </div>
          <div className="bg-gray-800 p-4 rounded-md">
            <p className="text-gray-400 text-sm">Risk Level</p>
            <p className={`text-2xl font-bold ${
              ['HIGH', 'EXTREME'].includes(normalizedRiskLevel) ? 'text-red-400' :
              normalizedRiskLevel === 'MEDIUM' ? 'text-yellow-400' :
              'text-green-400'
            }`}>
              {normalizedRiskLevel}
            </p>
          </div>
          <div className="bg-gray-800 p-4 rounded-md">
            <p className="text-gray-400 text-sm">Predicted Absolute Price</p>
            <p className="text-2xl font-bold text-white">
              {fittedSummaryPoint ? Number(fittedSummaryPoint.median || 0).toFixed(2) : '-'}
            </p>
          </div>
        </div>
      </motion.div>

      {/* Multi-horizon Table */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="bg-gray-900 p-6 rounded-lg border border-gray-800 mb-8"
      >
        <h3 className="text-xl font-bold mb-4 text-accent-primary">Multi-Horizon Forecast (1/3/7/14/30 days)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-gray-200">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-3 pr-4">Horizon</th>
                <th className="text-left py-3 pr-4">Expected Return</th>
                <th className="text-left py-3 pr-4">Median Price</th>
                <th className="text-left py-3 pr-4">Lower Bound</th>
                <th className="text-left py-3">Upper Bound</th>
              </tr>
            </thead>
            <tbody>
              {multiCycleRows.map((row: any) => (
                <tr key={row.cycle} className="border-b border-gray-800/80">
                  <td className="py-3 pr-4">{row.cycle}</td>
                  <td className="py-3 pr-4">{(row.predictedReturn * 100).toFixed(2)}%</td>
                  <td className="py-3 pr-4">{row.medianPrice.toFixed(4)}</td>
                  <td className="py-3 pr-4">{row.lowerPrice.toFixed(4)}</td>
                  <td className="py-3">{row.upperPrice.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Forecast Path */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="bg-gray-900 p-6 rounded-lg border border-gray-800 mb-8"
      >
        <h3 className="text-xl font-bold mb-4 text-accent-primary">Forecast Path</h3>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={pathData}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="label" stroke="#EAEAEA" />
              <YAxis stroke="#EAEAEA" />
              <Tooltip
                contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                labelStyle={{ color: '#EAEAEA' }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="median"
                  name="Median"
                stroke="#D4AF37"
                strokeWidth={2}
                activeDot={{ r: 8 }}
              />
              <Line
                type="monotone"
                dataKey="upper"
                  name="Upper"
                stroke="#F3E5AB"
                strokeWidth={1}
                strokeDasharray="5 5"
              />
              <Line
                type="monotone"
                dataKey="lower"
                  name="Lower"
                stroke="#B8860B"
                strokeWidth={1}
                strokeDasharray="5 5"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </motion.div>

      {/* Factor Contribution and Industry Shock */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        {/* Factor Contribution */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.6 }}
          className="bg-gray-900 p-6 rounded-lg border border-gray-800"
        >
          <h3 className="text-xl font-bold mb-4 text-accent-primary">Factor Contribution (%)</h3>
          <p className="text-xs text-gray-400 mb-4">
            Percentages are normalized by absolute contribution, aligned with SHAP-based ranking presentation.
          </p>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={factorContributionPercentData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="name" stroke="#EAEAEA" />
                <YAxis stroke="#EAEAEA" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                  labelStyle={{ color: '#EAEAEA' }}
                />
                <Bar dataKey="value" name="Contribution %">
                  {factorContributionPercentData.map((entry: { name: string; value: number }, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 space-y-2 max-h-44 overflow-auto pr-1">
            {factorContributionPercentData.map((item: { name: string; value: number; raw: number; direction: string }) => (
              <div key={item.name} className="flex items-center justify-between bg-gray-800 px-3 py-2 rounded-md text-sm">
                <span className="text-gray-200 truncate mr-3">{item.name}</span>
                <span className="text-gray-300 mr-2">{item.value.toFixed(2)}%</span>
                <span className={item.direction === 'Positive' ? 'text-green-400' : 'text-red-400'}>
                  {item.direction}
                </span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Industry Shock */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.8 }}
          className="bg-gray-900 p-6 rounded-lg border border-gray-800"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-accent-primary">Industry Shock</h3>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => openModal('industry')}
                className="text-sm text-accent-primary border border-accent-primary/50 px-3 py-1 rounded-md hover:bg-accent-primary hover:text-black transition-colors"
              >
                Details
              </button>
              <button
                type="button"
                onClick={() => downloadInsightPdf('industry')}
                className="text-sm text-accent-primary border border-accent-primary/50 px-3 py-1 rounded-md hover:bg-accent-primary hover:text-black transition-colors"
              >
                PDF
              </button>
            </div>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={industryData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${((percent || 0) * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {industryData.map((entry: { name: string; value: number }, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                  labelStyle={{ color: '#EAEAEA' }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>

      {/* Knowledge Graph */}
      {knowledge_graph && knowledge_graph.paths && knowledge_graph.paths.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="bg-gray-900 p-6 rounded-lg border border-gray-800 mb-8"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-accent-primary">Knowledge Graph</h3>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => openModal('kg')}
                className="text-sm text-accent-primary border border-accent-primary/50 px-3 py-1 rounded-md hover:bg-accent-primary hover:text-black transition-colors"
              >
                Details
              </button>
              <button
                type="button"
                onClick={() => downloadInsightPdf('kg')}
                className="text-sm text-accent-primary border border-accent-primary/50 px-3 py-1 rounded-md hover:bg-accent-primary hover:text-black transition-colors"
              >
                PDF
              </button>
            </div>
          </div>
          <div className="space-y-4">
            {knowledge_graph.paths.map((path: any, index: number) => (
              <div key={index} className="bg-gray-800 p-4 rounded-md">
                <h4 className="text-lg font-bold text-accent-primary mb-2">{path.industry}</h4>
                <p className="text-gray-300">{path.arrow_path}</p>
                {Array.isArray(path.node_levels) && path.node_levels.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {path.node_levels.map((node: any, nIdx: number) => (
                      <span
                        key={`${path.industry}-${nIdx}`}
                        className="text-xs bg-gray-700 text-gray-100 px-2 py-1 rounded"
                      >
                        {node.name}: {normalizeKgLevel(node.level)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Report Summary */}
      {result.report && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          className="bg-gray-900 p-6 rounded-lg border border-gray-800"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-accent-primary">Report Summary</h3>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => openModal('report')}
                className="text-sm text-accent-primary border border-accent-primary/50 px-3 py-1 rounded-md hover:bg-accent-primary hover:text-black transition-colors"
              >
                Details
              </button>
              <button
                type="button"
                onClick={downloadStructuredReportPdf}
                className="text-sm text-accent-primary border border-accent-primary/50 px-3 py-1 rounded-md hover:bg-accent-primary hover:text-black transition-colors"
              >
                PDF
              </button>
            </div>
          </div>
          <div className="text-gray-300 whitespace-pre-line">
            {result.report.sections?.executive_summary
              || result.report.sections?.trend_and_confidence
              || 'No report summary available.'}
          </div>
        </motion.div>
      )}

      {aiInsights?.financing?.detail && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.35 }}
          className="bg-gray-900 p-6 rounded-lg border border-gray-800 mt-8"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-accent-primary">Financing Recommendation Report</h3>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => openModal('financing')}
                className="text-sm text-accent-primary border border-accent-primary/50 px-3 py-1 rounded-md hover:bg-accent-primary hover:text-black transition-colors"
              >
                Details
              </button>
              <button
                type="button"
                onClick={() => downloadInsightPdf('financing')}
                className="text-sm text-accent-primary border border-accent-primary/50 px-3 py-1 rounded-md hover:bg-accent-primary hover:text-black transition-colors"
              >
                PDF
              </button>
            </div>
          </div>
          <div className="text-gray-300 whitespace-pre-line">
            {aiInsights.financing.detail}
          </div>
        </motion.div>
      )}

      {modal && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center px-4">
          <div className="w-full max-w-3xl bg-gray-900 border border-gray-700 rounded-lg p-6">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <h3 className="text-xl font-bold text-accent-primary">{modal.title}</h3>
                {modal.modelId && (
                  <p className="text-xs text-gray-400 mt-1">Model: {modal.modelId}</p>
                )}
              </div>
              <button
                type="button"
                onClick={() => setModal(null)}
                className="text-sm px-3 py-1 border border-gray-500 rounded-md text-gray-200 hover:bg-gray-800"
              >
                Close
              </button>
            </div>
            <div className="max-h-[60vh] overflow-auto whitespace-pre-line text-gray-200 leading-7">
              {modal.content}
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
