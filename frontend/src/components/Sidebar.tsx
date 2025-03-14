import React from 'react';
import { Conversation } from '../types';

interface SidebarProps {
  conversations: Conversation[] | undefined | null;
  currentConversation: number | null;
  onSelectConversation: (id: number) => void;
  onNewConversation: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  currentConversation,
  onSelectConversation,
  onNewConversation,
}) => {
  return (
    <div className="w-64 bg-gray-800 text-white flex flex-col">
      {/* 新建对话按钮 */}
      <div className="p-4">
        <button
          onClick={onNewConversation}
          className="w-full py-2 bg-blue-500 hover:bg-blue-600 rounded-lg flex items-center justify-center space-x-2"
        >
          <span>+</span>
          <span>新建对话</span>
        </button>
      </div>

      {/* 对话列表 */}
      <div className="flex-1 overflow-y-auto">
        {Array.isArray(conversations) && conversations.length > 0 ? (
          conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => onSelectConversation(conv.id)}
              className={`p-4 cursor-pointer hover:bg-gray-700 ${
                currentConversation === conv.id ? 'bg-gray-700' : ''
              }`}
            >
              <div className="font-medium truncate">{conv.name}</div>
              <div className="text-sm text-gray-400">
                {new Date(conv.created_at).toLocaleDateString()}
              </div>
            </div>
          ))
        ) : (
          <div className="p-4 text-gray-400 text-center">
            暂无对话记录
          </div>
        )}
      </div>
    </div>
  );
}; 