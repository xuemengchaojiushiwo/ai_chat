import React, { useState } from 'react';
import { Message } from '../types';

interface MessageListProps {
  messages: Message[];
}

export const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  const [hoveredCitation, setHoveredCitation] = useState<string | null>(null);

  const renderMessageContent = (message: Message) => {
    if (!message.citations || message.citations.length === 0) {
      return <p className="whitespace-pre-wrap">{message.content}</p>;
    }

    // 将引用标记替换为可交互的span
    let content = message.content;
    message.citations.forEach((citation, index) => {
      const citationMark = `[${index + 1}]`;
      content = content.replace(
        citationMark,
        `<span 
          class="citation-mark text-blue-500 cursor-pointer hover:text-blue-700" 
          data-citation="${citation}"
        >${citationMark}</span>`
      );
    });

    return (
      <div className="relative">
        <p 
          className="whitespace-pre-wrap"
          dangerouslySetInnerHTML={{ __html: content }}
          onClick={(e) => {
            const target = e.target as HTMLElement;
            if (target.classList.contains('citation-mark')) {
              setHoveredCitation(target.getAttribute('data-citation'));
            }
          }}
        />
        {hoveredCitation && (
          <div 
            className="absolute z-10 p-4 bg-white border rounded-lg shadow-lg max-w-md"
            style={{ top: '100%', left: '0' }}
          >
            <p className="text-sm text-gray-700">{hoveredCitation}</p>
            <button 
              className="absolute top-1 right-1 text-gray-500 hover:text-gray-700"
              onClick={() => setHoveredCitation(null)}
            >
              ✕
            </button>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`p-4 rounded-lg ${
            message.role === 'assistant'
              ? 'bg-blue-50 ml-4'
              : 'bg-gray-50 mr-4'
          }`}
        >
          <div className="text-sm text-gray-500 mb-2">
            {message.role === 'assistant' ? 'AI' : '你'}
          </div>
          {renderMessageContent(message)}
        </div>
      ))}
    </div>
  );
}; 