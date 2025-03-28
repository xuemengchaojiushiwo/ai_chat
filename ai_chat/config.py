import os
from typing import Optional
from pydantic_settings import BaseSettings

# MySQL数据库配置
MYSQL_USER = "root"
MYSQL_PASSWORD = "xmc131455"
MYSQL_HOST = "localhost"
MYSQL_PORT = "3306"
MYSQL_DATABASE = "ai_chat"
DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4&use_unicode=1&local_infile=1"

# Chroma配置
CHROMA_PERSIST_DIRECTORY = "./chroma_db"
COLLECTION_NAME = "document_embeddings"

# Silicon Flow API 配置
SF_API_KEY = "sk-jncftpdfzxaffluqbhswlnkureqgxnctjlbyrvelhwrvwxli"  # 恢复原来的格式
SF_API_BASE = "https://api.siliconflow.com/v1"
SF_EMBEDDING_URL = f"{SF_API_BASE}/embeddings"
SF_CHAT_URL = f"{SF_API_BASE}/chat/completions"

# 模型配置
CHAT_MODEL = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
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
    MYSQL_USER: str = MYSQL_USER
    MYSQL_PASSWORD: str = MYSQL_PASSWORD
    MYSQL_HOST: str = MYSQL_HOST
    MYSQL_PORT: str = MYSQL_PORT
    MYSQL_DATABASE: str = MYSQL_DATABASE
    
    # Chroma配置
    CHROMA_PERSIST_DIRECTORY: str = CHROMA_PERSIST_DIRECTORY
    COLLECTION_NAME: str = COLLECTION_NAME
    
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
os.environ['DATABASE_URL'] = DATABASE_URL

settings = Settings() 