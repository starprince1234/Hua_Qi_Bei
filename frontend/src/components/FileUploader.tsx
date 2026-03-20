'use client';

import { useState } from 'react';
import { getApiBasePath } from './apiBase';

interface FileUploaderProps {
  onUploadSuccess: (fileId: string) => void;
}

const API_BASE = getApiBasePath();

export default function FileUploader({ onUploadSuccess }: FileUploaderProps) {
  const [file, setFile] = useState<File | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
      if (!response.ok) throw new Error('上传失败');
      const data = await response.json();
      if (data.success) onUploadSuccess(data.data.file_id);
      else alert(data.message || '上传失败');
    } catch {
      alert('上传失败，请检查网络连接或后端服务是否运行');
    }
  };

  return <form onSubmit={handleSubmit}><input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} /><button type="submit">上传</button></form>;
}
