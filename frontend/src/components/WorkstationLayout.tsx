
"use client";

import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import BacktestPanel from './BacktestPanel';
import FactorPanel from './FactorPanel';
import FileUploader from './FileUploader';
import NewsPanel from './NewsPanel';
import PredictForm from './PredictForm';
import ResultDisplay from './ResultDisplay';
import { getOverview } from '@/lib/api';
import type { OverviewData } from '@/types/intelligence';

type WorkstationTab = 'overview' | 'workstation' | 'news' | 'backtest' | 'factorHistory';
type IntelligenceStep = 'upload' | 'predict' | 'result';

interface TabConfig {
  id: WorkstationTab;
  label: string;
}

interface CapabilityCardConfig {
  title: string;
  metric: string;
  description: string;
  actionLabel: string;
  onClick: () => void;
  primary?: boolean;
}

const tabs: TabConfig[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'workstation', label: 'Workstation' },
  { id: 'news', label: 'News Events' },
  { id: 'backtest', label: 'Backtest Validation' },
  { id: 'factorHistory', label: 'Factor History' },
];

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

function formatPercent(value?: number | null): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-';
  }
  return `${(value * 100).toFixed(1)}%`;
}

function formatReturn(value?: number | null): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 'Awaiting prediction';
  }
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`;
}

export default function WorkstationLayout() {
  const [activeTab, setActiveTab] = useState<WorkstationTab>('overview');
  const [step, setStep] = useState<IntelligenceStep>('upload');
  const [fileId, setFileId] = useState<string>('');
  const [predictionResult, setPredictionResult] = useState<Record<string, unknown> | null>(null);
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [overviewRefreshKey, setOverviewRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;

    async function loadOverview(): Promise<void> {
      try {
        const data = await getOverview();
        if (active) {
          setOverview(data);
          setOverviewError(null);
        }
      } catch (error: unknown) {
        if (active) {
          setOverviewError(error instanceof Error ? error.message : 'Overview data failed to load.');
        }
      }
    }

    void loadOverview();

    return () => {
      active = false;
    };
  }, [overviewRefreshKey]);

  const capabilityCards: CapabilityCardConfig[] = [
    {
      title: '上传预测',
      metric: '下一步: 生成预测',
      description: '上传油价与宏观因子数据，进入现有预测配置和结果解释流程。',
      actionLabel: '开始上传',
      primary: true,
      onClick: () => {
        setActiveTab('workstation');
        setStep('upload');
      },
    },
    {
      title: '新闻事件',
      metric: overview ? `事件数: ${overview.news_event_count}` : '事件加载中',
      description: '查看近 24 小时油价事件驱动信号、方向、强度和置信度。',
      actionLabel: '查看事件',
      onClick: () => setActiveTab('news'),
    },
    {
      title: '回测验证',
      metric: overview?.backtest.available ? `样本数: ${overview.backtest.point_count}` : '等待历史标签数据',
      description: '验证历史窗口下的方向命中、误差水平和区间覆盖表现；当前不再使用 demo 回测。',
      actionLabel: '查看回测',
      onClick: () => setActiveTab('backtest'),
    },
    {
      title: '因子历史',
      metric: overview?.dominant_factor.label
        ? `主导因子: ${overview.dominant_factor.label}`
        : '等待预测运行',
      description: '追踪上传推理后生成的库存、地缘、宏观、供需和技术因子贡献。',
      actionLabel: '查看因子',
      onClick: () => setActiveTab('factorHistory'),
    },
  ];

  const handleUploadSuccess = (id: string) => {
    setFileId(id);
    setStep('predict');
  };

  const handlePredictSuccess = (result: unknown) => {
    if (result && typeof result === 'object') {
      setPredictionResult(result as Record<string, unknown>);
    } else {
      setPredictionResult({});
    }
    setOverviewRefreshKey((current) => current + 1);
    setStep('result');
  };

  const handleBackToUpload = () => {
    setStep('upload');
    setFileId('');
    setPredictionResult(null);
  };

  const handleBackToPredict = () => {
    setStep('predict');
    setPredictionResult(null);
  };

  return (
    <div className="relative min-h-screen">
      {/* 噪点纹理 */}
      <div className="noise-texture"></div>

      {/* 聚焦效果 */}
      <div className="spotlight" id="spotlight"></div>

      <nav className="sticky top-0 z-20 border-b border-gray-800 bg-background/85 px-4 py-4 backdrop-blur-md">
        <div className="max-w-7xl mx-auto flex flex-wrap gap-3">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <motion.button
                key={tab.id}
                type="button"
                whileHover={{ y: -2 }}
                onClick={() => setActiveTab(tab.id)}
                className={`relative rounded-md px-4 py-2 text-sm font-medium transition-colors duration-300 ${
                  isActive
                    ? 'text-background'
                    : 'border border-gray-700 text-gray-300 hover:border-accent-primary hover:text-accent-primary'
                }`}
              >
                {isActive && (
                  <motion.span
                    layoutId="active-workstation-tab"
                    className="absolute inset-0 rounded-md bg-accent-primary"
                    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                  />
                )}
                <span className="relative z-10">{tab.label}</span>
              </motion.button>
            );
          })}
        </div>
      </nav>

      <AnimatePresence mode="wait">
        {activeTab === 'overview' && (
          <motion.div
            key="overview"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
            {/* 工作台首屏 */}
            <section className="relative z-10 min-h-screen px-4 py-12">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="mx-auto flex max-w-7xl flex-col gap-8"
              >
                <div className="rounded-lg border border-gray-800 bg-gray-900/90 p-5 shadow-2xl shadow-black/20">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                      <p className="text-sm uppercase tracking-[0.3em] text-accent-primary">Risk intelligence console</p>
                      <h1 className="mt-2 text-4xl font-bold text-white md:text-5xl">Oil Risk Intelligence 工作台</h1>
                    </div>
                    <div className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
                      <div className="rounded-md border border-gray-800 bg-gray-950 px-4 py-3">
                        <p className="text-xs uppercase tracking-wide text-gray-500">Data Updated</p>
                        <p className="mt-1 font-semibold text-gray-100">{formatTimestamp(overview?.updated_at)}</p>
                      </div>
                      <div className="rounded-md border border-gray-800 bg-gray-950 px-4 py-3">
                        <p className="text-xs uppercase tracking-wide text-gray-500">Model Version</p>
                        <p className="mt-1 font-semibold text-gray-100">{overview?.latest_prediction.model_version ?? 'Awaiting prediction'}</p>
                      </div>
                      <div className="rounded-md border border-green-500/30 bg-green-500/10 px-4 py-3">
                        <p className="text-xs uppercase tracking-wide text-green-300/80">News Provider</p>
                        <p className="mt-1 font-semibold text-green-200">{overview?.news_provider_status ?? 'Loading'}</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                  {capabilityCards.map((card) => (
                    <motion.button
                      key={card.title}
                      type="button"
                      whileHover={{ y: -6, boxShadow: '0 20px 40px rgba(0, 0, 0, 0.35)' }}
                      whileTap={{ scale: 0.98 }}
                      onClick={card.onClick}
                      className={`rounded-lg border p-5 text-left transition-all duration-300 ${
                        card.primary
                          ? 'border-accent-primary bg-accent-primary text-background'
                          : 'border-gray-800 bg-gray-900 text-gray-100 hover:border-accent-primary'
                      }`}
                    >
                      <div className="flex h-full min-h-48 flex-col justify-between gap-5">
                        <div>
                          <p className={`text-xs uppercase tracking-[0.25em] ${card.primary ? 'text-background/70' : 'text-gray-500'}`}>
                            Entry Point
                          </p>
                          <h2 className="mt-3 text-2xl font-bold">{card.title}</h2>
                          <p className={`mt-3 text-sm leading-6 ${card.primary ? 'text-background/80' : 'text-gray-400'}`}>{card.description}</p>
                        </div>
                        <div>
                          <p className={`text-lg font-semibold ${card.primary ? 'text-background' : 'text-accent-primary'}`}>{card.metric}</p>
                          <p className={`mt-2 text-sm font-medium ${card.primary ? 'text-background/80' : 'text-gray-300'}`}>{card.actionLabel} →</p>
                        </div>
                      </div>
                    </motion.button>
                  ))}
                </div>

                <div className="rounded-lg border border-gray-800 bg-gray-900 p-6">
                  <div className="mb-5 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
                    <div>
                      <p className="text-sm uppercase tracking-[0.25em] text-gray-500">Today&apos;s briefing</p>
                      <h2 className="mt-2 text-3xl font-bold text-accent-primary">今日风险摘要</h2>
                    </div>
                    <p className="text-sm text-gray-400">
                      {overviewError ? `Overview load warning: ${overviewError}` : 'Online data from news providers and successful uploaded prediction runs.'}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                    <article className="rounded-md border border-red-500/30 bg-red-500/10 p-4">
                      <p className="text-xs uppercase tracking-wide text-red-200/80">High-impact event</p>
                      <h3 className="mt-2 text-lg font-bold text-white">{overview?.high_impact_event?.title ?? 'No live event loaded yet'}</h3>
                      <p className="mt-2 text-sm leading-6 text-gray-300">
                        {overview?.high_impact_event
                          ? `${overview.high_impact_event.impact_direction} · ${overview.high_impact_event.impact_level} · ${overview.high_impact_event.source ?? 'unknown source'}`
                          : 'News provider has not returned a high-impact event for the current filters.'}
                      </p>
                    </article>
                    <article className="rounded-md border border-gray-800 bg-gray-950 p-4">
                      <p className="text-xs uppercase tracking-wide text-gray-500">Latest prediction</p>
                      <h3 className="mt-2 text-3xl font-bold text-white">{formatReturn(overview?.latest_prediction.median_return)}</h3>
                      <p className="mt-2 text-sm text-gray-300">
                        Risk {overview?.latest_prediction.risk_level ?? '-'} · confidence {formatPercent(overview?.latest_prediction.confidence_score)}
                      </p>
                    </article>
                    <article className="rounded-md border border-accent-primary/40 bg-accent-primary/10 p-4">
                      <p className="text-xs uppercase tracking-wide text-accent-primary/80">Dominant factor</p>
                      <h3 className="mt-2 text-2xl font-bold text-white">
                        {overview?.dominant_factor.label
                          ? `${overview.dominant_factor.label} ${formatPercent(overview.dominant_factor.contribution)}`
                          : 'Awaiting prediction'}
                      </h3>
                      <p className="mt-2 text-sm text-gray-300">
                        Factor history points: {overview?.factor_history_points ?? 0}; backtest status: {overview?.backtest.provider_status ?? 'online_empty'}.
                      </p>
                    </article>
                  </div>
                </div>
              </motion.div>
            </section>
          </motion.div>
        )}

        {activeTab === 'workstation' && (
          <motion.div
            key="workstation"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
          >

            {/* 文件上传 */}
            {step === 'upload' && (
              <section className="relative z-10 py-20 px-4">
                <div className="max-w-7xl mx-auto">
                  <motion.button
                    whileHover={{ letterSpacing: '2px', boxShadow: '0 0 20px rgba(212, 175, 55, 0.5)' }}
                    onClick={() => setActiveTab('overview')}
                    className="mb-8 px-6 py-2 bg-transparent border-2 border-accent-primary text-accent-primary rounded-md font-medium transition-all duration-300"
                  >
                    ← Back to Home
                  </motion.button>
                  <FileUploader onUploadSuccess={handleUploadSuccess} />
                </div>
              </section>
            )}

            {/* 预测表单 */}
            {step === 'predict' && (
              <section className="relative z-10 py-20 px-4">
                <div className="max-w-7xl mx-auto">
                  <motion.button
                    whileHover={{ letterSpacing: '2px', boxShadow: '0 0 20px rgba(212, 175, 55, 0.5)' }}
                    onClick={handleBackToUpload}
                    className="mb-8 px-6 py-2 bg-transparent border-2 border-accent-primary text-accent-primary rounded-md font-medium transition-all duration-300"
                  >
                    ← Back to Upload
                  </motion.button>
                  <PredictForm fileId={fileId} onPredictSuccess={handlePredictSuccess} />
                </div>
              </section>
            )}

            {/* 结果展示 */}
            {step === 'result' && (
              <section className="relative z-10 py-20 px-4">
                <div className="max-w-7xl mx-auto">
                  <motion.button
                    whileHover={{ letterSpacing: '2px', boxShadow: '0 0 20px rgba(212, 175, 55, 0.5)' }}
                    onClick={handleBackToPredict}
                    className="mb-8 px-6 py-2 bg-transparent border-2 border-accent-primary text-accent-primary rounded-md font-medium transition-all duration-300"
                  >
                    ← Back to Predict
                  </motion.button>
                  {predictionResult && <ResultDisplay result={predictionResult} />}
                </div>
              </section>
            )}
          </motion.div>
        )}

        {activeTab === 'news' && (
          <motion.div key="news" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <NewsPanel />
          </motion.div>
        )}

        {activeTab === 'backtest' && (
          <motion.div key="backtest" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <BacktestPanel />
          </motion.div>
        )}

        {activeTab === 'factorHistory' && (
          <motion.div key="factor-history" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <FactorPanel />
          </motion.div>
        )}
      </AnimatePresence>

      {/* 页脚 */}
      <footer className="relative z-10 py-12 px-4 border-t border-gray-800">
        <div className="max-w-7xl mx-auto text-center">
          <p className="text-gray-400">
            © 2026 Oil Risk Intelligence Platform | Enterprise-Grade Financial Analytics
          </p>
        </div>
      </footer>

      {/* 聚焦效果脚本 */}
      <script dangerouslySetInnerHTML={{
        __html: `
          document.addEventListener('mousemove', (e) => {
            const spotlight = document.getElementById('spotlight');
            if (spotlight) {
              spotlight.style.left = e.clientX + 'px';
              spotlight.style.top = e.clientY + 'px';
            }
          });
        `
      }} />
    </div>
  );
}
