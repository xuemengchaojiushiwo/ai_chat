import React, { useState, useEffect, useRef } from 'react';
import { Input, Button, Select, Tabs, Drawer, message as antMessage } from 'antd';
import { SendOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { Message } from './Message';
import { conversationApi, workspaceApi } from '../api';
import type { Conversation, Workspace } from '../types';

const { Option } = Select;
const { TabPane } = Tabs;

const NewChatInterface: React.FC = () => {
  const [message, setMessage] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<number | null>(null);
  const [sourcesDrawerVisible, setSourcesDrawerVisible] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 获取工作空间列表
  useEffect(() => {
    const fetchWorkspaces = async () => {
      try {
        const data = await workspaceApi.listWorkspaces();
        setWorkspaces(data);
      } catch (err) {
        console.error('获取工作空间失败:', err);
        antMessage.error('获取工作空间列表失败');
      }
    };
    fetchWorkspaces();
  }, []);

  // 初始化对话列表
  useEffect(() => {
    const initData = async () => {
      try {
        const data = await conversationApi.list();
        setConversations(data);
        if (data.length > 0) {
          setCurrentConversation(data[0].id);
        }
      } catch (err) {
        console.error('获取对话列表失败:', err);
        antMessage.error('获取对话列表失败');
      }
    };
    initData();
  }, []);

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversations]);

  // 发送消息
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    setLoading(true);
    try {
      // 如果没有当前对话，sendMessage 会自动创建一个新对话
      const response = await conversationApi.sendMessage(
        currentConversation,
        message,
        selectedWorkspace !== null
      );

      // 如果是新创建的对话，需要更新对话列表
      if (!currentConversation) {
        const conversations = await conversationApi.list();
        setConversations(conversations);
        setCurrentConversation(conversations[conversations.length - 1].id);
      } else {
        // 更新现有对话的消息
        const updatedConversations = conversations.map(conv => {
          if (conv.id === currentConversation) {
            return {
              ...conv,
              messages: [...conv.messages, response]
            };
          }
          return conv;
        });
        setConversations(updatedConversations);
      }
      
      setMessage('');
    } catch (err) {
      console.error('发送消息失败:', err);
      antMessage.error('发送消息失败');
    } finally {
      setLoading(false);
    }
  };

  // 创建新对话
  const handleNewChat = async () => {
    try {
      const newConversation = await conversationApi.create('新对话');
      setConversations([...conversations, newConversation]);
      setCurrentConversation(newConversation.id);
    } catch (err) {
      console.error('创建新对话失败:', err);
      antMessage.error('创建新对话失败');
    }
  };

  // 渲染历史对话分组
  const renderConversationGroups = () => {
    const today: Conversation[] = [];
    const yesterday: Conversation[] = [];
    const threeDaysAgo: Conversation[] = [];
    const earlier: Conversation[] = [];

    conversations.forEach(conv => {
      const date = new Date(conv.created_at);
      const now = new Date();
      const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

      if (diffDays === 0) today.push(conv);
      else if (diffDays === 1) yesterday.push(conv);
      else if (diffDays <= 3) threeDaysAgo.push(conv);
      else earlier.push(conv);
    });

    return (
      <Tabs defaultActiveKey="1" className="conversation-tabs">
        {today.length > 0 && (
          <TabPane tab={`今天 ${today.length}`} key="1">
            {renderConversationList(today)}
          </TabPane>
        )}
        {yesterday.length > 0 && (
          <TabPane tab={`昨天 ${yesterday.length}`} key="2">
            {renderConversationList(yesterday)}
          </TabPane>
        )}
        {threeDaysAgo.length > 0 && (
          <TabPane tab={`3天前 ${threeDaysAgo.length}`} key="3">
            {renderConversationList(threeDaysAgo)}
          </TabPane>
        )}
        {earlier.length > 0 && (
          <TabPane tab={`更早 ${earlier.length}`} key="4">
            {renderConversationList(earlier)}
          </TabPane>
        )}
      </Tabs>
    );
  };

  const renderConversationList = (convs: Conversation[]) => (
    <div className="flex-1 overflow-y-auto">
      {convs.map(conv => (
        <div
          key={conv.id}
          onClick={() => setCurrentConversation(conv.id)}
          className={`p-3 cursor-pointer rounded ${
            currentConversation === conv.id
              ? 'bg-blue-600'
              : 'hover:bg-gray-700'
          }`}
        >
          <div className="text-white truncate">{conv.name}</div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="flex h-screen">
      {/* 左侧边栏 */}
      <div className="w-64 bg-gray-800 p-4 flex flex-col">
        {/* 工作空间选择 */}
        <Select
          placeholder="选择工作空间（可选）"
          allowClear
          style={{ marginBottom: '16px' }}
          onChange={(value) => setSelectedWorkspace(value)}
        >
          {workspaces.map(workspace => (
            <Option key={workspace.id} value={workspace.id}>
              {workspace.name}
            </Option>
          ))}
        </Select>

        {/* 新建对话按钮 */}
        <Button
          type="primary"
          onClick={handleNewChat}
          className="mb-4"
        >
          新建对话
        </Button>

        {/* 分组的对话列表 */}
        {renderConversationGroups()}
      </div>

      {/* 主对话区域 */}
      <div className="flex-1 flex flex-col">
        {/* 顶部工具栏 */}
        <div className="flex justify-between items-center p-4 border-b">
          <div className="text-lg font-medium">
            {conversations.find(c => c.id === currentConversation)?.name || '新对话'}
          </div>
          <Button
            icon={<InfoCircleOutlined />}
            onClick={() => setSourcesDrawerVisible(true)}
          >
            信息源
          </Button>
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-4">
          {currentConversation &&
            conversations
              .find(conv => conv.id === currentConversation)
              ?.messages.map((msg, index) => (
                <Message
                  key={index}
                  role={msg.role}
                  content={msg.content}
                  citations={msg.citations}
                />
              ))}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <div className="border-t p-4">
          <form onSubmit={handleSubmit} className="flex space-x-4">
            <Input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="输入消息..."
              disabled={loading}
            />
            <Button
              type="primary"
              htmlType="submit"
              icon={<SendOutlined />}
              loading={loading}
            >
              发送
            </Button>
          </form>
        </div>
      </div>

      {/* 信息源抽屉 */}
      <Drawer
        title="信息源"
        placement="right"
        width={400}
        onClose={() => setSourcesDrawerVisible(false)}
        visible={sourcesDrawerVisible}
      >
        <div className="space-y-4">
          <div className="bg-gray-50 p-4 rounded">
            <h3 className="font-medium mb-2">监管机构指引</h3>
            <ul className="list-disc pl-4 space-y-2">
              <li>FATF Recommendations</li>
              <li>监管机构反洗钱指导意见</li>
              <li>Guidance on Risk-Based...</li>
            </ul>
          </div>
          <div className="bg-gray-50 p-4 rounded">
            <h3 className="font-medium mb-2">相关法规文件</h3>
            <ul className="list-disc pl-4 space-y-2">
              <li>《中华人民共和国反洗钱法》</li>
              <li>《金融机构反洗钱规定》</li>
              <li>《银行业金融机构反洗钱和反恐怖融资管理办法》</li>
            </ul>
          </div>
        </div>
      </Drawer>
    </div>
  );
};

export default NewChatInterface; 