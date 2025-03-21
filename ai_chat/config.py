import os
from typing import Optional
from pydantic_settings import BaseSettings

# 数据库配置
DATABASE_URL = "sqlite:///./ai_chat.db"

# Silicon Flow API 配置
SF_API_KEY = "sk-jncftpdfzxaffluqbhswlnkureqgxnctjlbyrvelhwrvwxli"  # 恢复原来的格式
SF_API_BASE = "https://api.siliconflow.com/v1"
SF_EMBEDDING_URL = f"{SF_API_BASE}/embeddings"
SF_CHAT_URL = f"{SF_API_BASE}/chat/completions"

# 模型配置
CHAT_MODEL = "Qwen/QwQ-32B"
EMBEDDING_MODEL = "BAAI/bge-m3"

# 向量搜索配置
VECTOR_SIMILARITY_THRESHOLD = 0.7
MAX_CONTEXT_SEGMENTS = 5

# OpenAI API 配置
OPENAI_API_KEY = ""  # 需要设置你的 API key
OPENAI_API_BASE = "https://api.openai.com"

class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = DATABASE_URL
    
    # Silicon Flow API 配置
    SF_API_KEY: str = SF_API_KEY
    SF_API_BASE: str = SF_API_BASE
    SF_EMBEDDING_URL: str = SF_EMBEDDING_URL
    SF_CHAT_URL: str = SF_CHAT_URL
    
    # 模型配置
    CHAT_MODEL: str = CHAT_MODEL
    EMBEDDING_MODEL: str = EMBEDDING_MODEL
    
    # 向量搜索配置
    VECTOR_SIMILARITY_THRESHOLD: float = VECTOR_SIMILARITY_THRESHOLD
    MAX_CONTEXT_SEGMENTS: int = MAX_CONTEXT_SEGMENTS
    
    # OpenAI API 配置
    OPENAI_API_KEY: str = OPENAI_API_KEY
    OPENAI_API_BASE: str = OPENAI_API_BASE
    
    # 应用配置
    DEBUG: bool = True
    
    class Config:
        case_sensitive = True

# 直接设置环境变量
os.environ['SF_API_KEY'] = 'sk-jncftpdfzxaffluqbhswlnkureqgxnctjlbyrvelhwrvwxli'  # 恢复原来的格式
os.environ['DATABASE_URL'] = 'sqlite:///./ai_chat.db'

settings = Settings() 