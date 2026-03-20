'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { getApiBasePath } from './apiBase';

interface FileUploaderProps {
  onUploadSuccess: (fileId: string) => void;
}

const API_BASE = getApiBasePath();

export default function FileUploader({ onUploadSuccess }: FileUploaderProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [datasetType, setDatasetType] = useState('oil_price_factors');
  const [timezone, setTimezone] = useState('UTC');
  const [frequency, setFrequency] = useState('D');
  const [strictMode, setStrictMode] = useState(false);
  const [encoding, setEncoding] = useState('utf-8');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setSuccess(null);
    }
  };

  useEffect(() => {
    const preventBrowserDropBehavior = (event: DragEvent) => {
      event.preventDefault();
    };

    const handleWindowDrop = (event: DragEvent) => {
      event.preventDefault();
      const droppedFile = event.dataTransfer?.files?.[0];
      if (!droppedFile) {
        return;
      }
      setFile(droppedFile);
      setError(null);
      setSuccess(null);
      setIsDragOver(false);
    };

    window.addEventListener('dragover', preventBrowserDropBehavior);
    window.addEventListener('drop', preventBrowserDropBehavior);
    window.addEventListener('drop', handleWindowDrop);

    return () => {
      window.removeEventListener('dragover', preventBrowserDropBehavior);
      window.removeEventListener('drop', preventBrowserDropBehavior);
      window.removeEventListener('drop', handleWindowDrop);
    };
  }, []);

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    const droppedFile = e.dataTransfer.files?.[0];
    if (!droppedFile) {
      return;
    }

    setFile(droppedFile);
    setError(null);
    setSuccess(null);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('请选择一个文件');
      return;
    }

    setIsUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('dataset_type', datasetType);
      formData.append('timezone', timezone);
      formData.append('frequency', frequency);
      formData.append('strict_mode', strictMode.toString());
      formData.append('encoding', encoding);

      const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('上传失败');
      }

      const data = await response.json();
      if (data.success) {
        setSuccess('文件上传成功');
        onUploadSuccess(data.data.file_id);
      } else {
        setError(data.message || '上传失败');
      }
    } catch (error) {
      setError('上传失败，请检查网络连接或后端服务是否运行');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="bg-gray-900 p-8 rounded-lg border border-gray-800 w-full max-w-3xl mx-auto"
    >
      <h2 className="text-2xl font-bold mb-6 text-center metal-gradient">数据上传</h2>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              选择文件 (CSV/XLSX/Parquet)
            </label>
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className={`relative border-2 border-dashed rounded-md p-8 text-center transition-colors duration-300 ${
                isDragOver ? 'border-accent-primary bg-accent-primary/10' : 'border-gray-700 hover:border-accent-primary'
              }`}
            >
              <input
                type="file"
                accept=".csv,.xlsx,.xls,.parquet"
                onChange={handleFileChange}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              <div className="flex flex-col items-center justify-center">
                <div className="text-4xl text-accent-primary mb-4">📁</div>
                <p className="text-gray-400">
                  {file ? file.name : '点击或拖拽文件到此处上传'}
                </p>
                <p className="text-gray-500 text-sm mt-2">
                  支持 CSV、XLSX、Parquet 格式
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                数据集类型
              </label>
              <select
                value={datasetType}
                onChange={(e) => setDatasetType(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-2 text-gray-300 focus:outline-none focus:border-accent-primary"
              >
                <option value="oil_price_factors">油价因子</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                时区
              </label>
              <input
                type="text"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-2 text-gray-300 focus:outline-none focus:border-accent-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                频率
              </label>
              <select
                value={frequency}
                onChange={(e) => setFrequency(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-2 text-gray-300 focus:outline-none focus:border-accent-primary"
              >
                <option value="D">日</option>
                <option value="W">周</option>
                <option value="M">月</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                编码
              </label>
              <input
                type="text"
                value={encoding}
                onChange={(e) => setEncoding(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-2 text-gray-300 focus:outline-none focus:border-accent-primary"
              />
            </div>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="strictMode"
              checked={strictMode}
              onChange={(e) => setStrictMode(e.target.checked)}
              className="mr-2 accent-accent-primary"
            />
            <label htmlFor="strictMode" className="text-sm text-gray-300">
              严格模式
            </label>
          </div>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-md p-4 text-red-400">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-900/30 border border-green-700 rounded-md p-4 text-green-400">
            {success}
          </div>
        )}

        <motion.button
          type="submit"
          whileHover={{ letterSpacing: '2px', boxShadow: '0 0 20px rgba(212, 175, 55, 0.5)' }}
          disabled={isUploading || !file}
          className="w-full px-6 py-3 bg-accent-primary text-background rounded-md font-medium transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isUploading ? '上传中...' : '上传文件'}
        </motion.button>
      </form>
    </motion.div>
  );
}
