import React from 'react';
import { Box, Text, Tooltip, VStack } from '@chakra-ui/react';

interface Citation {
  text: string;
  document_id: number;
  segment_id: number;
  index: number;
}

interface MessageProps {
  role: string;
  content: string;
  citations?: Citation[];
}

export const Message: React.FC<MessageProps> = ({ role, content, citations = [] }) => {
  // 处理消息内容，将引用标记替换为可点击的组件
  const renderContent = () => {
    if (!citations || citations.length === 0) {
      return <Text whiteSpace="pre-wrap">{content}</Text>;
    }

    // 将内容按引用标记分割
    const parts = content.split(/(\[\d+\])/);
    
    return (
      <Text whiteSpace="pre-wrap">
        {parts.map((part, index) => {
          // 检查是否是引用标记 [数字]
          const match = part.match(/\[(\d+)\]/);
          if (match) {
            const citationIndex = parseInt(match[1]);
            const citation = citations.find(c => c.index === citationIndex);
            
            if (citation) {
              return (
                <Tooltip 
                  key={index}
                  label={
                    <VStack align="start" p={2} maxW="400px">
                      <Text fontSize="sm" fontWeight="bold">引用内容：</Text>
                      <Text fontSize="sm">{citation.text}</Text>
                    </VStack>
                  }
                  placement="top"
                  hasArrow
                  bg="gray.700"
                  color="white"
                >
                  <Box
                    as="span"
                    color="blue.500"
                    cursor="pointer"
                    fontWeight="medium"
                    _hover={{ textDecoration: 'underline' }}
                  >
                    {part}
                  </Box>
                </Tooltip>
              );
            }
          }
          return <span key={index}>{part}</span>;
        })}
      </Text>
    );
  };

  return (
    <Box
      p={4}
      bg={role === 'assistant' ? 'gray.50' : 'white'}
      borderBottom="1px"
      borderColor="gray.200"
    >
      <Text fontWeight="bold" mb={2}>
        {role === 'assistant' ? 'AI Assistant' : 'You'}
      </Text>
      {renderContent()}
    </Box>
  );
}; 