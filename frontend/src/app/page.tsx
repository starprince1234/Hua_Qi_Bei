'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import FileUploader from '../components/FileUploader';
import PredictForm from '../components/PredictForm';
import ResultDisplay from '../components/ResultDisplay';

export default function Home() {
  const [step, setStep] = useState<'upload' | 'predict' | 'result' | 'initial'>('initial');
  const [fileId, setFileId] = useState<string>('');
  const [predictionResult, setPredictionResult] = useState<any>(null);

  const handleUploadSuccess = (id: string) => {
    setFileId(id);
    setStep('predict');
  };

  const handlePredictSuccess = (result: any) => {
    setPredictionResult(result);
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
      <div className="noise-texture"></div>
      <div className="spotlight" id="spotlight"></div>
      {step === 'initial' && (
        <section className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1 }}
            className="text-center max-w-4xl mx-auto"
          >
            <h1 className="text-6xl md:text-8xl font-bold mb-6 metal-gradient">油价风险智能预测</h1>
            <p className="text-xl md:text-2xl text-gray-300 mb-12">基于先进的机器学习模型，提供精准的油价预测和风险分析</p>
            <div className="flex flex-col md:flex-row gap-6 justify-center">
              <motion.button whileHover={{ letterSpacing: '2px' }} onClick={() => setStep('upload')} className="px-8 py-4 bg-transparent border-2 border-accent-primary text-accent-primary rounded-md font-medium transition-all duration-300">上传数据</motion.button>
              <motion.button whileHover={{ letterSpacing: '2px' }} onClick={() => setStep('upload')} className="px-8 py-4 bg-accent-primary text-background rounded-md font-medium transition-all duration-300">开始预测</motion.button>
            </div>
          </motion.div>
        </section>
      )}
      {step === 'upload' && <FileUploader onUploadSuccess={handleUploadSuccess} />}
      {step === 'predict' && <PredictForm fileId={fileId} onPredictSuccess={handlePredictSuccess} />}
      {step === 'result' && predictionResult && <ResultDisplay result={predictionResult} />}
      <footer className="relative z-10 py-12 px-4 border-t border-gray-800"><div className="max-w-7xl mx-auto text-center"><p className="text-gray-400">© 2026 油价风险智能预测系统</p></div></footer>
    </div>
  );
}
