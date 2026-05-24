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
  const [encoding, setEncoding] = useState('utf-8');
  const [showFormatGuide, setShowFormatGuide] = useState(false);

  useEffect(() => {
    setDatasetType('oil_price_factors');
    setFrequency('D');
  }, []);

  const formatFields = [
    { name: 'Brent_Crude(BZ=F)_Close', meaning: 'Brent closing price (USD/barrel), primary reference benchmark.' },
    { name: 'OVX_Daily_Change_Pct', meaning: 'Daily percentage change of OVX implied volatility index.' },
    { name: 'Gasoline_7D_Change_Pct', meaning: '7-day percentage change in gasoline price.' },
    { name: 'T5YIE_Trend_Flag_1_Up_0_Down', meaning: 'Trend flag of 5Y inflation expectation: 1=upward, 0=downward.' },
    { name: 'Brent_Close_1D_Diff', meaning: 'First-order daily difference of Brent close.' },
    { name: 'T5YIE_30D_Diff', meaning: '30-day difference of T5YIE inflation expectation.' },
    { name: 'Crack_Spread_3D_Diff', meaning: '3-day difference in crack spread.' },
    { name: 'OVX_3D_Rolling_Std', meaning: '3-day rolling standard deviation of OVX.' },
    { name: 'Brent_Intraday_Amplitude_Pct', meaning: 'Intraday amplitude percentage of Brent.' },
    { name: 'OVX', meaning: 'CBOE Crude Oil Volatility Index level.' },
    { name: 'T5YIE_30D_Change_Pct', meaning: '30-day percentage change of T5YIE.' },
    { name: 'Crack_Spread_Trend_Flag_1_Up_0_Down', meaning: 'Trend flag for crack spread: 1=upward, 0=downward.' },
    { name: 'Decay_Coefficient', meaning: 'Decay coefficient for signal attenuation in feature engineering.' },
    { name: 'OVX_Lag_1D', meaning: 'OVX lagged by 1 day.' },
    { name: 'DXY', meaning: 'US Dollar Index level.' },
    { name: 'DXY_Lag_1D', meaning: 'DXY lagged by 1 day.' },
    { name: 'DXY_7D_Rolling_Mean', meaning: '7-day rolling mean of DXY.' },
    { name: 'OVX_Lag_3D', meaning: 'OVX lagged by 3 days.' },
    { name: 'Brent_Close_7D_Rolling_Std', meaning: '7-day rolling standard deviation of Brent close.' },
    { name: 'DXY_Lag_7D', meaning: 'DXY lagged by 7 days.' },
    { name: 'WTI_Crude(CL=F)_Close', meaning: 'WTI closing price (USD/barrel).' },
    { name: 'T5YIE', meaning: 'US 5-year inflation expectation index.' },
    { name: 'Gasoline', meaning: 'Gasoline spot/futures benchmark value.' },
    { name: 'Brent_Crude(BZ=F)_Volume', meaning: 'Brent related volume feature.' },
  ];

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
      setError('Please select a file first.');
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
      formData.append('strict_mode', 'false');
      formData.append('encoding', encoding);

      const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const data = await response.json();
      if (data.success) {
        setSuccess('File uploaded successfully.');
        onUploadSuccess(data.data.file_id);
      } else {
        setError(data.message || 'Upload failed');
      }
    } catch {
      setError('Upload failed. Please check network connectivity or backend status.');
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
      <h2 className="text-2xl font-bold mb-6 text-center metal-gradient">Data Upload</h2>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-400">Please upload a feature snapshot file for prediction.</p>
            <button
              type="button"
              onClick={() => setShowFormatGuide(true)}
              className="text-sm px-3 py-1 border border-accent-primary/60 rounded-md text-accent-primary hover:bg-accent-primary hover:text-black transition-colors"
            >
              File Format Guide
            </button>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Select File (CSV/XLSX/Parquet)
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
                  {file ? file.name : 'Click or drag a file here to upload'}
                </p>
                <p className="text-gray-500 text-sm mt-2">
                  Supported formats: CSV, XLSX, Parquet
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Dataset Type
              </label>
              <input
                type="text"
                value="Oil Price Factors"
                readOnly
                className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-2 text-gray-300 focus:outline-none focus:border-accent-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Timezone
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
                Frequency
              </label>
              <input
                type="text"
                value="Daily (D)"
                readOnly
                className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-2 text-gray-300 focus:outline-none focus:border-accent-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Encoding
              </label>
              <input
                type="text"
                value={encoding}
                onChange={(e) => setEncoding(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-2 text-gray-300 focus:outline-none focus:border-accent-primary"
              />
            </div>
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
          {isUploading ? 'Uploading...' : 'Upload File'}
        </motion.button>
      </form>

      {showFormatGuide && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4">
          <div className="w-full max-w-5xl bg-gray-900 border border-gray-700 rounded-lg p-6">
            <div className="flex items-start justify-between mb-4 gap-4">
              <div>
                <h3 className="text-xl font-bold text-accent-primary">Input File Specification</h3>
                <p className="text-sm text-gray-400 mt-2">
                  Example template: D:\VScodeProjects\huaqibei\test1.xlsx
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowFormatGuide(false)}
                className="text-sm px-3 py-1 border border-gray-500 rounded-md text-gray-200 hover:bg-gray-800"
              >
                Close
              </button>
            </div>

            <div className="text-sm text-gray-300 mb-4 space-y-1">
              <p>- One row per prediction request (latest factor snapshot).</p>
              <p>- Required sheet: Sheet1. Keep original column names unchanged.</p>
              <p>- Numeric fields should be valid numbers; avoid empty strings in critical price fields.</p>
            </div>

            <div className="max-h-[55vh] overflow-auto border border-gray-800 rounded-md">
              <table className="w-full text-sm text-gray-200">
                <thead className="sticky top-0 bg-gray-800">
                  <tr>
                    <th className="text-left px-3 py-2 border-b border-gray-700">Field Name</th>
                    <th className="text-left px-3 py-2 border-b border-gray-700">Meaning</th>
                  </tr>
                </thead>
                <tbody>
                  {formatFields.map((item) => (
                    <tr key={item.name} className="border-b border-gray-800/70">
                      <td className="px-3 py-2 align-top text-accent-primary">{item.name}</td>
                      <td className="px-3 py-2 align-top">{item.meaning}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
