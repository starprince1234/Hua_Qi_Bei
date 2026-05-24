'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import FileUploader from '../components/FileUploader';
import PredictForm from '../components/PredictForm';
import ResultDisplay from '../components/ResultDisplay';

export default function Home() {
  const [step, setStep] = useState<'upload' | 'predict' | 'result' | 'initial'>('initial');
  const [fileId, setFileId] = useState<string>('');
  const [predictionResult, setPredictionResult] = useState<Record<string, unknown> | null>(null);

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
      
      {/* Hero Section */}
      {step === 'initial' && (
        <section className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1 }}
            className="text-center max-w-4xl mx-auto"
          >
            <h1 className="text-6xl md:text-8xl font-bold mb-6 metal-gradient">
              Oil Risk Intelligence
            </h1>
            <p className="text-xl md:text-2xl text-gray-300 mb-12">
              Advanced machine-learning forecasts and decision-grade risk analytics for oil markets.
            </p>
            <div className="flex flex-col md:flex-row gap-6 justify-center">
              <motion.button
                whileHover={{ letterSpacing: '2px', boxShadow: '0 0 20px rgba(212, 175, 55, 0.5)' }}
                onClick={() => setStep('upload')}
                className="px-8 py-4 bg-accent-primary text-background rounded-md font-medium transition-all duration-300"
              >
                Start Upload & Forecast
              </motion.button>
            </div>
          </motion.div>
        </section>
      )}
      
      {/* 功能介绍 */}
      {step === 'initial' && (
        <section className="relative z-10 py-20 px-4">
          <div className="max-w-7xl mx-auto">
            <h2 className="text-4xl font-bold text-center mb-16 metal-gradient">
              Core Capabilities
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
              <motion.div
                whileHover={{ y: -10, boxShadow: '0 20px 40px rgba(0, 0, 0, 0.3)' }}
                className="bg-gray-900 p-8 rounded-lg border border-gray-800 hover:border-accent-primary transition-all duration-300"
              >
                <h3 className="text-2xl font-bold mb-4 text-accent-primary">Data Intake</h3>
                <p className="text-gray-400">
                  Upload CSV, XLSX, or Parquet datasets with automatic validation and preview checks.
                </p>
              </motion.div>
              <motion.div
                whileHover={{ y: -10, boxShadow: '0 20px 40px rgba(0, 0, 0, 0.3)' }}
                className="bg-gray-900 p-8 rounded-lg border border-gray-800 hover:border-accent-primary transition-all duration-300"
              >
                <h3 className="text-2xl font-bold mb-4 text-accent-primary">Forecast Engine</h3>
                <p className="text-gray-400">
                  Cloud-hosted models generate multi-horizon oil price projections with calibrated risk scoring.
                </p>
              </motion.div>
              <motion.div
                whileHover={{ y: -10, boxShadow: '0 20px 40px rgba(0, 0, 0, 0.3)' }}
                className="bg-gray-900 p-8 rounded-lg border border-gray-800 hover:border-accent-primary transition-all duration-300"
              >
                <h3 className="text-2xl font-bold mb-4 text-accent-primary">Decision Analytics</h3>
                <p className="text-gray-400">
                  Explore factor attribution, industry transmission, and knowledge-graph enhanced decision support.
                </p>
              </motion.div>
            </div>
          </div>
        </section>
      )}
      
      {/* 业务流程 */}
      {step === 'initial' && (
        <section className="relative z-10 py-20 px-4 bg-gray-900/50">
          <div className="max-w-7xl mx-auto">
            <h2 className="text-4xl font-bold text-center mb-16 metal-gradient">
              Workflow
            </h2>
            <div className="flex flex-col md:flex-row justify-between items-center gap-8">
              <motion.div
                initial={{ opacity: 0, x: -50 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5 }}
                className="flex-1 bg-gray-900 p-6 rounded-lg border border-gray-800 text-center"
              >
                <div className="text-4xl font-bold text-accent-primary mb-4">1</div>
                <h3 className="text-xl font-bold mb-2">Upload</h3>
                <p className="text-gray-400">Submit a standardized input table.</p>
              </motion.div>
              <motion.div
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="hidden md:block text-4xl text-accent-primary">→</motion.div>
              <motion.div
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: 0.4 }}
                className="flex-1 bg-gray-900 p-6 rounded-lg border border-gray-800 text-center"
              >
                <div className="text-4xl font-bold text-accent-primary mb-4">2</div>
                <h3 className="text-xl font-bold mb-2">Inference</h3>
                <p className="text-gray-400">Backend orchestrates cloud model inference.</p>
              </motion.div>
              <motion.div
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: 0.6 }}
                className="hidden md:block text-4xl text-accent-primary">→</motion.div>
              <motion.div
                initial={{ opacity: 0, x: 50 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: 0.8 }}
                className="flex-1 bg-gray-900 p-6 rounded-lg border border-gray-800 text-center"
              >
                <div className="text-4xl font-bold text-accent-primary mb-4">3</div>
                <h3 className="text-xl font-bold mb-2">Delivery</h3>
                <p className="text-gray-400">Visualize forecasts and recommendations instantly.</p>
              </motion.div>
            </div>
          </div>
        </section>
      )}
      
      {/* 文件上传 */}
      {step === 'upload' && (
        <section className="relative z-10 py-20 px-4">
          <div className="max-w-7xl mx-auto">
            <motion.button
              whileHover={{ letterSpacing: '2px', boxShadow: '0 0 20px rgba(212, 175, 55, 0.5)' }}
              onClick={() => setStep('initial')}
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
