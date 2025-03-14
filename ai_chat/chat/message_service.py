from typing import List, Dict, Optional
from datetime import datetime
from .conversation import ConversationManager

class MessageService:
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.conversation_manager = ConversationManager(model_name)
        self.messages = []
        
    def add_message(self, role: str, content: str) -> dict:
        """Add a new message to the conversation"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.messages.append(message)
        return message
        
    def get_messages_for_completion(self, max_tokens: Optional[int] = None) -> List[dict]:
        """Get messages prepared for API completion"""
        if max_tokens is None:
            max_tokens = self.conversation_manager.max_tokens
            
        return self.conversation_manager.prepare_messages(
            self.messages,
            max_tokens
        )
        
    def clear_messages(self):
        """Clear all messages except system message"""
        system_message = next(
            (msg for msg in self.messages if msg["role"] == "system"),
            None
        )
        self.messages = [system_message] if system_message else [] 