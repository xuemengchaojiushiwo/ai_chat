import React from 'react';
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import WorkspaceManagement from './pages/WorkspaceManagement';
import DocumentManagement from './pages/DocumentManagement';
import ChatInterface from './components/ChatInterface';
import NewChatInterface from './components/NewChatInterface';

const { Header, Content, Sider } = Layout;

const App: React.FC = () => {
  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        <Header>
          <div className="text-white text-xl">AI Chat</div>
        </Header>
        <Layout>
          <Sider width={200}>
            <Menu
              mode="inline"
              defaultSelectedKeys={['1']}
              style={{ height: '100%' }}
            >
              <Menu.Item key="1">
                <Link to="/">旧版对话</Link>
              </Menu.Item>
              <Menu.Item key="2">
                <Link to="/new-chat">新版对话</Link>
              </Menu.Item>
              <Menu.Item key="3">
                <Link to="/workspaces">工作组管理</Link>
              </Menu.Item>
              <Menu.Item key="4">
                <Link to="/documents">文档管理</Link>
              </Menu.Item>
            </Menu>
          </Sider>
          <Content style={{ padding: '24px' }}>
            <Routes>
              <Route path="/" element={<ChatInterface />} />
              <Route path="/new-chat" element={<NewChatInterface />} />
              <Route path="/workspaces" element={<WorkspaceManagement />} />
              <Route path="/documents" element={<DocumentManagement />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Router>
  );
};

export default App;

export {}; 