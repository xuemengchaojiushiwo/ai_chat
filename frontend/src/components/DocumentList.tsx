import React, { useEffect, useState } from 'react';
import { Table, Button, message, Tooltip, Popconfirm, Badge, Space } from 'antd';
import { 
  DeleteOutlined, 
  CheckCircleOutlined, 
  SyncOutlined, 
  CloseCircleOutlined,
  DownloadOutlined,
  LinkOutlined,
  UploadOutlined
} from '@ant-design/icons';
import { documentApi } from '../api';
import type { ColumnsType } from 'antd/es/table';
import DocumentUpload from './DocumentUpload';

// 支持的文件类型
const SUPPORTED_MIME_TYPES = {
  'application/pdf': 'PDF',
  'application/msword': 'DOC',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
  'application/vnd.ms-excel': 'XLS',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
  'text/plain': 'TXT'
};

// 添加文件大小格式化函数
const formatFileSize = (bytes?: number): string => {
  if (bytes === undefined) return '-';
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

interface DocumentStatus {
  status: string;
  segments: number;
  segments_with_embeddings: number;
  error?: string;
}

interface DocumentItem {  // 重命名接口以避免与全局 Document 冲突
  id: number;
  name: string;
  mime_type: string;
  status: string;
  created_at: string;
  error?: string;
  size?: number;
  documentStatus?: DocumentStatus;
}

const DocumentList: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);

  const fetchDocuments = async () => {
    try {
      const docs = await documentApi.list();
      setDocuments(docs);
    } catch (error) {
      message.error('获取文档列表失败');
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleDelete = async (id: number) => {
    try {
      await documentApi.delete(id);
      message.success('删除成功');
      fetchDocuments();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const getStatusBadge = (doc: DocumentItem) => {
    const status = doc.documentStatus?.status || doc.status;
    switch (status) {
      case 'completed':
        return (
          <Tooltip title={`已生成向量: ${doc.documentStatus?.segments_with_embeddings}/${doc.documentStatus?.segments}`}>
            <Badge 
              status="success" 
              text={
                <span>
                  完成 <CheckCircleOutlined style={{ color: '#52c41a' }} />
                </span>
              }
            />
          </Tooltip>
        );
      case 'processing':
        return <Badge status="processing" text={<span>处理中 <SyncOutlined spin /></span>} />;
      case 'error':
        return (
          <Tooltip title={doc.documentStatus?.error || doc.error}>
            <Badge 
              status="error" 
              text={
                <span>
                  错误 <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                </span>
              }
            />
          </Tooltip>
        );
      default:
        return <Badge status="default" text="未知" />;
    }
  };

  // 修改下载处理函数
  const handleDownload = async (doc: DocumentItem) => {
    try {
      const response = await fetch(`/api/documents/${doc.id}/download`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      
      // 创建一个临时的 a 标签用于下载
      const link = window.document.createElement('a');
      link.href = url;
      link.download = doc.name;
      window.document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(link);
    } catch (error) {
      message.error('下载失败');
    }
  };

  // 处理关联工作空间
  const handleLink = (doc: DocumentItem) => {
    message.info('打开关联工作空间对话框');
  };

  const columns: ColumnsType<DocumentItem> = [
    {
      title: '文档名称',
      dataIndex: 'name',
      key: 'name',
      width: '25%',
      render: (text: string) => (
        <Tooltip title={text}>
          <div className="truncate">{text}</div>
        </Tooltip>
      )
    },
    {
      title: '文件大小',
      dataIndex: 'size',
      key: 'size',
      width: '12%',
      render: (size?: number) => formatFileSize(size)
    },
    {
      title: '类型',
      dataIndex: 'mime_type',
      key: 'mime_type',
      width: '12%',
      render: (mime_type: string | undefined) => {
        if (!mime_type) return '-';
        return SUPPORTED_MIME_TYPES[mime_type as keyof typeof SUPPORTED_MIME_TYPES] || mime_type;
      },
    },
    {
      title: '状态',
      key: 'status',
      width: '15%',
      render: (_: unknown, record: DocumentItem) => getStatusBadge(record),
    },
    {
      title: '上传者',
      key: 'uploader',
      width: '12%',
      render: () => 'admin'
    },
    {
      title: '上传时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: '15%',
      render: (date: string) => {
        try {
          return new Date(date).toLocaleString();
        } catch (error) {
          return '-';
        }
      },
    },
    {
      title: '操作',
      key: 'action',
      width: '15%',
      render: (_: unknown, record: DocumentItem) => (
        <Space>
          <Tooltip title="下载">
            <Button
              type="text"
              icon={<DownloadOutlined />}
              onClick={() => handleDownload(record)}
              size="small"
            />
          </Tooltip>
          <Tooltip title="关联工作空间">
            <Button
              type="text"
              icon={<LinkOutlined />}
              onClick={() => handleLink(record)}
              size="small"
            />
          </Tooltip>
          <Tooltip title="删除">
            <Popconfirm
              title="确定要删除这个文档吗？"
              onConfirm={() => handleDelete(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button 
                type="text"
                danger
                icon={<DeleteOutlined />}
                size="small"
              />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '16px' }}>
        <Button
          type="primary"
          icon={<UploadOutlined />}
          onClick={() => setUploadModalVisible(true)}
        >
          上传文档
        </Button>
        <div style={{ marginTop: '8px', color: '#666', fontSize: '12px' }}>
          支持的文件类型：PDF、Word、Excel、TXT
        </div>
      </div>

      <DocumentUpload
        visible={uploadModalVisible}
        onCancel={() => setUploadModalVisible(false)}
        onSuccess={fetchDocuments}
      />

      <Table<DocumentItem>
        columns={columns}
        dataSource={documents}
        rowKey="id"
        loading={loading}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条记录`,
        }}
        scroll={{ x: 1200 }}
      />
    </div>
  );
};

export default DocumentList; 