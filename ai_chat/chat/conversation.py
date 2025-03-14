from typing import List, Optional, Dict
import tiktoken

class ConversationManager:
    def __init__(self, model_name: str = "sf-chat"):
        self.model_name = model_name
        self.max_tokens = 8192  # 默认上下文窗口大小
        # 使用 cl100k_base 编码器，这是最通用的编码器之一
        self.encoding = tiktoken.get_encoding("cl100k_base")
        
    def get_token_count(self, text: str) -> int:
        """计算文本的token数量"""
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            # 如果编码失败，使用简单的估算
            return len(text.split()) * 2  # 简单估算：每个词约2个token
        
    def prepare_messages(self, messages: List[Dict], max_tokens: Optional[int] = None) -> List[Dict]:
        """准备发送给模型的消息列表"""
        if not max_tokens:
            max_tokens = self.max_tokens
            
        preserved_messages = []
        current_tokens = 0
        
        for message in reversed(messages):
            tokens = self.get_token_count(message["content"])
            if current_tokens + tokens <= max_tokens:
                preserved_messages.insert(0, message)
                current_tokens += tokens
            else:
                break
                
        return preserved_messages

    def get_messages_for_completion(self, messages: List[Dict], max_tokens: Optional[int] = None) -> List[Dict]:
        """兼容性方法，调用 prepare_messages"""
        return self.prepare_messages(messages, max_tokens) 