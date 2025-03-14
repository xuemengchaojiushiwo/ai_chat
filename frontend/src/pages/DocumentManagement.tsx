import React from 'react';
import DocumentList from '../components/DocumentList';
import { Button, Upload, message } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { documentApi } from '../api';

const DocumentManagement: React.FC = () => {
  const handleUpload = async (file: File) => {
    try {
      await documentApi.upload(file);
      message.success('文档上传成功');
      // 刷新文档列表
      window.location.reload();
    } catch (error) {
      message.error('文档上传失败');
    }
  };

  return (
    <div className="p-6">
      <div className="mb-4 flex justify-between items-center">
        <h1 className="text-2xl font-bold">文档管理</h1>
        <Upload
          beforeUpload={(file) => {
            handleUpload(file);
            return false;
          }}
          showUploadList={false}
        >
          <Button icon={<UploadOutlined />} type="primary">
            上传文档
          </Button>
        </Upload>
      </div>
      <DocumentList />
    </div>
  );
};

export default DocumentManagement;

// 添加这行使其成为模块
export {}; 