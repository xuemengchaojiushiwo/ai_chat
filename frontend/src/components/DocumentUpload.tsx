import React, { useState, useEffect } from 'react';
import { Modal, Upload, Select, Button, message, Form } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd/es/upload/interface';
import { documentApi, workspaceApi } from '../api';
import type { Workspace } from '../types';

interface DocumentUploadProps {
  visible: boolean;
  onCancel: () => void;
  onSuccess: () => void;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  visible,
  onCancel,
  onSuccess,
}) => {
  const [form] = Form.useForm();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);

  // 获取工作空间列表
  useEffect(() => {
    const fetchWorkspaces = async () => {
      try {
        const workspaceList = await workspaceApi.listWorkspaces();  // 改用 listWorkspaces
        setWorkspaces(workspaceList);
      } catch (error) {
        message.error('获取工作空间列表失败');
      }
    };
    if (visible) {
      fetchWorkspaces();
    }
  }, [visible]);

  const handleUpload = async () => {
    const values = await form.validateFields();
    const { workspace_ids } = values;

    if (fileList.length === 0) {
      message.error('请选择要上传的文件');
      return;
    }

    setUploading(true);
    try {
      // 上传所有文件
      for (const file of fileList) {
        if (file.originFileObj) {
          const response = await documentApi.upload(file.originFileObj);
          // 关联所有选择的工作空间
          await documentApi.linkWorkspace(response.id, workspace_ids);
        }
      }

      message.success('上传成功！');
      setFileList([]);
      form.resetFields();
      onSuccess();
      onCancel();
    } catch (error) {
      message.error('上传失败！');
    } finally {
      setUploading(false);
    }
  };

  const uploadProps: UploadProps = {
    multiple: true,
    accept: '.pdf,.doc,.docx,.xls,.xlsx,.txt',
    fileList,
    beforeUpload: (file: File) => {
      const isValidType = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain'
      ].includes(file.type);

      if (!isValidType) {
        message.error('不支持的文件类型！');
        return Upload.LIST_IGNORE;
      }

      const isLt100M = file.size / 1024 / 1024 < 100;
      if (!isLt100M) {
        message.error('文件大小不能超过100MB！');
        return Upload.LIST_IGNORE;
      }

      return false;
    },
    onChange: (info: { fileList: UploadFile[] }) => setFileList(info.fileList),
    onRemove: (file: UploadFile) => {
      const index = fileList.indexOf(file);
      const newFileList = fileList.slice();
      newFileList.splice(index, 1);
      setFileList(newFileList);
    },
  };

  return (
    <Modal
      title="上传文档"
      open={visible}
      onCancel={onCancel}
      footer={[
        <Button key="back" onClick={onCancel}>
          取消
        </Button>,
        <Button
          key="submit"
          type="primary"
          loading={uploading}
          onClick={handleUpload}
        >
          确定
        </Button>,
      ]}
    >
      <Form form={form}>
        <Form.Item
          name="workspace_ids"
          label="关联工作空间"
          rules={[{ required: true, message: '请选择关联的工作空间' }]}
        >
          <Select
            mode="multiple"
            placeholder="请选择工作空间"
            style={{ width: '100%' }}
            options={workspaces.map(ws => ({
              label: ws.name,
              value: ws.id
            }))}
          />
        </Form.Item>

        <Form.Item label="选择文档">
          <Upload.Dragger {...uploadProps}>
            <p className="ant-upload-drag-icon">
              <UploadOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
            <p className="ant-upload-hint">
              支持 PDF、Word、Excel、TXT 格式，单个文件最大100MB
            </p>
          </Upload.Dragger>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default DocumentUpload; 