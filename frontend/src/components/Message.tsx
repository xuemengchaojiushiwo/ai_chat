import React from 'react';
import { Box, Text, Tooltip, Link } from '@chakra-ui/react';

interface Citation {
  index: number;
  text: string;
  document_id: number;
  segment_id: number;
  document_name?: string;
}

interface MessageProps {
  role: string;
  content: string;
  citations?: Citation[];
  onViewDocument?: (documentId: number) => void;
}

export const Message: React.FC<MessageProps> = ({ role, content, citations = [], onViewDocument }) => {
  const renderContent = () => {
    if (!citations || citations.length === 0) {
      return <Text whiteSpace="pre-wrap">{content}</Text>;
    }

    // 创建引用映射
    const citationMap = new Map<number, Citation>();
    citations.forEach(citation => {
      citationMap.set(citation.index, citation);
    });

    const parts = content.split(/(\[\d+\])/g);
    
    return (
      <Text whiteSpace="pre-wrap">
        {parts.map((part, index) => {
          const match = part.match(/\[(\d+)\]/);
          if (match) {
            const citationIndex = parseInt(match[1], 10);
            const citation = citationMap.get(citationIndex);
            if (citation) {
              const docName = citation.document_name || `文档 ${citation.document_id}`;
              return (
                <Tooltip 
                  key={index}
                  label={
                    <Box p={2} maxW="400px">
                      <Text fontSize="sm" whiteSpace="pre-wrap">{citation.text}</Text>
                      <Link
                        fontSize="xs"
                        color="blue.300"
                        mt={1}
                        onClick={() => onViewDocument?.(citation.document_id)}
                        cursor="pointer"
                        _hover={{ textDecoration: 'underline' }}
                      >
                        点击查看原文：{docName}
                      </Link>
                    </Box>
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
                    display="inline"
                    onClick={() => onViewDocument?.(citation.document_id)}
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
      width="100%"
    >
      <Text fontWeight="bold" mb={2}>
        {role === 'assistant' ? 'AI Assistant' : 'You'}
      </Text>
      {renderContent()}
    </Box>
  );
}; 