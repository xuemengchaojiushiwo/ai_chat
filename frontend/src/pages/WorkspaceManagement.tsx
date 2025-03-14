import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, message, Space, Popconfirm } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { workgroupApi, workspaceApi } from '../api';
import dayjs from 'dayjs';
import { Workgroup, Workspace } from '../types';  // 导入类型定义

const WorkspaceManagement: React.FC = () => {
  const [workgroups, setWorkgroups] = useState<Workgroup[]>([]);
  const [workspaces, setWorkspaces] = useState<Record<number, Workspace[]>>({});
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [modalType, setModalType] = useState<'workspace' | 'workgroup'>('workspace');
  const [selectedWorkgroup, setSelectedWorkgroup] = useState<number | null>(null);
  const [editingItem, setEditingItem] = useState<Workspace | null>(null);

  // 获取工作组列表
  const fetchWorkgroups = async () => {
    try {
      const data = await workgroupApi.list();
      setWorkgroups(data as Workgroup[]);  // 添加类型断言
    } catch (error) {
      console.error('Error fetching workgroups:', error);
      message.error('获取工作组列表失败');
    }
  };

  // 获取工作空间列表
  const fetchWorkspaces = async (workgroupId: number) => {
    try {
      const workspaces = await workspaceApi.listWorkspaces(workgroupId);
      setWorkspaces(prev => {
        const newWorkspaces = { ...prev };
        newWorkspaces[workgroupId] = workspaces;
        return newWorkspaces;
      });
    } catch (error) {
      console.error('Error fetching workspaces:', error);
      message.error('获取工作空间列表失败');
    }
  };

  useEffect(() => {
    fetchWorkgroups();
  }, []);

  const handleCreate = async (values: any) => {
    try {
      if (modalType === 'workgroup') {
        await workgroupApi.create(values);
        fetchWorkgroups();
      } else if (selectedWorkgroup) {
        await workspaceApi.createWorkspace({
          ...values,
          group_id: selectedWorkgroup
        });
        await fetchWorkspaces(selectedWorkgroup);
      }
      setIsModalVisible(false);
      form.resetFields();
      message.success('创建成功');
    } catch (error) {
      console.error('Error creating:', error);
      message.error('创建失败');
    }
  };

  const handleEdit = async (values: any) => {
    try {
      if (editingItem) {
        await workspaceApi.updateWorkspace(editingItem.id, {
          ...values,
          group_id: editingItem.group_id
        });
        await fetchWorkspaces(editingItem.group_id);
        setIsModalVisible(false);
        form.resetFields();
        setEditingItem(null);
        message.success('更新成功');
      }
    } catch (error) {
      console.error('Error updating:', error);
      message.error('更新失败');
    }
  };

  const handleDelete = async (workspace: Workspace) => {
    try {
      await workspaceApi.deleteWorkspace(workspace.id);
      fetchWorkspaces(workspace.group_id);
      message.success('删除成功');
    } catch (error) {
      console.error('Error deleting workspace:', error);
      message.error('删除失败');
    }
  };

  // 格式化日期的辅助函数
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
        render: (_, record: Workspace) => (
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
      <div style={{ margin: '0 16px 16px 16px' }}>
        <div style={{ marginBottom: 16 }}>
          <Button
            type="primary"
            onClick={() => {
              setSelectedWorkgroup(workgroup.id);
              setModalType('workspace');
              setIsModalVisible(true);
              setEditingItem(null);
              form.resetFields();
            }}
          >
            新建工作空间
          </Button>
        </div>
        <Table
          columns={columns}
          dataSource={workspaces[workgroup.id] || []}
          rowKey="id"
          pagination={false}
        />
      </div>
    );
  };

  return (
    <div className="p-6">
      <div className="mb-4 flex justify-between items-center">
        <h1 className="text-2xl font-bold">工作组管理</h1>
        <Button 
          type="primary" 
          onClick={() => {
            setModalType('workgroup');
            setIsModalVisible(true);
            setEditingItem(null);
            form.resetFields();
          }}
        >
          新建工作组
        </Button>
      </div>

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
      />

      <Modal
        title={`${editingItem ? '编辑' : '新建'}${modalType === 'workgroup' ? '工作组' : '工作空间'}`}
        open={isModalVisible}
        onCancel={() => {
          setIsModalVisible(false);
          setEditingItem(null);
          form.resetFields();
        }}
        footer={null}
      >
        <Form
          form={form}
          onFinish={editingItem ? handleEdit : handleCreate}
          layout="vertical"
        >
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">
              {editingItem ? '保存' : '创建'}
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default WorkspaceManagement;

export {}; 