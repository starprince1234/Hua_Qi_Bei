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
              油价风险智能预测
            </h1>
            <p className="text-xl md:text-2xl text-gray-300 mb-12">
              基于先进的机器学习模型，提供精准的油价预测和风险分析
            </p>
            <div className="flex flex-col md:flex-row gap-6 justify-center">
              <motion.button
                whileHover={{ letterSpacing: '2px', boxShadow: '0 0 20px rgba(212, 175, 55, 0.5)' }}
                onClick={() => setStep('upload')}
                className="px-8 py-4 bg-transparent border-2 border-accent-primary text-accent-primary rounded-md font-medium transition-all duration-300"
              >
                上传数据
              </motion.button>
              <motion.button
                whileHover={{ letterSpacing: '2px', boxShadow: '0 0 20px rgba(212, 175, 55, 0.5)' }}
                onClick={() => setStep('upload')}
                className="px-8 py-4 bg-accent-primary text-background rounded-md font-medium transition-all duration-300"
              >
                开始预测
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
              核心功能
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
              <motion.div
                whileHover={{ y: -10, boxShadow: '0 20px 40px rgba(0, 0, 0, 0.3)' }}
                className="bg-gray-900 p-8 rounded-lg border border-gray-800 hover:border-accent-primary transition-all duration-300"
              >
                <h3 className="text-2xl font-bold mb-4 text-accent-primary">数据上传</h3>
                <p className="text-gray-400">
                  支持多种格式的数据文件上传，包括 CSV、XLSX 和 Parquet，系统会自动进行数据校验和预览。
                </p>
              </motion.div>
              <motion.div
                whileHover={{ y: -10, boxShadow: '0 20px 40px rgba(0, 0, 0, 0.3)' }}
                className="bg-gray-900 p-8 rounded-lg border border-gray-800 hover:border-accent-primary transition-all duration-300"
              >
                <h3 className="text-2xl font-bold mb-4 text-accent-primary">智能预测</h3>
                <p className="text-gray-400">
                  基于云端训练的机器学习模型，提供多维度的油价预测和风险评估，支持不同时间 horizon 的预测。
                </p>
              </motion.div>
              <motion.div
                whileHover={{ y: -10, boxShadow: '0 20px 40px rgba(0, 0, 0, 0.3)' }}
                className="bg-gray-900 p-8 rounded-lg border border-gray-800 hover:border-accent-primary transition-all duration-300"
              >
                <h3 className="text-2xl font-bold mb-4 text-accent-primary">数据分析</h3>
                <p className="text-gray-400">
                  提供详细的预测结果分析，包括行业冲击评估、因子贡献分析和知识图谱增强的决策支持。
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
              业务流程
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
                <h3 className="text-xl font-bold mb-2">数据上传</h3>
                <p className="text-gray-400">用户按照指定格式上传数据表</p>
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
                <h3 className="text-xl font-bold mb-2">模型推理</h3>
                <p className="text-gray-400">后端服务器转发给云端推理模型</p>
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
                <h3 className="text-xl font-bold mb-2">结果展示</h3>
                <p className="text-gray-400">后端处理后通过前端图表展示</p>
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
              ← 返回首页
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
              ← 返回上传
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
              ← 返回预测
            </motion.button>
            {predictionResult && <ResultDisplay result={predictionResult} />}
          </div>
        </section>
      )}
      
      {/* 页脚 */}
      <footer className="relative z-10 py-12 px-4 border-t border-gray-800">
        <div className="max-w-7xl mx-auto text-center">
          <p className="text-gray-400">
            © 2026 油价风险智能预测系统 | 高端商务科技解决方案
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
