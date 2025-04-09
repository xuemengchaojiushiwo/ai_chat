import asyncio
import logging

import uvicorn

from ai_chat.database import engine, Base

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def main():
    """主函数"""
    try:
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