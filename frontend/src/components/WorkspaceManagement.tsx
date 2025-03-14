import React, { useState, useEffect } from 'react';
import { Table, Button, Space, message, Popconfirm, Form } from 'antd';
import { workgroupApi, workspaceApi } from '../api';
import { ColumnsType } from 'antd/es/table';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

// 修改接口定义，允许 null 值
interface Workspace {
  id: number;
  name: string;
  description: string | null;  // 允许 null
  group_id: number;
  created_at: string | null;   // 允许 null
  updated_at: string | null;   // 允许 null
  document_count: number;
}

interface Workgroup {
  id: number;
  name: string;
  description: string | null;  // 允许 null
  created_at: string | null;   // 允许 null
}

const WorkspaceManagement: React.FC = () => {
  const [workgroups, setWorkgroups] = useState<Workgroup[]>([]);
  const [workspaces, setWorkspaces] = useState<Record<number, Workspace[]>>({});
  const [editingItem, setEditingItem] = useState<Workspace | null>(null);
  const [modalType, setModalType] = useState<'workspace' | 'workgroup'>('workspace');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();

  // 修改格式化日期的辅助函数
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    try {
      const date = dayjs(dateStr);
      return date.isValid() ? date.format('YYYY-MM-DD HH:mm:ss') : '-';
    } catch (error) {
      console.error('Error formatting date:', dateStr);
      return '-';
    }
  };

  // 获取工作组列表
  const fetchWorkgroups = async () => {
    try {
      const data = await workgroupApi.list();
      setWorkgroups(data);
    } catch (error) {
      console.error('Error fetching workgroups:', error);
      message.error('获取工作组列表失败');
    }
  };

  // 获取工作空间列表
  const fetchWorkspaces = async (groupId: number) => {
    try {
      const data = await workspaceApi.listWorkspaces(groupId);
      setWorkspaces(prev => ({
        ...prev,
        [groupId]: data
      }));
    } catch (error) {
      console.error('Error fetching workspaces:', error);
      message.error('获取工作空间列表失败');
    }
  };

  // 处理删除
  const handleDelete = async (workspace: Workspace) => {
    try {
      await workspaceApi.deleteWorkspace(workspace.id);
      message.success('删除成功');
      await fetchWorkspaces(workspace.group_id);
    } catch (error) {
      console.error('Error deleting workspace:', error);
      message.error('删除失败');
    }
  };

  useEffect(() => {
    fetchWorkgroups();
  }, []);

  const workgroupColumns: ColumnsType<Workgroup> = [
    {
      title: '工作组名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => text || '-'
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (text: string | null) => text || '-'
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string | null) => formatDate(date)
    }
  ];

  const expandedRowRender = (workgroup: Workgroup) => {
    const columns: ColumnsType<Workspace> = [
      {
        title: '工作空间名称',
        dataIndex: 'name',
        key: 'name',
        render: (text: string) => text || '-'
      },
      {
        title: '描述',
        dataIndex: 'description',
        key: 'description',
        render: (text: string | null) => text || '-'
      },
      {
        title: '文档数量',
        dataIndex: 'document_count',
        key: 'document_count',
        render: (count: number) => count || 0
      },
      {
        title: '创建时间',
        dataIndex: 'created_at',
        key: 'created_at',
        render: (date: string | null) => formatDate(date)
      },
      {
        title: '修改时间',
        dataIndex: 'updated_at',
        key: 'updated_at',
        render: (date: string | null) => formatDate(date)
      },
      {
        title: '操作',
        key: 'action',
        render: (_: unknown, record: Workspace) => (
          <Space>
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingItem(record);
                form.setFieldsValue({
                  name: record.name,
                  description: record.description,
                });
                setModalType('workspace');
                setIsModalVisible(true);
              }}
            >
              编辑
            </Button>
            <Popconfirm
              title="确定要删除这个工作空间吗？"
              onConfirm={() => handleDelete(record)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
              >
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ];

    return (
      <Table
        columns={columns}
        dataSource={workspaces[workgroup.id] || []}
        rowKey="id"
        pagination={false}
      />
    );
  };

  return (
    <div className="p-4">
      <Table 
        columns={workgroupColumns} 
        dataSource={workgroups}
        rowKey="id"
        expandable={{
          expandedRowRender,
          onExpand: (expanded, record) => {
            if (expanded) {
              fetchWorkspaces(record.id);
            }
          },
        }}
        pagination={{ 
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条记录`
        }}
      />
    </div>
  );
};

export default WorkspaceManagement; 