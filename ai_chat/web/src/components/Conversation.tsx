import React, { useEffect, useRef } from 'react';
import { Box, VStack, Input, Button, Flex } from '@chakra-ui/react';
import { Message } from './Message';

interface Citation {
  text: string;
  document_id: number;
  segment_id: number;
  index: number;
}

interface MessageType {
  id: number;
  role: string;
  content: string;
  citations: Citation[];
  created_at: string;
}

interface ConversationProps {
  messages: MessageType[];
  onSendMessage: (message: string) => void;
}

export const Conversation: React.FC<ConversationProps> = ({ messages, onSendMessage }) => {
  const [input, setInput] = React.useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      onSendMessage(input);
      setInput('');
    }
  };

  return (
    <Box h="100%" display="flex" flexDirection="column">
      <VStack flex="1" overflowY="auto" spacing={0} align="stretch">
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
      
      <Box p={4} borderTop="1px" borderColor="gray.200">
        <form onSubmit={handleSubmit}>
          <Flex gap={2}>
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
            />
            <Button type="submit" colorScheme="blue">
              Send
            </Button>
          </Flex>
        </form>
      </Box>
    </Box>
  );
}; 