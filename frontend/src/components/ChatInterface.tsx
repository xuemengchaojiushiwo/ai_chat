import React, { useEffect, useState, useRef } from 'react';
import { Box, Grid, GridItem, VStack, Input, Button, Flex, useToast, Text, List, ListItem } from '@chakra-ui/react';
import { Message } from './Message';
import { conversationApi, documentApi } from '../api';
import { Message as MessageType, Conversation, Document } from '../types';
import { MessageList } from './MessageList';

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const toast = useToast();

  // 获取对话列表和文档列表
  useEffect(() => {
    const initData = async () => {
      try {
        // 由于对话功能暂时不需要，我们可以只获取文档列表
        const docs = await documentApi.list();
        setDocuments(docs);

        /* 暂时注释掉对话相关的代码
        const [convs, docs] = await Promise.all([
          conversationApi.list(),
          documentApi.list()
        ]);
        setConversations(convs);
        setDocuments(docs);

        if (convs.length > 0) {
          setCurrentConversationId(convs[0].id);
          const history = await conversationApi.getMessages(convs[0].id);
          setMessages(history);
        } else {
          const newConv = await conversationApi.create('New Chat');
          setCurrentConversationId(newConv.id);
          setConversations([newConv]);
        }
        */
      } catch (error) {
        console.error('Failed to initialize:', error);
        toast({
          title: '初始化失败',
          status: 'error',
          duration: 3000,
        });
      }
    };

    initData();
  }, [toast]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const generateTitle = async (message: string) => {
    try {
      const response = await fetch('/ai_chat/generate_title', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate title');
      }
      
      const data = await response.json();
      return data.title || message;
    } catch (error) {
      console.error('Error generating title:', error);
      // 如果生成失败，使用消息内容作为标题
      return message.length > 20 ? message.substring(0, 20) + '...' : message;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: MessageType = {
      id: Date.now(),
      role: 'user',
      content: input,
      conversation_id: currentConversationId || 0,
      created_at: new Date().toISOString(),
      citations: []
    };

    // 立即显示用户消息
    setMessages(prev => [...prev, userMessage]);
    
    const messageContent = input;
    setInput('');
    setIsLoading(true);

    try {
      // 如果是新对话，先创建对话并生成标题
      if (!currentConversationId) {
        const title = await generateTitle(messageContent);
        const newConv = await conversationApi.create(title);
        setConversations(prev => [newConv, ...prev]);
        setCurrentConversationId(newConv.id);
        userMessage.conversation_id = newConv.id;
      }

      const response = await conversationApi.sendMessage(currentConversationId || userMessage.conversation_id, messageContent);
      setMessages(prev => [...prev, response]);
    } catch (error) {
      setMessages(prev => prev.filter(msg => msg.id !== userMessage.id));
      toast({
        title: '发送消息失败',
        status: 'error',
        duration: 3000,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = async () => {
    // 只清空当前对话，不立即创建新对话
    setCurrentConversationId(null);
    setMessages([]);
  };

  const handleSelectConversation = async (convId: number) => {
    if (convId === currentConversationId) return;
    
    try {
      const history = await conversationApi.getMessages(convId);
      setMessages(history);
      setCurrentConversationId(convId);
    } catch (error) {
      toast({
        title: '加载对话失败',
        status: 'error',
        duration: 3000,
      });
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const response = await documentApi.upload(file);
      // 确保响应包含所需的所有字段
      const newDocument: Document = {
        ...response,
        mime_type: file.type,
        created_at: new Date().toISOString()
      };
      setDocuments(prev => [...prev, newDocument]);
      toast({
        title: '文档上传成功',
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: '文档上传失败',
        status: 'error',
        duration: 3000,
      });
    }
  };

  return (
    <Grid
      h="100vh"
      templateColumns="250px 1fr 250px"
      gap={0}
    >
      {/* 左侧对话列表 */}
      <GridItem borderRight="1px" borderColor="gray.200" bg="gray.50" overflowY="auto">
        <VStack p={4} spacing={4} align="stretch">
          <Button colorScheme="blue" onClick={handleNewChat}>
            新建对话
          </Button>
          <List spacing={2}>
            {conversations.map(conv => (
              <ListItem
                key={conv.id}
                p={2}
                bg={conv.id === currentConversationId ? 'blue.100' : 'transparent'}
                cursor="pointer"
                borderRadius="md"
                _hover={{ bg: 'blue.50' }}
                onClick={() => handleSelectConversation(conv.id)}
              >
                {conv.name}
              </ListItem>
            ))}
          </List>
        </VStack>
      </GridItem>

      {/* 中间对话区域 */}
      <GridItem display="flex" flexDirection="column" maxH="100vh">
        {/* 消息列表区域 */}
        <Box flex="1" overflowY="auto" p={4}>
          <VStack spacing={4} align="stretch">
            {messages.map((message) => (
              <Message
                key={message.id}
                role={message.role}
                content={message.content}
                citations={message.citations}
              />
            ))}
            <div ref={messagesEndRef} />
          </VStack>
        </Box>
        
        {/* 输入区域 - 固定在底部 */}
        <Box p={4} borderTop="1px" borderColor="gray.200" bg="white">
          <form onSubmit={handleSubmit}>
            <Flex gap={2}>
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message..."
                disabled={isLoading}
                bg="white"
              />
              <Button 
                type="submit" 
                colorScheme="blue"
                isLoading={isLoading}
                minW="80px"
              >
                Send
              </Button>
            </Flex>
          </form>
        </Box>
      </GridItem>

      {/* 右侧文档列表 */}
      <GridItem borderLeft="1px" borderColor="gray.200" bg="gray.50" overflowY="auto">
        <VStack p={4} spacing={4} align="stretch">
          <Button as="label" colorScheme="green" cursor="pointer">
            上传文档
            <input
              type="file"
              hidden
              onChange={handleFileUpload}
              accept=".txt,.pdf,.doc,.docx"
            />
          </Button>
          <List spacing={2}>
            {documents.map(doc => (
              <ListItem
                key={doc.id}
                p={2}
                borderRadius="md"
                bg="white"
                border="1px"
                borderColor="gray.200"
              >
                <Text fontSize="sm" noOfLines={1}>{doc.name}</Text>
                <Text fontSize="xs" color="gray.500">{doc.status}</Text>
              </ListItem>
            ))}
          </List>
        </VStack>
      </GridItem>
    </Grid>
  );
};

export default ChatInterface; 