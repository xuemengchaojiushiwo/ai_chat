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

# 轨迹流动 API 配置
SF_API_KEY = "sk-jncftpdfzxaffluqbhswlnkureqgxnctjlbyrvelhwrvwxli"
SF_API_BASE = "https://api.siliconflow.com/v1"
SF_EMBEDDING_URL = f"{SF_API_BASE}/embeddings"
SF_CHAT_URL = f"{SF_API_BASE}/chat/completions"

# 极客智坊 API 配置
GEEKAI_API_KEY = "sk-riZoibcXcgVzPr2SPdFMCUJduCoMZMibASf2yvFBwwNLQIky"
GEEKAI_API_BASE = "https://geekai.co/api/v1"
GEEKAI_EMBEDDING_URL = f"{GEEKAI_API_BASE}/embeddings"
GEEKAI_CHAT_URL = f"{GEEKAI_API_BASE}/chat/completions"

# 模型配置
CHAT_MODEL = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
SF_EMBEDDING_MODEL = "Pro/BAAI/bge-m3"  # 轨迹流动的嵌入模型
GEEKAI_EMBEDDING_MODEL = "gemini-embedding-exp-03-07"  # 极客智坊的嵌入模型

# 向量搜索配置
VECTOR_SIMILARITY_THRESHOLD = 0.5  # 向量搜索相似度阈值
MAX_CONTEXT_SEGMENTS = 5
SIMILARITY_THRESHOLD = 0.5  # 相似度阈值

# OpenAI API 配置
OPENAI_API_KEY = "sk-riZoibcXcgVzPr2SPdFMCUJduCoMZMibASf2yvFBwwNLQIky"
OPENAI_API_BASE = "https://geekai.co/api/v1"
OPENAI_EMBEDDING_URL = f"{OPENAI_API_BASE}/embeddings"
EMBEDDING_MODEL = "text-embedding-3-small"

# 文档处理配置
DOCUMENT_PROCESSING = {
    "max_segment_length": 500,  # 每个段落的最大字符数
    "overlap_length": 50,       # 段落之间的重叠字符数
    "min_segment_length": 100,   # 最小段落长度
    "max_segments_per_page": 10 # 每页最大段落数
}

# 向量检索配置
VECTOR_RETRIEVAL = {
    "similarity_threshold": 0.3,  # 相似度阈值
    "max_results": 5,            # 最大返回结果数
    "min_similarity": 0.1        # 最小相似度
}

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
    
    # 轨迹流动 API 配置
    SF_API_KEY: str = SF_API_KEY
    SF_API_BASE: str = SF_API_BASE
    SF_EMBEDDING_URL: str = SF_EMBEDDING_URL
    SF_CHAT_URL: str = SF_CHAT_URL
    
    # 极客智坊 API 配置
    GEEKAI_API_KEY: str = GEEKAI_API_KEY
    GEEKAI_API_BASE: str = GEEKAI_API_BASE
    GEEKAI_EMBEDDING_URL: str = GEEKAI_EMBEDDING_URL
    GEEKAI_CHAT_URL: str = GEEKAI_CHAT_URL
    
    # 模型配置
    CHAT_MODEL: str = CHAT_MODEL
    SF_EMBEDDING_MODEL: str = SF_EMBEDDING_MODEL
    GEEKAI_EMBEDDING_MODEL: str = GEEKAI_EMBEDDING_MODEL
    
    # 向量搜索配置
    VECTOR_SIMILARITY_THRESHOLD: float = VECTOR_SIMILARITY_THRESHOLD
    MAX_CONTEXT_SEGMENTS: int = MAX_CONTEXT_SEGMENTS
    SIMILARITY_THRESHOLD: float = SIMILARITY_THRESHOLD
    
    # OpenAI API 配置
    OPENAI_API_KEY: str = OPENAI_API_KEY
    OPENAI_API_BASE: str = OPENAI_API_BASE
    OPENAI_EMBEDDING_URL: str = OPENAI_EMBEDDING_URL
    EMBEDDING_MODEL: str = EMBEDDING_MODEL
    
    # 应用配置
    DEBUG: bool = True
    
    # 文档处理配置
    DOCUMENT_PROCESSING: dict = DOCUMENT_PROCESSING
    
    # 向量检索配置
    VECTOR_RETRIEVAL: dict = VECTOR_RETRIEVAL
    
    class Config:
        case_sensitive = True

# 直接设置环境变量
os.environ['SF_API_KEY'] = SF_API_KEY
os.environ['GEEKAI_API_KEY'] = GEEKAI_API_KEY
os.environ['DATABASE_URL'] = DATABASE_URL

settings = Settings() 