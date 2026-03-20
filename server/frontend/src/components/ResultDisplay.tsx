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

export default function ResultDisplay({ result }: ResultDisplayProps) {
  const [modal, setModal] = useState<{ title: string; content: string; modelId?: string } | null>(null);
  const { prediction, future_path, shock_signal, explainability, knowledge_graph } = result;
  const aiInsights = result?.ai_insights || {};
  const steps = Array.isArray(future_path?.steps) ? future_path.steps : [];

  // 准备预测路径数据
  const pathData = steps.map((step: any) => ({
    step: step.step,
    label: `${step.step}天`,
    median: step.median_price,
    upper: step.upper_price,
    lower: step.lower_price,
  }));

  const multiCycleRows = steps.map((step: any) => ({
    cycle: `${step.step}天`,
    predictedReturn: Number(step.predicted_return || 0),
    medianPrice: Number(step.median_price || 0),
    lowerPrice: Number(step.lower_price || 0),
    upperPrice: Number(step.upper_price || 0),
  }));

  const latestStep = steps.length > 0 ? steps[steps.length - 1] : null;
  const summaryHorizon = Math.max(1, Number(prediction?.horizon || latestStep?.step || 30));

  const fittedSummaryPoint = useMemo(() => {
    const fitSource: StepPoint[] = steps
      .map((step: any) => ({
        step: Number(step.step || 0),
        median: Number(step.median_price || 0),
        upper: Number(step.upper_price || 0),
        lower: Number(step.lower_price || 0),
        predictedReturn: Number(step.predicted_return || 0),
      }))
      .filter((item: StepPoint) => item.step > 0);

    return fitPointByHorizon(fitSource, summaryHorizon);
  }, [steps, summaryHorizon]);

  // 准备因子贡献数据
  const factorData = (explainability?.top_factors || []).map((factor: any) => ({
    name: factor.factor,
    value: factor.contribution,
  }));

  // 准备行业冲击数据
  const industryData = (shock_signal?.top_affected_industries || []).map((item: any) => ({
    name: item.industry,
    value: item.magnitude,
  }));

  const insightContent = useMemo(
    () => ({
      risk: {
        title: '风险水平详情',
        content: aiInsights?.risk?.detail || '暂无风险详情。',
        modelId: aiInsights?.risk?.model_id,
      },
      industry: {
        title: '行业冲击详情',
        content: aiInsights?.industry?.detail || '暂无行业冲击详情。',
        modelId: aiInsights?.industry?.model_id,
      },
      kg: {
        title: '知识图谱详情',
        content: aiInsights?.knowledge_graph?.detail || '暂无知识图谱详情。',
        modelId: aiInsights?.knowledge_graph?.model_id,
      },
      report: {
        title: '报告摘要详情',
        content: aiInsights?.report?.detail || '暂无报告详情。',
        modelId: aiInsights?.report?.model_id,
      },
    }),
    [aiInsights]
  );

  const openModal = (key: 'risk' | 'industry' | 'kg' | 'report') => {
    setModal(insightContent[key]);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="w-full max-w-7xl mx-auto p-4"
    >
      <h2 className="text-3xl font-bold mb-8 text-center metal-gradient">预测结果</h2>

      {/* 预测摘要 */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="bg-gray-900 p-6 rounded-lg border border-gray-800 mb-8"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-accent-primary">预测摘要</h3>
          <button
            type="button"
            onClick={() => openModal('risk')}
            className="text-sm text-accent-primary border border-accent-primary/50 px-3 py-1 rounded-md hover:bg-accent-primary hover:text-black transition-colors"
          >
            详情
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-800 p-4 rounded-md">
            <p className="text-gray-400 text-sm">{summaryHorizon}天预期收益率</p>
            <p className="text-2xl font-bold text-white">
              {((fittedSummaryPoint?.predictedReturn || 0) * 100).toFixed(2)}%
            </p>
          </div>
          <div className="bg-gray-800 p-4 rounded-md">
            <p className="text-gray-400 text-sm">{summaryHorizon}天价格区间</p>
            <p className="text-2xl font-bold text-white">
              {fittedSummaryPoint
                ? `${Number(fittedSummaryPoint.lower || 0).toFixed(2)} - ${Number(fittedSummaryPoint.upper || 0).toFixed(2)}`
                : '-'}
            </p>
          </div>
          <div className="bg-gray-800 p-4 rounded-md">
            <p className="text-gray-400 text-sm">风险水平</p>
            <p className={`text-2xl font-bold ${
              ['HIGH', 'EXTREME', '高风险', '极高风险'].includes(String(prediction?.risk_level || '').toUpperCase()) ||
              String(prediction?.risk_level || '').includes('高') ? 'text-red-400' :
              ['MEDIUM', '中风险'].includes(String(prediction?.risk_level || '').toUpperCase()) ||
              String(prediction?.risk_level || '').includes('中') ? 'text-yellow-400' :
              'text-green-400'
            }`}>
              {prediction?.risk_level || 'UNKNOWN'}
            </p>
          </div>
          <div className="bg-gray-800 p-4 rounded-md">
            <p className="text-gray-400 text-sm">预测绝对价格</p>
            <p className="text-2xl font-bold text-white">
              {fittedSummaryPoint ? Number(fittedSummaryPoint.median || 0).toFixed(2) : '-'}
            </p>
          </div>
        </div>
      </motion.div>

      {/* 多周期结果表 */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="bg-gray-900 p-6 rounded-lg border border-gray-800 mb-8"
      >
        <h3 className="text-xl font-bold mb-4 text-accent-primary">多周期预测结果 (1/3/7/14/30 天)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-gray-200">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-3 pr-4">周期</th>
                <th className="text-left py-3 pr-4">预测涨跌幅</th>
                <th className="text-left py-3 pr-4">预测绝对价格</th>
                <th className="text-left py-3 pr-4">风险区间下限</th>
                <th className="text-left py-3">风险区间上限</th>
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

      {/* 预测路径图表 */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="bg-gray-900 p-6 rounded-lg border border-gray-800 mb-8"
      >
        <h3 className="text-xl font-bold mb-4 text-accent-primary">预测路径</h3>
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
                name="中位数价格"
                stroke="#D4AF37"
                strokeWidth={2}
                activeDot={{ r: 8 }}
              />
              <Line
                type="monotone"
                dataKey="upper"
                name="上限价格"
                stroke="#F3E5AB"
                strokeWidth={1}
                strokeDasharray="5 5"
              />
              <Line
                type="monotone"
                dataKey="lower"
                name="下限价格"
                stroke="#B8860B"
                strokeWidth={1}
                strokeDasharray="5 5"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </motion.div>

      {/* 因子贡献和行业冲击 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        {/* 因子贡献 */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.6 }}
          className="bg-gray-900 p-6 rounded-lg border border-gray-800"
        >
          <h3 className="text-xl font-bold mb-4 text-accent-primary">因子贡献</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={factorData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="name" stroke="#EAEAEA" />
                <YAxis stroke="#EAEAEA" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                  labelStyle={{ color: '#EAEAEA' }}
                />
                <Bar dataKey="value" name="贡献值">
                  {factorData.map((entry: { name: string; value: number }, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* 行业冲击 */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.8 }}
          className="bg-gray-900 p-6 rounded-lg border border-gray-800"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-accent-primary">行业冲击</h3>
            <button
              type="button"
              onClick={() => openModal('industry')}
              className="text-sm text-accent-primary border border-accent-primary/50 px-3 py-1 rounded-md hover:bg-accent-primary hover:text-black transition-colors"
            >
              详情
            </button>
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

      {/* 知识图谱 */}
      {knowledge_graph && knowledge_graph.paths && knowledge_graph.paths.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="bg-gray-900 p-6 rounded-lg border border-gray-800 mb-8"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-accent-primary">知识图谱</h3>
            <button
              type="button"
              onClick={() => openModal('kg')}
              className="text-sm text-accent-primary border border-accent-primary/50 px-3 py-1 rounded-md hover:bg-accent-primary hover:text-black transition-colors"
            >
              详情
            </button>
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
                        {node.name}: {node.level}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* 报告摘要 */}
      {result.report && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          className="bg-gray-900 p-6 rounded-lg border border-gray-800"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-accent-primary">报告摘要</h3>
            <button
              type="button"
              onClick={() => openModal('report')}
              className="text-sm text-accent-primary border border-accent-primary/50 px-3 py-1 rounded-md hover:bg-accent-primary hover:text-black transition-colors"
            >
              详情
            </button>
          </div>
          <div className="text-gray-300 whitespace-pre-line">
            {result.report.sections?.executive_summary
              || result.report.sections?.trend_and_confidence
              || '暂无报告摘要'}
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
                  <p className="text-xs text-gray-400 mt-1">模型：{modal.modelId}</p>
                )}
              </div>
              <button
                type="button"
                onClick={() => setModal(null)}
                className="text-sm px-3 py-1 border border-gray-500 rounded-md text-gray-200 hover:bg-gray-800"
              >
                关闭
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
