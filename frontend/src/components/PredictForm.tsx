'use client';

import { useState } from 'react';
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsPredicting(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_id: fileId, horizon, include_explainability: true, include_knowledge_graph: true, report_style: 'banking', industries: ['aviation', 'shipping', 'chemical'] }),
      });
      if (!response.ok) throw new Error('预测失败');
      const data = await response.json();
      if (data.success) onPredictSuccess(data.data);
      else setError(data.message || '预测失败');
    } catch {
      setError('预测失败，请检查网络连接或后端服务是否运行');
    } finally {
      setIsPredicting(false);
    }
  };

  return <form onSubmit={handleSubmit}><button type="submit" disabled={isPredicting}>{isPredicting ? '预测中...' : '开始预测'}</button>{error}</form>;
}
