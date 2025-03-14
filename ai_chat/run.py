import uvicorn
import logging
from ai_chat.api.main import app
from ai_chat.database import engine, Base
import asyncio

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_database():
    """初始化数据库"""
    try:
        async with engine.begin() as conn:
            # 创建所有表
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")
            
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

def main():
    """主函数"""
    try:
        # 初始化数据库
        asyncio.run(init_database())
        
        # 启动服务器
        logger.info("Starting server...")
        uvicorn.run(
            "ai_chat.api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["ai_chat"],
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Server startup error: {e}")
        raise

if __name__ == "__main__":
    main() 