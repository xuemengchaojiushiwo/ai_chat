import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { Document, UploadResponse, DocumentStatus } from '../types';
import { documentApi } from '../api';

interface DocumentPanelProps {
  onClose: () => void;
}

export const DocumentPanel: React.FC<DocumentPanelProps> = ({ onClose }) => {
  const [uploadingFile, setUploadingFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: documents, isLoading } = useQuery<Document[]>(
    'documents',
    () => documentApi.list()
  );

  // 上传文档
  const uploadDocument = useMutation<UploadResponse, Error, File>(
    (file) => documentApi.upload(file),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('documents');
        setUploadingFile(null);
        setError(null);
      },
      onError: (error) => {
        setError(`上传失败: ${error.message}`);
      }
    }
  );

  // 删除文档
  const deleteDocument = useMutation<void, Error, number>(
    async (documentId) => {
      await documentApi.delete(documentId);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries('documents');
        setError(null);
      },
      onError: (error) => {
        setError(`删除失败: ${error.message}`);
      }
    }
  );

  // 轮询文档状态
  const pollDocumentStatus = async (documentId: number) => {
    try {
      const status = await documentApi.getStatus(documentId);
      if (status.status === 'pending') {
        setTimeout(() => pollDocumentStatus(documentId), 2000);
      } else {
        queryClient.invalidateQueries('documents');
      }
    } catch (error) {
      setError(`获取状态失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  const handleFileUpload = async (file: File) => {
    try {
      setError(null);
      const result = await uploadDocument.mutateAsync(file);
      if (result.id) {
        pollDocumentStatus(result.id);
      }
    } catch (error) {
      setError(`上传失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  const handleDelete = async (documentId: number) => {
    try {
      setError(null);
      await deleteDocument.mutateAsync(documentId);
    } catch (error) {
      setError(`删除失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  return (
    <div className="w-96 bg-white border-l shadow-lg">
      <div className="p-4 border-b flex justify-between items-center">
        <h2 className="text-lg font-semibold">知识库文档</h2>
        <button 
          onClick={onClose}
          className="text-gray-500 hover:text-gray-700"
        >
          ✕
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* 上传区域 */}
      <div className="p-4 border-b">
        <input
          type="file"
          onChange={(e) => e.target.files?.[0] && setUploadingFile(e.target.files[0])}
          className="hidden"
          id="file-upload"
          accept=".txt,.md,.pdf"
        />
        <label
          htmlFor="file-upload"
          className="block w-full p-4 border-2 border-dashed rounded-lg text-center cursor-pointer hover:border-blue-500"
        >
          点击或拖拽文件上传
        </label>
        {uploadingFile && (
          <div className="mt-2 flex justify-between items-center">
            <span className="text-sm text-gray-600">{uploadingFile.name}</span>
            <button
              onClick={() => handleFileUpload(uploadingFile)}
              className="px-3 py-1 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600"
              disabled={uploadDocument.isLoading}
            >
              {uploadDocument.isLoading ? '上传中...' : '上传'}
            </button>
          </div>
        )}
      </div>

      {/* 文档列表 */}
      <div className="overflow-y-auto" style={{ height: 'calc(100vh - 200px)' }}>
        {isLoading ? (
          <div className="p-4 text-center text-gray-500">加载中...</div>
        ) : documents?.length === 0 ? (
          <div className="p-4 text-center text-gray-500">暂无文档</div>
        ) : (
          documents?.map((doc: Document) => (
            <div key={doc.id} className="p-4 border-b hover:bg-gray-50">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-medium">{doc.name}</h3>
                  <div className="text-sm text-gray-500">
                    {new Date(doc.created_at).toLocaleString()}
                  </div>
                  <div className="text-sm mt-1">
                    状态：
                    <span className={`${
                      doc.status === 'completed' ? 'text-green-500' :
                      doc.status === 'error' ? 'text-red-500' :
                      'text-yellow-500'
                    }`}>
                      {doc.status === 'completed' ? '已处理' :
                       doc.status === 'error' ? '处理失败' :
                       '处理中'}
                    </span>
                    {doc.error && (
                      <span className="text-red-500 ml-2">({doc.error})</span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(doc.id)}
                  className={`text-red-500 hover:text-red-700 ${
                    deleteDocument.isLoading
                      ? 'opacity-50 cursor-not-allowed'
                      : 'cursor-pointer'
                  }`}
                  disabled={deleteDocument.isLoading}
                >
                  {deleteDocument.isLoading ? '删除中...' : '删除'}
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}; 