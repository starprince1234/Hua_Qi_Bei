'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { getApiBasePath } from './apiBase';

interface PredictFormProps {
  fileId: string;
  onPredictSuccess: (result: unknown) => void;
}

const API_BASE = getApiBasePath();

export default function PredictForm({ fileId, onPredictSuccess }: PredictFormProps) {
  const [isPredicting, setIsPredicting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [horizon, setHorizon] = useState(30);
  const [industries, setIndustries] = useState<string[]>(['aviation', 'shipping', 'chemical']);
  const [progressStep, setProgressStep] = useState(0);

  const progressStages = useMemo(
    () => [
      'Validating request and feature snapshot',
      'Model inference and path reconstruction',
      'Risk, explainability, and graph analysis',
      'Generating AI reports and financing advice',
    ],
    []
  );

  useEffect(() => {
    if (!isPredicting) {
      return;
    }

    const timer = window.setInterval(() => {
      setProgressStep((prev) => Math.min(prev + 1, progressStages.length - 1));
    }, 20000);

    return () => window.clearInterval(timer);
  }, [isPredicting, progressStages.length]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsPredicting(true);
    setError(null);
    setProgressStep(0);

    try {
      const response = await fetch(`${API_BASE}/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_id: fileId,
          horizon,
          include_explainability: true,
          include_knowledge_graph: true,
          report_style: 'banking',
          industries,
        }),
      });

      if (!response.ok) {
        throw new Error('Prediction failed');
      }

      const data = await response.json();
      if (data.success) {
        onPredictSuccess(data.data);
      } else {
        setError(data.message || 'Prediction failed');
      }
    } catch {
      setError('Prediction failed. Please check network connectivity or backend status.');
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
      <h2 className="text-2xl font-bold mb-6 text-center metal-gradient">Smart Prediction</h2>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Forecast Horizon (days)
            </label>
            <input
              type="number"
              min={1}
              max={60}
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-2 text-gray-300 focus:outline-none focus:border-accent-primary"
            />
            <p className="text-xs text-gray-500 mt-1">Range: 1-60 days. Non-standard horizons are fitted from 1/3/7/14/30-day paths.</p>
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-300">
              Target Entities
            </label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {[
                { value: 'aviation', label: 'Aviation' },
                { value: 'shipping', label: 'Shipping' },
                { value: 'chemical', label: 'Chemical' },
                { value: 'refinery', label: 'Refinery' },
                { value: 'logistics', label: 'Logistics' },
                { value: 'heavy_manufacturing', label: 'Heavy Manufacturing' },
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
          {isPredicting && (
            <div className="bg-gray-800/60 border border-gray-700 rounded-md p-4 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-200 font-medium">Prediction Pipeline Progress</p>
                <p className="text-xs text-accent-primary">Estimated time: 3 min</p>
              </div>
              <div className="w-full h-2 rounded-full bg-gray-700 overflow-hidden">
                <div
                  className="h-full bg-accent-primary transition-all duration-500"
                  style={{ width: `${((progressStep + 1) / progressStages.length) * 100}%` }}
                />
              </div>
              <ul className="space-y-2 text-sm">
                {progressStages.map((stage, index) => {
                  const status = index < progressStep ? 'done' : index === progressStep ? 'in-progress' : 'pending';
                  return (
                    <li key={stage} className="flex items-center justify-between">
                      <span className={status === 'pending' ? 'text-gray-500' : 'text-gray-200'}>{stage}</span>
                      <span
                        className={
                          status === 'done'
                            ? 'text-green-400'
                            : status === 'in-progress'
                              ? 'text-yellow-400'
                              : 'text-gray-500'
                        }
                      >
                        {status === 'done' ? 'Completed' : status === 'in-progress' ? 'In Progress' : 'Pending'}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
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
          {isPredicting ? 'Predicting...' : 'Start Prediction'}
        </motion.button>
      </form>
    </motion.div>
  );
}
