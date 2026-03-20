'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { getApiBasePath } from './apiBase';

interface PredictFormProps {
  fileId: string;
  onPredictSuccess: (result: any) => void;
}

const API_BASE = getApiBasePath();

export default function PredictForm({ fileId, onPredictSuccess }: PredictFormProps) {
  const [isPredicting, setIsPredicting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [horizon, setHorizon] = useState(30);
  const [includeExplainability, setIncludeExplainability] = useState(true);
  const [includeKnowledgeGraph, setIncludeKnowledgeGraph] = useState(true);
  const [reportStyle, setReportStyle] = useState('banking');
  const [industries, setIndustries] = useState<string[]>(['aviation', 'shipping', 'chemical']);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsPredicting(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_id: fileId,
          horizon,
          include_explainability: includeExplainability,
          include_knowledge_graph: includeKnowledgeGraph,
          report_style: reportStyle,
          industries,
        }),
      });

      if (!response.ok) {
        throw new Error('预测失败');
      }

      const data = await response.json();
      if (data.success) {
        onPredictSuccess(data.data);
      } else {
        setError(data.message || '预测失败');
      }
    } catch (error) {
      setError('预测失败，请检查网络连接或后端服务是否运行');
    } finally {
      setIsPredicting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="bg-gray-900 p-8 rounded-lg border border-gray-800 w-full max-w-3xl mx-auto"
    >
      <h2 className="text-2xl font-bold mb-6 text-center metal-gradient">智能预测</h2>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              预测周期 (天)
            </label>
            <input
              type="number"
              min={1}
              max={60}
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-2 text-gray-300 focus:outline-none focus:border-accent-primary"
            />
            <p className="text-xs text-gray-500 mt-1">支持 1-60 天，非标准周期将基于 1/3/7/14/30 路径拟合展示。</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                报告风格
              </label>
              <select
                value={reportStyle}
                onChange={(e) => setReportStyle(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-2 text-gray-300 focus:outline-none focus:border-accent-primary"
              >
                <option value="banking">银行风格</option>
                <option value="concise">精简</option>
                <option value="verbose">详细</option>
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-300">
              目标行业
            </label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {[
                { value: 'aviation', label: '航空' },
                { value: 'shipping', label: '航运' },
                { value: 'chemical', label: '化工' },
                { value: 'refinery', label: '炼化' },
                { value: 'logistics', label: '物流' },
                { value: 'heavy_manufacturing', label: '重制造' },
              ].map((industry) => (
                <div key={industry.value} className="flex items-center">
                  <input
                    type="checkbox"
                    id={`industry-${industry.value}`}
                    checked={industries.includes(industry.value)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setIndustries([...industries, industry.value]);
                      } else {
                        setIndustries(industries.filter((i) => i !== industry.value));
                      }
                    }}
                    className="mr-2 accent-accent-primary"
                  />
                  <label htmlFor={`industry-${industry.value}`} className="text-sm text-gray-300">
                    {industry.label}
                  </label>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="includeExplainability"
                checked={includeExplainability}
                onChange={(e) => setIncludeExplainability(e.target.checked)}
                className="mr-2 accent-accent-primary"
              />
              <label htmlFor="includeExplainability" className="text-sm text-gray-300">
                包含因子解释
              </label>
            </div>
            <div className="flex items-center">
              <input
                type="checkbox"
                id="includeKnowledgeGraph"
                checked={includeKnowledgeGraph}
                onChange={(e) => setIncludeKnowledgeGraph(e.target.checked)}
                className="mr-2 accent-accent-primary"
              />
              <label htmlFor="includeKnowledgeGraph" className="text-sm text-gray-300">
                包含知识图谱
              </label>
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-md p-4 text-red-400">
            {error}
          </div>
        )}

        <motion.button
          type="submit"
          whileHover={{ letterSpacing: '2px', boxShadow: '0 0 20px rgba(212, 175, 55, 0.5)' }}
          disabled={isPredicting}
          className="w-full px-6 py-3 bg-accent-primary text-background rounded-md font-medium transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isPredicting ? '预测中...' : '开始预测'}
        </motion.button>
      </form>
    </motion.div>
  );
}
